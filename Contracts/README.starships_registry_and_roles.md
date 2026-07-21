# Starship Registry & Roles - Quick Use Guide

Purpose: Show how to resolve "usable actions" for a character and how the registry enables clean separation of combat vs non-combat.

Key Files
- Character roles: SW5e_Data_Hub/schema/Character.schema.json (starship section)
- Roles lookup: SW5e_Data_Hub/data/starship_roles.yml
- Roles rules: SW5e_Data_Hub/data/starship_roles_rules.yml
- Actions registry: SW5e_Data_Hub/data/starship_actions_registry.yml
- Combat actions: SW5e_Data_Hub/data/starship_actions_combat.yml
- Non-combat actions: SW5e_Data_Hub/data/starship_actions_non_combat.yml

UI: Resolve Usable Actions (pseudocode)
1) Read character.starship.primary_role/secondary_role and training_tier.
2) Load roles map from starship_roles.yml; get each role's action_filters.
3) Load registry (starship_actions_registry.yml) to get file paths for combat and non-combat sets.
4) Load actions from chosen set(s); filter by station and/or tags using the role filters.
5) Apply bonuses from starship_roles_rules.yml (tier scaling, certifications) at display/runtime.

Example Flow
- If character.starship.primary_role = "Pilot":
  - Get filters: stations ["Pilot"], tags ["maneuver", "evasion", "positioning"].
  - Use registry.combat.file to load combat actions; show only actions whose station = Pilot and tags intersect.
  - Also load registry.non_combat.file and show exploration/travel actions tagged for Pilot.

Why the Registry?
- Explicit separation of action sets by purpose (combat vs non-combat).
- Central place to add new sets (e.g., downtime, cinematic sequences) without touching consumers.
- Enables back-compat renames and smooth migrations.

Other Uses Across the Project
- Tests: load only the registry, then load each declared set for validation.
- Era/faction mods: add overlay registries (per era/faction) that extend or replace the base paths.
- Item/class integration: attach tags to new actions and let filters discover them automatically.
- Tooling: generators or docs can iterate registry entries to build indexes or UI menus.

Migration Notes
- starship_actions.yml renamed to starship_actions_combat.yml; use the registry file path.
- Consumers should not hardcode file names; always resolve via the registry.
