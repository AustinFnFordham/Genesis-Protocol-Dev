import os
import glob
import json
import yaml
import re
import traceback
import sys
import random
from typing import List, Dict, Any, Tuple, Set

# === CONFIGURATION ===
BASE_DIR = r"e:\StarWars\SW5e_Data_Hub\SW5e_Data_Hub"
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTIONS_DIR = os.path.join(DATA_DIR, "factions")
EXPANSIONS_DIR = os.path.join(DATA_DIR, "faction_expansions")
REGISTRIES_DIR = os.path.join(BASE_DIR, "docs", "registries")
SCHEMAS_DIR = os.path.join(BASE_DIR, "schema")

os.makedirs(FACTIONS_DIR, exist_ok=True)
os.makedirs(EXPANSIONS_DIR, exist_ok=True)

# === LOADERS ===
def load_yaml(path: str) -> Dict:
    if not os.path.exists(path): return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def load_json_schema(filename: str) -> Dict:
    path = os.path.join(SCHEMAS_DIR, filename)
    if not os.path.exists(path):
        path = os.path.join(DATA_DIR, "schemas", filename)
    if not os.path.exists(path):
        print(f"CRITICAL: Schema missing: {filename}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

CORE_SCHEMA = load_json_schema("faction_core.schema.json")
EXP_SCHEMA = load_json_schema("faction_expansion.schema.json")

SKILLS_REGISTRY = load_yaml(os.path.join(REGISTRIES_DIR, "skills.registry.yml"))
VALID_SKILL_IDS = [s['id'] for s in SKILLS_REGISTRY.get('skills', [])]
VALID_SAVE_IDS = [f"save_{a}" for a in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]]
VALID_COMBAT_IDS = ["check_initiative", "attack_rolls"]
VALID_TARGETS = set(VALID_SKILL_IDS + VALID_SAVE_IDS + VALID_COMBAT_IDS)

# === FLAVOR BANKS (SOUL ENGINE V4) ===
# Expanded for entropy
FLAVOR_TEMPLATES = {
    "skill_intimidation": ["Your presence alone silences rooms.", "Fear is a tool you wield with precision.", "Commands spoken softly carry double weight.", "A raised eyebrow is your strongest weapon.", "You cultivate an aura of dread."],
    "skill_persuasion": ["Words open doors blasters cannot.", "You leverage bureaucratic pressure instantly.", "Diplomacy is just warfare by other means.", "You trade favors like currency.", "An agreement is inevitable."],
    "skill_deception": ["Truth is a flexible commodity.", "Your cover stories are impenetrable.", "You lie with the conviction of a saint.", "Misdirection is your primary shield.", "You are never who they think you are."],
    "skill_stealth": ["Unseen, unheard, and inevitable.", "You move like a ghost in the machine.", "Shadows cling to you like armor.", "Footsteps are for the clumsy.", "You exist only when you choose to."],
    "skill_investigation": ["No secret stays buried forever.", "You connect dots others don't see.", "Files reveal more than interrogations.", "The trash chute tells a story.", "Patterns emerge from the noise."],
    "skill_lore": ["History teaches how to conquer the future.", "Ancient protocols override modern locks.", "Knowledge is the ultimate leverage.", "You know the old laws.", "Trivia saves lives."],
    "skill_medicine": ["You decide who walks away.", "Field triage involves hard choices.", "Anatomy has its useful vulnerabilities.", "Healing is just biological engineering.", "You keep the machine running."],
    "skill_mechanics": ["Machines have no loyalty, only functions.", "Sabotage is an art form to you.", "You speak the binary language of repair.", "Percussive maintenance is a valid technique.", "Engines hum a song only you hear."],
    "skill_piloting": ["Gravity is just a suggestion.", "Evasive maneuvers are second nature.", "You fly closer to the sun than most dared.", "Orbits are just math.", "The stick feels like an extension of your arm."],
    "skill_computers": ["Encryption is just a puzzle to solve.", "Data flows where you direct it.", "You hold the keys to the digital kingdom.", "Firewalls are mere suggestions.", "Zeroes and ones bow to you."],
    "skill_athletics": ["Physical dominance asserts authority.", "Obstacles are meant to be broken.", "Strength solves problems words cannot.", "Endurance is the only virtue.", "You carry the weight."],
    "skill_acrobatics": ["Balance is key to survival.", "You move faster than the eye tracks.", "Agility keeps you one step ahead.", "Falling is just flying with style.", "You land on your feet."],
    "skill_insight": ["You read intention like a datapad.", "Lies have a specific scent.", "Motivations are transparent to you.", "You see the twitch before the draw.", "Trust is earned, never given."],
    "skill_survival": ["Comfort is a lie; survival is truth.", "You endure where others perish.", "The environment is your ally.", "You can eat anything.", "Exposure is just a mindset."],
    "skill_streetwise": ["The gutter whispers its secrets.", "Black markets obey your currency.", "You know a guy who knows a guy.", "The underworld has its own laws.", "Respect is the only currency here."],
    "skill_leadership": ["Command is a burden you accept.", "Men follow, you lead.", "Your orders are absolute.", "Morale is a resource to be managed.", "Victory begins with will."],
    "skill_politics": ["Power is a game of shadows.", "Legality is a matter of perspective.", "Influence is currency.", "A favor owed is better than credits.", "The Senate is just a stage."],
    "skill_xenology": ["Alien minds are not so different.", "Cultural understanding bridges worlds.", "Every species has a price.", "You speak the language of profit.", "Diversity is a resource."],
    "skill_astrogation": ["The stars are your map.", "Hyperspace is a river you navigate.", "Coordinates are locked.", "No system is beyond reach.", "The galaxy is smaller than they think."],
    "skill_skulduggery": ["Locks are just puzzles.", "Nothing is secure.", "You are the vulnerability.", "Access granted.", "Dirty hands, clean credits."],
    "skill_brawl": ["Fists don't jam.", "Up close and personal.", "Pain is the best teacher.", "A fair fight is a lost fight.", "Knuckles solve complications."],
    "skill_perception": ["Nothing escapes your notice.", "You see the details others miss.", "Vigilance is survival.", "The eyes never lie.", "Awareness is the first line of defense."],
    "skill_animal_handling": ["Beasts respect dominance.", "Nature obeys your command.", "A mount is a weapon.", "Wild things know their master.", "Instinct recognizes instinct."],
    "skill_nature": ["The wild is your home.", "Plants whisper warning.", "Track the untrackable.", "Survival is natural.", "The living force binds all."],
    "skill_performance": ["The galaxy is your stage.", "Distraction is a subtle art.", "All eyes on you.", "Emotion is a tool.", "The show must go on."],
    "skill_sleight_of_hand": ["Now you see it, now you don't.", "Faster than the eye.", "A hidden blade is best.", "Pockets are never empty.", "The hand is quicker than the mind."],
    "save_constitution": ["Pain is merely information.", "You endure the unendurable.", "Hardiness is a prerequisite for rank.", "Poison is just a flavor.", "You stand when others fall."],
    "save_wisdom": ["Your mind is a steel fortress.", "Mental conditioning resists all intrusion.", "Clarity pierces the fog of war.", "You see the trap before it springs.", "Willpower is your armor."],
    "save_intelligence": ["You outthink enemies before they act.", "Strategy defeats brute force.", "Calculated risks yield high rewards.", "You are three moves ahead.", "Logic dictates victory."],
    "save_strength": ["You are an immovable object.", "Force is met with greater force.", "You hold the line.", "Muscles are just hydraulics.", "Push comes to shove."],
    "save_dexterity": ["Reflexes save lives.", "You are never where they aim.", "Speed kills.", "A moving target lives longer.", "Dodge, duck, dip, dive, and dodge."],
    "save_charisma": ["Your will dominates the weak.", "Presence demands obedience.", "You are the center of attention.", "Leadership is natural to you.", "They follow because they must."],
    "check_initiative": ["You always shoot first.", "Hesitation is death.", "Action beats reaction.", "You are already moving.", "The first strike is the last."],
    "attack_rolls": ["Your aim is true.", "Combat is a solved equation.", "Violence is applied with precision.", "One shot, one problem solved.", "The weapon is part of you."]
}

# Names for features based on target
FEATURE_NOUNS = {
    "skill": ["Protocol", "Discipline", "Doctrine", "Method", "Technique", "Drill", "Algorithm", "Code"],
    "save": ["Training", "Fortitude", "Reflex", "Conditioning", "Mindset", "Shield", "Barrier"],
    "check": ["Reflex", "Instinct", "Response", "Manuever"]
}

ESSENCE_BANKS = {
    "government": {
        "customs": ["Saluting superiors.", "Reciting the pledge.", "Carrying ID chits."],
        "taboos": ["Disrespecting the flag.", "Unauthorized assembly.", "Questioning orders."],
        "status_markers": ["Rank cylinders.", "Medals of service.", "High-clearance keycards."]
    },
    "criminal_syndicate": {
        "customs": ["Paying the tithe.", "Kissing the ring.", "Vouching for new blood."],
        "taboos": ["Talking to cops.", "Skimming off the top.", "Dating a rival."],
        "status_markers": ["Flashy jewelry.", "Unique blasters.", "Exotic pets."]
    },
    "religious_order": {
        "customs": ["Daily meditation.", "Dietary restrictions.", "Ritual chanting."],
        "taboos": ["Touching the sacred.", "Speaking forbidden names.", "Missing prayer."],
        "status_markers": ["Ceremonial robes.", "Relics.", "Tattoos of scripture."]
    }
}

# === HELPERS ===
def to_snake_case(text: str) -> str:
    if not text: return "unknown"
    return re.sub(r'[^a-z0-9_]', '_', str(text).lower()).strip('_')

def map_status(raw_status: str) -> str:
    """Strict Schema Enum Mapper"""
    s = raw_status.lower()
    if "ally" in s or "allied" in s: return "Allied"
    if "friendly" in s: return "Friendly"
    if "hostile" in s: return "Hostile"
    if "war" in s: return "War"
    if "unfriendly" in s: return "Unfriendly"
    # Fallback for "Superior", "Subordinate", "Neutral"
    return "Neutral"

def standardize_id(prefix, val, context_slug):
    slug = to_snake_case(val)
    if not slug or slug in ["unknown", "none", "todo"]: 
         if prefix == "pla" and "hq" in slug: return f"pla_{context_slug}_hq"
         return f"{prefix}_{context_slug}_todo"
    
    if prefix == "fac" and slug.startswith("the_"): slug = slug[4:]
    if slug.startswith(f"{prefix}_"): return slug
    return f"{prefix}_{slug}"

# === GENERATORS ===
def generate_rule_object(target: str, rule_type: str = "skill_bonus", value: int = 1) -> Dict:
    if "save_" in target and rule_type == "skill_bonus": rule_type = "check_advantage"
    if target in ["check_initiative", "attack_rolls"] and rule_type == "skill_bonus": rule_type = "check_advantage"
    obj = {"type": rule_type, "target": target, "value": value}
    return {"rule": obj, "rule_object": obj}

def get_taxonomy_defaults(legacy: Dict, faction_name: str) -> Tuple[List[str], List[str]]:
    l_type = str(legacy.get('faction_type', 'criminal_syndicate')).lower()
    types = []
    if "government" in l_type: types.append("government")
    elif "relig" in l_type: types.append("religious_order")
    elif "milit" in l_type: types.append("military")
    elif "corp" in l_type: types.append("corporation")
    elif "rebel" in l_type: types.append("rebellion")
    else: types.append("criminal_syndicate")
    
    tags = ["established"]
    if "underworld" in l_type: tags.append("underworld")
    if "imperial" in faction_name.lower(): tags.append("imperial")
    # Schema safety
    if len(tags) < 2: tags.append("galactic_power")
    return types, tags

def get_feature_name_and_narrative(target: str, seed_int: int, used_narratives: Set[str]) -> Tuple[str, str]:
    # Narrative
    options = FLAVOR_TEMPLATES.get(target, ["Focus brings power."])
    narrative = "Standard protocol."
    
    # Entropy search
    for i in range(len(options)):
        candidate = options[(seed_int + i) % len(options)]
        if candidate not in used_narratives:
            narrative = candidate
            break
    used_narratives.add(narrative)
    
    # Name
    target_clean = target.replace("skill_", "").replace("save_", "").replace("check_", "").capitalize()
    cat = "skill" if "skill" in target else "save" if "save" in target else "check"
    noun = FEATURE_NOUNS.get(cat, ["Protocol"])[seed_int % len(FEATURE_NOUNS.get(cat, ["Protocol"]))]
    
    name = f"{target_clean} {noun}"
    return name, narrative

def generate_structure_platinum(legacy: Dict, taxonomy: Dict, faction_name: str, slug: str) -> Dict:
    ranks_out = []
    
    # Extract Titles
    legacy_ranks = legacy.get('ranks')
    if not legacy_ranks:
        org_engine = legacy.get('organization_engine') or {}
        legacy_ranks = org_engine.get('ranks')

    titles = []
    if legacy_ranks and isinstance(legacy_ranks, list):
        for r in legacy_ranks:
            t_str = "Unknown"
            if isinstance(r, str): t_str = r.split('(')[0].strip()
            elif isinstance(r, dict): t_str = r.get('title', 'Unknown')
            titles.append(t_str)
    
    while len(titles) < 5:
        if len(titles) == 0: titles = ["Associate", "Member", "Veteran", "Elite", "Leader"]
        else: titles.insert(len(titles)-1, f"Senior {titles[-2]}")
    titles = titles[:5]
    
    costs = [0, 15, 35, 75, 150]
    used_triplets = {} 
    used_narratives = set() # NARRATIVE ENTROPY
    targets_pool =  list(VALID_TARGETS)
    random.seed(slug) 
    random.shuffle(targets_pool)
    
    count = 0
    for i in range(5):
        rank_choices = []
        for j in range(3):
            target = targets_pool[(i*3 + j + count) % len(targets_pool)]
            rule_type = "skill_bonus" if "skill" in target else "check_advantage"
            triplet = (rule_type, target, 1)
            
            if used_triplets.get(triplet, 0) >= 1: 
                count += 1
                target = targets_pool[(i*3 + j + count) % len(targets_pool)]
                triplet = (rule_type, target, 1)
                
            used_triplets[triplet] = used_triplets.get(triplet, 0) + 1
            
            feat_id = f"feat_{slug}_{i}_{j+1}"
            
            # SOUL V4 Name + Narrative
            name, narrative = get_feature_name_and_narrative(target, i*3+j, used_narratives)
            
            rules = generate_rule_object(target, rule_type, 1)
            choice = {"id": feat_id, "name": name, "narrative": narrative}
            choice.update(rules)
            rank_choices.append(choice)
            
        ranks_out.append({
            "rank_level": i+1,
            "title": titles[i],
            "renown_cost": costs[i],
            "feature_choices": rank_choices
        })
        
    return {
        "power": {"wealth": 5, "military": 5, "influence": 5, "tech_level": 5},
        "ranks": ranks_out
    }

def generate_connections_platinum(legacy: Dict, slug: str, self_id: str) -> Dict:
    hq_raw = legacy.get('headquarters_id') or "hq"
    hq_id = standardize_id("pla", hq_raw, slug)
    if "imperial_palace" in str(legacy).lower() or "coruscant" in str(legacy).lower():
        hq_id = "pla_coruscant"
    if "dathomir" in str(legacy).lower():
        hq_id = "pla_dathomir"
    if "nal_hutta" in str(legacy).lower():
        hq_id = "pla_nal_hutta"
        
    legacy_rels = legacy.get('relationships', [])
    new_rels = []
    
    for r in legacy_rels:
        raw_tid = r.get('faction_id') or r.get('target_faction_id')
        if not raw_tid: continue
        tid = standardize_id("fac", raw_tid, "unknown")
        if tid == self_id: continue 

        # Strict Enum
        status = map_status(r.get('relationship_type', 'Neutral'))
        
        # Varied Mechanics based on status
        mech = {"type": "skill_bonus", "target": "skill_politics", "value": 1}
        if status in ["Hostile", "War"]:
            mech = {"type": "check_advantage", "target": "check_initiative", "value": 1}
        elif status == "Allied":
            mech = {"type": "skill_bonus", "target": "skill_persuasion", "value": 1}
        
        new_rels.append({
            "target_faction_id": tid,
            "status": status,
            "narrative": r.get('narrative', "A complex dynamic."),
            "mechanical_rule": mech
        })
        
    if not new_rels:
        new_rels.append({
            "target_faction_id": "fac_black_sun",
            "status": "Neutral",
            "narrative": "Shadowy dealings.",
            "mechanical_rule": {"type": "skill_bonus", "target": "skill_streetwise", "value": 1}
        })

    return {
        "headquarters_id": hq_id,
        "key_npc_ids": [standardize_id("npc", nid, slug) for nid in legacy.get('notable_npcs', [])],
        "relationships": new_rels,
        "membership_integration": {
            "class_synergies": [{"class_id": "cls_operative", "narrative": "Operatives fit well here.", **generate_rule_object("skill_stealth", "skill_bonus", 1)}],
            "species_synergies": [{"species_id": "spc_human", "narrative": "Humans are common.", **generate_rule_object("skill_lore", "skill_bonus", 1)}],
            "background_synergies": [{"id": "bg_noble", "background_id": "bg_noble", "narrative": "Nobles find influence.", **generate_rule_object("skill_persuasion", "skill_bonus", 1)}]
        }
    }

def generate_essence_platinum(legacy: Dict, taxonomy: Dict, name: str) -> Dict:
    # Populate Sub Objects (Schema Fix)
    main_type = taxonomy['types'][0]
    bank = ESSENCE_BANKS.get(main_type, ESSENCE_BANKS['criminal_syndicate'])
    
    return {
        "overview": legacy.get('narrative') or legacy.get('description') or "A faction.",
        "ideology": legacy.get('core_ideology') or "Survival.",
        "culture": {
            "customs": bank['customs'],
            "taboos": bank['taboos'],
            "status_markers": bank['status_markers']
        },
        "style_guide": {
            "tone": getattr(legacy.get('llm_guidance',{}), 'get', lambda k,d: d)('tone', "Gritty"),
            "key_phrases": ["For the cause.", "Order.", "Power."],
            "image_prompt_base": f"A cinematic shot of {name}",
            "image_prompt_modifiers": ["dark", "moody"]
        },
        "gm_guidance": {
            "first_missions": ["Courier run", "Sentry duty"],
            "hooks": ["A bounty", "A rumor"],
            "rumors": ["They are everywhere", "They are broke"],
            "conflicts": ["Internal strife", "External war"],
            "tells_by_rank": {"rank_1": "Nervous", "rank_5": "Terrifying"}
        },
        "tone_levers": {
            "mystical_horror_dial": 1,
            "notes": "Standard scifi."
        }
    }

def process_file_platinum(path: str):
    filename = os.path.basename(path)
    if "black_sun" in filename: return 
    if filename.startswith("fac_"): return

    with open(path, 'r', encoding='utf-8') as f:
        legacy = yaml.safe_load(f) or {}
        
    name = legacy.get('name', "Unknown")
    raw_slug = to_snake_case(name)
    if raw_slug.startswith("the_"): raw_slug = raw_slug[4:]
    new_id = f"fac_{raw_slug}"
    
    print(f"Diamond Processing {name} -> {new_id}...")
    
    types, tags = get_taxonomy_defaults(legacy, name)
    taxonomy = {"types": types, "alignment": ["neutral"], "tags": tags}
    
    # Axes
    axes = [{"axis": "Loyalty", "polarity": "positive", "description": "Duty."}] 
    if "gov" in types[0]: axes = [{"axis": "Loyalty", "polarity": "positive", "description": "Adherence."} for i in range(3)] 
    # Just reusing the logic from V3 (implied) or simple default, the user liked the V3 axes.
    # Re-injecting V3 axes logic:
    AXES_TEMPLATES = {
        "government": [{"axis": "Loyalty", "polarity": "positive", "description": "State adherence."}, {"axis": "Bureaucracy", "polarity": "positive", "description": "Paperwork."}, {"axis": "Dissent", "polarity": "negative", "description": "Rebellion."}],
        "criminal_syndicate": [{"axis": "Profit", "polarity": "positive", "description": "Credits."}, {"axis": "Omerta", "polarity": "positive", "description": "Silence."}, {"axis": "Heat", "polarity": "negative", "description": "Police attention."}],
        "religious_order": [{"axis": "Piety", "polarity": "positive", "description": "Faith."}, {"axis": "Orthodoxy", "polarity": "positive", "description": "Tradition."}, {"axis": "Heresy", "polarity": "negative", "description": "Blasphemy."}]
    }
    axes = AXES_TEMPLATES.get(types[0], AXES_TEMPLATES['criminal_syndicate'])

    core = {
        "id": new_id,
        "name": name,
        "source": "Canon",
        "era": ["Rebellion"],
        "taxonomy": taxonomy,
        "affiliation": {
            "renown_scale": {"min": 0, "max": 200},
            "reputation_axes": axes
        },
        "structure": generate_structure_platinum(legacy, taxonomy, name, raw_slug),
        "essence": generate_essence_platinum(legacy, taxonomy, name),
        "connections": generate_connections_platinum(legacy, raw_slug, new_id),
        "ui": {"color_hex": "#000000", "icon_path": "path", "image_path": "path"}
    }
    
    out_path = os.path.join(FACTIONS_DIR, f"{new_id}.yml")
    class CleanDumper(yaml.SafeDumper):
        def ignore_aliases(self, data): return True
    
    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.dump(core, f, Dumper=CleanDumper, sort_keys=False, default_flow_style=False)
    print(f"Generated Diamond {out_path}")

if __name__ == "__main__":
    targets = glob.glob(os.path.join(FACTIONS_DIR, "*.yml"))
    for t in targets:
        fname = os.path.basename(t)
        if fname in ["factions_rules.yml", "faction_tags.yml", "master_tags.yml"]: continue
        if "black_sun" in fname: continue
        if not fname.startswith("fac_"):
            process_file_platinum(t)
