"""Accepted legacy damage is read faithfully; new write rules are not relaxed."""
import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'campaigns/starwars_litrpg/ui'))
sys.path.insert(0, str(Path(__file__).parent))
from hp_compat import hp_delta
import export_state
import post_turn

for d, expected in [({'amount':-10},-10),({'delta':-3},-3),({'delta':0,'amount':-10},0),
                    ({'delta':2,'amount':-10},2),({'amount':'-10'},0),({'amount':True},0),
                    ({'delta':None,'amount':-10},0),({},0)]:
    original=copy.deepcopy(d)
    assert hp_delta(d)==expected and d==original
legacy={'event_id':'evt_0026','kind':'hp_change','actor':'gm','details':{'target':'aero','amount':-10}}
decl={'event_id':'evt_0025','kind':'player_declaration','actor':'aero','details':{}}
events=[decl,legacy]; original=copy.deepcopy(events)
r=post_turn.propose(events,[])
assert r['candidates'][0]['theme']=='pain_and_shock'
assert r['candidates'][0]['evidence']==['evt_0026']
assert events==original
# Exercise the actual exporter with a disposable public fixture; no campaign file writes.
fixture=ROOT/'development/mobile_test/fixture_campaign'
base=export_state.build(campaign_dir=fixture,campaign_id='mobile-test-1')
with tempfile.TemporaryDirectory() as td:
    from shutil import copytree
    run=Path(td)/'fixture';copytree(fixture,run)
    log=run/'records/events.jsonl'
    rows=[json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    sample=copy.deepcopy(rows[-1]);sample.update(legacy);sample['event_id']='evt_0007'
    sample['summary']='Accepted damage compatibility fixture.'
    with log.open('a') as f:f.write(json.dumps(sample)+'\n')
    before=log.read_bytes()
    result=export_state.build(campaign_dir=run,campaign_id='mobile-test-1')
    assert log.read_bytes()==before
    assert result['character']['hp'][0]==max(0,base['character']['hp'][0]-10), result['character']
print('HP compatibility: legacy damage, delta precedence, appraisal evidence, exporter and immutable input passed')
