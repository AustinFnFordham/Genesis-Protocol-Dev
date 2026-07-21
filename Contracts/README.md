# Starship Systems - Consolidated Directory

## Overview
This directory contains all starship-related systems, data, and mechanics for the SW5e x FFG unified system. The starship systems provide a comprehensive framework for starship operations, combat, and character progression.

## Directory Structure

### `/careers/` - Starship Career System
- **Purpose**: Defines character roles and progression within starship operations
- **Files**:
  - `starship_careers_master.yml` - Complete career definitions with progression paths
  - `career_synergies.yml` - Career combination bonuses and interactions
  - `career_prerequisites.yml` - Requirements and qualifications for each career

### `/actions/` - Starship Actions System
- **Purpose**: Defines all available actions during starship operations
- **Files**:
  - `combat_actions.yml` - Combat-specific starship actions
  - `non_combat_actions.yml` - Navigation, maintenance, and utility actions
  - `action_registry.yml` - Central registry of all starship actions
  - `action_integration.yml` - How actions integrate with classes, powers, and other systems

### `/rules/` - Starship Rules and Mechanics
- **Purpose**: Core rules and mechanical frameworks
- **Files**:
  - `combat_rules.yml` - Starship combat flow and mechanics
  - `roles_rules.yml` - Role-based proficiency system
  - `progression_rules.yml` - XP and advancement mechanics

### `/data/` - Starship Data and Content
- **Purpose**: Starship specifications, templates, and content
- **Files**:
  - `starship_templates.yml` - Base starship classes and templates
  - `starship_modifications.yml` - Upgrade and modification options
  - `starship_equipment.yml` - Starship-specific equipment and gear

### `/integration/` - System Integration
- **Purpose**: How starship systems connect with other game systems
- **Files**:
  - `class_integration.yml` - How character classes interact with starship careers
  - `power_integration.yml` - Force/Tech power integration with starship operations
  - `faction_integration.yml` - Faction-specific starship benefits and restrictions

## Key Systems

### Starship Careers System
- **Dual Progression**: Characters have both a ground-based class and a starship career
- **5-Tier Progression**: Novice → Adept → Expert → Master → Legendary
- **Synergy System**: Careers work together to create powerful combinations
- **Ship Compatibility**: Each career excels with specific ship types

### Starship Actions System
- **Combat Actions**: Maneuvers, attacks, and tactical options
- **Non-Combat Actions**: Navigation, maintenance, and utility operations
- **Role-Based Actions**: Actions that require specific career proficiencies
- **Integration Actions**: Actions that bridge starship and ground operations

### Starship Rules Framework
- **Range Bands**: Close, Medium, Long, Extreme ranges for starship combat
- **Action Economy**: Action, Bonus Action, Reaction system for starship operations
- **Progression**: XP-based advancement separate from character class progression
- **Balance**: Bounded bonuses and clear mechanical limits

## Integration Points

### With Character Classes
- Each character class provides bonuses to specific starship actions
- Class features can enhance starship career abilities
- Multiclass characters can combine ground and space expertise

### With Force/Tech Powers
- Force powers can enhance starship operations
- Tech powers integrate directly with starship systems
- Hybrid powers bridge ground and space capabilities

### With Factions
- Factions provide access to specific starship types
- Faction ranks unlock advanced starship capabilities
- Faction-specific modifications and equipment

## Usage Guidelines

### For Players
1. Choose a primary character class for ground operations
2. Select a starship career for space operations
3. Progress both systems independently
4. Use appropriate abilities based on current situation

### For Game Masters
1. Use starship templates for quick ship creation
2. Leverage the synergy system for crew coordination
3. Integrate starship operations with ground adventures
4. Use faction restrictions to create narrative tension

### For Developers
1. All starship data follows the established schema patterns
2. New careers should include full progression paths and synergies
3. Actions should specify mechanical effects and integration points
4. Rules should maintain balance with existing systems

## Schema Compliance
All files in this directory conform to their respective schemas:
- `StarshipCareer.schema.json` for career definitions
- `StarshipAction.schema.json` for action definitions
- `Starship.schema.json` for starship specifications
- `CombatRules.schema.json` for rules and mechanics

## Future Expansions
- Vehicle careers (ground, aquatic, atmospheric)
- Advanced synergy combinations
- Fleet operations and capital ship mechanics
- Starship customization and modification systems
