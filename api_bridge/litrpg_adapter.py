"""LitRPG ledger -> Genesis bridge adapter (READ-ONLY projection).

The Star Wars LitRPG is GM'd outside the bridge. Its single source of truth is the
append-only event ledger (campaigns/starwars_litrpg/records + hidden). This module
DERIVES the bridge's per-campaign files from the PLAYER-VISIBLE view of that ledger.
It never reads hidden/ files and never writes to the ledger. Derived files may be
regenerated at any time; delete them and the next mount rebuilds them.

The bridge's own Ollama GM loop is disabled for this campaign (gm_mode=external)
so there is exactly one authority.
"""
import importlib.util
import json
import os
import yaml

CID = 'starwars_litrpg'
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, '..'))
CAMPAIGN_DIR = os.path.join(_REPO, 'campaigns', 'starwars_litrpg')
_LEDGER_PY = os.path.join(_REPO, '.claude', 'skills', 'litrpg-ledger', 'ledger.py')
_SHEET = os.path.join(_HERE, 'gm', 'aero_character_runtime.yml')
_OUT = os.path.join(_HERE, 'gm', 'campaigns', CID)

_FACT_CLASS = {'fact': 'objective_fact', 'report': 'observed_report', 'belief': 'belief'}


def _ledger():
    spec = importlib.util.spec_from_file_location('litrpg_ledger_mod', _LEDGER_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def player_events():
    """Player-visible events only (gm_only dropped, hidden causes redacted).
    Reads the ledger module's own player_view, but ONLY the public file, so
    hidden/ is never opened."""
    m = _ledger()
    from pathlib import Path
    public = m.read_jsonl(Path(CAMPAIGN_DIR) / 'records' / 'events.jsonl')
    return m.player_view(public)


def _transcript(ev):
    return [{'entry_id': f"te_{e['event_id']}", 'type': 'narrator', 'speaker_id': 'game_master',
             'text': e['details'].get('text', e['summary']), 'dice': [], 'source_event_id': e['event_id'],
             'world_time': e['world_time']} for e in ev if e['kind'] == 'gm_narration']


def build_runtime():
    sheet = (yaml.safe_load(open(_SHEET, encoding='utf-8')) or {}).get('character_runtime', {})
    ev = player_events()
    last = ev[-1] if ev else {}
    scene = next((e['details'].get('scene') for e in reversed(ev) if e['kind'] == 'gm_narration'), None)
    return {
        'metadata': {'campaign_id': CID, 'session_id': 'session_1', 'scene_id': 'ledger_scene',
                     'runtime_version': len(ev), 'turn_no': last.get('turn_no', 0), 'seed': 0,
                     'active_player': 'aero', 'gm_mode': 'external'},
        # era is deliberately undisclosed to the player (campaign rule)
        'campaign': {'era': 'Undisclosed', 'current_time': last.get('world_time'),
                     'current_location': scene, 'active_objectives': [], 'campaign_flags': {}},
        'player_characters': {'aero': sheet},
        'transcript': _transcript(ev), 'conversation': {'suggestions': [], 'unresolved': False},
        'active_npcs': {}, 'canon': {'facts': [], 'prohibitions': []}, 'dialogue_memory': [],
        'combat': {'active': False, 'combat_id': None, 'initiative': [], 'positions': {},
                   'round': 0, 'turn': None, 'effects': []},
        'environment': {'visible_objects': [], 'hidden_objects': [], 'exits': [], 'hazards': [], 'world_damage': []},
        'ship': None,
    }


def sync():
    """Regenerate derived bridge files from the player-visible ledger. Idempotent."""
    os.makedirs(_OUT, exist_ok=True)
    ev = player_events()
    transcript, chronicle = [], []
    scene = None
    for e in ev:
        if e['kind'] == 'gm_narration':
            scene = e['details'].get('scene') or scene
            transcript.append({'entry_id': f"te_{e['event_id']}", 'type': 'narrator', 'speaker_id': 'game_master',
                               'text': e['details'].get('text', e['summary']), 'dice': [],
                               'source_event_id': e['event_id'], 'campaign_id': CID,
                               'world_time': e['world_time']})
        else:
            chronicle.append({'event_id': e['event_id'], 'timestamp': e['world_time'],
                              'objective_event': f"[{e['kind']}] {e['summary']}",
                              'participants': ['aero'] if 'aero' in (e.get('known_to') or []) else [],
                              'location': scene, 'source_resolution': 'game_master', 'dice': [],
                              'fact_class': _FACT_CLASS.get(e['knowledge_type'], 'objective_fact')})
    with open(os.path.join(_OUT, 'transcript_archive.jsonl'), 'w', encoding='utf-8') as f:
        for r in transcript:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(os.path.join(_OUT, 'chronicle.jsonl'), 'w', encoding='utf-8') as f:
        for r in chronicle:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    start = next((e for e in ev if e['kind'] == 'scenario_start'), None)
    with open(os.path.join(_OUT, 'opening.md'), 'w', encoding='utf-8') as f:
        f.write(start['summary'] if start else '')
    rt = build_runtime()
    with open(os.path.join(_OUT, 'runtime_state.json'), 'w', encoding='utf-8') as f:
        json.dump(rt, f, indent=1, ensure_ascii=False)
    return {'events': len(ev), 'transcript': len(transcript), 'chronicle': len(chronicle)}


if __name__ == '__main__':
    print(sync())
