"""Local JWT, serialization and SIGKILL/disk-loss tests; no real campaign writes."""
import asyncio
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import mcp_adapter as adapter
from worktree_guard import WorktreeGuard
import test_mcp_adapter as fixture
import test_shared_store as shared
from test_gateway import Base, INSPECT, HOLSTER, QA, ledger
import staging
ISSUER='https://genesis-test.auth0.com/'
RESOURCE='https://genesis.example.invalid/mcp'
CLIENTS={'chatgpt-client':'gpt-session','gemini-client':'gemini-session'}

class JWT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    def verifier(self):
        key=self.key.public_key()
        class Keys:
            def get_signing_key_from_jwt(self,token):return type('Key',(),{'key':key})()
        return adapter.JWTVerifier(ISSUER,RESOURCE,CLIENTS,fixture.SUBJECT,key_client=Keys())
    def token(self,**changes):
        claims=dict(iss=ISSUER,aud=RESOURCE,sub=fixture.SUBJECT,azp='chatgpt-client',iat=int(time.time()),exp=int(time.time())+300,scope='genesis:read genesis:gm')
        claims.update(changes)
        return jwt.encode(claims,self.key,algorithm='RS256',headers={'kid':'test-key'})
    def test_signature_owner_issuer_audience_times_scopes_and_client_binding(self):
        for client,provider in CLIENTS.items():
            out=asyncio.run(self.verifier().verify_token(self.token(azp=client)))
            self.assertEqual(out.claims['provider'],provider)
        for changes in ({'sub':'other-owner'},{'iss':'https://attacker.invalid/'},{'aud':'other-api'},{'exp':1},{'iat':int(time.time())+300},{'nbf':int(time.time())+300},{'azp':'unregistered-client'},{'scope':'genesis:gm'}):
            with self.subTest(changes=changes):self.assertIsNone(asyncio.run(self.verifier().verify_token(self.token(**changes))))
        bad=jwt.encode({'sub':fixture.SUBJECT},'owner-login-is-not-the-server-signing-key',algorithm='HS256')
        self.assertIsNone(asyncio.run(self.verifier().verify_token(bad)))
    def test_opaque_authorization_code_never_accepted_before_or_after_restart(self):
        # One-time code exchange is owned by Auth0, not by this resource server.
        for _ in range(2):self.assertIsNone(asyncio.run(self.verifier().verify_token('previously-used-authorization-code')))
        self.assertIsNotNone(asyncio.run(self.verifier().verify_token(self.token())))
    def test_jwks_failure_closes_access_and_endpoint_is_fixed(self):
        v=self.verifier()
        with patch.object(v.keys,'get_signing_key_from_jwt',side_effect=jwt.PyJWKClientError('private upstream text')):self.assertIsNone(asyncio.run(v.verify_token(self.token())))
        with patch('mcp_adapter.jwt.PyJWKClient') as keys:
            adapter.JWTVerifier(ISSUER,RESOURCE,CLIENTS,fixture.SUBJECT)
            keys.assert_called_once_with(ISSUER+'.well-known/jwks.json',timeout=5)
        for url in ('http://host/mcp','https://user:secret@host/mcp','https://host/mcp?token=secret'):
            with self.assertRaises(ValueError):adapter.https_url(url)

class BoundSessions(Base):
    def setUp(self):
        super().setUp();self.tools=fixture.tools(self.gw)
        self.tools.app.gm_tokens['gemini-session']='test-server-gemini-token'
    def test_both_sessions_read_identical_public_revision_and_digest(self):
        action,_=self.act(HOLSTER,provider='gpt-session');outputs=[]
        for provider in ('gpt-session','gemini-session'):
            token=fixture.access();token.claims={'provider':provider}
            with patch('mcp_adapter.get_access_token',return_value=token):
                out=self.tools.read('refresh');self.assertEqual(out['connection_provider'],provider)
                self.assertNotIn('state',out['public']);cursor=out['public']['cursor']
                same=self.tools.read('refresh',known_revision=cursor['revision'],known_ledger_head=cursor['ledger_head'],known_public_sha256=cursor['public_sha256']);self.assertFalse(same['changed'])
                with self.assertRaises(adapter.Refused):self.tools.read('refresh',known_revision=cursor['revision']+1)
                with self.assertRaises(adapter.Refused):self.tools.read('refresh',known_revision=cursor['revision'],known_ledger_head='wrong-head')
                self.assertIn('state',self.tools.read('refresh',include_full_state=True)['public']);outputs.append(cursor)
        self.assertEqual(*outputs);self.assertEqual(self.gw.action_status(action['action_id'])['status'],'submitted')
    def test_provider_is_bound_to_token_not_model_or_session(self):
        self.act(HOLSTER,provider='gemini-session')
        with patch('mcp_adapter.get_access_token',return_value=fixture.access()):
            out=self.tools.gm('claim','run',model='gemini-session',session='gemini-session')
            self.assertEqual(out['result']['error']['code'],'NOT_ROUTED_HERE')
        token=fixture.access();token.claims={'provider':'gemini-session'}
        with patch('mcp_adapter.get_access_token',return_value=token):self.assertEqual(self.tools.gm('claim','gemini-run',model='gpt-session',session='chatgpt')['http_status'],200)
        self.assertEqual(self.gw._lock()[1]['provider'],'gemini-session')

    def test_real_tcp_mcp_refresh_from_two_distinct_oauth_clients(self):
        import httpx,threading,uvicorn
        signer=JWT();signer.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.tools.writes=False
        server=adapter.create_server(self.tools,signer.verifier(),ISSUER,RESOURCE)
        live=uvicorn.Server(uvicorn.Config(server.streamable_http_app(),host='127.0.0.1',port=0,log_level='error',access_log=False))
        thread=threading.Thread(target=live.run,daemon=True);thread.start()
        try:
            deadline=time.monotonic()+5
            while not live.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(live.started)
            port=live.servers[0].sockets[0].getsockname()[1]
            headers={'accept':'application/json, text/event-stream','mcp-protocol-version':'2025-11-25'}
            cursors=[]
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as client:
                for client_id,provider in CLIENTS.items():
                    headers['authorization']='Bearer '+signer.token(azp=client_id)
                    headers['origin']='https://chatgpt.com' if provider=='gpt-session' else 'https://gemini.google.com'
                    init={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':client_id,'version':'test'}}}
                    self.assertEqual(client.post('/mcp',headers=headers,json=init).status_code,200)
                    listing=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}).json()['result']['tools']
                    self.assertTrue(all(t['annotations']['readOnlyHint'] for t in listing))
                    self.assertNotIn('genesis_context',{t['name'] for t in listing})
                    response=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'genesis_refresh','arguments':{}}})
                    self.assertEqual(response.status_code,200)
                    out=response.json()['result']['structuredContent']
                    self.assertEqual(out['connection_provider'],provider);cursors.append(out['public']['cursor'])
                    for private in ('CANARY','recent_private','test-server-gemini-token'):self.assertNotIn(private,response.text)
            self.assertEqual(*cursors)
        finally:live.should_exit=True;thread.join(timeout=5)

class Serialization(unittest.TestCase):
    def test_two_processes_serialize_and_killed_holder_releases_kernel_lock(self):
        QA.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=QA) as temp:
            path=Path(temp)/'operation.lock';log=Path(temp)/'order.jsonl'
            source="""import json,sys,time
from worktree_guard import WorktreeGuard
with WorktreeGuard(sys.argv[1]):
 with open(sys.argv[2],'a') as f:f.write(json.dumps([sys.argv[3],'enter'])+'\\n');f.flush()
 time.sleep(0.15)
 with open(sys.argv[2],'a') as f:f.write(json.dumps([sys.argv[3],'exit'])+'\\n')
"""
            env=dict(__import__('os').environ,PYTHONPATH=str(HERE))
            workers=[subprocess.Popen([sys.executable,'-c',source,str(path),str(log),n],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for n in ('a','b')]
            for worker in workers:worker.communicate(timeout=10);self.assertEqual(worker.returncode,0)
            rows=[json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([r[1] for r in rows],['enter','exit','enter','exit']);self.assertEqual(rows[0][0],rows[1][0]);self.assertEqual(rows[2][0],rows[3][0])
            holder=subprocess.Popen([sys.executable,'-u','-c',"import sys,time;from worktree_guard import WorktreeGuard\nwith WorktreeGuard(sys.argv[1]):\n print('held',flush=True);time.sleep(10)",str(path)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:self.assertEqual(holder.stdout.readline().strip(),'held')
            finally:holder.kill();holder.communicate(timeout=5)
            with WorktreeGuard(path):pass
    def test_generation_survives_restart_but_disk_loss_requires_reapproval(self):
        with tempfile.TemporaryDirectory(dir=QA) as temp:
            path=Path(temp)/'operation.lock';first=WorktreeGuard(path)
            self.assertFalse(WorktreeGuard(path,first.generation).recovery_required)
            path.with_suffix('.generation.json').unlink();lost=WorktreeGuard(path,first.generation)
            self.assertTrue(lost.recovery_required);self.assertNotEqual(lost.generation,first.generation)

CHILD=r'''
import json,os,signal,subprocess,sys
from pathlib import Path
import staging
from service import App
from mcp_adapter import GatewayTools
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from test_mcp_adapter import access,SUBJECT
from test_gateway import script
gw=staging.open_shared(sys.argv[1],min_sync_s=0)
tool=GatewayTools(App({gw.id:gw},{},None,gm_tokens={'gpt-session':'test-only-server-token'}),gw.id,SUBJECT,writes=True)
auth_context_var.set(AuthenticatedUser(access()))
assert tool.gm('claim','recovery-run')['http_status']==200
ctx=tool.gm('context','recovery-run')['result'];move=script('gpt-session').step(ctx)
assert tool.gm('tables','recovery-run',move['tables'])['http_status']==200
ctx=tool.gm('context','recovery-run')['result'];request=script('gpt-session').step(ctx)['rolls'][0]
mode=sys.argv[2];observed=Path(sys.argv[3]);real=gw._save_op
def save(op):
 if op['rolls']:
  observed.write_text(json.dumps({'request':request,'result':next(iter(op['rolls'].values()))['result']}))
  if mode=='before-push':os.kill(os.getpid(),signal.SIGKILL)
  if mode=='lost-ack':
   run=gw.store._run
   def dropped(args,**kwargs):
    out=run(args,**kwargs)
    if len(args)>1 and args[1]=='push' and out.returncode==0:return subprocess.CompletedProcess(args,128,'','fatal: Connection reset by peer')
    return out
   gw.store._run=dropped
   try:real(op)
   finally:os.kill(os.getpid(),signal.SIGKILL)
 return real(op)
gw._save_op=save
tool.gm('roll','recovery-run',request)
os.kill(os.getpid(),signal.SIGKILL)
'''

class DiskRecovery(unittest.TestCase):
    setUp=shared.Shared.setUp
    tearDown=shared.Shared.tearDown
    clone=shared.Shared.clone
    session=shared.Shared.session
    def scenario(self,phase,lose_disk):
        action=staging.declare(self.player,'recovery-0001',text=INSPECT,provider='gpt-session');self.player.submit(action)
        root=self.clone('server');scope=root/'staging/env';observed=self.root/'observed.json'
        env=dict(__import__('os').environ,PYTHONPATH=str(HERE),PYTHONDONTWRITEBYTECODE='1')
        child=subprocess.run([sys.executable,'-c',CHILD,str(scope),phase,str(observed)],env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(child.returncode,-9,'Child must stop abruptly at the requested boundary')
        expected=json.loads(observed.read_text())
        if lose_disk:shutil.rmtree(root);root=self.clone('restored');scope=root/'staging/env'
        gw=staging.open_shared(scope,min_sync_s=0);tool=fixture.tools(gw);token=auth_context_var.set(AuthenticatedUser(fixture.access()))
        try:
            result=tool.gm('roll','recovery-run',expected['request']);self.assertEqual(result['http_status'],200)
            self.assertEqual(result['result']['result'],expected['result'])
            if phase!='before-push':self.assertTrue(result['result']['replayed'])
            again=tool.gm('roll','recovery-run',expected['request']);self.assertTrue(again['result']['replayed'])
            self.assertEqual(result['result']['result'],again['result']['result'])
            rows=[r for r in ledger.read_jsonl(gw.campaign/'records/roll_log.jsonl') if action['action_id'] in r['purpose']];self.assertEqual(len(rows),1)
        finally:auth_context_var.reset(token)
    def test_process_restart_after_local_dice_write_before_push(self):self.scenario('before-push',False)
    def test_complete_disk_loss_before_unacknowledged_push(self):self.scenario('before-push',True)
    def test_complete_disk_loss_after_accepted_roll(self):self.scenario('accepted',True)
    def test_complete_disk_loss_after_server_accepts_but_ack_is_lost(self):self.scenario('lost-ack',True)

    def test_disk_loss_during_partial_batch_uses_remotely_accepted_plan(self):
        import gateway as module
        from runner import run_turn
        from test_gateway import script
        action=staging.declare(self.player,'batch-loss-0001',text=INSPECT,provider='gpt-session')
        self.player.submit(action);first=self.session('batch-server');real=module.batch.apply
        def torn(campaign,request,lock,run,led,after_stream=None):
            def crash(_):raise RuntimeError('test process interruption')
            return real(campaign,request,lock,run,led,after_stream=crash)
        with patch.object(module.batch,'apply',side_effect=torn):
            with self.assertRaises(RuntimeError):run_turn(first,script('gpt-session'),run='batch-run')
        accepted=first._op(action['action_id'])['commit']['fingerprint']
        shutil.rmtree(first.store.repo)
        recovered=self.session('batch-restored')
        out=run_turn(recovered,script('gpt-session',lambda *_:self.fail('Recovery cannot ask a GM to re-author')),run='batch-run')
        self.assertEqual((out['outcome'],out['authored']),('committed',False))
        self.assertEqual(recovered._op(action['action_id'])['commit']['fingerprint'],accepted)
        self.assertFalse(ledger.validate_all(recovered.campaign)[1])

    def test_render_boot_preserves_dirty_or_ahead_work_and_fresh_clone_recovers(self):
        spec=importlib.util.spec_from_file_location('render_boot',HERE/'deploy/start.py')
        boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
        data=self.root/'render-disk';remote=str(self.root/'origin.git')
        def prepare():return boot.prepare(data,repository=remote,branch='staging',scope_relative='staging/env',campaign_id='shared-test')
        scope=prepare();repo=data/'authority';before=shared.git(repo,'rev-parse','HEAD')
        self.assertEqual(prepare(),scope);self.assertEqual(shared.git(repo,'rev-parse','HEAD'),before)
        file=repo/'unaccepted.txt';file.write_text('preserve local-only work')
        with self.assertRaises(ValueError):prepare()
        self.assertTrue(file.exists())
        shared.git(repo,'add','unaccepted.txt');shared.git(repo,'-c','user.name=test','-c','user.email=t@invalid','commit','--quiet','-m','unconfirmed')
        ahead=shared.git(repo,'rev-parse','HEAD')
        with self.assertRaises(ValueError):prepare()
        self.assertEqual(shared.git(repo,'rev-parse','HEAD'),ahead)

if __name__=='__main__':unittest.main()
