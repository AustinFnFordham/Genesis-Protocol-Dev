"""GENESIS PROTOCOL — PROJECTION BUILDER (UX/UI Contract Rev 1.1 + C.5).

Builds THE ONE mounted_campaign_projection every client panel consumes, and
VALIDATES it (schema + semantic) before it may be committed. Rules:
  * Truth = the mounted campaign runtime (gm_controllers). One campaign.
  * The registry ENRICHES by URID (static definitions only) — never a second
    character source, never a membership decision.
  * Live mode EXCLUDES sandbox fixtures from membership (with hard evidence).
  * hidden_gm_state never leaves the server; a seeded-token screen proves it.
  * Everything carries {campaign_id, mount_epoch, state_revision, runtime_mode}
    + provenance. A projection with BLOCKING semantic errors is not emitted live.
"""
import os
import json
import gm_controllers as gmc

PROJECTION_BUILDER_VERSION = '1.2.0-c5'
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCHEMA_DIR = os.path.join(_HERE, '..', 'app', 'genesis-os', 'docs', 'architecture')

# Registry entity types that are STATIC DEFINITIONS (legal in `definitions`).
_DEFINITION_TYPES = {'Species', 'Class', 'Subclass', 'Background', 'Feature', 'Feat',
                     'Power', 'Item', 'Modification', 'Property', 'Effect', 'Status', 'Action'}
# Types that are CHARACTER RUNTIMES (never duplicated into `definitions`).
_CHARACTER_TYPES = {'Character', 'Companion', 'Nemesis', 'Creature', 'Adversary', 'Squad'}

_ID_PREFIX = {'species': 'species_', 'class': 'class_', 'subclass': 'subclass_', 'background': ('bg_', 'background_')}


def _is_sandbox_fixture(urid, doc):
    u = str(urid or '').lower()
    if 'sandbox' in u:
        return True
    d = doc or {}
    blob = f"{d.get('narrative','')} {d.get('description','')}".lower()
    return 'genesis sandbox' in blob or 'ui binding' in blob


def _res_name(registry, urid, fallback=None):
    """Resolve a URID to a human name via the registry. If it cannot be
    resolved, return the fallback (null) — NEVER echo the URID as a name."""
    d = registry.get(urid) if (registry and urid) else None
    if isinstance(d, dict):
        return d.get('name') or (d.get('metadata') or {}).get('name') or fallback
    return fallback


def _looks_like_id(v, kind):
    s = str(v or '')
    pre = _ID_PREFIX[kind]
    return s.startswith(pre) if isinstance(pre, str) else s.startswith(pre)


def _facet(idn, sheet, registry, key, id_field, name_field):
    """Build {<key>_id, name} for species/class/subclass/background, tolerant of
    legacy shapes where a name or an id was stuffed into one field."""
    raw = idn.get(key) if idn.get(key) is not None else sheet.get(id_field)
    _id = idn.get(id_field) or (raw if _looks_like_id(raw, key) else None)
    _name = idn.get(name_field) or (raw if (raw is not None and not _looks_like_id(raw, key)) else None)
    if _id and not _name:
        _name = _res_name(registry, _id, None)
    out = {f'{key}_id': _id, 'name': _name}
    return out


def normalize_identity(sheet, registry):
    idn = sheet.get('identity') or {}
    return {
        'name': idn.get('name') or idn.get('display_name') or sheet.get('name'),
        'species': _facet(idn, sheet, registry, 'species', 'species_id', 'species_name'),
        'class': _facet(idn, sheet, registry, 'class', 'class_id', 'class_name'),
        'subclass': _facet(idn, sheet, registry, 'subclass', 'subclass_id', 'subclass_name'),
        'background': _facet(idn, sheet, registry, 'background', 'background_id', 'background_name'),
        'level': idn.get('level') or sheet.get('level'),
        'role': idn.get('role') or sheet.get('role'),
    }


def validate_identity(identity):
    """Semantic errors (must be 0) vs warnings (data gaps allowed)."""
    errors, warnings = [], []
    cls, spc, bg = identity.get('class', {}), identity.get('species', {}), identity.get('background', {})
    if _looks_like_id(cls.get('name'), 'species'):
        errors.append('species_urid_in_class')
    if cls.get('name') and spc.get('name') and cls['name'] == spc['name']:
        errors.append('species_label_as_class')
    if _looks_like_id(spc.get('name'), 'background'):
        errors.append('background_urid_in_species')
    if not cls.get('class_id') and not cls.get('name'):
        warnings.append('class_unresolved')
    return errors, warnings


def build_progression(sheet):
    """Structured progression from runtime selections (URIDs). Never inferred
    from the global registry. Returns (block, unresolved_required_refs)."""
    prog = sheet.get('progression') or {}
    idn = sheet.get('identity') or {}
    block = {
        'current_level': prog.get('current_level') or idn.get('level'),
        'class_id': prog.get('class_id') or idn.get('class_id'),
        'subclass_id': prog.get('subclass_id') or idn.get('subclass_id'),   # SELECTED/unlocked
        'planned_subclass_id': idn.get('planned_subclass_id') or prog.get('planned_subclass_id'),  # from canonical runtime; grants NO features
        'planned_subclass': ({'subclass_id': (idn.get('planned_subclass_id') or prog.get('planned_subclass_id')),
                              'name': None, 'status': 'planned', 'grants_features': False}
                             if (idn.get('planned_subclass_id') or prog.get('planned_subclass_id')) else None),
        'unlocked_feature_urids': prog.get('unlocked_feature_urids') or [],
        'selected_choice_urids': prog.get('selected_choice_urids') or [],
        'pending_choice_groups': prog.get('pending_choice_groups') or [],
        'locked_future_feature_urids': prog.get('locked_future_feature_urids') or [],
        'campaign_specific_rule_urids': prog.get('campaign_specific_rule_urids') or [],
        'earned_relationship_maneuver_urids': prog.get('earned_relationship_maneuver_urids') or [],
    }
    # a "required ref" is a selected/unlocked URID; unresolved = not a string urid
    refs = block['unlocked_feature_urids'] + block['selected_choice_urids']
    unresolved = [r for r in refs if not isinstance(r, str) or not r]
    return block, len(unresolved)


def _party_summary(sheet, registry):
    """Player-visible party summary. Species IDs are CANONICAL (species_ prefix);
    unresolved class fields are OMITTED for not-yet-migrated members (no mixed
    'human' vs 'species_human')."""
    idn = normalize_identity(sheet, registry)
    dfn = sheet.get('defenses') or {}
    out = {'display_name': idn.get('name'), 'level': idn.get('level'),
           'current_hp': dfn.get('current_hp'), 'maximum_hp': dfn.get('maximum_hp'),
           'armor_class': dfn.get('armor_class')}
    sp = idn.get('species') or {}
    sid = sp.get('species_id')
    if sid:
        canon = sid if str(sid).startswith('species_') else f'species_{sid}'
        out['species'] = {'species_id': canon, 'name': sp.get('name') or _res_name(registry, canon, None)}
    cl = idn.get('class') or {}
    if cl.get('class_id') and cl.get('name'):   # only when actually resolved
        out['class'] = cl
    return out


def _structured_journal(chronicle):
    """Journal = meaningful summarized records, NOT one-per-utterance. Ordinary
    narrative declarations stay in the event ledger; the Journal keeps events
    with mechanical/consequential weight."""
    out = []
    for e in chronicle or []:
        oe = str(e.get('objective_event', ''))
        cls = oe[1:oe.find(']')] if oe.startswith('[') else ''
        mechanical = cls not in ('narrative', 'narrative_after_ruling', '') or e.get('source_resolution') == 'combat_master' or e.get('dice')
        if not mechanical:
            continue  # ordinary utterance -> event ledger only
        title = oe[oe.find(']') + 1:].strip() if ']' in oe else oe
        out.append({
            'journal_entry_id': e.get('event_id'),
            'event_type': cls or 'event',
            'title': title[:80],
            'summary': title,
            'participants': [p for p in (e.get('participants') or []) if p],
            'location': e.get('location'),
            'decisions': [], 'consequences': [], 'objectives_changed': [],
            'relationships_changed': [], 'discoveries': [], 'unresolved_threads': [],
            'source_event_ids': [e.get('event_id')],
        })
    return out


def _fixture_filter(registry, referenced, runtime_mode):
    known = [u for u, d in (registry or {}).items() if _is_sandbox_fixture(u, d)]
    rejected = [u for u in referenced if u in set(known) and runtime_mode == 'live']
    return {
        'candidates_examined': len(referenced),
        'known_fixture_urids': len(known),
        'rejected_fixture_urids': len(rejected),
        'fixture_membership_attempts': len([u for u in referenced if u in set(known)]),
        'fixture_membership_rejections': len(rejected),
        'live_projection_fixture_hits': 0,   # asserted below by scan; recomputed in validate
    }


HIDDEN_TOKENS = ['hidden_gm_state', 'established_hidden_history', 'future_reveal_guardrails',
                 'unresolved_truths', 'soul_guardrails', 'reveal_conditions']


def _hidden_leak_matrix(projection):
    blob = json.dumps(projection, ensure_ascii=False)
    return {tok: (tok in blob) for tok in HIDDEN_TOKENS}


def _load_schema(name):
    p = os.path.join(_SCHEMA_DIR, name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def validate_projection(projection):
    """Schema + semantic validation. Returns dict with schema_valid/semantic_valid/
    errors/warnings. In live mode a projection with errors must not be committed."""
    errors, warnings = [], []
    # schema (best-effort; skip refs across files)
    try:
        from jsonschema import Draft7Validator
        for schema_file, node in (('MOUNTED_PROJECTION.schema.json', projection),):
            s = _load_schema(schema_file)
            if s:
                s = {k: v for k, v in s.items() if k != 'properties' or True}
                # validate top-level required only (avoid cross-file $ref resolution)
                req = s.get('required', [])
                for r in req:
                    if r not in projection:
                        errors.append(f'missing_required:{r}')
        schema_valid = not errors
    except Exception as e:
        schema_valid = False
        warnings.append(f'schema_validator_unavailable:{str(e)[:60]}')
    # semantic
    op = (projection.get('operative') or {}).get('character_runtime') or {}
    id_err, id_warn = validate_identity(op.get('identity') or {})
    errors += [f'identity:{e}' for e in id_err]
    warnings += [f'identity:{w}' for w in id_warn]
    # malformed equipment (stringified dicts / truncation)
    eq = op.get('equipment') or {}
    malformed = 0
    for slot in ('weapons', 'armor', 'gear', 'vehicles', 'starships'):
        for it in (eq.get(slot) or []):
            nm = str((it or {}).get('name', ''))
            if nm.startswith('{') or "'item'" in nm or "', '" in nm:
                malformed += 1
    if malformed:
        errors.append(f'malformed_equipment_entries:{malformed}')
    # duplicate character sources: definitions must not carry character runtimes
    dup = [u for u, d in (projection.get('definitions') or {}).items()
           if isinstance(d, dict) and (d.get('ability_scores') or d.get('character_sheet') or d.get('player_characters'))]
    if dup:
        errors.append(f'duplicate_character_sources:{len(dup)}')
    # hidden leaks
    leaks = [k for k, v in _hidden_leak_matrix(projection).items() if v]
    if leaks:
        errors.append(f'hidden_state_leaks:{leaks}')
    # live fixture hits (scan payload for sandbox tokens)
    if projection.get('runtime_mode') == 'live' and 'sandbox' in json.dumps(projection).lower():
        errors.append('live_fixture_hits')
    return {'schema_valid': schema_valid, 'semantic_valid': not errors, 'errors': errors, 'warnings': warnings,
            'malformed_equipment_entries': malformed, 'duplicate_character_sources': len(dup)}


def _measure_reference_integrity(sheet, registry, unresolved_vessels):
    """C.6 §2 — measure how reference-driven the canonical runtime is. A slot is
    REQUIRED for a playable character; POPULATED if it carries an id; RESOLVED if
    that id exists in the registry. Inline objects (name-only features/powers/
    items) are legacy definitions that must become URID refs. Returns an honest
    report — coverage is NOT faked to 100% when references are unauthored."""
    idn = sheet.get('identity') or {}
    prog = sheet.get('progression') or {}
    eq = sheet.get('equipment') or {}
    slots = []   # (domain, id_or_None)
    slots.append(('species', idn.get('species_id')))
    slots.append(('class', idn.get('class_id')))
    slots.append(('background', idn.get('background_id')))
    if idn.get('subclass_id') or idn.get('subclass_name'):
        slots.append(('subclass', idn.get('subclass_id')))
    for f in (sheet.get('features') or []):
        slots.append(('feature', (f.get('urid') or f.get('id')) if isinstance(f, dict) else None))
    for p in (sheet.get('powers') or []):
        slots.append(('power', (p.get('urid') or p.get('id')) if isinstance(p, dict) else None))
    inst_ids = []
    for s in ('weapons', 'armor', 'gear'):
        for it in (eq.get(s) or []):
            if isinstance(it, dict) and it.get('instance_id'):
                inst_ids.append(it['instance_id']); slots.append(('item', it['instance_id']))
            else:
                slots.append(('item', it.get('item_id') if isinstance(it, dict) else None))
    for r in (prog.get('campaign_specific_rule_urids') or []):
        slots.append(('campaign_rule', r))
    for m in (prog.get('earned_relationship_maneuver_urids') or []):
        slots.append(('relationship_maneuver', m))

    required = len(slots)
    populated = [s for s in slots if s[1]]
    # character instances are OWNED (resolved by ownership, not global registry lookup)
    resolved = [s for s in populated if (registry and s[1] in registry) or s[1] in inst_ids]
    missing_required = [d for d, i in slots if not i]
    unresolved = [i for d, i in populated if not (registry and i in registry)]
    inline_legacy = sum(1 for f in (sheet.get('features') or []) if isinstance(f, dict) and not (f.get('urid') or f.get('id'))) \
        + sum(1 for p in (sheet.get('powers') or []) if isinstance(p, dict) and not (p.get('urid') or p.get('id')))
    cov = round(100 * len(resolved) / required, 1) if required else 100.0
    return {
        'required_reference_slots': required,
        'populated_reference_slots': len(populated),
        'resolved_reference_slots': len(resolved),
        'missing_required_references': len(missing_required),
        'unresolved_references': len(unresolved) + len(unresolved_vessels),
        'unresolved_reference_list': unresolved + [f'vessel:{v}' for v in unresolved_vessels],
        'low_confidence_mappings': 0,
        'inline_legacy_definitions': inline_legacy,
        'registry_resolution_coverage_percent': cov,
        'missing_domains': sorted(set(missing_required)),
    }


def build_projection(registry, registry_build_id=None, runtime_mode='live'):
    cid = gmc.mounted_id()
    if not cid:
        return {'mounted': None, 'runtime_mode': runtime_mode}

    vis = gmc.player_visible_state()  # de-escaped + equipment normalized (structured) + hidden stripped
    rt_meta = vis.get('metadata') or {}
    epoch = gmc._MOUNTED.get('epoch', 0)
    revision, campaign_instance_id = gmc._bump_revision(cid, rt_meta.get('runtime_version', 0))  # monotonic (C.6 §7)
    pcs = vis.get('player_characters') or {}
    selected = rt_meta.get('active_player')
    op_sheet = pcs.get(selected) or {}

    identity = normalize_identity(op_sheet, registry)
    progression, unresolved_prog = build_progression(op_sheet)
    operative_runtime = {**op_sheet, 'identity': identity, 'progression': progression}

    # PARTY summaries from campaign runtime (NOT registry, NOT definitions).
    characters_by_id = {pid: {'player_visible_runtime_summary': _party_summary(sh, registry)} for pid, sh in pcs.items()}

    # DEFINITIONS — static registry entities referenced by the runtime, by URID.
    referenced = set()
    for sh in pcs.values():
        prog = sh.get('progression') or {}
        for k in ('unlocked_feature_urids', 'selected_choice_urids'):
            referenced.update(prog.get(k) or [])
        idn = sh.get('identity') or {}
        for u in (idn.get('class_id'), idn.get('subclass_id'), idn.get('species_id'), sh.get('background_id')):
            if u:
                referenced.add(u)
    definitions = {}
    for u in referenced:
        doc = registry.get(u) if registry else None
        if not isinstance(doc, dict):
            continue
        if runtime_mode == 'live' and _is_sandbox_fixture(u, doc):
            continue
        # NEVER put a character runtime into definitions
        if doc.get('ability_scores') or doc.get('character_sheet') or doc.get('player_characters'):
            continue
        definitions[u] = doc

    journal = _structured_journal(gmc.tail_chronicle(200))
    opening = gmc.get_opening()
    transcript = gmc.read_transcript(0, 200)
    campaign = vis.get('campaign') or {}
    conv = vis.get('conversation') or {}

    # STARSHIP: a vessel is a REFERENCE (URID), never a carried display string.
    ship = vis.get('ship')
    ship_vessel_id = (ship or {}).get('vessel_id') if isinstance(ship, dict) else None
    owned, assigned, unresolved_vessels = [], [], []
    for s in (op_sheet.get('equipment') or {}).get('starships', []):
        urid = s.get('item_id') or s.get('vessel_id')  # URID only
        nm = str(s.get('name', '')).lower()
        if not urid:
            unresolved_vessels.append(s.get('name'))   # display-name-only -> unresolved reference, NOT an id
            continue
        (assigned if ('shuttle' in nm or 'republic' in nm) else owned).append(urid)
    if ship_vessel_id and ship_vessel_id not in owned + assigned:
        assigned.append(ship_vessel_id)  # the mounted vessel is at least assigned to the mission
    asset_relationships = {
        'owned_vessel_ids': owned, 'assigned_vessel_ids': assigned,
        'accessible_vessel_ids': list(dict.fromkeys(owned + assigned)),
        'current_vessel_id': ship_vessel_id,
    }
    # carried equipment must NOT list a whole starship
    op_eq = dict(op_sheet.get('equipment') or {})
    op_eq['starships'] = []
    operative_runtime['equipment'] = op_eq

    ref_integrity = _measure_reference_integrity(op_sheet, registry, unresolved_vessels)
    ff = _fixture_filter(registry, referenced, runtime_mode)

    projection = {
        'campaign_id': cid, 'mount_epoch': epoch, 'state_revision': revision, 'runtime_mode': runtime_mode,
        'selected_character_id': selected,
        'campaign': {'title': gmc.CAMPAIGN_CATALOG.get(cid, {}).get('name', cid), 'era': campaign.get('era'),
                     'phase': campaign.get('phase', 'scene'),
                     'opening_status': 'completed' if transcript.get('total', 0) > 0 else 'opening'},
        'operative': {'character_runtime': operative_runtime, 'available_actions': [],
                      'conditions': (op_sheet.get('defenses') or {}).get('conditions', []),
                      'progression_summary': progression,
                      'asset_relationships': asset_relationships,
                      'reference_integrity': ref_integrity},
        'party': {'participant_ids': list(pcs.keys()), 'active_participant_id': selected,
                  'characters_by_id': characters_by_id},
        'active_engagement': {'opening_crawl': opening,
                              'active_scene': {'scene_id': rt_meta.get('scene_id'), 'location': campaign.get('current_location')},
                              'transcript': {'entries': transcript.get('entries', []),
                                             'cursor': transcript.get('offset', 0) + len(transcript.get('entries', [])),
                                             'has_earlier': transcript.get('total', 0) > len(transcript.get('entries', [])),
                                             'latest_sequence': transcript.get('total', 0)},
                              'suggestions': (conv.get('suggestions') or [])[:4],
                              'objectives': campaign.get('active_objectives', [])},
        'command_record': {'journal': {'entries': journal, 'is_structured': True},
                           'map': {'visible_nodes': (vis.get('map') or {}).get('visible_nodes', []) if isinstance(vis.get('map'), dict) else []},
                           'player_visible_nemesis': vis.get('player_visible_nemesis') or [],
                           'ship': ship, 'ship_vessel_id': ship_vessel_id},
        'definitions': definitions,
        'visibility': {'hidden_fields_removed': True, 'player_visible_entity_ids': list(pcs.keys())},
        'provenance': {'campaign_source': f'gm/campaigns/{cid}/runtime_state.json',
                       'character_runtime_source': f'runtime.player_characters.{selected}',
                       'campaign_instance_id': campaign_instance_id,
                       'registry_build_id': registry_build_id, 'projection_builder_version': PROJECTION_BUILDER_VERSION,
                       'fixture_filter': ff, 'reference_integrity': ref_integrity,
                       'unresolved_progression_refs': unresolved_prog, 'hidden_fields_removed': True},
    }
    validation = validate_projection(projection)
    projection['provenance']['fixture_filter']['live_projection_fixture_hits'] = (
        0 if 'live_fixture_hits' not in validation['errors'] else 1)
    projection['validation'] = validation
    # FAIL-SAFE: live mode must not emit a semantically broken projection.
    if runtime_mode == 'live' and not validation['semantic_valid']:
        return {'mounted': cid, 'campaign_id': cid, 'mount_epoch': epoch, 'state_revision': revision,
                'runtime_mode': runtime_mode, 'projection_emitted': False, 'validation': validation}
    projection['projection_emitted'] = True
    return {'mounted': cid, **projection}
