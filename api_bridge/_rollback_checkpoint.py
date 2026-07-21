import json, glob, os, hashlib, shutil
import gm_controllers as gmc
def h(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
out = {}
for cid in ('meridian_reach', 'shadows_of_empire'):
    rp = gmc._paths(cid)['runtime']
    baks = sorted(glob.glob(os.path.join(r'E:\StarWars\registry\golden_slice\migration', cid + '_*.bak.json')))
    if not baks:
        out[cid] = {'error': 'no backup found'}; continue
    bak = baks[-1]
    pre = h(bak); migrated = h(rp)
    shutil.copy2(bak, rp)          # ROLLBACK to pre-migration
    post = h(rp)
    out[cid] = {'backup': os.path.relpath(bak, r'E:\StarWars'),
                'pre_migration_hash': pre, 'migrated_hash': migrated, 'restored_hash': post,
                'rollback_ok': post == pre, 'migration_changed_runtime': migrated != pre}
json.dump(out, open(r'E:\StarWars\_readiness_checkpoint_20260720\rollback_verification.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
