# Inter-Party Influence Engine
# Dynamic Moral Influence System for SW5e/FFG Hybrid

## Overview
The Inter-Party Influence Engine creates meaningful moral dynamics within the party, where player choices can subtly influence companions and other party members. This system tracks alignment shifts, provides narrative feedback, and creates rich roleplaying opportunities.

## Core Components

### 1. Alignment Tracking System

Every character (player and companion) has an alignment tracking block:

```yaml
alignment_tracking:
  alignment_score: 50  # 0 (Pure Dark) to 100 (Pure Light), 50 is neutral
  alignment_descriptor: "Neutral"  # Human-readable tag
  alignment_history:
    - period: "Session 1"
      score: 50
      descriptor: "Neutral"
      trigger: "Character creation"
  
  influence_resistance:
    dark_side_influence: "DC 15 to resist"
    light_side_influence: "DC 15 to resist"
    neutral_influence: "DC 15 to resist"
  
  alignment_effects:
    light_side_benefits: ["Enhanced Force healing", "Reduced dark side corruption"]
    dark_side_benefits: ["Increased Force power", "Enhanced intimidation"]
    neutral_benefits: ["Balanced Force abilities", "Flexible moral choices"]
```

### 2. Influence Effect System

Actions and dialogue choices can be tagged with influence effects:

```yaml
influence_effect:
  alignment: "Light"  # "Light", "Dark", or "Neutral"
  magnitude: 5        # How powerful the moral statement is (1-10)
  radius: "party"     # "self", "party", "companion", or "all"
  target_specific: ["companion_id"]  # Optional: specific targets
  conditions:
    - requirement: "target_alignment"
      value: "dark_side"
      modifier: "+2"  # Bonus to influence if condition met
```

### 3. Engine Logic Flow

#### Step 1: Action Execution
When a player performs an action with an influence effect:

1. **Actor's Alignment Shift**: The character who performed the action has their alignment_score directly affected
2. **Party Reaction Calculation**: Engine iterates through all party members
3. **Resistance Check**: Each party member makes a Wisdom (Discipline) saving throw
4. **Influence Application**: Based on save result, alignment shifts occur
5. **Narrative Feedback**: LLM-GM generates roleplaying feedback

#### Step 2: Resistance Check Formula
```
DC = 10 + magnitude + actor_charisma_modifier
Save Result = d20 + Wisdom modifier + Discipline proficiency
```

#### Step 3: Influence Application
- **Failed Save**: Alignment shifts by (magnitude ÷ 2) toward influencing alignment
- **Successful Save**: No alignment change (character holds true to beliefs)
- **Critical Success (20+)**: Character gains +1 to future resistance against this alignment

### 4. Narrative Feedback System

The LLM-GM uses the influence results to generate contextual roleplaying feedback:

#### Light Side Influence Examples:
**Failed Save**: "Vader's apprentice sees your act of mercy and hesitates, a flicker of conflict visible in their eyes. The darkness in their heart wavers slightly."
**Successful Save**: "Your bounty hunter companion scoffs at your weakness, cleaning their blaster. 'Mercy doesn't pay the bills,' they mutter, though there's a hint of uncertainty in their voice."

#### Dark Side Influence Examples:
**Failed Save**: "The Jedi Padawan watches your ruthless efficiency with growing concern. Their faith in the light side seems to waver for a moment."
**Successful Save**: "Your medic companion maintains their composure, though you can see the conflict in their eyes. 'There must be another way,' they insist."

### 5. Implementation Examples

#### Example 1: Sparing an Enemy
```yaml
action: "spare_defeated_enemy"
narrative: "You choose to show mercy, lowering your weapon."
mechanics:
  - effect: "enemy_surrenders"
    target: "defeated_enemy"
influence_effect:
  alignment: "Light"
  magnitude: 5
  radius: "party"
  conditions:
    - requirement: "enemy_was_combatant"
      modifier: "+2"
```

#### Example 2: Using Dark Side Powers
```yaml
action: "force_choke_enemy"
narrative: "You use the dark side to choke your opponent."
mechanics:
  - effect: "enemy_damage"
    damage: "2d6 force"
influence_effect:
  alignment: "Dark"
  magnitude: 7
  radius: "party"
  conditions:
    - requirement: "enemy_was_innocent"
      modifier: "+3"
```

#### Example 3: Neutral Diplomacy
```yaml
action: "negotiate_peace"
narrative: "You attempt to find a peaceful solution."
mechanics:
  - effect: "diplomacy_check"
    dc: 15
influence_effect:
  alignment: "Neutral"
  magnitude: 3
  radius: "party"
```

### 6. Advanced Features

#### Companion-Specific Reactions
```yaml
companion_reactions:
  jedi_master:
    light_side_actions: "Nods approvingly, offering gentle guidance"
    dark_side_actions: "Expresses concern, offers meditation to find balance"
    neutral_actions: "Observes thoughtfully, ready to provide wisdom"
  
  sith_lord:
    light_side_actions: "Shows internal conflict, memories of her own redemption"
    dark_side_actions: "Recognizes the power, but warns of its cost"
    neutral_actions: "Appreciates the pragmatism, offers strategic advice"
```

#### Relationship Impact
```yaml
relationship_effects:
  trust_modifiers:
    light_side_actions: "+1 trust with light-aligned companions"
    dark_side_actions: "+1 trust with dark-aligned companions"
    neutral_actions: "+1 trust with neutral companions"
  
  romance_impact:
    alignment_compatibility: "Romance points affected by alignment compatibility"
    moral_conflict: "Romance tension from moral disagreements"
    shared_values: "Romance growth from shared moral choices"
```

### 7. Campaign Integration

#### Session Tracking
```yaml
session_influence_summary:
  session_date: "2024-01-15"
  total_influence_events: 8
  alignment_shifts:
    player_character: +3 (toward light)
    jedi_master: +1 (toward light)
    bounty_hunter: -2 (toward dark)
    medic: +2 (toward light)
  
  notable_events:
    - event: "Spared Imperial officer"
      impact: "Major light side influence on party"
    - event: "Used Force choke on civilian"
      impact: "Dark side influence, caused party tension"
```

#### Long-term Effects
```yaml
campaign_effects:
  party_moral_cohesion: 75  # Percentage of party with similar alignment
  moral_conflicts: 3        # Number of moral disagreements this session
  redemption_opportunities: 2  # Potential redemption arcs available
  
  faction_relations:
    jedi_order: "Improved due to light side actions"
    sith_order: "Strained due to light side actions"
    neutral_factions: "Maintained through balanced approach"
```

### 8. Balance Considerations

#### Influence Magnitude Guidelines
- **1-2**: Minor actions (small choices, casual dialogue)
- **3-4**: Moderate actions (significant choices, combat decisions)
- **5-6**: Major actions (life-or-death decisions, moral crossroads)
- **7-8**: Critical actions (defining character moments)
- **9-10**: Legendary actions (galaxy-changing decisions)

#### Resistance Scaling
- **Low Resistance**: DC 12-14 (easily influenced)
- **Medium Resistance**: DC 15-17 (standard resistance)
- **High Resistance**: DC 18-20 (difficult to influence)
- **Legendary Resistance**: DC 21+ (nearly impossible to influence)

### 9. GM Tools

#### Influence Calculator
```yaml
influence_calculator:
  base_dc: 10
  magnitude_bonus: "magnitude_value"
  charisma_bonus: "actor_charisma_modifier"
  target_resistance: "target_wisdom_modifier + discipline_proficiency"
  
  success_chance: "Calculate percentage chance of influence"
  expected_shift: "Calculate average alignment change"
```

#### Narrative Prompt Generator
```yaml
narrative_prompts:
  light_side_success: "Describe how the light side action inspires others"
  light_side_failure: "Describe how others resist the light side influence"
  dark_side_success: "Describe how the dark side action corrupts others"
  dark_side_failure: "Describe how others resist the dark side influence"
  neutral_success: "Describe how the balanced approach affects others"
  neutral_failure: "Describe how others react to the neutral stance"
```

### 10. Player Agency Protection

#### Opt-Out Options
- Players can choose to resist all influence effects
- Critical character-defining moments can be protected
- Alignment shifts can be limited per session
- Players can set influence sensitivity levels

#### Consent Mechanics
```yaml
player_consent:
  influence_sensitivity: "high"  # "low", "medium", "high"
  protected_alignments: ["extreme_light", "extreme_dark"]
  session_limits: "max_3_alignment_shifts_per_session"
  character_arc_protection: "true"
```

This system creates a dynamic, living world where every choice matters and the party's moral journey becomes a shared experience. The Inter-Party Influence Engine transforms simple actions into meaningful character development opportunities, making every session a story of growth, conflict, and redemption.
