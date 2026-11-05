"""Tests: LitRPG adapter exposes ONLY player-visible ledger state through the bridge."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gm_controllers as gmc, projection, litrpg_adapter

HIDDEN_MARKERS = ['holocron', 'tally', 'Tolliver', 'Biscuit', 'Silo', 'shard', 'roll_t0', 'Old Republic', 'High Republic', 'Cold War', 'mimic']

def test_all():
    litrpg_adapter.sync()
    meta = gmc.mount_campaign('starwars_litrpg')
    assert meta['gm_mode'] == 'external'
    proj = projection.build_projection({}, runtime_mode='live')
    assert proj.get('projection_emitted') is True, proj.get('validation')
    assert proj['validation']['semantic_valid']
    blob = json.dumps(proj, ensure_ascii=False)
    for m in HIDDEN_MARKERS:
        assert m.lower() not in blob.lower(), f'leak: {m}'
    assert proj['campaign']['era'] == 'Undisclosed'
    entries = proj['active_engagement']['transcript']['entries']
    assert entries and 'Hask Meadow' in entries[0]['text'] and entries[0]['type'] == 'narrator'
    assert gmc.player_visible_state()['transcript'][0]['type'] == 'narrator'
    j = proj['command_record']['journal']['entries']
    assert j and all(x['event_type'] != 'gm_narration' for x in j)
    assert proj['operative']['character_runtime']['identity']['name'].startswith('Aeleron')
    try:
        gmc.run_turn('I draw my saber')
        raise AssertionError('bridge GM loop must be disabled')
    except RuntimeError as e:
        assert 'externally' in str(e)
    try:
        gmc.restart_campaign_from_opening('starwars_litrpg', confirm=True)
        raise AssertionError('restart must be refused')
    except ValueError:
        pass
    # idempotent resync
    a = litrpg_adapter.sync(); b = litrpg_adapter.sync()
    assert a == b
    print('ok', a, 'journal', len(j))

if __name__ == '__main__':
    test_all()
