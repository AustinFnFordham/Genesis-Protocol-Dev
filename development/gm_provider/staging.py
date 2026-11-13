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
from store import SqliteStore  # noqa: E402

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
