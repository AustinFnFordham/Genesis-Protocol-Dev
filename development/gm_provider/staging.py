"""Isolated staging copies for provider tests and demonstrations. Never touches a source campaign."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from gateway import Gateway   # noqa: E402
from store import SqliteStore, GitStore  # noqa: E402

SOURCE = ROOT / "campaigns/starwars_litrpg/runs/sandbox"


def make(directory, campaign_id="provider-staging", experimental=False, lease_ms=180000, clock=None, source=SOURCE):
    """Copy a source campaign into `directory` and seed a fresh store with its published view."""
    directory = Path(directory)
    campaign = directory / "campaign"
    shutil.copytree(source, campaign)
    if experimental:
        (campaign / "experimental_resolution.json").write_text(json.dumps(
            {"enabled": True, "canonical": False, "campaign_id": campaign_id, "controlled_actors": ["aero"]}))
    store = SqliteStore(directory / "store.sqlite")
    kwargs = {"lease_ms": lease_ms}
    if clock:
        kwargs["clock"] = clock
    gateway = Gateway(campaign, campaign_id, store, **kwargs)
    first = gateway.public_state()
    import export_state
    documents = export_state.publish_set(export_state.build(campaign_dir=campaign, campaign_id=campaign_id))
    for name, page in documents["pages"].items():
        store.put("view/" + name, page, 0)
    store.put("view/state", documents["state"], 0)
    return gateway, first


def declare(gateway, action_id, text=None, steps=None, provider=None, settings=None):
    """Build an action against the current public revision, exactly as a player client would."""
    public = gateway.public_state()
    context = public["state"]["turn_context"]
    ui = ROOT / "campaigns/starwars_litrpg/ui/turn_contract.js"
    path = gateway.campaign.parent / "declare_context.json"
    path.write_text(json.dumps(context))
    if steps is not None:
        declaration = {"actor": "aero", "source": "composer", "freeform": "", "unmapped": [], "steps": steps}
        out = json.loads(subprocess.run(["node", str(ui), "validate", "-", str(path)], input=json.dumps(declaration),
                                        capture_output=True, text=True).stdout)
        declaration = out.get("declaration", declaration)
    else:
        declaration = json.loads(subprocess.check_output(["node", str(ui), "parse", text, str(path)], text=True))["declaration"]
    action = {"action_id": action_id, "campaign_id": gateway.id, "actor": "aero", "text": text or "",
              "declaration": declaration, "contract": "turn-contract/3", **copy.deepcopy(public["cursor"])}
    action["based_on_revision"] = action.pop("revision")
    action.pop("campaign_id", None)
    action["campaign_id"] = gateway.id
    if provider:
        action["gm_provider"] = provider
    if settings:
        action["resolution_settings"] = settings
    return action


IGNORE = ".ledger_writer.lock\ndeclare_context.json\n*.tmp\ntmp*.json\n__pycache__/\n"


def make_shared(scope, campaign_id, experimental=False, source=SOURCE, note=""):
    """Create a shared staging environment inside a git clone and push it. `scope` is a directory in the
    clone, for example <clone>/staging/shared-1. Refuses to reuse an existing scope."""
    scope = Path(scope)
    if scope.exists():
        raise ValueError("this shared environment already exists")
    campaign = scope / "campaign"
    shutil.copytree(source, campaign, ignore=shutil.ignore_patterns(".ledger_writer.lock", "__pycache__"))
    if experimental:
        (campaign / "experimental_resolution.json").write_text(json.dumps(
            {"enabled": True, "canonical": False, "campaign_id": campaign_id, "controlled_actors": ["aero"]}))
    (scope / ".gitignore").write_text(IGNORE)
    (scope / "environment.json").write_text(json.dumps({
        "schema": "genesis-shared-staging/1", "campaign_id": campaign_id, "canonical": False,
        "source": str(Path(source).resolve().relative_to(ROOT)), "experimental_resolution": experimental,
        "note": note or "Isolated staging copy. Not a canonical campaign. Safe to delete."}, indent=1))
    gateway = open_shared(scope, min_sync_s=0)
    import export_state
    documents = export_state.publish_set(export_state.build(campaign_dir=campaign, campaign_id=campaign_id))
    for name, page in documents["pages"].items():
        (gateway.store._path("view/" + name)).parent.mkdir(parents=True, exist_ok=True)
        gateway.store._path("view/" + name).write_text(json.dumps({"version": 1, "data": page}, ensure_ascii=False, indent=1))
    gateway.store._path("view/state").write_text(json.dumps({"version": 1, "data": documents["state"]}, ensure_ascii=False, indent=1))
    gateway.store.checkpoint("environment created")
    return gateway


def open_shared(scope, lease_ms=600000, clock=None, min_sync_s=2.0):
    """Open a shared environment from this clone. The lease defaults to ten minutes: agent sessions think slowly."""
    scope = Path(scope)
    environment = json.loads((scope / "environment.json").read_text())
    if environment.get("canonical") is not False:
        raise ValueError("a shared staging environment must be marked non-canonical")
    kwargs = {"lease_ms": lease_ms}
    if clock:
        kwargs["clock"] = clock
    return Gateway(scope / "campaign", environment["campaign_id"], GitStore(scope, min_sync_s=min_sync_s), **kwargs)
