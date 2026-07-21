# Legendary Glow System Implementation Plan

## Overview
The Legendary Glow System provides immediate, satisfying visual feedback for player achievements and rare items. When players reach maximum faction rank or acquire legendary items, they receive a distinctive golden "legendary" glow that clearly communicates their accomplishments. This system enhances player satisfaction and provides clear visual hierarchy for different rarity levels and achievement tiers.

## Key Features
- **Faction Achievement Glow**: Golden pulsing borders for maximum faction rank
- **Item Rarity Glow**: Color-coded borders based on item rarity levels
- **Achievement Recognition**: Visual celebration of player accomplishments
- **Clear Visual Hierarchy**: Immediate recognition of legendary status
- **Performance Optimized**: Efficient glow effects that don't impact performance
- **Accessibility Support**: Alternative indicators for color-blind users
- **Customizable Effects**: Different glow styles for different achievement types

## State Management Architecture

### Redux State Structure
```typescript
interface LegendaryGlowState {
  activeGlows: GlowEffect[];
  glowQueue: GlowEffect[];
  settings: GlowSettings;
  achievements: Achievement[];
  factionStatus: FactionStatus[];
}

interface GlowEffect {
  id: string;
  type: 'faction_rank' | 'item_rarity' | 'achievement' | 'mastery';
  targetId: string;
  targetType: 'faction' | 'item' | 'character' | 'ability';
  glowStyle: GlowStyle;
  duration: number;
  priority: 'low' | 'medium' | 'high' | 'legendary';
  isActive: boolean;
  startTime: number;
  animationState: 'entering' | 'active' | 'pulsing' | 'exiting';
}

interface GlowStyle {
  color: string;
  intensity: number;
  pulseRate: number;
  borderWidth: number;
  shadowColor: string;
  shadowBlur: number;
  animationType: 'pulse' | 'ripple' | 'sparkle' | 'aurora';
}

interface Achievement {
  id: string;
  name: string;
  description: string;
  type: 'faction_rank' | 'item_collection' | 'combat_mastery' | 'story_completion';
  rarity: 'common' | 'uncommon' | 'rare' | 'legendary';
  glowEffect: GlowStyle;
  unlockedAt: Date;
  isDisplayed: boolean;
}

interface FactionStatus {
  factionId: string;
  factionName: string;
  currentRank: number;
  maxRank: number;
  isLegendary: boolean;
  glowEffect?: GlowStyle;
}
```

### Redux Actions
```typescript
const legendaryGlowSlice = createSlice({
  name: 'legendaryGlow',
  initialState,
  reducers: {
    addGlowEffect: (state, action: PayloadAction<GlowEffect>) => {
      state.activeGlows.push(action.payload);
      state.glowQueue.push(action.payload);
    },
    removeGlowEffect: (state, action: PayloadAction<string>) => {
      state.activeGlows = state.activeGlows.filter(glow => glow.id !== action.payload);
    },
    updateGlowAnimation: (state, action: PayloadAction<{ id: string; animationState: string }>) => {
      const glow = state.activeGlows.find(g => g.id === action.payload.id);
      if (glow) {
        glow.animationState = action.payload.animationState;
      }
    },
    unlockAchievement: (state, action: PayloadAction<Achievement>) => {
      state.achievements.push(action.payload);
      // Trigger glow effect
      const glowEffect: GlowEffect = {
        id: `achievement_${action.payload.id}`,
        type: 'achievement',
        targetId: action.payload.id,
        targetType: 'character',
        glowStyle: action.payload.glowEffect,
        duration: 5000,
        priority: 'legendary',
        isActive: true,
        startTime: Date.now(),
        animationState: 'entering'
      };
      state.activeGlows.push(glowEffect);
    },
    updateFactionRank: (state, action: PayloadAction<{ factionId: string; newRank: number }>) => {
      const faction = state.factionStatus.find(f => f.factionId === action.payload.factionId);
      if (faction) {
        faction.currentRank = action.payload.newRank;
        faction.isLegendary = faction.currentRank >= faction.maxRank;
        
        if (faction.isLegendary && !faction.glowEffect) {
          faction.glowEffect = createLegendaryFactionGlow();
          // Trigger legendary glow
          const glowEffect: GlowEffect = {
            id: `faction_${faction.factionId}`,
            type: 'faction_rank',
            targetId: faction.factionId,
            targetType: 'faction',
            glowStyle: faction.glowEffect,
            duration: -1, // Permanent
            priority: 'legendary',
            isActive: true,
            startTime: Date.now(),
            animationState: 'active'
          };
          state.activeGlows.push(glowEffect);
        }
      }
    },
    updateGlowSettings: (state, action: PayloadAction<Partial<GlowSettings>>) => {
      state.settings = { ...state.settings, ...action.payload };
    }
  }
});

export const {
  addGlowEffect,
  removeGlowEffect,
  updateGlowAnimation,
  unlockAchievement,
  updateFactionRank,
  updateGlowSettings
} = legendaryGlowSlice.actions;
```

### Async Actions
```typescript
export const checkItemRarityAsync = createAsyncThunk(
  'legendaryGlow/checkItemRarity',
  async (item: Item, { dispatch, getState }) => {
    const state = getState() as RootState;
    
    // Determine rarity glow
    const glowStyle = getRarityGlowStyle(item.rarity);
    
    if (glowStyle) {
      const glowEffect: GlowEffect = {
        id: `item_${item.id}`,
        type: 'item_rarity',
        targetId: item.id,
        targetType: 'item',
        glowStyle,
        duration: 3000,
        priority: getRarityPriority(item.rarity),
        isActive: true,
        startTime: Date.now(),
        animationState: 'entering'
      };
      
      dispatch(addGlowEffect(glowEffect));
      
      // Auto-remove after duration
      setTimeout(() => {
        dispatch(removeGlowEffect(glowEffect.id));
      }, glowEffect.duration);
    }
    
    return glowStyle;
  }
);

export const checkFactionAchievementsAsync = createAsyncThunk(
  'legendaryGlow/checkFactionAchievements',
  async (factionId: string, { dispatch, getState }) => {
    const state = getState() as RootState;
    const faction = state.legendaryGlow.factionStatus.find(f => f.factionId === factionId);
    
    if (faction && faction.isLegendary) {
      // Check if legendary achievement is unlocked
      const legendaryAchievement = state.legendaryGlow.achievements.find(
        a => a.type === 'faction_rank' && a.rarity === 'legendary'
      );
      
      if (!legendaryAchievement) {
        const achievement: Achievement = {
          id: `faction_legendary_${factionId}`,
          name: `${faction.factionName} Legend`,
          description: `Reached maximum rank with ${faction.factionName}`,
          type: 'faction_rank',
          rarity: 'legendary',
          glowEffect: createLegendaryFactionGlow(),
          unlockedAt: new Date(),
          isDisplayed: false
        };
        
        dispatch(unlockAchievement(achievement));
      }
    }
  }
);
```

## Component Architecture

### Main Glow Manager Component
```typescript
const LegendaryGlowManager: React.FC = () => {
  const dispatch = useDispatch();
  const { activeGlows, settings } = useSelector(selectLegendaryGlowState);
  
  useEffect(() => {
    // Process glow queue
    activeGlows.forEach(glow => {
      if (glow.isActive && Date.now() - glow.startTime > glow.duration && glow.duration > 0) {
        dispatch(removeGlowEffect(glow.id));
      }
    });
  }, [activeGlows, dispatch]);
  
  return (
    <GlowManagerContainer>
      {activeGlows.map(glow => (
        <GlowEffect
          key={glow.id}
          glow={glow}
          settings={settings}
        />
      ))}
    </GlowManagerContainer>
  );
};
```

### Glow Effect Component
```typescript
const GlowEffect: React.FC<GlowEffectProps> = ({ glow, settings }) => {
  const effectRef = useRef<HTMLDivElement>(null);
  const dispatch = useDispatch();
  
  useEffect(() => {
    if (!effectRef.current) return;
    
    const timeline = gsap.timeline();
    
    switch (glow.animationState) {
      case 'entering':
        timeline
          .fromTo(effectRef.current, {
            scale: 0,
            opacity: 0
          }, {
            scale: 1,
            opacity: 1,
            duration: 0.5,
            ease: 'back.out(1.7)'
          })
          .call(() => {
            dispatch(updateGlowAnimation({ id: glow.id, animationState: 'active' }));
          });
        break;
        
      case 'active':
        if (glow.glowStyle.animationType === 'pulse') {
          timeline.to(effectRef.current, {
            scale: 1.1,
            duration: glow.glowStyle.pulseRate / 1000,
            ease: 'power2.inOut',
            yoyo: true,
            repeat: -1
          });
        }
        break;
        
      case 'exiting':
        timeline
          .to(effectRef.current, {
            scale: 0,
            opacity: 0,
            duration: 0.3,
            ease: 'power2.in'
          })
          .call(() => {
            dispatch(removeGlowEffect(glow.id));
          });
        break;
    }
  }, [glow.animationState, glow.glowStyle, dispatch, glow.id]);
  
  return (
    <GlowEffectContainer
      ref={effectRef}
      glowStyle={glow.glowStyle}
      settings={settings}
      priority={glow.priority}
    >
      <GlowBorder />
      <GlowShadow />
      {glow.glowStyle.animationType === 'sparkle' && <SparkleEffect />}
      {glow.glowStyle.animationType === 'aurora' && <AuroraEffect />}
    </GlowEffectContainer>
  );
};
```

### Faction Glow Component
```typescript
const FactionGlow: React.FC<FactionGlowProps> = ({ faction, isLegendary }) => {
  const dispatch = useDispatch();
  
  useEffect(() => {
    if (isLegendary && !faction.glowEffect) {
      const glowEffect: GlowEffect = {
        id: `faction_${faction.factionId}`,
        type: 'faction_rank',
        targetId: faction.factionId,
        targetType: 'faction',
        glowStyle: createLegendaryFactionGlow(),
        duration: -1,
        priority: 'legendary',
        isActive: true,
        startTime: Date.now(),
        animationState: 'active'
      };
      
      dispatch(addGlowEffect(glowEffect));
    }
  }, [isLegendary, faction, dispatch]);
  
  return (
    <FactionContainer isLegendary={isLegendary}>
      <FactionIcon src={faction.icon} alt={faction.factionName} />
      <FactionName>{faction.factionName}</FactionName>
      <FactionRank>
        Rank {faction.currentRank}/{faction.maxRank}
      </FactionRank>
      {isLegendary && <LegendaryBadge>LEGENDARY</LegendaryBadge>}
    </FactionContainer>
  );
};
```

### Item Rarity Glow Component
```typescript
const ItemRarityGlow: React.FC<ItemRarityGlowProps> = ({ item, rarity }) => {
  const dispatch = useDispatch();
  
  useEffect(() => {
    if (rarity >= 7) { // Rare or higher
      dispatch(checkItemRarityAsync(item));
    }
  }, [item, rarity, dispatch]);
  
  const glowStyle = getRarityGlowStyle(rarity);
  
  return (
    <ItemContainer rarity={rarity}>
      <ItemImage src={item.image} alt={item.name} />
      <ItemName>{item.name}</ItemName>
      {glowStyle && (
        <RarityGlow glowStyle={glowStyle} />
      )}
      <RarityBadge rarity={rarity}>
        {getRarityName(rarity)}
      </RarityBadge>
    </ItemContainer>
  );
};
```

## Glow Style System

### Glow Style Factory
```typescript
class GlowStyleFactory {
  static createLegendaryFactionGlow(): GlowStyle {
    return {
      color: '#FFD700',
      intensity: 1.0,
      pulseRate: 2000,
      borderWidth: 3,
      shadowColor: '#FFD700',
      shadowBlur: 20,
      animationType: 'pulse'
    };
  }
  
  static createItemRarityGlow(rarity: number): GlowStyle {
    const rarityConfigs = {
      1: { color: '#888888', intensity: 0.3, animationType: 'none' },
      2: { color: '#888888', intensity: 0.5, animationType: 'none' },
      3: { color: '#888888', intensity: 0.7, animationType: 'none' },
      4: { color: '#00FF00', intensity: 0.6, animationType: 'pulse' },
      5: { color: '#00FF00', intensity: 0.8, animationType: 'pulse' },
      6: { color: '#00FF00', intensity: 1.0, animationType: 'pulse' },
      7: { color: '#0088FF', intensity: 0.8, animationType: 'ripple' },
      8: { color: '#0088FF', intensity: 1.0, animationType: 'ripple' },
      9: { color: '#0088FF', intensity: 1.2, animationType: 'sparkle' },
      10: { color: '#FFD700', intensity: 1.5, animationType: 'aurora' }
    };
    
    const config = rarityConfigs[rarity as keyof typeof rarityConfigs] || rarityConfigs[1];
    
    return {
      color: config.color,
      intensity: config.intensity,
      pulseRate: 1500,
      borderWidth: Math.min(rarity, 4),
      shadowColor: config.color,
      shadowBlur: rarity * 2,
      animationType: config.animationType as any
    };
  }
  
  static createAchievementGlow(achievementType: string): GlowStyle {
    const typeConfigs = {
      faction_rank: {
        color: '#FFD700',
        intensity: 1.2,
        animationType: 'pulse'
      },
      item_collection: {
        color: '#FF6B6B',
        intensity: 1.0,
        animationType: 'sparkle'
      },
      combat_mastery: {
        color: '#4ECDC4',
        intensity: 1.1,
        animationType: 'ripple'
      },
      story_completion: {
        color: '#45B7D1',
        intensity: 1.3,
        animationType: 'aurora'
      }
    };
    
    const config = typeConfigs[achievementType as keyof typeof typeConfigs] || typeConfigs.faction_rank;
    
    return {
      color: config.color,
      intensity: config.intensity,
      pulseRate: 2000,
      borderWidth: 4,
      shadowColor: config.color,
      shadowBlur: 25,
      animationType: config.animationType as any
    };
  }
}
```

## Animation Effects

### Special Animation Components
```typescript
const SparkleEffect: React.FC = () => {
  const sparklesRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!sparklesRef.current) return;
    
    // Create sparkle particles
    const sparkles = Array.from({ length: 8 }, (_, i) => {
      const sparkle = document.createElement('div');
      sparkle.className = 'sparkle';
      sparkle.style.setProperty('--delay', `${i * 0.2}s`);
      sparkle.style.setProperty('--angle', `${i * 45}deg`);
      return sparkle;
    });
    
    sparkles.forEach(sparkle => {
      sparklesRef.current!.appendChild(sparkle);
    });
    
    return () => {
      sparkles.forEach(sparkle => {
        sparklesRef.current?.removeChild(sparkle);
      });
    };
  }, []);
  
  return <SparklesContainer ref={sparklesRef} />;
};

const AuroraEffect: React.FC = () => {
  const auroraRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!auroraRef.current) return;
    
    // Create aurora wave effect
    const timeline = gsap.timeline({ repeat: -1 });
    
    timeline
      .to(auroraRef.current, {
        backgroundPosition: '200% 0%',
        duration: 3,
        ease: 'power2.inOut'
      })
      .to(auroraRef.current, {
        backgroundPosition: '0% 0%',
        duration: 3,
        ease: 'power2.inOut'
      });
  }, []);
  
  return <AuroraContainer ref={auroraRef} />;
};

const RippleEffect: React.FC = () => {
  const rippleRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!rippleRef.current) return;
    
    // Create ripple waves
    const timeline = gsap.timeline({ repeat: -1 });
    
    timeline
      .to(rippleRef.current, {
        scale: 1.5,
        opacity: 0,
        duration: 2,
        ease: 'power2.out'
      })
      .set(rippleRef.current, {
        scale: 1,
        opacity: 1
      });
  }, []);
  
  return <RippleContainer ref={rippleRef} />;
};
```

## Integration with Existing Systems

### Faction System Integration
```typescript
export const updateFactionRankAsync = createAsyncThunk(
  'factions/updateRank',
  async (updateData: { factionId: string; newRank: number }, { dispatch, getState }) => {
    const state = getState() as RootState;
    const faction = state.factions.factions.find(f => f.id === updateData.factionId);
    
    if (!faction) throw new Error('Faction not found');
    
    // Update faction rank
    await dispatch(updateFactionRank(updateData));
    
    // Check for legendary status
    if (updateData.newRank >= faction.maxRank) {
      await dispatch(checkFactionAchievementsAsync(updateData.factionId));
    }
    
    return updateData;
  }
);
```

### Inventory System Integration
```typescript
export const addItemToInventoryAsync = createAsyncThunk(
  'inventory/addItem',
  async (item: Item, { dispatch }) => {
    // Add item to inventory
    await dispatch(addInventoryItem(item));
    
    // Check for rarity glow
    if (item.rarity >= 4) { // Uncommon or higher
      await dispatch(checkItemRarityAsync(item));
    }
    
    return item;
  }
);
```

## Styled Components

```typescript
const GlowManagerContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 1000;
`;

const GlowEffectContainer = styled.div<{ 
  glowStyle: GlowStyle; 
  settings: GlowSettings; 
  priority: string; 
}>`
  position: absolute;
  pointer-events: none;
  z-index: ${props => getPriorityZIndex(props.priority)};
  opacity: ${props => props.settings.enabled ? 1 : 0};
`;

const GlowBorder = styled.div<{ glowStyle: GlowStyle }>`
  position: absolute;
  top: -${props => props.glowStyle.borderWidth}px;
  left: -${props => props.glowStyle.borderWidth}px;
  right: -${props => props.glowStyle.borderWidth}px;
  bottom: -${props => props.glowStyle.borderWidth}px;
  border: ${props => props.glowStyle.borderWidth}px solid ${props => props.glowStyle.color};
  border-radius: inherit;
  opacity: ${props => props.glowStyle.intensity};
`;

const GlowShadow = styled.div<{ glowStyle: GlowStyle }>`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: inherit;
  box-shadow: 0 0 ${props => props.glowStyle.shadowBlur}px ${props => props.glowStyle.shadowColor};
  opacity: ${props => props.glowStyle.intensity * 0.5};
`;

const FactionContainer = styled.div<{ isLegendary: boolean }>`
  position: relative;
  padding: 1rem;
  border-radius: 8px;
  background: ${props => props.isLegendary ? 'rgba(255, 215, 0, 0.1)' : 'rgba(0, 0, 0, 0.8)'};
  border: 2px solid ${props => props.isLegendary ? '#FFD700' : 'transparent'};
  transition: all 0.3s ease;
  
  ${props => props.isLegendary && `
    animation: legendaryPulse 2s infinite;
    
    @keyframes legendaryPulse {
      0%, 100% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.5); }
      50% { box-shadow: 0 0 40px rgba(255, 215, 0, 0.8); }
    }
  `}
`;

const LegendaryBadge = styled.div`
  position: absolute;
  top: -10px;
  right: -10px;
  background: linear-gradient(45deg, #FFD700, #FFA500);
  color: #000;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  text-transform: uppercase;
  animation: badgeGlow 1.5s infinite;
  
  @keyframes badgeGlow {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }
`;

const ItemContainer = styled.div<{ rarity: number }>`
  position: relative;
  padding: 0.5rem;
  border-radius: 6px;
  background: ${props => getRarityBackground(props.rarity)};
  border: 2px solid ${props => getRarityBorder(props.rarity)};
  transition: all 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
`;

const RarityGlow = styled.div<{ glowStyle: GlowStyle }>`
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  border-radius: 8px;
  background: ${props => props.glowStyle.color};
  opacity: ${props => props.glowStyle.intensity * 0.3};
  z-index: -1;
`;

const RarityBadge = styled.div<{ rarity: number }>`
  position: absolute;
  top: -5px;
  right: -5px;
  background: ${props => getRarityColor(props.rarity)};
  color: white;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-size: 0.6rem;
  font-weight: bold;
  text-transform: uppercase;
`;

const SparklesContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  
  .sparkle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: #FFD700;
    border-radius: 50%;
    animation: sparkle 2s infinite;
    animation-delay: var(--delay);
    transform: rotate(var(--angle)) translateX(20px);
  }
  
  @keyframes sparkle {
    0%, 100% { opacity: 0; transform: rotate(var(--angle)) translateX(20px) scale(0); }
    50% { opacity: 1; transform: rotate(var(--angle)) translateX(30px) scale(1); }
  }
`;

const AuroraContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 215, 0, 0.3),
    rgba(255, 215, 0, 0.6),
    rgba(255, 215, 0, 0.3),
    transparent
  );
  background-size: 200% 100%;
  border-radius: inherit;
  pointer-events: none;
`;

const RippleContainer = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  border: 2px solid currentColor;
  border-radius: inherit;
  transform: translate(-50%, -50%);
  pointer-events: none;
`;
```

## Performance Optimizations

### Glow Performance Manager
```typescript
class GlowPerformanceManager {
  private static instance: GlowPerformanceManager;
  private activeEffects = new Set<string>();
  private maxEffects = 10;
  
  static getInstance(): GlowPerformanceManager {
    if (!GlowPerformanceManager.instance) {
      GlowPerformanceManager.instance = new GlowPerformanceManager();
    }
    return GlowPerformanceManager.instance;
  }
  
  canAddEffect(effectId: string, priority: string): boolean {
    if (this.activeEffects.has(effectId)) return false;
    
    if (this.activeEffects.size >= this.maxEffects) {
      // Remove lowest priority effect if at limit
      this.removeLowestPriorityEffect();
    }
    
    this.activeEffects.add(effectId);
    return true;
  }
  
  removeEffect(effectId: string): void {
    this.activeEffects.delete(effectId);
  }
  
  private removeLowestPriorityEffect(): void {
    // Implementation to remove lowest priority glow effect
    // This would interact with the Redux store
  }
  
  adjustMaxEffects(performance: number): void {
    if (performance < 30) {
      this.maxEffects = 5;
    } else if (performance < 45) {
      this.maxEffects = 8;
    } else {
      this.maxEffects = 10;
    }
  }
}
```

### Effect Pooling
```typescript
class GlowEffectPool {
  private pool: HTMLDivElement[] = [];
  private maxPoolSize = 20;
  
  getEffect(): HTMLDivElement {
    if (this.pool.length > 0) {
      return this.pool.pop()!;
    }
    
    const effect = document.createElement('div');
    effect.className = 'glow-effect';
    return effect;
  }
  
  returnEffect(effect: HTMLDivElement): void {
    if (this.pool.length < this.maxPoolSize) {
      effect.className = 'glow-effect';
      this.pool.push(effect);
    }
  }
  
  clearPool(): void {
    this.pool = [];
  }
}
```

## Accessibility Features

```typescript
const useGlowAccessibility = () => {
  const [isColorBlind, setIsColorBlind] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  
  useEffect(() => {
    // Check for color blindness support
    const colorBlindQuery = window.matchMedia('(prefers-color-scheme: high-contrast)');
    setIsColorBlind(colorBlindQuery.matches);
    
    // Check for reduced motion preference
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(motionQuery.matches);
    
    const handleColorBlindChange = (event: MediaQueryListEvent) => {
      setIsColorBlind(event.matches);
    };
    
    const handleMotionChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };
    
    colorBlindQuery.addEventListener('change', handleColorBlindChange);
    motionQuery.addEventListener('change', handleMotionChange);
    
    return () => {
      colorBlindQuery.removeEventListener('change', handleColorBlindChange);
      motionQuery.removeEventListener('change', handleMotionChange);
    };
  }, []);
  
  const getAccessibleGlowStyle = (baseStyle: GlowStyle): GlowStyle => {
    if (isColorBlind) {
      // Use high contrast colors for color-blind users
      return {
        ...baseStyle,
        color: '#FFFFFF',
        shadowColor: '#FFFFFF',
        borderWidth: baseStyle.borderWidth + 1
      };
    }
    
    if (prefersReducedMotion) {
      // Disable animations for users who prefer reduced motion
      return {
        ...baseStyle,
        animationType: 'none',
        pulseRate: 0
      };
    }
    
    return baseStyle;
  };
  
  return { isColorBlind, prefersReducedMotion, getAccessibleGlowStyle };
};
```

## Testing Strategy

### Unit Tests
```typescript
describe('LegendaryGlowManager', () => {
  it('should add glow effect when achievement is unlocked', () => {
    const mockAchievement = {
      id: 'test_achievement',
      name: 'Test Achievement',
      rarity: 'legendary'
    };
    
    const { store } = renderWithProviders(<LegendaryGlowManager />);
    
    store.dispatch(unlockAchievement(mockAchievement));
    
    const state = store.getState();
    expect(state.legendaryGlow.activeGlows).toHaveLength(1);
    expect(state.legendaryGlow.activeGlows[0].type).toBe('achievement');
  });
  
  it('should apply correct rarity glow to items', () => {
    const mockItem = {
      id: 'test_item',
      name: 'Legendary Sword',
      rarity: 10
    };
    
    render(<ItemRarityGlow item={mockItem} rarity={10} />);
    
    expect(screen.getByText('Legendary')).toBeInTheDocument();
  });
});
```

### Integration Tests
```typescript
describe('Legendary Glow Integration', () => {
  it('should trigger faction glow when reaching max rank', async () => {
    const { store } = renderWithProviders(<FactionScreen />);
    
    // Update faction to max rank
    await store.dispatch(updateFactionRankAsync({
      factionId: 'test_faction',
      newRank: 10
    }));
    
    const state = store.getState();
    const faction = state.legendaryGlow.factionStatus.find(f => f.factionId === 'test_faction');
    expect(faction?.isLegendary).toBe(true);
  });
});
```

## Success Metrics

1. **User Satisfaction**: Feedback on visual feedback for achievements
2. **Engagement**: Time spent viewing legendary items and achievements
3. **Performance**: Frame rate impact of glow effects
4. **Accessibility**: Usage by color-blind and motion-sensitive users
5. **Achievement Completion**: Rate of achievement unlocking
6. **Visual Clarity**: User understanding of rarity and achievement levels

This implementation plan provides immediate, satisfying visual feedback for player accomplishments while maintaining performance and accessibility standards, enhancing the overall user experience in the Star Wars universe.
