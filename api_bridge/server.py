"""GENESIS//OS — Local API Bridge (FastAPI, sits alongside Ollama).

Kills frontend hardcoding: scans the Gold stores on launch, builds the O(1)
URID registry in memory, and serves entities dynamically. Also persists the
live CampaignState save file (the Campaign Initialization Loop's backend half)
and proxies portrait requests to the anchors dir / ComfyUI.

Run:  pip install fastapi uvicorn pyyaml --break-system-packages (once)
      python server.py            -> http://localhost:8788
Endpoints:
  GET  /api/v1/registry                    boot payload {registry, manifest, campaign}
  GET  /api/v1/entities/{urid}             single entity, O(1)
  GET  /api/v1/status                      pipeline_status.json passthrough
  POST /api/v1/campaign                    persist CampaignState -> saves/save_state.json
  GET  /api/v1/campaign                    load persisted CampaignState
  POST /api/v1/patch/{urid}                apply RFC6902 batch to in-memory entity (+persist snapshot)
  GET  /api/v1/portrait/{character_id}     anchor png if generated, else 404 (UI keeps placeholder)
  POST /api/v1/ledger                      append event envelope -> saves/event_ledger.jsonl (append-only)
  GET  /api/v1/ledger                      tail of the ledger (?n=50)
  POST /api/v1/generate/entity             AI CONTENT PIPELINE: brief -> qwen -> deterministic repair
                                           -> schema validation gate -> campaign-local store w/ provenance
  GET  /api/v1/generate/health             Ollama reachability + model list
"""
import json
import os
import time

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

FORGE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'SW5e_Data_Hub', 'forge_v3'))
CAMPAIGN_LOCAL = os.path.join(FORGE, 'data', 'campaign_local')
GOLD_STORES = [os.path.join(FORGE, 'data', 'gold'), os.path.join(FORGE, 'data', 'sandbox_gold'), CAMPAIGN_LOCAL]
os.makedirs(CAMPAIGN_LOCAL, exist_ok=True)
ANCHORS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'genesis-os', 'anchors'))
SAVES = os.path.join(os.path.dirname(__file__), 'saves')
os.makedirs(SAVES, exist_ok=True)
os.makedirs(ANCHORS, exist_ok=True)

app = FastAPI(title='Genesis Local API Bridge')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

REGISTRY: dict = {}
MANIFEST: list = []


def _ingest_file(path, schema_hint):
    try:
        if path.endswith(('.yml', '.yaml')):
            doc = yaml.safe_load(open(path, encoding='utf-8'))
        else:
            doc = json.load(open(path, encoding='utf-8'))
    except Exception:
        return
    if isinstance(doc, list):
        doc = {'items': doc, 'metadata': {'id': f'sandbox_{schema_hint.lower()}', 'name': schema_hint}}
    if not isinstance(doc, dict):
        return
    urid = (doc.get('metadata') or {}).get('id') or doc.get('id') or f'sandbox_{schema_hint.lower()}'
    if urid in REGISTRY:
        urid = f'{urid}__{schema_hint.lower()}'
    REGISTRY[urid] = doc
    MANIFEST.append({
        'urid': urid, 'schema': schema_hint, 'tier': 'gold',
        'name': (doc.get('metadata') or {}).get('name') or doc.get('name') or schema_hint,
    })


def build_registry():
    """O(1) mandate: one scan at launch, dict lookups forever after."""
    REGISTRY.clear()
    MANIFEST.clear()
    t0 = time.time()
    for store in GOLD_STORES:
        if not os.path.isdir(store):
            continue
        for dirpath, dirs, files in os.walk(store):
            dirs[:] = [d for d in dirs if d != '.forge_runs']
            for f in sorted(files):
                if not f.endswith(('.yml', '.yaml')) or 'report' in f or 'summary' in f or f.endswith('.bak'):
                    continue
                if f.endswith('.sandbox.yml'):
                    hint = f[:-len('.sandbox.yml')].split('__')[0]
                else:
                    # gold tree layout: category dir is the schema hint
                    rel = os.path.relpath(dirpath, store)
                    hint = (rel.split(os.sep)[0] if rel != '.' else 'Entity').rstrip('s').capitalize()
                _ingest_file(os.path.join(dirpath, f), hint)
    _load_golden_slice()
    global REGISTRY_BUILD_ID
    REGISTRY_BUILD_ID = f'reg_{len(REGISTRY)}_{int(t0)}'
    print(f'registry built: {len(REGISTRY)} entities in {int((time.time()-t0)*1000)}ms')


GOLDEN_SLICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'registry', 'golden_slice'))


def _load_golden_slice():
    """C.6: ingest the golden-slice reference lane (records keyed by 'urid').
    These are the resolved/authored definitions the mounted runtimes reference."""
    if not os.path.isdir(GOLDEN_SLICE_DIR):
        return
    n = 0
    for dirpath, dirs, files in os.walk(GOLDEN_SLICE_DIR):
        if os.path.basename(dirpath) in ('migration', 'validation', 'manifests'):
            continue
        for f in sorted(files):
            if not f.endswith(('.yml', '.yaml')):
                continue
            try:
                doc = yaml.safe_load(open(os.path.join(dirpath, f), encoding='utf-8'))
            except Exception:
                continue
            urid = (doc or {}).get('urid')
            if not urid:
                continue
            REGISTRY[urid] = doc
            MANIFEST.append({'urid': urid, 'schema': doc.get('entity_type', 'Entity'),
                             'tier': 'golden_slice', 'name': doc.get('name', urid)})
            n += 1
    print(f'golden_slice lane loaded: {n} records')


@app.on_event('startup')
def _startup():
    build_registry()


@app.get('/api/v1/registry')
def get_registry():
    campaign = load_campaign_from_disk()
    if campaign is None:
        campaign = next((REGISTRY[m['urid']] for m in MANIFEST if m['schema'] == 'CampaignState'), {})
    return {'registry': REGISTRY, 'manifest': MANIFEST, 'campaign': campaign,
            'pipeline': 'Genesis Protocol / Forge V3 / API bridge (live scan)'}


@app.get('/api/v1/entities/{urid}')
def get_entity(urid: str):
    if urid not in REGISTRY:
        raise HTTPException(404, f'unknown URID: {urid}')
    return REGISTRY[urid]


@app.get('/api/v1/status')
def get_status():
    p = os.path.join(FORGE, 'pipeline_status.json')
    if not os.path.exists(p):
        raise HTTPException(404, 'run tools/pipeline_status.py first')
    return json.load(open(p, encoding='utf-8'))


def load_campaign_from_disk():
    p = os.path.join(SAVES, 'save_state.json')
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    return None


@app.post('/api/v1/campaign')
async def save_campaign(req: Request):
    state = await req.json()
    p = os.path.join(SAVES, 'save_state.json')
    json.dump(state, open(p, 'w', encoding='utf-8'), indent=1)
    # snapshot history for the journal / replay
    json.dump(state, open(os.path.join(SAVES, f'save_{time.strftime("%Y%m%d_%H%M%S")}.json'), 'w', encoding='utf-8'))
    return {'saved': True, 'path': p}


@app.get('/api/v1/campaign')
def get_campaign():
    c = load_campaign_from_disk()
    if c is None:
        raise HTTPException(404, 'no save state yet')
    return c


@app.post('/api/v1/patch/{urid}')
async def patch_entity(urid: str, req: Request):
    """RFC6902 batch against the in-memory registry (server-side patch bus)."""
    import jsonpatch
    if urid not in REGISTRY:
        raise HTTPException(404, f'unknown URID: {urid}')
    ops = await req.json()
    try:
        REGISTRY[urid] = jsonpatch.apply_patch(REGISTRY[urid], ops)
    except Exception as e:
        raise HTTPException(422, f'patch rejected: {e}')
    return {'applied': len(ops), 'urid': urid}


# ---------------------------------------------------------------------------
# THE EVENT LEDGER — append-only (GEN-ARCH-002). Never edited, never deleted.
# ---------------------------------------------------------------------------
LEDGER_PATH = os.path.join(SAVES, 'event_ledger.jsonl')


@app.post('/api/v1/ledger')
async def append_ledger(req: Request):
    envelope = await req.json()
    with open(LEDGER_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(envelope, ensure_ascii=False) + '\n')
    return {'appended': True}


@app.get('/api/v1/ledger')
def read_ledger(n: int = 50):
    if not os.path.exists(LEDGER_PATH):
        return {'events': [], 'total': 0}
    lines = open(LEDGER_PATH, encoding='utf-8').read().splitlines()
    return {'events': [json.loads(l) for l in lines[-n:] if l.strip()], 'total': len(lines)}


# ---------------------------------------------------------------------------
# THE AI CONTENT PIPELINE (runtime Creator engine).
# The AI proposes; deterministic engines validate and execute (Article law):
#   brief -> qwen (Ollama) -> deterministic repair (forge tools) ->
#   schema validation gate (must be ZERO violations) ->
#   campaign-local store with provenance -> O(1) registry.
# A model response that fails the gate NEVER becomes truth — repair fixes it
# deterministically or the request reports failure.
# ---------------------------------------------------------------------------
import sys as _sys
_sys.path.insert(0, os.path.join(FORGE, 'tools'))

OLLAMA = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
GEN_MODEL = os.environ.get('GENESIS_GEN_MODEL', 'qwen2.5-coder:32b')


def _forge_tools():
    import build_genesis_sandbox as bgs
    return bgs


def _load_schema(schema_name: str):
    p = os.path.join(FORGE, 'schemas', f'{schema_name}.schema.json')
    if not os.path.exists(p):
        raise HTTPException(404, f'no such schema: {schema_name}')
    return json.load(open(p, encoding='utf-8'))


def _call_ollama(prompt: str, timeout=420):
    import urllib.request
    body = json.dumps({
        'model': GEN_MODEL, 'prompt': prompt, 'stream': False, 'format': 'json',
        'options': {'temperature': 0.7, 'num_predict': 4096},
    }).encode()
    req = urllib.request.Request(f'{OLLAMA}/api/generate', data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())['response']


def _gen_prompt(schema_name, schema, brief, urid):
    trimmed = {k: v for k, v in schema.items() if k not in ('$defs', 'definitions')}
    return (
        'You are the Genesis Creator engine for a Star Wars TTRPG. '
        f'Author ONE {schema_name} entity as a single JSON object.\n'
        f'CREATIVE BRIEF:\n{brief}\n\n'
        f'The object MUST satisfy this JSON Schema (draft 2020-12):\n{json.dumps(trimmed)[:12000]}\n\n'
        f'Rules: id/metadata.id = "{urid}". Fill required fields with rich, '
        'era-appropriate Star Wars content matching the brief. No markdown, no commentary — '
        'output ONLY the JSON object.'
    )


@app.get('/api/v1/generate/health')
def generate_health():
    try:
        import urllib.request
        with urllib.request.urlopen(f'{OLLAMA}/api/tags', timeout=5) as r:
            models = [m['name'] for m in json.loads(r.read()).get('models', [])]
        return {'ollama': True, 'models': models, 'default': GEN_MODEL}
    except Exception as e:
        return {'ollama': False, 'error': str(e), 'default': GEN_MODEL}


@app.post('/api/v1/generate/entity')
async def generate_entity(req: Request):
    """{schema, brief, urid?, model?} -> validated entity with provenance."""
    body = await req.json()
    schema_name = body.get('schema')
    brief = body.get('brief', '')
    if not schema_name:
        raise HTTPException(422, 'schema is required')
    schema = _load_schema(schema_name)
    bgs = _forge_tools()
    slug = body.get('urid') or f'{schema_name.lower()}_{bgs.slugify(brief[:40]) or "generated"}'

    # 1. THE AI PROPOSES
    raw, gen_error = {}, None
    try:
        txt = _call_ollama(_gen_prompt(schema_name, schema, brief, slug))
        raw = json.loads(txt)
        if not isinstance(raw, dict):
            raw, gen_error = {}, 'model returned non-object'
    except Exception as e:
        gen_error = f'ollama unavailable/failed: {e}'

    # 2. DETERMINISTIC ENGINES VALIDATE AND EXECUTE
    doc = raw if isinstance(raw, dict) else {}
    for key in ('id',):
        doc.setdefault(key, slug)
    if isinstance(doc.get('metadata'), dict):
        doc['metadata']['id'] = slug
    repair_log = []
    try:
        doc, _repaired_ok = bgs.repair(doc, schema, repair_log)
    except Exception as e:
        raise HTTPException(500, f'repair engine error: {e}')

    # 3. THE VALIDATION GATE — zero violations or it does not exist
    validator = bgs.validator_for(schema)
    violations = [f'{"/".join(map(str, err.path)) or "<root>"}: {err.message[:160]}'
                  for err in validator.iter_errors(doc)]
    if violations:
        return {'accepted': False, 'urid': slug, 'violations': violations,
                'gen_error': gen_error, 'repair_ops': len(repair_log)}

    # 4. PROVENANCE + CAMPAIGN-LOCAL STORE (never touches gold)
    doc['_provenance'] = {
        'pipeline': 'runtime_creator_v1',
        'model': None if gen_error else GEN_MODEL,
        'brief': brief,
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'repair_ops': len(repair_log),
        'deterministic_fallback': bool(gen_error),
        'tier': 'campaign_local',
    }
    out = os.path.join(CAMPAIGN_LOCAL, f'{schema_name}__{slug}.yml')
    yaml.safe_dump(doc, open(out, 'w', encoding='utf-8'), allow_unicode=True, sort_keys=False)

    # 5. O(1) REGISTRY — live immediately, no restart
    REGISTRY[slug] = doc
    MANIFEST.append({'urid': slug, 'schema': schema_name, 'tier': 'campaign', 'name': doc.get('name') or (doc.get('metadata') or {}).get('name') or slug})
    return {'accepted': True, 'urid': slug, 'violations': [], 'gen_error': gen_error,
            'repair_ops': len(repair_log), 'path': out, 'doc': doc}


# ---------------------------------------------------------------------------
# THE FOUR-CONTROLLER AI GM (GENESIS_GM_ARCHITECTURE.md)
# GM performs the world · Combat Master resolves conflict ·
# Record Keeper preserves truth · Steward keeps the system honest.
# ---------------------------------------------------------------------------
import gm_controllers as gmc


@app.get('/api/v1/gm/campaigns')
def gm_campaigns():
    return {'campaigns': gmc.list_campaigns(), 'mounted': gmc.mounted_id()}


@app.post('/api/v1/gm/mount')
async def gm_mount(req: Request):
    body = await req.json()
    cid = body.get('campaign_id')
    try:
        meta = gmc.mount_campaign(cid)
        return {'mounted': cid, 'metadata': meta}
    except Exception as e:
        raise HTTPException(422, f'mount failed: {e}')


@app.post('/api/v1/gm/unmount')
def gm_unmount():
    return {'unmounted': gmc.unmount_campaign()}


@app.post('/api/v1/gm/turn')
async def gm_turn_endpoint(req: Request):
    body = await req.json()
    declaration = (body.get('declaration') or '').strip()
    if not declaration:
        raise HTTPException(422, 'declaration is required')
    if not gmc.mounted_id():
        raise HTTPException(409, 'no campaign mounted — select a campaign first')
    try:
        res = gmc.run_turn(declaration, idempotency_key=body.get('idempotency_key'))
        res['campaign_id'] = gmc.mounted_id()
        res['mount_epoch'] = gmc._MOUNTED.get('epoch', 0)
        return res
    except Exception as e:
        raise HTTPException(500, f'gm turn failed: {e}')


@app.get('/api/v1/gm/transcript')
def gm_transcript(offset: int = 0, limit: int = 100):
    if not gmc.mounted_id():
        raise HTTPException(409, 'no campaign mounted')
    return gmc.read_transcript(offset, limit)


@app.get('/api/v1/gm/state')
def gm_state():
    """Player-visible runtime slice. hidden_gm_state never leaves the server."""
    return gmc.player_visible_state()


import projection as _proj
RUNTIME_MODE = os.environ.get('GENESIS_DATA_MODE', 'live')  # live | test | development
REGISTRY_BUILD_ID = None  # set at build_registry time


@app.get('/api/v1/gm/projection')
def gm_projection():
    """THE ONE mounted campaign projection (UX/UI Contract Rev 1.1). Every panel
    consumes this; registry enriches by URID but never decides membership; live
    mode excludes sandbox fixtures; carries campaign_id/epoch/revision + provenance."""
    if not gmc.mounted_id():
        return {'mounted': None, 'runtime_mode': RUNTIME_MODE}
    return _proj.build_projection(REGISTRY, registry_build_id=REGISTRY_BUILD_ID, runtime_mode=RUNTIME_MODE)


@app.post('/api/v1/gm/reset')
def gm_reset():
    return {'reset': True, 'metadata': gmc.reset_runtime()}


@app.get('/api/v1/gm/opening')
def gm_opening():
    if not gmc.mounted_id():
        raise HTTPException(409, 'no campaign mounted')
    return gmc.get_opening()


@app.post('/api/v1/gm/restart')
async def gm_restart(req: Request):
    """Restart a campaign FROM ITS OPENING. Backs up all current state as a
    regression fixture BEFORE clearing session state; preserves the persisted
    opening crawl and immutable foundation. Requires explicit confirm."""
    body = await req.json()
    cid = body.get('campaign_id') or gmc.mounted_id()
    if not cid:
        raise HTTPException(422, 'campaign_id required')
    try:
        return gmc.restart_campaign_from_opening(cid, confirm=bool(body.get('confirm')))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get('/api/v1/gm/item_check')
def gm_item_check(character_id: str):
    """Deterministic item-slot validation for a mounted character sheet."""
    if not gmc.mounted_id():
        raise HTTPException(409, 'no campaign mounted')
    rt = gmc.player_visible_state()
    sheet = (rt.get('player_characters') or {}).get(character_id)
    if sheet is None:
        raise HTTPException(404, f'no such character in mounted campaign: {character_id}')
    return {'character_id': character_id, 'violations': gmc.validate_item_slots(sheet)}


@app.get('/api/v1/gm/chronicle')
def gm_chronicle(n: int = 20):
    return {'entries': gmc.tail_chronicle(n), 'campaign_id': gmc.mounted_id(),
            'mount_epoch': gmc._MOUNTED.get('epoch', 0)}


@app.get('/api/v1/portrait/{character_id}')
def get_portrait(character_id: str):
    for ext in ('.png', '.jpg', '.webp'):
        p = os.path.join(ANCHORS, character_id + ext)
        if os.path.exists(p):
            return FileResponse(p)
    raise HTTPException(404, 'anchor not generated yet — UI keeps its placeholder')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8788, log_level='warning')
