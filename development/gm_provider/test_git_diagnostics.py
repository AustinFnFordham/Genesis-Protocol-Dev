"""Failure classification and CAS regressions. Local bare remotes and test doubles only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from git_errors import diagnostic, sanitize, GitFailure
from store import GitStore, GitRefConflict, Conflict
from gateway import Refused
import gmctl
from runner import run_turn
from test_gateway import Base, HOLSTER, script, QA

CASES = [
    (128, "fatal: could not read Username for 'https://user:secret@github.com/private': terminal prompts disabled", "authentication_or_permission", "GIT_AUTH_OR_PERMISSION"),
    (1, "remote: Permission to org/repo.git denied to a-user.", "authentication_or_permission", "GIT_AUTH_OR_PERMISSION"),
    (1, "remote: GH006: Protected branch update failed for refs/heads/staging.", "protected_branch", "GIT_PROTECTED_BRANCH"),
    (1, "remote: error: GH013: Repository rule violations found for refs/heads/staging.", "protected_branch", "GIT_PROTECTED_BRANCH"),
    (128, "fatal: unable to access 'https://u:secret@example.invalid/repo': Could not resolve host: example.invalid", "transport", "GIT_TRANSPORT"),
    (1, " ! [rejected] HEAD -> staging (non-fast-forward)", "stale_ref", "GIT_STALE_REF"),
    (1, "error: cannot lock ref 'refs/heads/staging': is at abc123 but expected def456", "stale_ref", "GIT_STALE_REF"),
    (1, "remote: pre-receive hook declined", "remote_hook_rejected", "GIT_HOOK_REJECTED"),
    (1, "error: failed to push some refs to 'https://u:secret@example.invalid/repo'", "unknown", "GIT_FAILED"),
]


def failure(code, stderr):
    details = diagnostic("push", code, stderr)
    return (GitRefConflict if details["classification"] == "stale_ref" else GitFailure)(details)


class Diagnostics(unittest.TestCase):
    def test_failure_classes_preserve_exit_code(self):
        for code, stderr, category, expected in CASES:
            with self.subTest(category=category, stderr_index=CASES.index((code,stderr,category,expected))):
                error = failure(code, stderr)
                self.assertEqual(error.details["exit_code"], code)
                self.assertEqual(error.details["classification"], category)
                self.assertEqual(error.code, expected)
                self.assertNotEqual(error.code, "PROVIDER_BUSY")

    def test_sanitization_omits_credentials_urls_and_private_hook_context(self):
        raw = "\x1b[31mfatal: Authentication failed for 'https://name:ghp_SUPERSECRET@host/repo?token=QUERYSECRET'\x1b[0m\n"
        raw += "Authorization: Bearer HEADERSECRET\npassword=PLAINSECRET\nremote: PRIVATE_GM_CANARY hidden intention\n"
        raw += "remote: GH006: Protected branch update failed for refs/heads/x PRIVATE_GM_INLINE\n"
        raw += "remote: ssh://name:OTHERSECRET@host/repo git@host:private/repo github_pat_TOKENVALUE\n"
        result = sanitize(raw)
        for secret in ("SUPERSECRET","QUERYSECRET","HEADERSECRET","PLAINSECRET","PRIVATE_GM_CANARY","PRIVATE_GM_INLINE","OTHERSECRET","TOKENVALUE","https://","ssh://","git@host"):
            self.assertNotIn(secret, result)
        self.assertIn("Authentication failed", result)
        self.assertIn("Protected branch update failed", result)
        self.assertIn("omitted", result)

    def test_timeout_has_no_fabricated_exit_code(self):
        value = diagnostic("push", None, b"private hook text", timed_out=True)
        self.assertEqual(value["classification"], "transport")
        self.assertIsNone(value["exit_code"])
        self.assertEqual(value["remote_outcome"], "unknown")

    def test_cli_initialization_reports_sanitized_failure(self):
        error = failure(128, CASES[0][1])
        output = io.StringIO()
        with patch("staging.open_shared", side_effect=error), contextlib.redirect_stdout(output):
            self.assertEqual(gmctl.main(["--shared","unused","recovery"]), 3)
        result = json.loads(output.getvalue())
        self.assertEqual(result["error"]["git"]["exit_code"], 128)
        self.assertEqual(result["error"]["code"], "GIT_AUTH_OR_PERMISSION")
        self.assertNotIn("secret", output.getvalue())


class LocalGit(unittest.TestCase):
    def setUp(self):
        QA.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="git-diagnostics-", dir=QA)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git(self.root,"init","--quiet","--bare","-b","staging","origin.git")
        self.git(self.root,"clone","--quiet",str(self.root/"origin.git"),"clone")
        self.repo = self.root/"clone"
        self.scope = self.repo/"staging/env"
        document = self.scope/"store/locks/test.json"
        document.parent.mkdir(parents=True)
        document.write_text(json.dumps({"version":1,"data":{"holder":None,"expires_ms":0}}))
        self.git(self.repo,"add","-A")
        self.git(self.repo,"-c","user.name=t","-c","user.email=t@invalid","commit","--quiet","-m","seed")
        self.git(self.repo,"push","--quiet","origin","HEAD:staging")
        self.store = GitStore(self.scope, min_sync_s=0)
        self.head = self.git(self.repo,"rev-parse","HEAD").strip()
        self.before = document.read_bytes()
        self.document = document

    def git(self, cwd, *args):
        result = subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True)
        if result.returncode:
            self.fail(json.dumps(diagnostic("test-git",result.returncode,result.stderr,result.stdout)))
        return result.stdout

    def intercept(self, callback):
        real = self.store._run
        self.commands = []
        def run(args, **kwargs):
            self.commands.append(args)
            if len(args)>1 and args[1]=="push":
                return callback(real,args,kwargs)
            return real(args, **kwargs)
        self.store._run = run

    def test_definitive_rejections_restore_only_the_unaccepted_local_write(self):
        for code, stderr, category, expected in CASES:
            if category not in ("authentication_or_permission","protected_branch","stale_ref","remote_hook_rejected"):
                continue
            with self.subTest(category=category):
                self.intercept(lambda real,args,kwargs: subprocess.CompletedProcess(args,code,"",stderr))
                with self.assertRaises(GitFailure) as caught:
                    self.store.put("locks/test", {"holder":"candidate","expires_ms":99999}, 1)
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(caught.exception.details["exit_code"], code)
                self.assertTrue(caught.exception.details["local_commit_reverted"])
                self.assertEqual(self.git(self.repo,"rev-parse","HEAD").strip(), self.head)
                self.assertEqual(self.document.read_bytes(), self.before)
                self.assertEqual(self.git(self.root/"origin.git","rev-parse","refs/heads/staging").strip(), self.head)
                self.assertFalse(any("--force" in a or "--force-with-lease" in a for a in self.commands))

    def test_uncertain_network_push_keeps_local_work_and_fences_new_writes(self):
        self.intercept(lambda real,args,kwargs: subprocess.CompletedProcess(args,128,"","fatal: Connection reset by peer"))
        with self.assertRaises(GitFailure) as caught:
            self.store.put("locks/test", {"holder":"candidate","expires_ms":99999}, 1)
        self.assertEqual(caught.exception.code,"GIT_TRANSPORT")
        self.assertFalse(caught.exception.details["local_commit_reverted"])
        self.assertNotEqual(self.git(self.repo,"rev-parse","HEAD").strip(), self.head)
        self.assertEqual(self.git(self.root/"origin.git","rev-parse","refs/heads/staging").strip(), self.head)
        fresh = GitStore(self.scope)
        # A failed sync must not populate the success cache and let the second
        # read expose an unconfirmed local lease.
        for _ in range(2):
            with self.assertRaises(GitFailure) as unreadable:
                fresh.read("locks/test")
            self.assertEqual(unreadable.exception.code,"GIT_SYNC_REQUIRED")
        with self.assertRaises(GitFailure) as fenced:
            fresh.put("locks/test", {"holder":"another"}, 1)
        self.assertEqual(fenced.exception.code,"GIT_SYNC_REQUIRED")

    def test_lost_push_ack_does_not_erase_a_lease_accepted_by_the_remote(self):
        def accepted_then_disconnected(real,args,kwargs):
            out = real(args,**kwargs)
            self.assertEqual(out.returncode,0)
            return subprocess.CompletedProcess(args,128,"","fatal: Connection reset by peer")
        self.intercept(accepted_then_disconnected)
        with self.assertRaises(GitFailure):
            self.store.put("locks/test", {"holder":"accepted","expires_ms":99999}, 1)
        self.assertNotEqual(self.git(self.root/"origin.git","rev-parse","refs/heads/staging").strip(), self.head)
        version, data = self.store.read("locks/test")
        self.assertEqual((version,data["holder"]),(2,"accepted"))
        self.assertEqual(len([a for a in self.commands if a[1]=="push"]),1)

    def test_push_timeout_keeps_work_and_redacts_partial_output(self):
        def timeout(real,args,kwargs):
            raise subprocess.TimeoutExpired(args,30,stderr=b"fatal: Authentication failed for 'https://a:secret@host/repo'\nPRIVATE_GM_CANARY")
        self.intercept(timeout)
        with self.assertRaises(GitFailure) as caught:
            self.store.put("locks/test", {"holder":"candidate"}, 1)
        self.assertTrue(caught.exception.details["timed_out"])
        self.assertIsNone(caught.exception.details["exit_code"])
        self.assertNotIn("secret",str(caught.exception.as_dict()))
        self.assertNotIn("PRIVATE_GM_CANARY",str(caught.exception.as_dict()))

    def test_remote_ref_race_is_rejected_by_real_git(self):
        self.git(self.root,"clone","--quiet",str(self.root/"origin.git"),"competitor")
        other = self.root/"competitor"
        def race(real,args,kwargs):
            (other/"unrelated.txt").write_text("another writer\n")
            self.git(other,"add","-A")
            self.git(other,"-c","user.name=t","-c","user.email=t@invalid","commit","--quiet","-m","other writer")
            self.git(other,"push","--quiet","origin","HEAD:staging")
            return real(args, **kwargs)
        self.intercept(race)
        with self.assertRaises(GitRefConflict) as caught:
            self.store.put("locks/test", {"holder":"candidate"}, 1)
        self.assertEqual(caught.exception.code,"GIT_STALE_REF")
        self.assertIsInstance(caught.exception,Conflict)
        self.assertEqual(self.document.read_bytes(),self.before)
        self.assertNotIn("PROVIDER_BUSY",str(caught.exception))


class ClaimFailures(Base):
    def queued(self):
        action,_ = self.act(HOLSTER,provider="gpt-session")
        return action

    def test_git_failure_never_becomes_provider_busy(self):
        action = self.queued()
        for code, stderr, category, expected in CASES:
            with self.subTest(category=category), patch.object(self.gw.store,"put",side_effect=failure(code,stderr)):
                with self.assertRaises(GitFailure) as caught:
                    self.gw.claim("gpt-session","run")
                self.assertEqual(caught.exception.code,expected)
        self.assertEqual(self.gw.action_status(action["action_id"])["status"],"submitted")
        self.assertIsNone(self.gw._op(action["action_id"]))

    def test_cas_conflict_without_a_holder_is_not_busy(self):
        self.queued()
        with patch.object(self.gw.store,"put",side_effect=Conflict("version changed")):
            with self.assertRaises(Refused) as caught:
                self.gw.claim("gpt-session","run")
        self.assertEqual(caught.exception.code,"CLAIM_CAS_CONFLICT")
        self.assertFalse(caught.exception.extra["verified_competing_holder"])

    def test_verified_live_holder_is_busy(self):
        self.queued()
        self.gw.store.put("locks/"+self.gw.id,{"holder":"other-run","provider":"gemini-session","expires_ms":self.clock()+60000},0)
        with patch.object(self.gw.store,"put") as writes:
            with self.assertRaises(Refused) as caught:
                self.gw.claim("gpt-session","run")
        self.assertEqual(caught.exception.code,"PROVIDER_BUSY")
        self.assertTrue(caught.exception.extra["verified_competing_holder"])
        writes.assert_not_called()

    def test_competing_holder_is_verified_after_the_cas_race(self):
        self.queued()
        original = self.gw.store.put
        def race(key,data,expected):
            original(key,{"holder":"other-run","provider":"gemini-session","expires_ms":self.clock()+60000},expected)
            raise Conflict("version changed")
        with patch.object(self.gw.store,"put",side_effect=race):
            with self.assertRaises(Refused) as caught:
                self.gw.claim("gpt-session","run")
        self.assertEqual(caught.exception.code,"PROVIDER_BUSY")
        self.assertTrue(caught.exception.extra["verified_competing_holder"])

    def test_runner_blocks_without_calling_model_or_releasing_an_unclaimed_lease(self):
        self.queued()
        provider=script("gpt-session")
        with patch.object(self.gw.store,"put",side_effect=failure(128,CASES[0][1])), patch.object(provider,"step") as model:
            out=run_turn(self.gw,provider,run="diagnostic")
        self.assertEqual(out["outcome"],"blocked")
        self.assertEqual(out["error"]["git"]["exit_code"],128)
        model.assert_not_called()

    def test_gm_http_error_boundary_preserves_sanitized_git_diagnostics(self):
        from service import App
        self.queued()
        app = App({self.gw.id:self.gw}, {}, "test-player-token", gm_tokens={"gpt-session":"test-gm-token"})
        for code, stderr, expected_status in ((128,CASES[0][1],503),(1,CASES[5][1],409)):
            with patch.object(self.gw.store,"put",side_effect=failure(code,stderr)):
                status, body = app.gm("POST",self.gw.id,"gpt-session","claim",
                                      {"authorization":"Bearer test-gm-token"},json.dumps({"run":"test"}).encode())
            self.assertEqual(status,expected_status)
            self.assertEqual(body["error"]["git"]["exit_code"],code)
            self.assertNotIn("secret",json.dumps(body))


if __name__ == "__main__":
    unittest.main()
