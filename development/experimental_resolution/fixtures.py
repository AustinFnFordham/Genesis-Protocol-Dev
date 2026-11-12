"""Disposable noncanonical integration fixtures; never write a source campaign."""
import copy
import json
from pathlib import Path
import shutil
import sys
from engine import ROOT
import export_state


def campaign_copy(root):
    campaign = Path(root) / "campaign"
    shutil.copytree(ROOT / "campaigns/starwars_litrpg/runs/sandbox", campaign)
    (campaign / "experimental_resolution.json").write_text(json.dumps({"enabled": True, "canonical": False,
        "campaign_id": "resolution-staging-copy", "controlled_actors": ["aero"]}))
    return campaign


def action_for(campaign, temperature="regular", narrative=False):
    state = export_state.build(campaign_dir=campaign, campaign_id="resolution-staging-copy")
    declaration = {"actor": "aero", "source": "composer", "speech": None,
        "actions": [{"option": "inspect_remote", "target": "remote", "trigger": None}],
        "bonus_actions": [], "objects": [], "reactions": [], "movement": {"option": "hold"}, "unmapped": [],
        "steps": [{"id": "inspect", "seq": 0, "type": "action", "option": "inspect_remote", "target": "remote"}],
        "sequences": [{"label": ""}]}
    return {"campaign_id": "resolution-staging-copy", "actor": "aero", "based_on_revision": state["revision"],
        "ledger_head": state["ledger_head"], "context_id": state["turn_context"]["context_id"],
        "text": "Inspect the disabled remote by eye; leave the conditional pickup pending.",
        "declaration": declaration, "resolution_settings": {"temperature": temperature, "narrative_consequences": narrative}}


def request_for(key="inspection"):
    return {"roll_key": key, "step_id": "inspect", "formula": "1d20+3", "mode": "normal", "kind": "check",
            "requested_by": "aero", "purpose": "Technology: study the remote (isolated comparison)", "dc": 17,
            "rule_sources": ["api_bridge/gm/aero_character_runtime.yml:proficiencies.skills.technology",
                             "owner experimental resolution specification; sandbox GM DC17"]}
