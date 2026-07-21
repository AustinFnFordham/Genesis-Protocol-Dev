"""GENESIS — FOUR-CONTROLLER AI GM RUNTIME (Phase 1 MVI).

Per GENESIS_GM_ARCHITECTURE.md:
  Game Master     -> qwen2.5:32b        performs the world (narrative only)
  Combat Master   -> qwen2.5-coder:32b  resolves conflict (mechanics only)
  Record Keeper   -> deterministic code preserves truth (commit only)
  Genesis Steward -> deterministic code keeps the system honest (route/validate)

The models do not own the campaign. They operate it.
Dice come from the seeded service; a model may request a roll, never fabricate one.
The hidden GM ledger never enters a player-visible prompt unmediated.
"""
import json
import os
import re
import time

import yaml

GM_DIR = os.path.dirname(os.path.abspath(__file__))
GM_DATA = os.path.join(GM_DIR, 'gm')
CAMPAIGNS_DIR = os.path.join(GM_DATA, 'campaigns')
FORGE = os.path.abspath(os.path.join(GM_DIR, '..', 'SW5e_Data_Hub', 'forge_v3'))

# ---------------------------------------------------------------------------
# CAMPAIGN ISOLATION — one mounted campaign instance at a time. Each campaign
# owns its runtime, chronicle, turn log, and hidden ledger under
# gm/campaigns/<id>/. The controller stack mounts one and unloads it cleanly
# before another opens. Test data (Meridian Reach) is a CAMPAIGN, not a
# hardcoded world.
# ---------------------------------------------------------------------------
_MOUNTED = {'id': None, 'epoch': 0}


def _cdir(cid):
    d = os.path.join(CAMPAIGNS_DIR, cid)
    os.makedirs(d, exist_ok=True)
    return d


def _paths(cid):
    d = _cdir(cid)
    return {
        'runtime': os.path.join(d, 'runtime_state.json'),
        'chronicle': os.path.join(d, 'chronicle.jsonl'),
        'turnlog': os.path.join(d, 'turn_log.jsonl'),
        # CANONICAL transcript — append-only, campaign lifetime, silent
        # deletion prohibited. runtime['transcript'] is only the projection
        # window (200); THIS file is the truth.
        'transcript': os.path.join(d, 'transcript_archive.jsonl'),
        # REVISION LINEAGE (C.6 §7): monotonic floor + campaign_instance_id,
        # persisted OUTSIDE runtime_state.json so a rebuild cannot roll it back.
        'revision': os.path.join(d, 'revision.json'),
    }


def _revision_lineage(cid):
    p = _paths(cid)['revision']
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    lin = {'campaign_id': cid, 'campaign_instance_id': f'{cid}__{int(time.time())}', 'floor': 0}
    json.dump(lin, open(p, 'w', encoding='utf-8'), indent=1)
    return lin


def _bump_revision(cid, runtime_version):
    """state_revision may NEVER decrease within a campaign_instance. Returns the
    effective (monotonic) revision = max(persisted floor, runtime_version)."""
    lin = _revision_lineage(cid)
    eff = max(lin.get('floor', 0), int(runtime_version or 0))
    if eff != lin.get('floor'):
        lin['floor'] = eff
        json.dump(lin, open(_paths(cid)['revision'], 'w', encoding='utf-8'), indent=1)
    return eff, lin['campaign_instance_id']


def new_campaign_instance(cid):
    """A TRUE restart/new instance gets a fresh campaign_instance_id; the floor
    continues (revisions are globally monotonic per campaign_id lineage record)."""
    lin = _revision_lineage(cid)
    lin['campaign_instance_id'] = f'{cid}__{int(time.time())}'
    lin['previous_revision'] = lin.get('floor', 0)
    json.dump(lin, open(_paths(cid)['revision'], 'w', encoding='utf-8'), indent=1)
    return lin


def mounted_id():
    return _MOUNTED['id']


def _require_mounted():
    if not _MOUNTED['id']:
        raise RuntimeError('no campaign mounted — POST /api/v1/gm/mount first')
    return _paths(_MOUNTED['id'])


# CAMPAIGN CATALOG — display DATA for the select screen, not engine logic.
# Character/campaign specifics live here and in the builders (fixtures) ONLY;
# the turn loop, steward, dice service, and rules lawyer are character-blind.
CAMPAIGN_CATALOG = {
    'meridian_reach': {'name': 'Meridian Reach — The Sensor Array', 'era': 'High Republic',
                       'player': 'Aeleron "Aero" Do\'ordo', 'source': 'reference runtime (test data)'},
    'shadows_of_empire': {'name': 'Shadows of Empire: Remnants', 'era': 'New Republic',
                          'player': 'The Reconciliators (Voss / Ren / Zoran)', 'source': 'forge gold + AI pipeline'},
}


def list_campaigns():
    """Catalog + instantiation state on disk."""
    out = []
    for cid, meta in CAMPAIGN_CATALOG.items():
        inst = os.path.exists(os.path.join(CAMPAIGNS_DIR, cid, 'runtime_state.json'))
        out.append({'campaign_id': cid, **meta, 'instantiated': inst, 'mounted': _MOUNTED['id'] == cid})
    return out


def mount_campaign(cid):
    """Unload the current instance cleanly, then mount cid (building its
    runtime on first mount). Only one campaign lives in the stack at a time."""
    if _MOUNTED['id'] == cid:
        return load_runtime()['metadata']
    _MOUNTED['id'] = None  # clean unload — no state carries over
    builders = {'meridian_reach': build_initial_runtime, 'shadows_of_empire': build_shadows_runtime}
    if cid not in builders:
        raise ValueError(f'unknown campaign: {cid}')
    _MOUNTED['id'] = cid
    _MOUNTED['epoch'] = _MOUNTED.get('epoch', 0) + 1  # new mount transaction — stale responses discarded client-side
    p = _paths(cid)
    if not os.path.exists(p['runtime']):
        save_runtime(builders[cid]())
    rt = load_runtime()
    # migrations (nondestructive): pre-isolation runtimes lack fields
    changed = False
    if not rt['metadata'].get('active_player') and rt.get('player_characters'):
        rt['metadata']['active_player'] = next(iter(rt['player_characters']))
        changed = True
    if 'ship' not in rt:
        rt['ship'] = builders[cid]().get('ship')
        changed = True
    if changed:
        save_runtime(rt)
    return rt['metadata']


def unmount_campaign():
    prev = _MOUNTED['id']
    _MOUNTED['id'] = None
    return prev

OLLAMA = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
GM_MODEL = os.environ.get('GENESIS_GM_MODEL', 'qwen2.5:32b')
CM_MODEL = os.environ.get('GENESIS_CM_MODEL', 'qwen2.5-coder:32b')


# ===========================================================================
# DICE SERVICE — deterministic, seeded, verifiable (§9)
# ===========================================================================
def _mulberry(seed):
    a = seed & 0xFFFFFFFF
    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rand


class DiceService:
    """Rolls belong to the service. Seed = campaign seed ^ turn counter."""

    def __init__(self, seed, turn_no):
        self._rand = _mulberry((seed ^ (turn_no * 0x9E3779B9)) & 0xFFFFFFFF)
        self._n = 0
        self.log = []

    def roll(self, formula, purpose='', requested_by='system', mode='normal'):
        """formula like '1d20+5', '2d6', 'd8-1'. mode: normal|advantage|disadvantage."""
        m = re.fullmatch(r'\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*', str(formula))
        if not m:
            raise ValueError(f'bad dice formula: {formula}')
        count = int(m.group(1) or 1)
        sides = int(m.group(2))
        mod = int(m.group(3).replace(' ', '')) if m.group(3) else 0
        def throw():
            return [1 + int(self._rand() * sides) for _ in range(count)]
        dice = throw()
        alt = None
        if mode in ('advantage', 'disadvantage') and count == 1 and sides == 20:
            alt = throw()
            pick = max if mode == 'advantage' else min
            dice = [pick(dice[0], alt[0])]
        raw = sum(dice)
        self._n += 1
        rec = {
            'roll_id': f'roll_{int(time.time())}_{self._n}',
            'requested_by': requested_by, 'purpose': purpose,
            'formula': formula, 'mode': mode,
            'individual_dice': dice, 'alt_dice': alt,
            'raw_total': raw, 'modifiers': mod, 'final_total': raw + mod,
            'verified_by_steward': True,
        }
        self.log.append(rec)
        return rec


# ===========================================================================
# RUNTIME — shared contract (§5), seeded from the Aero reference files
# ===========================================================================
def _load_yaml(name):
    p = os.path.join(GM_DATA, name)
    return yaml.safe_load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def build_initial_runtime():
    sheet = (_load_yaml('aero_character_runtime.yml') or {}).get('character_runtime', {})
    ledger = (_load_yaml('aero_hidden_gm_ledger.yml') or {}).get('hidden_gm_ledger', {})
    scope = ledger.get('opening_scope', {})
    return {
        'metadata': {'campaign_id': 'meridian_reach', 'session_id': 'session_1',
                     'scene_id': 'scene_shuttle_briefing', 'runtime_version': 1,
                     'turn_no': 0, 'seed': 776211453, 'active_player': 'aero'},
        'campaign': {'era': scope.get('era', 'High Republic'), 'current_time': 'two weeks before the Harvest Festival',
                     'current_location': 'Republic shuttle en route to the frontier sensor array',
                     'active_objectives': [scope.get('mission', 'escort the engineers')],
                     'campaign_flags': {}},
        'player_characters': {'aero': sheet},
        # CANON CAST — corrected per hidden ledger: Nona Ladiern is the Harvest
        # Festival's namesake on the frontier, NOT aboard this shuttle. Aero
        # commands an unfamiliar team of three young operatives + six engineers.
        'active_npcs': {
            'pilot_dax': {'name': 'Dax Ferren', 'role': 'Republic shuttle pilot',
                          'disposition': 'jovial, talkative, gossip-prone', 'memories': [],
                          'knowledge_boundary': 'route and frontier chatter only'},
            'operative_senn': {'name': 'Senn Varga', 'role': 'Republic field operative (survey/security)',
                               'disposition': 'earnest, over-prepared, first frontier posting', 'memories': [],
                               'knowledge_boundary': 'mission brief + academy training only'},
            'operative_ilo': {'name': 'Ilo Reeth', 'role': 'Republic field operative (comms/slicing)',
                              'disposition': 'dry-witted, watchful, privately skeptical of Jedi', 'memories': [],
                              'knowledge_boundary': 'mission brief + relay technical specs'},
            'operative_maza': {'name': 'Maza Ketrel', 'role': 'Republic field operative (medic/quartermaster)',
                               'disposition': 'steady, older than the others, keeps count of everything', 'memories': [],
                               'knowledge_boundary': 'mission brief + crew logistics'},
            'chief_engineer_besk': {'name': 'Besk Ollor', 'role': 'chief of the six-engineer reactivation team',
                                    'disposition': 'gruff, deadline-minded, protective of his crew and crates', 'memories': [],
                                    'knowledge_boundary': 'relay hardware and reactivation procedure only'},
        },
        'canon': {  # LOOKUP layer — authoritative facts the GM may not contradict or exceed
            'facts': [
                'The Meridian Reach is a frontier sector of scattered settlements joined by old trade lanes and volunteer relays.',
                'Jedi serving the Reach are called the Walking Cloaks — they walk fields, repair pumps, and serve without ceremony.',
                "Nona Ladiern's Harvest Festival is two weeks away; Nona Ladiern is a frontier festival figure, not a crew member.",
                'The mission: escort six Republic engineers to reactivate an abandoned frontier beacon relay (sensor array). Restore the station, confirm the signal, bring everyone home.',
                'Aero was recently knighted; his master Vael Taron is missing; the Stillwater records are sealed.',
                'The shuttle is in transit; nothing anomalous has been detected en route.',
                'Aero has never met the three operatives before this mission.',
            ],
            'prohibitions': [
                'No invented rituals, ancient events, dark-side phenomena, energy signatures, or named lore absent from canon or chronicle.',
                'Force Connection reads emotional state and apparent concealment only — never thoughts, memories, or objective truth.',
                'No Republic-founding ceremonies attached to the Harvest Festival.',
            ],
        },
        'dialogue_memory': [],
        'combat': {'active': False, 'combat_id': None, 'initiative': [], 'positions': {},
                   'round': 0, 'turn': None, 'effects': []},
        'environment': {
            'visible_objects': ['engineer crates', 'sensor array schematics', 'ration lockers'],
            'hidden_objects': [], 'exits': ['cockpit', 'aft cargo bay'],
            'hazards': [], 'world_damage': [],
            'interactables': ['schematics table', 'comm panel', 'viewport'],
            'positions': {'aero': 'beside_schematics_table', 'chief_engineer_nona': '3_ft_across_table',
                          'pilot_dax': 'cockpit_door', 'engineers': 'aft_seating'},
        },
        'relationships': {}, 'quests': {'sensor_array_escort': {'state': 'active'}},
        'factions': {}, 'inventory_state': {}, 'open_threads': {},
        'player_knowledge': {'aero': ['official mission brief', 'Taron missing', 'own Stillwater memory gaps']},
        'hidden_gm_state': ledger,   # NEVER serialized into player-visible prompts
        'chronicle_reference': 'chronicle.jsonl',
        'validation': {'last_approved_patch': None, 'unresolved_data': [], 'provisional_rulings': []},
        'scene_state': {'mode': 'dialogue', 'action_lock': False, 'player_interrupts_allowed': True,
                        'physical_actions_allowed': True, 'powers_allowed': True,
                        'movement_allowed': True, 'custom_action_allowed': True},
        'ship': {
            'vessel_id': 'republic_shuttle_escort', 'name': 'Republic Shuttle (Consular-class tender)',
            'silhouette': 4, 'speed': 2, 'armor': 2,
            'hull': {'current': 14, 'threshold': 14}, 'strain': {'current': 10, 'threshold': 10},
            'shields': {'fore': 1, 'aft': 0, 'port': 0, 'starboard': 0},
            'systems': {'engines': 'operational', 'navigation': 'operational',
                        'communications': 'operational', 'shields': 'operational'},
            # NO weapons, NO turret — this vessel does not expose them.
            'stations': [
                {'station_id': 'pilot', 'name': 'Pilot', 'occupied_by': 'pilot_dax',
                 'required_proficiencies': ['piloting'], 'status': 'operational',
                 'available_actions': ['Fly/Drive', 'Evasive Maneuvers'], 'disabled_actions': []},
                {'station_id': 'communications', 'name': 'Communications', 'occupied_by': None,
                 'required_proficiencies': ['computers'], 'status': 'operational',
                 'available_actions': ['Hail Vessel', 'Scan Frequencies', 'Slice Comms'], 'disabled_actions': []},
                {'station_id': 'engineering', 'name': 'Engineering', 'occupied_by': None,
                 'required_proficiencies': ['mechanics'], 'status': 'operational',
                 'available_actions': ['Damage Control', 'Boost Shields'], 'disabled_actions': []},
            ],
            'weapons': [],
        },
    }


# ---------------------------------------------------------------------------
# ITEM TAXONOMY (Phase A) — a deterministic classifier + slot router. The UI
# and runtime must NEVER infer type from the array/panel that contains an item.
# item_type is authoritative (Item.schema enum). A ship is a Starship, not an
# Item, and never occupies a weapon slot.
# ---------------------------------------------------------------------------
ITEM_TYPES = {'Weapon', 'Armor', 'Gear', 'Consumable', 'Artifact', 'Droid_Part',
              'Starship', 'Starship_Component', 'Trade_Good', 'Other'}
SLOT_FOR_TYPE = {'Weapon': 'weapons', 'Armor': 'armor', 'Gear': 'gear', 'Trinket': 'gear',
                 'Consumable': 'gear', 'Artifact': 'gear', 'Droid_Part': 'gear',
                 'Starship': 'vehicles', 'Starship_Component': 'vehicles',
                 'Trade_Good': 'gear', 'Other': 'gear'}
_WEAPON_HINTS = re.compile(r'\b(blaster|rifle|pistol|saber|lightsaber|vibro|carbine|cannon|bowcaster|disruptor|sword|blade|dagger|staff|whip|grenade|detonator)\b', re.I)
_SHIP_HINTS = re.compile(r'\b(yt-?\d{3,4}|freighter|shuttle|starfighter|x-?wing|fighter|cruiser|corvette|frigate|transport|speeder|swoop|walker)\b', re.I)
_ARMOR_HINTS = re.compile(r'\b(armor|armour|plate|vest|shield generator|helmet|greaves|gauntlet|beskar)\b', re.I)
_APPAREL_HINTS = re.compile(r'\b(jacket|coat|cloak|robe|tunic|boots|gloves|hat|clothes|clothing|garb|outfit)\b', re.I)
_TRINKET_HINTS = re.compile(r'\b(chip|token|charm|trinket|dice|medallion|pendant|holo(?:cron|graph)?|keepsake|memento|card)\b', re.I)


def classify_item(item):
    """Return authoritative item_type for a str or dict. Explicit item_type
    wins; otherwise deterministic name heuristics. Apparel without armor
    mechanics is Gear, NOT Armor."""
    if isinstance(item, dict):
        t = item.get('item_type') or item.get('type')
        if t in ITEM_TYPES:
            return t
        name = str(item.get('name', ''))
        has_armor_mech = bool(item.get('armor_class') or item.get('armor_value') or (item.get('mechanics') or {}).get('armor'))
        has_weapon_mech = bool(item.get('damage') or (item.get('mechanics') or {}).get('damage'))
    else:
        name = str(item)
        has_armor_mech = has_weapon_mech = False
    if _SHIP_HINTS.search(name):
        return 'Starship'
    if has_weapon_mech or _WEAPON_HINTS.search(name):
        return 'Weapon'
    if has_armor_mech or (_ARMOR_HINTS.search(name) and not _APPAREL_HINTS.search(name)):
        return 'Armor'
    if _TRINKET_HINTS.search(name):
        return 'Trade_Good'
    if _APPAREL_HINTS.search(name):
        return 'Gear'   # apparel WITHOUT armor mechanics is Gear, not Armor
    return 'Gear'


def _norm_item(it, t):
    """Structured equipment entry. NEVER stringify a dict into name (C.5 §2):
    resolve a human name from name/item/item_name, and PRESERVE all fields."""
    if not isinstance(it, dict):
        it = {'name': str(it)}
    name = it.get('name') or it.get('item') or it.get('item_name') or it.get('id') or 'Unknown Item'
    entry = {
        'item_id': it.get('item_id') or it.get('id') or it.get('urid'),
        'instance_id': it.get('instance_id'),
        'name': str(name),
        'entity_type': 'Item',
        'item_type': t,
        'item_subtype': it.get('item_subtype') or it.get('subtype'),
        'quantity': it.get('quantity', 1),
        'equipped': it.get('equipped', t in ('Weapon', 'Armor')),
        'exact_effect': it.get('exact_effect') or it.get('effect') or it.get('description'),
        'properties': it.get('properties'),
        'provenance': it.get('provenance'),
    }
    return {k: v for k, v in entry.items() if v is not None}


def route_equipment(raw_items):
    """Route a raw equipment list into typed slots by authoritative item_type.
    NON-weapons never land in weapons[]. A complete Starship goes to starships[]
    (a vessel reference), NOT vehicles/carried. Entries stay STRUCTURED."""
    slots = {'weapons': [], 'armor': [], 'gear': [], 'vehicles': [], 'starships': []}
    for e in raw_items or []:
        it = e if isinstance(e, dict) else {'name': str(e)}
        t = classify_item(it)
        slot = 'starships' if t in ('Starship', 'Starship_Component') else SLOT_FOR_TYPE.get(t, 'gear')
        if slot == 'vehicles':  # Starship types already diverted; keep vehicles for non-starship craft
            slot = 'vehicles'
        slots.setdefault(slot, []).append(_norm_item(it, t))
    return slots


def validate_item_slots(sheet):
    """DETERMINISTIC item-slot validator (Phase A). Returns a list of
    violations. A non-Weapon in weapons[], apparel-without-armor in armor[],
    a ship in any carried slot, or a weapon missing damage all fail."""
    v = []
    eq = (sheet or {}).get('equipment') or {}
    for w in eq.get('weapons') or []:
        t = classify_item(w)
        if t != 'Weapon':
            v.append(f'non_weapon_in_weapon_slot: {w.get("name", w)} is {t}')
    for a in eq.get('armor') or []:
        if classify_item(a) != 'Armor':
            v.append(f'non_armor_in_armor_slot: {a.get("name", a)}')
    for slot in ('weapons', 'armor', 'gear'):
        for it in eq.get(slot) or []:
            if classify_item(it) == 'Starship':
                v.append(f'starship_in_carried_slot: {it.get("name", it)} in {slot}')
    return v


def build_shadows_runtime():
    """Instantiate 'Shadows of Empire: Remnants' from GENESIS GOLD DATA —
    the CampaignState entity + the AI-forged Reconciliators. Nothing here is
    hardcoded world truth; it is a projection of forge data into the shared
    runtime contract."""
    def _forge_yaml(rel):
        p = os.path.join(FORGE, rel)
        return yaml.safe_load(open(p, encoding='utf-8')) if os.path.exists(p) else {}

    cs = _forge_yaml(os.path.join('data', 'sandbox_gold', 'CampaignState.sandbox.yml'))
    party_ids = (cs.get('party') or {}).get('character_ids', [])
    pcs = {}
    for cid in party_ids:
        doc = _forge_yaml(os.path.join('data', 'campaign_local', f'Character__{cid}.yml'))
        if not doc:
            continue
        a = doc.get('ability_scores') or {}
        pcs[cid] = {   # project the Character entity into character-sheet-runtime shape
            # explicit id/name taxonomy — NEVER put a species tag into class (C.5 §3)
            'identity': {'name': doc.get('name', cid),
                         'species_id': doc.get('species_id'), 'species_name': doc.get('species_name'),
                         'class_id': doc.get('class_id'), 'class_name': doc.get('class_name'),
                         'subclass_id': doc.get('subclass_id'), 'subclass_name': doc.get('subclass_name'),
                         'background_id': doc.get('background_id'), 'background_name': doc.get('background_name'),
                         'level': doc.get('level', 5)},
            'abilities': {'scores': a, 'modifiers': {k: (v - 10) // 2 for k, v in a.items() if isinstance(v, int)},
                          'proficiency_bonus': 3},
            'defenses': {'current_hp': doc.get('hit_points', 30), 'maximum_hp': doc.get('max_hit_points', doc.get('hit_points', 30)),
                         'armor_class': doc.get('armor_class', 14), 'conditions': []},
            'movement': {'speed': doc.get('speed', 30)},
            'resources': {},
            'features': [{'name': f.get('name', f) if isinstance(f, dict) else str(f), 'action_type': 'passive',
                          'exact_effect': (f.get('description', '') if isinstance(f, dict) else '')[:200]}
                         for f in (doc.get('features') or [])[:8]],
            'powers': doc.get('spells') or [],
            # ITEM TAXONOMY: route by authoritative item_type, never dump all
            # equipment into weapons[]. Ships/apparel/trinkets land in their
            # correct slots; only true Weapons occupy the weapon slot.
            'equipment': {**route_equipment((doc.get('equipment') or [])[:12]), 'inventory': []},
        }
    session = cs.get('current_session') or {}
    return {
        'metadata': {'campaign_id': 'shadows_of_empire', 'session_id': f"session_{session.get('session_number', 1)}",
                     'scene_id': 'scene_vardos_aftermath', 'runtime_version': 1,
                     'turn_no': 0, 'seed': 378539591, 'active_player': party_ids[0] if party_ids else None},
        'campaign': {'era': cs.get('era', 'New_Republic'),
                     'current_time': session.get('session_date', 'after the Vardos exfiltration'),
                     'current_location': "docking bay 9, Vardos orbital transfer station",
                     'active_objectives': ['deliver the exfiltrated listening-post intel', 'shake the local enforcers'],
                     'campaign_flags': {}},
        'player_characters': pcs,
        'active_npcs': {
            'enforcer_captain_reyes': {'name': 'Captain Dara Reyes', 'role': 'Vardos enforcer captain',
                                       'disposition': 'suspicious, procedural, watching the docking manifests',
                                       'memories': [], 'knowledge_boundary': 'knows a listening post was breached; no descriptions yet'},
            'dockhand_yuel': {'name': 'Yuel', 'role': 'dockhand and information broker',
                              'disposition': 'transactional, friendly to credits', 'memories': [],
                              'knowledge_boundary': 'dock traffic and rumors only'},
        },
        'combat': {'active': False, 'combat_id': None, 'initiative': [], 'positions': {}, 'round': 0, 'turn': None, 'effects': []},
        'environment': {
            'visible_objects': ['fuel lines', 'cargo sleds', 'manifest kiosk'],
            'hidden_objects': [], 'exits': ['transit tube', 'maintenance crawlway', 'the Reconciliators\' freighter ramp'],
            'hazards': [], 'world_damage': [],
            'interactables': ['manifest kiosk', 'comm booth', 'cargo sled'],
            'positions': {pid: 'docking_bay_floor' for pid in party_ids} | {'enforcer_captain_reyes': 'bay_entrance_25_ft', 'dockhand_yuel': 'beside_cargo_sled_10_ft'},
        },
        'relationships': {}, 'quests': {'listening_post_intel': {'state': 'active', 'summary': session.get('session_summary', '')}},
        'factions': {}, 'inventory_state': {}, 'open_threads': {},
        'player_knowledge': {pid: ['the intel is hot', 'enforcers are alerted'] for pid in party_ids},
        'hidden_gm_state': {
            'established_hidden_history': [],
            'unresolved_truths': [{'id': 'thread_intel_buyer', 'status': 'unresolved',
                                   'constraint': 'who wants the listening-post intel must be established through play'}],
            'future_reveal_guardrails': ['no reveal without an earned causal path'],
        },
        'chronicle_reference': 'chronicle.jsonl',
        'validation': {'last_approved_patch': None, 'unresolved_data': [], 'provisional_rulings': []},
        'scene_state': {'mode': 'dialogue', 'action_lock': False, 'player_interrupts_allowed': True,
                        'physical_actions_allowed': True, 'powers_allowed': True,
                        'movement_allowed': True, 'custom_action_allowed': True},
        'ship': {
            'vessel_id': 'yt2400_reconciliator', 'name': "The Reconciliator (YT-2400)",
            'silhouette': 4, 'speed': 3, 'armor': 3,
            'hull': {'current': 22, 'threshold': 22}, 'strain': {'current': 15, 'threshold': 15},
            'shields': {'fore': 1, 'aft': 1, 'port': 0, 'starboard': 0},
            'systems': {'engines': 'operational', 'navigation': 'operational', 'communications': 'operational',
                        'weapons': 'operational', 'shields': 'operational'},
            'stations': [
                {'station_id': 'pilot', 'name': 'Pilot', 'occupied_by': 'char_smuggler_pilot_aran_voss',
                 'required_proficiencies': ['piloting'], 'status': 'operational',
                 'available_actions': ['Fly/Drive', 'Evasive Maneuvers', 'Gain the Advantage', 'Punch It'],
                 'disabled_actions': []},
                {'station_id': 'navigation', 'name': 'Navigation', 'occupied_by': 'char_former_isb_analyst_tala_ren',
                 'required_proficiencies': ['astrogation'], 'status': 'operational',
                 'available_actions': ['Plot Course', 'Scan the Enemy', 'Calculate Hyperroute'],
                 'disabled_actions': []},
                {'station_id': 'turret_dorsal', 'name': 'Dorsal Turret', 'occupied_by': None,
                 'required_proficiencies': ['gunnery'], 'status': 'operational',
                 'available_actions': ['Fire Turret', 'Suppressing Fire', 'Aim'],
                 'disabled_actions': []},
                {'station_id': 'engineering', 'name': 'Engineering', 'occupied_by': 'char_iridonian_guardian_kass_zoran',
                 'required_proficiencies': ['mechanics'], 'status': 'operational',
                 'available_actions': ['Damage Control', 'Boost Shields', 'Reroute Power'],
                 'disabled_actions': []},
            ],
            'weapons': [{'weapon_id': 'dorsal_laser_cannon', 'arc': 'dorsal 360', 'range': 'close',
                         'damage': 6, 'qualities': ['Accurate 1'], 'current_status': 'operational'}],
        },
    }


def load_runtime():
    p = _require_mounted()
    if os.path.exists(p['runtime']):
        return json.load(open(p['runtime'], encoding='utf-8'))
    raise RuntimeError('mounted campaign has no runtime — mount_campaign builds it')


def save_runtime(rt):
    p = _require_mounted()
    json.dump(rt, open(p['runtime'], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


# ===========================================================================
# GENESIS STEWARD — deterministic route / classify / validate / approve (§4.4)
# ===========================================================================
HOSTILE_PAT = re.compile(r'\b(punch|strike|hit|attack|stab|shoot|fire at|choke|slam|tackle|kick|throw.*(at|against)|ignite.*(saber|blade)|draw.*(blaster|weapon|saber).*(fire|attack)|blast)\b', re.I)
CONTESTED_PAT = re.compile(r'\b(grab|grapple|wrestle|snatch|disarm|shove|restrain|pin|hold.*(wrist|arm))\b', re.I)
ENVIRONMENT_PAT = re.compile(r'\b(shoot|fire).*(ceiling|air|wall|floor|console|panel)|smash.*(table|console|panel)|throw.*(table|chair|crate)\b', re.I)
POWER_PAT = re.compile(r'\b(force (push|pull|choke|lightning|burst|grip|jump)|battle insight|use (the |my )?force|telekine|levitate|read (his|her|their) (mind|thoughts)|sense (his|her|their) thoughts|with the force|burst)\b', re.I)
MOVE_PAT = re.compile(r'\b(walk|move|step|leave|exit|approach|back away|retreat|circle|run)\b', re.I)
SOCIAL_INT_PAT = re.compile(r'\b(interrupt|cut (him|her|them) off|talk over|slam.*hand.*table|raise (my|a) hand)\b', re.I)


def classify_declaration(text, runtime):
    """§17.3 interrupt classification — deterministic first pass."""
    t = text.lower()
    if HOSTILE_PAT.search(t):
        if runtime['combat']['active']:
            return 'combat_action'
        return 'isolated_attack'
    if CONTESTED_PAT.search(t):
        return 'contested_action'
    if ENVIRONMENT_PAT.search(t):
        return 'environmental_action'
    if POWER_PAT.search(t):
        return 'power_use'
    if SOCIAL_INT_PAT.search(t):
        return 'social_interruption'
    if MOVE_PAT.search(t) and len(t) < 90:
        return 'movement'
    return 'narrative'


MECHANICAL = {'isolated_attack', 'contested_action', 'environmental_action', 'power_use', 'combat_action'}


def hidden_leak_screen(text, runtime):
    """No hidden-ledger fact may surface without an earned causal path (§12).
    Deterministic screen: hard names/terms from the hidden ledger."""
    ledger = runtime.get('hidden_gm_state') or {}
    terms = set()
    for s in ledger.get('established_hidden_history', []):
        facts = s.get('facts', {})
        if isinstance(facts, dict) and facts.get('name'):
            terms.add(str(facts['name']).lower())
    terms.discard('')
    hits = [w for w in terms if w and w in (text or '').lower()]
    return hits  # empty list = clean


def _norm(s):
    return re.sub(r'[^a-z0-9 ]', '', str(s).lower()).strip()


def validate_gm_output(doc, runtime):
    """THE NARRATIVE TRUTH GATE. Hard checks:
    gm_may_not_speak_for_active_player, npc_identity_collision_blocks_turn,
    repeated_dialogue_without_new_purpose_requires_repair, hidden-leak screen,
    plus structural checks. Canon prohibitions ride in the prompt (Lookup);
    identity and voice are enforced here in code."""
    violations = []
    if not isinstance(doc, dict):
        return ['gm output is not an object']
    beats = doc.get('beats')
    if not isinstance(beats, list) or not beats:
        violations.append('no dialogue/narration beats')
    pid = runtime['metadata'].get('active_player')
    _, sheet = _active_sheet(runtime)
    player_names = {_norm(pid), _norm(sheet.get('identity', {}).get('name', ''))}
    player_names |= {_norm(w) for w in _norm(sheet.get('identity', {}).get('name', '')).split() if len(w) > 3}
    valid_speakers = {_norm(k) for k in (runtime.get('active_npcs') or {})} | {'narrator'}
    recent = [_norm(m) for m in (runtime.get('dialogue_memory') or [])]
    for b in beats or []:
        sid = _norm(str(b.get('speaker', 'narrator')).replace('npc_id|', ''))
        # HARD CHECK: the GM may not speak for the active player
        if sid in player_names and b.get('spoken_text'):
            violations.append(f'gm_may_not_speak_for_active_player: beat voiced by {sid}')
        # HARD CHECK: identity collision — unknown speakers block the turn
        elif sid not in valid_speakers and sid not in player_names and b.get('spoken_text'):
            violations.append(f'npc_identity_collision: unknown speaker "{sid}" is not in the active cast')
        # HARD CHECK: repeated dialogue without new purpose
        st = _norm(b.get('spoken_text', ''))
        if st and len(st) > 24 and any(st in r or r in st for r in recent):
            violations.append('repeated_dialogue_without_new_purpose: beat restates prior line')
    opts = doc.get('suggested_actions') or []
    if len(opts) > 4:
        violations.append('more than four suggested actions')
    labels = [_norm(o.get('spoken_line') or o.get('label', '')) for o in opts if isinstance(o, dict)]
    if len(labels) != len(set(labels)):
        violations.append('suggested actions are not meaningfully different')
    recent_all = [_norm(m) for m in (runtime.get('dialogue_memory') or [])]
    for l in labels:  # repeated questions are not suggested
        if l and len(l) > 24 and any(l in r or r in l for r in recent_all):
            violations.append('suggested option repeats an already-asked line')
    if doc.get('custom_action_allowed') is False:
        violations.append('custom_action_allowed must never be false')
    joined = ' '.join(str(b.get('spoken_text', '')) + ' ' + str(b.get('narration', '')) for b in beats if isinstance(b, dict))
    leaks = hidden_leak_screen(joined, runtime)
    if leaks:
        violations.append(f'hidden-state leak: {leaks}')
    return violations


def validate_cm_output(doc, dice_log):
    violations = []
    if not isinstance(doc, dict):
        return ['cm output is not an object']
    if 'resolution' not in doc:
        violations.append('missing resolution')
    used = doc.get('dice_results') or []
    valid_ids = {r['roll_id'] for r in dice_log}
    for r in used:
        rid = r.get('roll_id') if isinstance(r, dict) else None
        if rid not in valid_ids:
            violations.append(f'fabricated or unknown roll: {rid}')
        else:
            svc = next(x for x in dice_log if x['roll_id'] == rid)
            if r.get('final_total') != svc['final_total']:
                violations.append(f'altered roll result on {rid}')
    patch = doc.get('proposed_runtime_patch') or []
    for op in patch:
        p = op.get('path', '')
        if p.startswith(('/hidden_gm_state', '/chronicle', '/metadata/seed')):
            violations.append(f'combat master has no authority over {p}')
    return violations


# ===========================================================================
# OLLAMA CALL (shared plumbing; isolated prompts per controller)
# ===========================================================================
def _ollama(model, system, user, temperature, timeout=420):
    import urllib.request
    body = json.dumps({
        'model': model, 'system': system, 'prompt': user, 'stream': False, 'format': 'json',
        'options': {'temperature': temperature, 'num_predict': 2048},
    }).encode()
    req = urllib.request.Request(f'{OLLAMA}/api/generate', data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(json.loads(r.read())['response'])


# ===========================================================================
# GAME MASTER — narrative controller (§4.1). Sees NO hidden facts, only
# steward directives distilled from them.
# ===========================================================================
GM_SYSTEM = """You are the GAME MASTER of a Star Wars TTRPG (High Republic era). You perform the world.
YOU MAY: narrate scenes, portray NPCs with distinct voices, frame choices, interpret player intent, request specialist resolution.
YOU MAY NOT: roll dice, decide mechanical outcomes, change HP/resources/inventory/relationships, invent established-lore facts, reveal anything the player has not earned, choose actions or feelings FOR the player, or finish an NPC sentence after a valid physical interruption.
DIALOGUE IS NOT A CUTSCENE: break speech into short beats; after each meaningful beat the player may act. Track positions and objects — the scene stays physical while people talk.
TRUTH: AUTHORITATIVE_CANON_LOOKUP is law — never contradict it, never exceed it. Invent NO new named lore, rituals, ancient events, Force phenomena, or NPC identities. Only the listed active_npcs may speak. The full relevant cast is present in scene descriptions. Never repeat lines from recent_dialogue_memory without a new purpose. NEVER write dialogue for the player character — describe the world, then stop.
POWERS: any Force/ability effect must come from the player's provided sheet. If they lack a legal power for what they attempt, that is a mechanical question — flag specialist_required, do not narrate success.
STYLE: cinematic, concrete, sensory, no purple prose walls. 1-3 beats per turn. Stop at a meaningful player decision.
OPTIONS: suggested_actions are NATURAL SPOKEN LINES or concrete physical acts as the character would say/do them (e.g. "What exactly are you expecting to find when we arrive?"), never command-menu summaries. Include intent metadata per option.
Respond ONLY with JSON:
{
 "beats": [{"speaker": "npc_id|narrator", "spoken_text": "", "narration": "", "physical_behavior": "", "environmental_change": "", "interruption_window": "open|closed", "mood": "calm|amused|guarded|angry|warm|tense"}],
 "scene_analysis": {"current_mode": "dialogue|exploration|tension", "specialist_required": false, "requested_specialist": null, "pacing_recommendation": "hold|advance"},
 "suggested_actions": [{"spoken_line": "", "intent": {"topic": "", "goal": "", "tone": ""}, "category": "social|physical|power|movement|investigation", "legal": true, "visible_basis": ""}],
 "custom_action_allowed": true,
 "npc_memory_notes": [{"npc_id": "", "witnessed": ""}]
}
Max 4 suggested_actions. Base every suggestion on visible information only."""


def _active_sheet(runtime):
    pid = runtime['metadata'].get('active_player')
    return pid, (runtime['player_characters'].get(pid) or {})


def gm_turn(runtime, declaration, steward_directives, mechanics_summary=None):
    pid, sheet = _active_sheet(runtime)
    weapons = [w.get('name') for w in (sheet.get('equipment', {}).get('weapons') or []) if w.get('equipped')]
    visible = {
        'scene_id': runtime['metadata']['scene_id'],
        'campaign': runtime['campaign'],
        'scene_state': runtime['scene_state'],
        'player_character': {
            'id': pid,
            'name': sheet.get('identity', {}).get('name', pid),
            'class': sheet.get('identity', {}).get('class'),
            'hp': sheet.get('defenses', {}).get('current_hp'),
            'visible_gear': weapons,
        },
        'party': {k: v.get('identity', {}).get('name', k) for k, v in runtime['player_characters'].items()},
        'active_npcs': {k: {kk: vv for kk, vv in v.items() if kk != 'memories'} for k, v in runtime['active_npcs'].items()},
        'environment': runtime['environment'],
        'player_knowledge': runtime['player_knowledge'],
        'recent_chronicle': tail_chronicle(6),
        'combat_active': runtime['combat']['active'],
    }
    user = json.dumps({
        'runtime_visible': visible,
        'AUTHORITATIVE_CANON_LOOKUP': runtime.get('canon', {}),  # Lookup layer — may not be contradicted or exceeded
        'recent_dialogue_memory': (runtime.get('dialogue_memory') or [])[-8:],  # Character Keeper — do not repeat these
        'player_declaration': declaration,
        'steward_directives': steward_directives,
        'validated_mechanics_summary': mechanics_summary,
    }, ensure_ascii=False)
    return _ollama(GM_MODEL, GM_SYSTEM, user, temperature=0.75)


# ===========================================================================
# COMBAT MASTER — mechanical controller (§4.2). Two-phase: adjudicate
# (declare required rolls) -> service rolls -> resolve with real dice.
# ===========================================================================
CM_SYSTEM_ADJUDICATE = """You are the COMBAT MASTER, the mechanical adjudicator of a SW5e-hybrid TTRPG.
Phase 1 of 2 — ADJUDICATION ONLY. Given a declared action, the actor's exact character-sheet mechanics, and scene context: decide legality, applicable rules, action cost, targets, surprise considerations (target awareness, distance, readiness), and EXACTLY which rolls are required.
YOU DO NOT ROLL DICE. YOU DO NOT DECIDE OUTCOMES. YOU DO NOT NARRATE.
Use ONLY the mechanics provided in the character sheet entries — every attack bonus, DC and die comes from there. If a needed rule is absent, set "lookup_required" with what is missing.
Respond ONLY with JSON:
{"adjudication": {"declared_intent": "", "legal": true, "rules_used": [""], "action_cost": "", "surprise_assessment": {"target_aware_of_threat": false, "grants_advantage": false, "rationale": ""}, "targets": [""], "lookup_required": null},
 "required_rolls": [{"purpose": "attack|damage|save|contest|check", "formula": "1d20+5", "mode": "normal|advantage|disadvantage", "against": "AC 12|DC 12|contested:..."}]}"""

CM_SYSTEM_RESOLVE = """You are the COMBAT MASTER. Phase 2 of 2 — RESOLUTION.
You are given your own adjudication and the ACTUAL dice results from the trusted dice service. Apply them mechanically. You may not alter, reroll, or ignore any result. Reference each roll by its roll_id and use its final_total exactly.
Propose runtime patches ONLY for combat-legal paths (hp, strain, conditions, positions, combat block, resource spending). No narrative. No relationship changes. No loot.
Respond ONLY with JSON:
{"dice_results": [{"roll_id": "", "final_total": 0, "applied_to": ""}],
 "resolution": {"hit_or_miss": "", "damage": 0, "conditions_applied": [], "resources_spent": [], "movement_completed": "", "reactions_triggered": [], "defeated_entities": []},
 "player_visible_summary": "",
 "proposed_runtime_patch": [{"op": "replace|add", "path": "", "value": null}],
 "combat_state": {"combat_continues": false, "escalation_recommended": "none|brawl|full_combat", "termination_reason": ""}}"""


def _relevant_sheet(runtime, declaration):
    _, sheet = _active_sheet(runtime)
    return {
        # rules_status provenance: confirmed / provisional / unresolved rulings
        # ride with the sheet — a provisional table ruling is enforceable in
        # play but is NEVER silently promoted to universal Genesis canon.
        'rules_status': sheet.get('validation'),
        'abilities': sheet.get('abilities'), 'defenses': sheet.get('defenses'),
        'movement': sheet.get('movement'), 'resources': sheet.get('resources'),
        'weapons': sheet.get('equipment', {}).get('weapons'),
        'features': [f for f in sheet.get('features', []) if f.get('action_type') != 'narrative or social'],
        'powers': sheet.get('powers'),
    }


def combat_master(runtime, declaration, classification, dice):
    context = {
        'declared_action': declaration,
        'classification': classification,
        'scene_positions': runtime['environment'].get('positions'),
        'combat': runtime['combat'],
        'hostile_interrupt_context': {
            'tension_level': 'calm' if not runtime['combat']['active'] else 'combat',
            'target_ready_state': 'conversational' if not runtime['combat']['active'] else 'combat',
        },
        'actor_sheet': _relevant_sheet(runtime, declaration),
        # RULES LAWYER: noncombat does not mean nonmechanical. The actor's
        # LEGAL powers are exactly these — an attempt without a legal power
        # must be adjudicated as impossible or an ordinary ability check.
        'rules_lawyer_note': {
            'legal_powers': [p.get('name') for p in _relevant_sheet(runtime, declaration).get('powers') or []],
            'ruling_basis': 'If the declared effect requires a power the actor does not possess, legal=false or resolve as a mundane ability check. Force Connection reads emotional state and apparent concealment ONLY.',
        },
        'npc_combat_profiles': {k: {'name': v.get('name'), 'role': v.get('role')} for k, v in runtime['active_npcs'].items()},
    }
    adjudication = _ollama(CM_MODEL, CM_SYSTEM_ADJUDICATE, json.dumps(context, ensure_ascii=False), temperature=0.15)
    rolls = []
    for req in (adjudication.get('required_rolls') or [])[:8]:
        try:
            rolls.append(dice.roll(req.get('formula', '1d20'), purpose=req.get('purpose', ''),
                                   requested_by='combat_master', mode=req.get('mode', 'normal')))
        except ValueError:
            pass
    resolve_input = {'adjudication': adjudication, 'dice_service_results': rolls, 'combat': runtime['combat'],
                     'actor_sheet': context['actor_sheet']}
    resolution = _ollama(CM_MODEL, CM_SYSTEM_RESOLVE, json.dumps(resolve_input, ensure_ascii=False), temperature=0.1)
    return adjudication, rolls, resolution


# ===========================================================================
# RECORD KEEPER — deterministic commit (§4.3)
# ===========================================================================
def tail_chronicle(n=6):
    if not _MOUNTED['id']:
        return []
    p = _paths(_MOUNTED['id'])['chronicle']
    if not os.path.exists(p):
        return []
    lines = open(p, encoding='utf-8').read().splitlines()
    return [_clean(json.loads(l)) for l in lines[-n:] if l.strip()]


def record_keeper_commit(runtime, approved_patch, chronicle_entry, memory_notes):
    import jsonpatch
    if approved_patch:
        runtime = jsonpatch.apply_patch(runtime, approved_patch)
    for note in memory_notes or []:
        npc = runtime['active_npcs'].get(note.get('npc_id'))
        if npc is not None and note.get('witnessed'):
            npc.setdefault('memories', []).append({
                'event_id': chronicle_entry['event_id'], 'witnessed': str(note['witnessed'])[:200]})
    runtime['metadata']['runtime_version'] += 1
    runtime['metadata']['turn_no'] += 1
    save_runtime(runtime)
    with open(_require_mounted()['chronicle'], 'a', encoding='utf-8') as f:
        f.write(json.dumps(chronicle_entry, ensure_ascii=False) + '\n')
    return runtime


# ===========================================================================
# THE TURN LOOP — Steward-orchestrated (§3, §7, §17)
# ===========================================================================
def run_turn(declaration, idempotency_key=None):
    runtime = load_runtime()
    # DURABLE IDEMPOTENCY — gmBusy is UX; THIS is authoritative. A key that
    # was already processed returns its original command, creating nothing.
    if idempotency_key:
        seen = runtime.setdefault('idempotency', {})
        if idempotency_key in seen:
            return {'status': 'duplicate', 'command_id': seen[idempotency_key],
                    'reason': 'idempotency key already processed — exactly one commit exists'}
    turn_no = runtime['metadata']['turn_no']
    dice = DiceService(runtime['metadata']['seed'], turn_no)
    audit = {'turn_no': turn_no, 'declaration': declaration, 'violations': [], 'repairs': 0}

    # 1. STEWARD: route
    classification = classify_declaration(declaration, runtime)
    audit['classification'] = classification
    mechanics_summary = None
    approved_patch = []
    cm_bundle = None

    # 1.5 RULES LAWYER (deterministic — the law does not rationalize):
    # power_effect_requires_exact_feature_validation. A power_use declaration
    # must name a power the actor actually possesses; otherwise the effect is
    # ILLEGAL before any model sees it. Force Connection never moves objects
    # or reads thoughts (information_boundary).
    # ---- TURN DISPOSITION (Gameplay Runtime gate §3): a moral, hostile,
    # disruptive, or suicidal choice is NEVER by itself invalid. Every
    # non-accepted turn returns block_evidence with preserved intent and
    # nearest executable options. Generic 'STEWARD BLOCKED' is dead.
    turn_disposition = 'accepted'
    block_evidence = None
    decl_n_all = _norm(declaration)

    # §2/§5: attempted AUTOMATIC outcome ("instantly kill everyone", "without a
    # chance to react") -> accepted_with_interpretation: the desired outcome
    # becomes an ATTEMPT with mechanics; automatic success is stripped.
    AUTO_PAT = re.compile(r'\b(instantly|automatically|without (giving )?(them |anyone )?(a )?chance|kill(s)? every(one|body)|all of them die|succeeds? automatically)\b', re.I)
    desired_outcome = None
    if AUTO_PAT.search(declaration):
        desired_outcome = declaration
        turn_disposition = 'accepted_with_interpretation'
        audit['violations'] = audit.get('violations', [])
        # If no concrete executable act accompanies the desired outcome,
        # ask HOW rather than rejecting the turn.
        if classification == 'narrative' and not any(w in decl_n_all for w in ('attack', 'stab', 'shoot', 'ignite', 'drive', 'strike', 'punch', 'saber', 'blaster')):
            block_evidence = {
                'disposition': 'clarification_required',
                'preserved_intent': {'type': 'hostile_mass_outcome', 'declaration': declaration},
                'exact_reason': 'A desired outcome is not an executable action; automatic success cannot be declared.',
                'authoritative_rule_or_state': 'gameplay_gate.player_agency: mechanics determine success',
                'nearest_executable_options': ['Attack a specific person or object with a held weapon',
                                               'Sabotage a named shuttle system', 'Declare the first concrete action of the attempt'],
                'clarification_prompt': 'How does your character attempt this? Name the first concrete action.',
            }
            turn_disposition = 'clarification_required'

    if classification == 'power_use':
        _, sheet_rl = _active_sheet(runtime)
        legal = [p.get('name', '') for p in (sheet_rl.get('powers') or [])]
        decl_n = _norm(declaration)
        if not any(_norm(n) and _norm(n) in decl_n for n in legal):
            # §3 capability_blocked: explain, preserve intent, offer alternatives.
            block_evidence = {
                'disposition': 'capability_blocked',
                'preserved_intent': {'type': 'hostile_or_force_effect', 'declaration': declaration},
                'exact_reason': f'Character does not possess a power matching this effect. Known powers: {", ".join(legal) or "none"}.',
                'authoritative_rule_or_state': 'rules_lawyer:power_effect_requires_exact_feature_validation',
                'nearest_executable_options': ['Physical grapple or restraint (contested check)',
                                               'Threaten or intimidate (social)',
                                               *(f'Use {n}' for n in legal if n)],
                'clarification_prompt': 'Choose a capability you possess, or attempt it physically.',
            }
            turn_disposition = 'capability_blocked'
            mechanics_summary = {
                'classification': 'power_use',
                'adjudication': {'declared_intent': declaration, 'legal': False,
                                 'rules_used': ['rules_lawyer:power_effect_requires_exact_feature_validation'],
                                 'targets': []},
                'dice': [], 'resolution': {'hit_or_miss': 'illegal'},
                'summary': block_evidence['exact_reason'] + ' The intent is preserved — narrate the attempt falling short and surface the alternatives.',
                'escalation': 'none',
            }
            audit['violations'].append({'controller': 'rules_lawyer', 'code': 'capability_blocked'})
            classification = 'narrative_after_ruling'  # GM narrates the validated failure

    # 2. COMBAT MASTER when mechanical (scene frozen at the interruption point)
    if classification in MECHANICAL:
        adjudication, rolls, resolution = combat_master(runtime, declaration, classification, dice)
        cm_violations = validate_cm_output(resolution, dice.log)
        if cm_violations:
            audit['violations'] += [{'controller': 'combat_master', 'code': v} for v in cm_violations]
            audit['repairs'] += 1
            adjudication, rolls, resolution = combat_master(runtime, declaration, classification, dice)
            cm_violations = validate_cm_output(resolution, dice.log)
            if cm_violations:
                return {'status': 'blocked', 'reason': 'combat_master_invalid', 'violations': cm_violations,
                        'audit': audit}
        # STEWARD: approve only authority-legal ops
        for op in (resolution.get('proposed_runtime_patch') or []):
            path = op.get('path', '')
            if path.startswith(('/player_characters', '/active_npcs', '/combat', '/environment')):
                approved_patch.append(op)
            else:
                audit['violations'].append({'controller': 'combat_master', 'code': f'patch outside authority: {path}'})
        # escalation per §17.3: steward decides mode AFTER resolution
        esc = (resolution.get('combat_state') or {}).get('escalation_recommended', 'none')
        if esc == 'full_combat' and not runtime['combat']['active']:
            # CM → DIORAMA: initialize the combat block GENERICALLY from the
            # runtime — active party + present NPCs, seeded initiative, grid
            # positions derived from scene positions. No character constants.
            participants = list(runtime['player_characters'].keys()) + list(runtime['active_npcs'].keys())
            init_rolls = []
            for p in participants:
                r = dice.roll('1d20', purpose=f'initiative:{p}', requested_by='combat_master')
                init_rolls.append((r['final_total'], p))
            order = [p for _, p in sorted(init_rolls, reverse=True)]
            tokens = []
            for i, p in enumerate(participants):
                is_pc = p in runtime['player_characters']
                tokens.append({'token_id': p, 'entity_id': p,
                               'name': (runtime['player_characters'].get(p, {}).get('identity', {}).get('name')
                                        or runtime['active_npcs'].get(p, {}).get('name') or p),
                               'is_pc': is_pc, 'x': 4 + (i % 4) * 2 + (0 if is_pc else 8), 'y': 4 + (i // 4) * 2})
            approved_patch += [
                {'op': 'replace', 'path': '/combat', 'value': {
                    'active': True, 'combat_id': f'combat_{turn_no}', 'round': 1,
                    'initiative': order, 'turn': order[0] if order else None,
                    'tokens': tokens, 'grid': {'width': 20, 'height': 14}, 'effects': [],
                }},
            ]
        mechanics_summary = {
            'classification': classification,
            'adjudication': adjudication.get('adjudication'),
            'dice': [{'roll_id': r['roll_id'], 'formula': r['formula'], 'dice': r['individual_dice'],
                      'total': r['final_total'], 'purpose': r['purpose']} for r in dice.log],
            'resolution': resolution.get('resolution'),
            'summary': resolution.get('player_visible_summary'),
            'escalation': esc,
        }
        cm_bundle = {'adjudication': adjudication, 'resolution': resolution}

    # 3. GAME MASTER narrates (validated mechanics in, hidden facts out)
    directives = {
        'freeze_point': 'Narrate from the exact interruption point; the interrupted NPC does not finish their sentence.' if classification in MECHANICAL else None,
        'pacing': 'Stop at a meaningful player decision. 1-3 beats.',
        'hidden_state': 'You do not know the contents of any sealed record, hidden history, or unresolved thread. Do not invent them.',
    }
    gm_error = None
    try:
        gm_out = gm_turn(runtime, declaration, directives, mechanics_summary)
    except Exception as e:
        gm_out, gm_error = None, str(e)[:200]
    if gm_out is not None:
        gm_violations = validate_gm_output(gm_out, runtime)
        if gm_violations:
            audit['violations'] += [{'controller': 'game_master', 'code': v} for v in gm_violations]
            audit['repairs'] += 1
            directives['repair'] = f'Your previous output violated: {gm_violations}. Fix these exactly.'
            try:
                gm_out = gm_turn(runtime, declaration, directives, mechanics_summary)
                gm_violations = validate_gm_output(gm_out, runtime)
                if gm_violations:
                    gm_out = None
                    gm_error = f'unrepaired: {gm_violations}'
            except Exception as e:
                gm_out, gm_error = None, str(e)[:200]
    if gm_out is None:
        # deterministic fallback beat — the game never dies with the model
        gm_out = {
            'beats': [{'speaker': 'narrator', 'spoken_text': '',
                       'narration': mechanics_summary['summary'] if mechanics_summary else 'The moment hangs. The shuttle hums on toward the frontier.',
                       'physical_behavior': '', 'environmental_change': '', 'interruption_window': 'open'}],
            'scene_analysis': {'current_mode': 'dialogue', 'specialist_required': False, 'pacing_recommendation': 'hold'},
            'suggested_actions': [], 'custom_action_allowed': True, 'npc_memory_notes': [],
            '_fallback': True, '_gm_error': gm_error,
        }

    # 3.5 CHARACTER KEEPER: discourse continuity — remember what was said
    spoken = [b.get('spoken_text') for b in (gm_out.get('beats') or []) if isinstance(b, dict) and b.get('spoken_text')]
    if spoken or declaration:
        mem = (runtime.get('dialogue_memory') or []) + [declaration] + spoken
        runtime['dialogue_memory'] = mem[-24:]

    # 3.6 THE SERVER-OWNED TRANSCRIPT — canonical conversation record.
    # Views project this; no client tab owns it. Survives navigation,
    # refresh, and (per-campaign) mount cycles.
    cmd_id = f'cmd_{int(time.time())}_{turn_no}'
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    # SCENE / INTERACTION PARTITIONING — every entry carries its full address.
    part = {
        'campaign_id': runtime['metadata'].get('campaign_id'),
        'session_id': runtime['metadata'].get('session_id'),
        'scene_id': runtime['metadata'].get('scene_id'),
        'interaction_id': runtime['metadata'].get('interaction_id') or f"int_{runtime['metadata'].get('scene_id')}",
    }
    new_entries = []
    new_entries.append({'entry_id': f'te_{turn_no}_p', 'type': 'player', 'speaker_id': runtime['metadata'].get('active_player'),
                        'text': declaration, 'source_command_id': cmd_id, 'created_at': ts, **part})
    if mechanics_summary:
        new_entries.append({'entry_id': f'te_{turn_no}_m', 'type': 'mechanics', 'speaker_id': 'combat_master',
                            'text': mechanics_summary.get('summary', ''), 'dice': mechanics_summary.get('dice'),
                            'source_command_id': cmd_id, 'created_at': ts, **part})
    for bi, b in enumerate(gm_out.get('beats') or []):
        if not isinstance(b, dict):
            continue
        sid = str(b.get('speaker', 'narrator')).replace('npc_id|', '')
        new_entries.append({'entry_id': f'te_{turn_no}_b{bi}', 'type': 'narrator' if sid == 'narrator' else 'npc',
                            'speaker_id': sid, 'text': b.get('spoken_text') or '',
                            'narration': b.get('narration') or '', 'behavior': b.get('physical_behavior') or '',
                            'mood': b.get('mood'), 'source_command_id': cmd_id, 'created_at': ts, **part})
    # CANONICAL: append-only archive, campaign lifetime, never truncated.
    with open(_require_mounted()['transcript'], 'a', encoding='utf-8') as f:
        for e in new_entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    # PROJECTION WINDOW: runtime carries only the recent slice for hydration.
    runtime['transcript'] = ((runtime.get('transcript') or []) + new_entries)[-200:]
    if idempotency_key:
        runtime.setdefault('idempotency', {})[idempotency_key] = cmd_id
        # bound the map without losing recent protection
        if len(runtime['idempotency']) > 200:
            runtime['idempotency'] = dict(list(runtime['idempotency'].items())[-100:])
    # conversation projection: pending choices + unresolved state survive too
    runtime['conversation'] = {
        'suggestions': (gm_out.get('suggested_actions') or [])[:4],
        'unresolved': bool(gm_out.get('suggested_actions')),
        'last_command_id': cmd_id,
    }

    # 4. RECORD KEEPER commits
    entry = {
        'event_id': f'evt_{int(time.time())}_{turn_no}',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'objective_event': f'[{classification}] {declaration[:160]}',
        'participants': [runtime['metadata'].get('active_player')] + list((mechanics_summary or {}).get('adjudication', {}).get('targets', []) if mechanics_summary else []),
        'location': runtime['campaign']['current_location'],
        'source_resolution': 'combat_master' if mechanics_summary else 'game_master',
        'dice': [r['roll_id'] for r in dice.log],
        'fact_class': 'objective_fact',
    }
    runtime = record_keeper_commit(runtime, approved_patch, entry, gm_out.get('npc_memory_notes'))

    # 5. TURN LOG (provenance)
    with open(_require_mounted()['turnlog'], 'a', encoding='utf-8') as f:
        f.write(json.dumps({'audit': audit, 'approved_patch': approved_patch,
                            'dice': dice.log, 'gm_fallback': gm_out.get('_fallback', False)},
                           ensure_ascii=False) + '\n')

    # REACTION WINDOW (§17.8): when stakes shift but full combat isn't
    # warranted, offer a quick-time prompt. Generic — options derive from the
    # resolved mechanics, custom action always implied.
    reaction_window = None
    if mechanics_summary and mechanics_summary.get('escalation') == 'brawl':
        reaction_window = {
            'prompt': mechanics_summary.get('summary') or 'The situation is escalating. What do you do?',
            'options': ['Press on', 'Break away and de-escalate'],
            'timer_seconds': 10,
            'custom_action_allowed': True,
        }

    # §6 UNIVERSE TURN: after every accepted player turn, the world acts.
    # Derived from GM beats (NPC actions) + mechanics (environment/relations).
    universe_turn = {
        'local_npc_actions': [
            {'npc_id': str(b.get('speaker', '')).replace('npc_id|', ''),
             'action': (b.get('physical_behavior') or b.get('spoken_text', ''))[:140]}
            for b in (gm_out.get('beats') or []) if isinstance(b, dict) and b.get('speaker') not in (None, 'narrator')
        ],
        'environmental_changes': [b.get('environmental_change') for b in (gm_out.get('beats') or []) if isinstance(b, dict) and b.get('environmental_change')],
        'relationship_changes': [], 'objective_changes': [], 'faction_reactions': [],
        'rumors_created': [], 'threats_advanced': [], 'opportunities_created': [],
    }

    return {
        'status': 'ok',
        'command_id': cmd_id,
        'turn_disposition': turn_disposition,
        'block_evidence': block_evidence,
        'desired_outcome': desired_outcome,
        'universe_turn': universe_turn,
        'classification': classification,
        'reaction_window': reaction_window,
        'beats': gm_out.get('beats'),
        'suggested_actions': (gm_out.get('suggested_actions') or [])[:4],
        'custom_action_allowed': True,
        'mechanics': mechanics_summary,
        'scene_state': runtime['scene_state'],
        'combat_active': runtime['combat']['active'],
        'audit': {'violations': audit['violations'], 'repairs': audit['repairs'],
                  'dice_verified': all(r.get('verified_by_steward') for r in dice.log)},
        'turn_no': runtime['metadata']['turn_no'],
    }


def read_transcript(offset=0, limit=100):
    """Paginated read of the CANONICAL archive (append-only, campaign life)."""
    p = _require_mounted()['transcript']
    if not os.path.exists(p):
        return {'entries': [], 'total': 0, 'offset': offset}
    lines = open(p, encoding='utf-8').read().splitlines()
    total = len(lines)
    page = [_clean(json.loads(l)) for l in lines[offset:offset + max(1, min(500, limit))] if l.strip()]
    return {'entries': page, 'total': total, 'offset': offset,
            'campaign_id': _MOUNTED['id'], 'mount_epoch': _MOUNTED.get('epoch', 0),
            'canonical_retention': 'campaign_lifetime', 'projection_window': 200}


OPENING_SYSTEM = """You are the GAME MASTER writing a CAMPAIGN OPENING — screen-crawl-quality cinematic exposition. Three movements: (1) Chronicle inheritance — what kind of place this region is and what shaped it; (2) Character inheritance — place the protagonist emotionally and historically inside that world (their history, losses, unresolved threads, current status); (3) Immediate mission — only then narrow into the present scene; the objective emerges through story, never as a checklist. PROHIBITED: raw objective dumps, invented lore beyond the provided canon, hidden-ledger leakage, dialogue for the player character, starting with a menu. End at the physical scene with the full cast present, then stop.
Respond ONLY with JSON: {"cinematic_exposition": "", "scene_transition": "", "immediate_visible_context": "", "active_cast": [""], "action_window": "What does <name> do?"}"""


def get_opening(force_regenerate=False):
    """Campaign-opening contract — GENERATED ONCE, PERSISTED, REPLAYED.
    Priority: (1) authored opening.md served verbatim (gold); (2) a persisted
    opening.generated.json served verbatim so the crawl NEVER changes across
    ordinary mounts; (3) only when neither exists (or a restart forces it) does
    the GM generate one under the opening contract, screen it for hidden-state
    leaks, and PERSIST it. The crawl belongs to this campaign_id for its life."""
    p = _require_mounted()
    rt = load_runtime()
    cdir = os.path.dirname(p['runtime'])
    authored = os.path.join(cdir, 'opening.md')
    cache = os.path.join(cdir, 'opening.generated.json')
    pid, sheet = _active_sheet(rt)
    cast = [v.get('name') for v in (rt.get('active_npcs') or {}).values()]
    if os.path.exists(authored):
        txt = open(authored, encoding='utf-8').read()
        return {'source': 'authored', 'campaign_id': _MOUNTED['id'], 'cinematic_exposition': txt,
                'scene_transition': None, 'immediate_visible_context': rt['campaign'].get('current_location'),
                'active_cast': cast, 'action_window': f"What does {sheet.get('identity', {}).get('name', pid)} do?",
                'mission_summary': ' · '.join(rt['campaign'].get('active_objectives', []))}
    if os.path.exists(cache) and not force_regenerate:
        out = json.load(open(cache, encoding='utf-8'))
        out['source'] = 'persisted'
        return out
    user = json.dumps({
        'canon': rt.get('canon', {}), 'campaign': rt['campaign'],
        'protagonist': {'identity': sheet.get('identity'), 'background': sheet.get('background'), 'soul': sheet.get('soul')},
        'active_cast': cast, 'recent_chronicle': tail_chronicle(6),
    }, ensure_ascii=False)
    try:
        out = _ollama(GM_MODEL, OPENING_SYSTEM, user, temperature=0.8)
        leaks = hidden_leak_screen(json.dumps(out), rt)
        if leaks:
            return {'source': 'blocked', 'error': f'hidden-state leak: {leaks}'}
        out['source'] = 'generated'
        out['campaign_id'] = _MOUNTED['id']
        out['mission_summary'] = ' · '.join(rt['campaign'].get('active_objectives', []))
        out['generated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        json.dump(out, open(cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)  # PERSIST — stable thereafter
        return out
    except Exception as e:
        return {'source': 'unavailable', 'error': str(e)[:200]}


def restart_campaign_from_opening(cid, confirm=False):
    """PHASE A restart flow. BEFORE any destructive reset, snapshot the whole
    campaign dir (contaminated/historical state) into gm/_restart_backups/ as a
    regression fixture. Then clear ONLY the session-projection state and rebuild
    the fresh session from the campaign's builder. The persisted opening crawl,
    authored bible, and immutable foundation are PRESERVED and replayed.

    CLEARED:   runtime_state.json (session), transcript_archive.jsonl,
               chronicle.jsonl, turn_log.jsonl (moved to backup, not deleted).
    RETAINED:  opening.md (authored), opening.generated.json (persisted crawl),
               any campaign_bible.* / character definitions in the dir.
    """
    if not confirm:
        raise ValueError('restart requires explicit confirm=true')
    import shutil
    src = _cdir(cid)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(GM_DATA, '_restart_backups', f'{cid}_{stamp}')
    os.makedirs(backup, exist_ok=True)
    retained = {'opening.md', 'opening.generated.json'}
    retain_prefix = ('campaign_bible', 'character_')
    cleared, kept = [], []
    for fn in os.listdir(src):
        fp = os.path.join(src, fn)
        if not os.path.isfile(fp):
            continue
        if fn in retained or fn.startswith(retain_prefix):
            shutil.copy2(fp, os.path.join(backup, fn))  # copy (preserve in place)
            kept.append(fn)
        else:
            shutil.move(fp, os.path.join(backup, fn))    # move out (cleared, but never destroyed)
            cleared.append(fn)
    prev = _MOUNTED['id']
    _MOUNTED['id'] = None
    meta = mount_campaign(cid)  # rebuilds a fresh session runtime from the builder
    return {'campaign_id': cid, 'restarted': True, 'backup_dir': backup,
            'cleared': cleared, 'retained': kept, 'remounted_from': prev,
            'opening_preserved': os.path.exists(os.path.join(src, 'opening.generated.json')) or os.path.exists(os.path.join(src, 'opening.md')),
            'metadata': meta}


# ---------------------------------------------------------------------------
# THE SINGLE HYDRATION BOUNDARY (Phase A repair). Every player-visible response
# passes through here: string de-escaping (repair legacy \xNN corruption ->
# real Unicode) and the CANONICAL EQUIPMENT CONTRACT normalization. The client
# never guesses shapes; the server guarantees them.
# ---------------------------------------------------------------------------
_XESC = re.compile(r'\\x([0-9A-Fa-f]{2})')


def _deescape(s):
    """Repair strings that carry literal \\xNN escape sequences (legacy data
    corruption) back into real Unicode characters. Idempotent on clean text."""
    if not isinstance(s, str) or '\\x' not in s:
        return s
    return _XESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def _clean(obj):
    if isinstance(obj, str):
        return _deescape(obj)
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    return obj


# CANONICAL EQUIPMENT CONTRACT — every slot is a LIST. Declared once here.
EQUIP_SLOTS = ('weapons', 'armor', 'gear', 'vehicles', 'trinkets', 'starships')


def _as_list(v):
    """null -> [] ; dict/object -> [object] ; list -> list ; scalar -> [scalar]."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def normalize_equipment(sheet):
    """Coerce any historical equipment shape into the canonical all-arrays
    contract, then RE-ROUTE every item by authoritative item_type so a mislabeled
    slot (e.g. a jacket saved under weapons) is corrected at this one boundary."""
    if not isinstance(sheet, dict):
        return sheet
    eq = sheet.get('equipment')
    if not isinstance(eq, dict):
        eq = {}
    pool = []
    for slot in EQUIP_SLOTS:
        pool.extend(_as_list(eq.get(slot)))
    pool.extend(_as_list(eq.get('inventory')))
    routed = route_equipment(pool)  # weapons/armor/gear/vehicles/starships by item_type
    canonical = {s: [] for s in EQUIP_SLOTS}
    for slot in ('weapons', 'armor', 'gear', 'vehicles', 'starships'):
        canonical[slot] = routed.get(slot, [])
    # preserve non-slot equipment metadata (credits, etc.)
    for k, v in eq.items():
        if k not in EQUIP_SLOTS and k != 'inventory':
            canonical[k] = v
    canonical['inventory'] = []
    sheet = {**sheet, 'equipment': canonical}
    return sheet


def player_visible_state():
    if not _MOUNTED['id']:
        return {'mounted': None, 'campaigns': list_campaigns()}
    rt = load_runtime()
    visible = {k: v for k, v in rt.items() if k != 'hidden_gm_state'}
    # normalize every player character's equipment to the canonical contract
    pcs = visible.get('player_characters')
    if isinstance(pcs, dict):
        visible['player_characters'] = {pid: normalize_equipment(sheet) for pid, sheet in pcs.items()}
    # de-escape ALL strings (repair legacy \xNN) + stamp the mount transaction id
    visible = _clean(visible)
    return {'mounted': _MOUNTED['id'], 'campaign_id': _MOUNTED['id'],
            'mount_epoch': _MOUNTED.get('epoch', 0), **visible}


def reset_runtime():
    """Rebuild the MOUNTED campaign's runtime from its builder (fresh session).
    Chronicle and turn log are append-only history — never deleted."""
    cid = _MOUNTED['id']
    if not cid:
        raise RuntimeError('no campaign mounted')
    p = _paths(cid)
    if os.path.exists(p['runtime']):
        os.remove(p['runtime'])
    _MOUNTED['id'] = None
    return mount_campaign(cid)
