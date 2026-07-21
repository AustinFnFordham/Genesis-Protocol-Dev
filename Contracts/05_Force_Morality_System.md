# Force & Morality System Implementation Plan

## Overview
This document outlines the implementation of the Force and Morality system, including conflict mechanics, visual feedback for alignment changes, and the mastery system that allows characters to use opposing powers without falling to the dark side.

## Core Force System Architecture

### Force State Management
```typescript
interface ForceState {
  morality: number; // -100 to 100
  conflict: number; // 0 to 100
  forcePoints: number;
  alignment: 'light' | 'dark' | 'neutral';
  mastery: {
    forcePurity: boolean;
    wisdomModifier: number;
    conflictReduction: number;
  };
  powers: {
    [powerId: string]: {
      level: number;
      alignment: 'light' | 'dark' | 'neutral';
      lastUsed: Date;
    };
  };
}

interface ForceAction {
  type: 'usePower' | 'gainConflict' | 'resolveConflict' | 'updateMorality';
  payload: any;
  timestamp: Date;
}
```

### Redux Actions & Reducers
```typescript
const forceSlice = createSlice({
  name: 'force',
  initialState: {
    morality: 50,
    conflict: 0,
    forcePoints: 0,
    alignment: 'neutral' as const,
    mastery: {
      forcePurity: false,
      wisdomModifier: 0,
      conflictReduction: 0,
    },
    powers: {},
  },
  reducers: {
    useForcePower: (state, action) => {
      const { powerId, level, alignment } = action.payload;
      const power = state.powers[powerId];
      
      // Calculate conflict gain
      let conflictGain = calculateConflictGain(alignment, state.alignment, level);
      
      // Apply Force Purity mastery if applicable
      if (state.mastery.forcePurity && alignment !== state.alignment) {
        conflictGain = Math.max(0, conflictGain - state.mastery.conflictReduction);
      }
      
      state.conflict = Math.min(100, state.conflict + conflictGain);
      state.powers[powerId] = {
        level,
        alignment,
        lastUsed: new Date(),
      };
      
      // Update alignment if conflict threshold reached
      if (state.conflict >= 50) {
        state.alignment = determineNewAlignment(state.morality, state.conflict);
      }
    },
    
    gainConflict: (state, action) => {
      const { amount, source } = action.payload;
      state.conflict = Math.min(100, state.conflict + amount);
      
      // Log conflict gain for session review
      state.conflictHistory.push({
        amount,
        source,
        timestamp: new Date(),
      });
    },
    
    resolveConflict: (state, action) => {
      const { goodDeeds, sessionLength } = action.payload;
      
      // Calculate morality change based on conflict vs good deeds
      const conflictWeight = state.conflict * 0.7;
      const goodDeedsWeight = goodDeeds * 0.3;
      const moralityChange = goodDeedsWeight - conflictWeight;
      
      state.morality = Math.max(-100, Math.min(100, state.morality + moralityChange));
      state.conflict = 0;
      state.alignment = determineAlignment(state.morality);
    },
    
    unlockForcePurity: (state, action) => {
      const { wisdomModifier } = action.payload;
      state.mastery.forcePurity = true;
      state.mastery.wisdomModifier = wisdomModifier;
      state.mastery.conflictReduction = wisdomModifier;
    },
  },
});
```

## Conflict Calculation System

### Conflict Gain Calculation
```typescript
const calculateConflictGain = (
  powerAlignment: string,
  characterAlignment: string,
  powerLevel: number
): number => {
  let baseConflict = 0;
  
  // Base conflict for using opposing alignment powers
  if (powerAlignment !== characterAlignment) {
    baseConflict = 10; // Base conflict for opposing powers
    
    // Additional conflict for dark side powers
    if (powerAlignment === 'dark') {
      baseConflict += 5;
    }
    
    // Conflict scales with power level
    baseConflict *= (1 + (powerLevel - 1) * 0.2);
  }
  
  // Additional conflict for high-level powers
  if (powerLevel > 3) {
    baseConflict += (powerLevel - 3) * 2;
  }
  
  return Math.round(baseConflict);
};

const determineNewAlignment = (morality: number, conflict: number): string => {
  if (conflict >= 75) {
    return 'dark';
  } else if (morality > 25) {
    return 'light';
  } else {
    return 'neutral';
  }
};

const determineAlignment = (morality: number): string => {
  if (morality >= 25) {
    return 'light';
  } else if (morality <= -25) {
    return 'dark';
  } else {
    return 'neutral';
  }
};
```

## Visual Feedback System

### Alignment Aura Visualization
```typescript
interface AlignmentVisualizer {
  updateAura(alignment: string, morality: number, conflict: number): void;
  showConflictGain(amount: number, source: string): void;
  showMoralityChange(change: number): void;
  animateForcePurity(): void;
}

class AlignmentVisualizer {
  private scene: THREE.Scene;
  private auraParticles: THREE.Points;
  private conflictIndicator: HTMLElement;
  private moralityBar: HTMLElement;
  
  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.setupVisualElements();
  }
  
  private setupVisualElements() {
    // Setup aura particle system
    this.setupAuraParticles();
    
    // Setup UI elements
    this.setupUIElements();
  }
  
  updateAura(alignment: string, morality: number, conflict: number) {
    const colorMap = {
      light: '#4A90E2',
      dark: '#E74C3C',
      neutral: '#F39C12',
    };
    
    const baseColor = colorMap[alignment];
    const intensity = Math.abs(morality) / 100;
    const conflictIntensity = conflict / 100;
    
    // Update particle color and intensity
    this.updateParticleSystem(baseColor, intensity, conflictIntensity);
    
    // Update UI elements
    this.updateUIElements(alignment, morality, conflict);
  }
  
  showConflictGain(amount: number, source: string) {
    // Create floating conflict indicator
    const conflictIndicator = document.createElement('div');
    conflictIndicator.className = 'conflict-indicator';
    conflictIndicator.textContent = `+${amount} Conflict`;
    conflictIndicator.style.color = '#E74C3C';
    
    // Animate the indicator
    gsap.timeline()
      .set(conflictIndicator, {
        opacity: 0,
        y: 0,
      })
      .to(conflictIndicator, {
        opacity: 1,
        duration: 0.3,
        ease: 'power2.out',
      })
      .to(conflictIndicator, {
        y: -50,
        opacity: 0,
        duration: 1,
        delay: 1,
        ease: 'power2.in',
        onComplete: () => {
          conflictIndicator.remove();
        },
      });
    
    document.body.appendChild(conflictIndicator);
  }
  
  showMoralityChange(change: number) {
    const moralityIndicator = document.createElement('div');
    moralityIndicator.className = 'morality-indicator';
    moralityIndicator.textContent = change > 0 ? `+${change} Morality` : `${change} Morality`;
    moralityIndicator.style.color = change > 0 ? '#27AE60' : '#E74C3C';
    
    // Animate morality change
    gsap.timeline()
      .set(moralityIndicator, {
        opacity: 0,
        scale: 0.8,
      })
      .to(moralityIndicator, {
        opacity: 1,
        scale: 1.2,
        duration: 0.3,
        ease: 'power2.out',
      })
      .to(moralityIndicator, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.in',
      })
      .to(moralityIndicator, {
        opacity: 0,
        duration: 0.5,
        delay: 2,
        ease: 'power2.in',
        onComplete: () => {
          moralityIndicator.remove();
        },
      });
    
    document.body.appendChild(moralityIndicator);
  }
  
  animateForcePurity() {
    // Create special visual effect for Force Purity mastery
    const purityEffect = document.createElement('div');
    purityEffect.className = 'force-purity-effect';
    
    gsap.timeline()
      .set(purityEffect, {
        opacity: 0,
        scale: 0,
      })
      .to(purityEffect, {
        opacity: 1,
        scale: 1,
        duration: 0.5,
        ease: 'power2.out',
      })
      .to(purityEffect, {
        opacity: 0,
        scale: 1.5,
        duration: 0.5,
        delay: 1,
        ease: 'power2.in',
        onComplete: () => {
          purityEffect.remove();
        },
      });
    
    document.body.appendChild(purityEffect);
  }
}
```

## Power Usage Interface

### Power Card with Alignment Indicators
```typescript
interface PowerCardProps {
  power: Power;
  characterAlignment: string;
  onUse: (powerId: string, level: number) => void;
}

const PowerCard: React.FC<PowerCardProps> = ({
  power,
  characterAlignment,
  onUse,
}) => {
  const [selectedLevel, setSelectedLevel] = useState(1);
  const [showConflictWarning, setShowConflictWarning] = useState(false);
  
  const isOpposingAlignment = power.alignment !== characterAlignment;
  const conflictGain = calculateConflictGain(power.alignment, characterAlignment, selectedLevel);
  
  const handleUsePower = () => {
    if (isOpposingAlignment && conflictGain > 0) {
      setShowConflictWarning(true);
    } else {
      onUse(power.id, selectedLevel);
    }
  };
  
  return (
    <div className={`power-card ${power.alignment} ${isOpposingAlignment ? 'opposing' : ''}`}>
      <div className="power-header">
        <h3>{power.name}</h3>
        <div className={`alignment-indicator ${power.alignment}`}>
          {power.alignment === 'light' && '☀️'}
          {power.alignment === 'dark' && '🌙'}
          {power.alignment === 'neutral' && '⚖️'}
        </div>
      </div>
      
      <div className="power-description">
        {power.description}
      </div>
      
      <div className="power-scaling">
        <h4>Power Level</h4>
        <div className="level-selector">
          {Array.from({ length: power.maxLevel }, (_, i) => i + 1).map(level => (
            <button
              key={level}
              className={`level-btn ${selectedLevel === level ? 'selected' : ''}`}
              onClick={() => setSelectedLevel(level)}
            >
              {level}
            </button>
          ))}
        </div>
        
        <div className="level-effects">
          {power.scaling_effects?.[selectedLevel]?.map((effect, index) => (
            <div key={index} className="effect-item">
              {effect.description}
            </div>
          ))}
        </div>
      </div>
      
      {isOpposingAlignment && (
        <div className="conflict-warning">
          <div className="warning-icon">⚠️</div>
          <div className="warning-text">
            Using this power will gain {conflictGain} Conflict points.
          </div>
        </div>
      )}
      
      <div className="power-controls">
        <button
          className={`use-power-btn ${isOpposingAlignment ? 'dangerous' : ''}`}
          onClick={handleUsePower}
        >
          Use Power
        </button>
      </div>
      
      {showConflictWarning && (
        <div className="conflict-confirmation">
          <h4>Warning: Opposing Alignment</h4>
          <p>Using this {power.alignment} power will gain {conflictGain} Conflict points.</p>
          <p>Are you sure you want to proceed?</p>
          <div className="confirmation-buttons">
            <button onClick={() => setShowConflictWarning(false)}>Cancel</button>
            <button
              className="confirm-btn"
              onClick={() => {
                onUse(power.id, selectedLevel);
                setShowConflictWarning(false);
              }}
            >
              Use Power
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
```

## Session Conflict Resolution

### End of Session Review
```typescript
interface SessionReviewProps {
  conflictHistory: ConflictEntry[];
  goodDeeds: GoodDeed[];
  onResolve: (goodDeeds: GoodDeed[]) => void;
}

const SessionReview: React.FC<SessionReviewProps> = ({
  conflictHistory,
  goodDeeds,
  onResolve,
}) => {
  const [newGoodDeed, setNewGoodDeed] = useState('');
  const [sessionGoodDeeds, setSessionGoodDeeds] = useState<GoodDeed[]>(goodDeeds);
  
  const totalConflict = conflictHistory.reduce((sum, entry) => sum + entry.amount, 0);
  const totalGoodDeeds = sessionGoodDeeds.length;
  
  const handleAddGoodDeed = () => {
    if (newGoodDeed.trim()) {
      setSessionGoodDeeds(prev => [...prev, {
        description: newGoodDeed,
        timestamp: new Date(),
      }]);
      setNewGoodDeed('');
    }
  };
  
  const handleResolveSession = () => {
    onResolve(sessionGoodDeeds);
  };
  
  return (
    <div className="session-review">
      <h2>Session Review</h2>
      
      <div className="conflict-summary">
        <h3>Conflict Gained</h3>
        <div className="conflict-total">
          Total: {totalConflict} points
        </div>
        <div className="conflict-breakdown">
          {conflictHistory.map((entry, index) => (
            <div key={index} className="conflict-entry">
              <span className="conflict-amount">+{entry.amount}</span>
              <span className="conflict-source">{entry.source}</span>
              <span className="conflict-time">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="good-deeds-section">
        <h3>Good Deeds</h3>
        <div className="good-deeds-list">
          {sessionGoodDeeds.map((deed, index) => (
            <div key={index} className="good-deed-item">
              {deed.description}
            </div>
          ))}
        </div>
        
        <div className="add-good-deed">
          <input
            type="text"
            value={newGoodDeed}
            onChange={(e) => setNewGoodDeed(e.target.value)}
            placeholder="Describe a good deed performed..."
            onKeyPress={(e) => e.key === 'Enter' && handleAddGoodDeed()}
          />
          <button onClick={handleAddGoodDeed}>Add Good Deed</button>
        </div>
      </div>
      
      <div className="morality-preview">
        <h3>Morality Change Preview</h3>
        <div className="morality-calculation">
          <div>Conflict Weight: {totalConflict * 0.7}</div>
          <div>Good Deeds Weight: {totalGoodDeeds * 0.3}</div>
          <div className="net-change">
            Net Change: {(totalGoodDeeds * 0.3) - (totalConflict * 0.7)}
          </div>
        </div>
      </div>
      
      <button
        className="resolve-session-btn"
        onClick={handleResolveSession}
      >
        Resolve Session
      </button>
    </div>
  );
};
```

## Mastery System

### Force Purity Feat Implementation
```typescript
interface ForcePurityFeat {
  id: 'force_purity';
  name: 'Force Purity';
  description: 'Your understanding of the Force is so profound that you can touch the darkness without being consumed by it.';
  prerequisites: {
    level: 15;
    wisdom: 20;
  };
  effects: {
    conflictReduction: number; // Based on Wisdom modifier
    allowsOpposingPowers: boolean;
  };
}

const checkForcePurityPrerequisites = (character: Character): boolean => {
  return character.level >= 15 && character.stats.wisdom >= 20;
};

const applyForcePurity = (character: Character): void => {
  const wisdomModifier = Math.floor((character.stats.wisdom - 10) / 2);
  
  store.dispatch(forceActions.unlockForcePurity({
    wisdomModifier,
  }));
  
  // Show visual feedback
  const visualizer = new AlignmentVisualizer(scene);
  visualizer.animateForcePurity();
};
```

## Integration with Character Progression

### Progression Tree Integration
```typescript
const ForceProgressionNode: React.FC<ProgressionNodeProps> = ({
  node,
  isAvailable,
  isSelected,
  onClick,
}) => {
  const { force } = useSelector(selectForce);
  
  const isForcePurityNode = node.id === 'force_purity';
  const meetsPrerequisites = isForcePurityNode ? checkForcePurityPrerequisites(character) : true;
  
  return (
    <div
      className={`progression-node force-node ${node.type} ${isAvailable && meetsPrerequisites ? 'available' : 'locked'}`}
      onClick={isAvailable && meetsPrerequisites ? onClick : undefined}
    >
      <div className="node-icon">
        {isForcePurityNode && '✨'}
        {node.type === 'force_power' && '⚡'}
      </div>
      
      <div className="node-content">
        <h4>{node.name}</h4>
        <p>{node.description}</p>
        
        {isForcePurityNode && (
          <div className="prerequisites">
            <div className="prerequisite">
              Level 15: {character.level >= 15 ? '✅' : '❌'}
            </div>
            <div className="prerequisite">
              Wisdom 20: {character.stats.wisdom >= 20 ? '✅' : '❌'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
```

This Force and Morality system provides a rich, mechanically sound implementation that captures the nuanced nature of Force usage while providing clear visual feedback and meaningful choices for players.
