# Tactical Visual Novel System Implementation Plan

## Overview
The Tactical Visual Novel System creates a unique hybrid experience that combines the expressive storytelling of visual novels with tactical gameplay. High-quality 2D character portraits appear during dialogue and key combat moments, providing emotional depth and character focus while maintaining the immersive 3D tactical gameplay. This system bridges the gap between narrative and gameplay, creating memorable character moments and dramatic combat sequences.

## Key Features
- **2D Character Portraits**: High-quality, expressive character artwork for dialogue and key moments
- **Tactical Integration**: Seamless blending of 2D portraits with 3D tactical gameplay
- **Emotional Storytelling**: Character portraits that convey emotions and reactions
- **Combat Emphasis**: Portrait pop-ups during critical hits, special abilities, and dramatic moments
- **Accessibility**: Resource-efficient alternative to 3D facial animations
- **Character Personality**: Unique portrait styles and expressions for each character
- **Cinematic Moments**: Portrait-based storytelling during pivotal story beats

## State Management Architecture

### Redux State Structure
```typescript
interface VisualNovelState {
  isActive: boolean;
  currentPortrait: CharacterPortrait | null;
  portraitQueue: CharacterPortrait[];
  displayMode: 'dialogue' | 'combat' | 'story' | 'idle';
  portraitPosition: 'left' | 'right' | 'center' | 'fullscreen';
  animationState: 'entering' | 'idle' | 'emoting' | 'exiting';
  backgroundBlur: boolean;
  audioContext: AudioContext;
}

interface CharacterPortrait {
  id: string;
  characterId: string;
  characterName: string;
  portraitImage: string;
  emotion: 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'determined' | 'fearful';
  position: 'left' | 'right' | 'center' | 'fullscreen';
  dialogue: string;
  audioFile?: string;
  duration: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  combatContext?: CombatContext;
}

interface CombatContext {
  triggerType: 'critical_hit' | 'special_ability' | 'damage_taken' | 'victory' | 'defeat';
  targetCharacter?: string;
  damageAmount?: number;
  abilityName?: string;
  oneLiner?: string;
}

interface PortraitAnimation {
  type: 'fade_in' | 'slide_in' | 'zoom_in' | 'shake' | 'flash' | 'fade_out';
  duration: number;
  easing: string;
  delay?: number;
}
```

### Redux Actions
```typescript
const visualNovelSlice = createSlice({
  name: 'visualNovel',
  initialState,
  reducers: {
    showPortrait: (state, action: PayloadAction<CharacterPortrait>) => {
      state.isActive = true;
      state.currentPortrait = action.payload;
      state.animationState = 'entering';
      state.displayMode = action.payload.combatContext ? 'combat' : 'dialogue';
      state.portraitPosition = action.payload.position;
    },
    updateEmotion: (state, action: PayloadAction<{ emotion: string; duration?: number }>) => {
      if (state.currentPortrait) {
        state.currentPortrait.emotion = action.payload.emotion;
        state.animationState = 'emoting';
      }
    },
    hidePortrait: (state) => {
      state.animationState = 'exiting';
    },
    clearPortrait: (state) => {
      state.isActive = false;
      state.currentPortrait = null;
      state.animationState = 'idle';
    },
    queuePortrait: (state, action: PayloadAction<CharacterPortrait>) => {
      state.portraitQueue.push(action.payload);
    },
    setBackgroundBlur: (state, action: PayloadAction<boolean>) => {
      state.backgroundBlur = action.payload;
    }
  }
});

export const {
  showPortrait,
  updateEmotion,
  hidePortrait,
  clearPortrait,
  queuePortrait,
  setBackgroundBlur
} = visualNovelSlice.actions;
```

### Async Actions
```typescript
export const displayCombatPortraitAsync = createAsyncThunk(
  'visualNovel/displayCombatPortrait',
  async (context: CombatContext, { dispatch, getState }) => {
    const state = getState() as RootState;
    const character = state.combat.characters.find(c => c.id === context.targetCharacter);
    
    if (!character) return;
    
    const portrait: CharacterPortrait = {
      id: `combat_${Date.now()}`,
      characterId: character.id,
      characterName: character.name,
      portraitImage: character.portraitImage,
      emotion: getEmotionForContext(context),
      position: 'center',
      dialogue: context.oneLiner || '',
      duration: 3000,
      priority: 'high',
      combatContext: context
    };
    
    dispatch(showPortrait(portrait));
    
    // Auto-hide after duration
    setTimeout(() => {
      dispatch(hidePortrait());
    }, portrait.duration);
    
    return portrait;
  }
);

export const displayDialoguePortraitAsync = createAsyncThunk(
  'visualNovel/displayDialoguePortrait',
  async (dialogueData: DialogueData, { dispatch }) => {
    const portrait: CharacterPortrait = {
      id: `dialogue_${Date.now()}`,
      characterId: dialogueData.characterId,
      characterName: dialogueData.characterName,
      portraitImage: dialogueData.portraitImage,
      emotion: dialogueData.emotion,
      position: dialogueData.position,
      dialogue: dialogueData.text,
      audioFile: dialogueData.audioFile,
      duration: calculateDialogueDuration(dialogueData.text),
      priority: 'medium'
    };
    
    dispatch(showPortrait(portrait));
    
    return portrait;
  }
);
```

## Component Architecture

### Main Visual Novel Component
```typescript
const VisualNovelOverlay: React.FC = () => {
  const dispatch = useDispatch();
  const { 
    isActive, 
    currentPortrait, 
    displayMode, 
    portraitPosition, 
    animationState, 
    backgroundBlur 
  } = useSelector(selectVisualNovelState);
  
  const handlePortraitClick = () => {
    if (currentPortrait && displayMode === 'dialogue') {
      // Advance dialogue or close portrait
      dispatch(hidePortrait());
    }
  };
  
  if (!isActive || !currentPortrait) return null;
  
  return (
    <VisualNovelContainer>
      {backgroundBlur && <BackgroundBlur />}
      <PortraitDisplay
        portrait={currentPortrait}
        position={portraitPosition}
        animationState={animationState}
        onClick={handlePortraitClick}
      />
      {displayMode === 'dialogue' && (
        <DialogueBox
          text={currentPortrait.dialogue}
          characterName={currentPortrait.characterName}
        />
      )}
      {displayMode === 'combat' && (
        <CombatOverlay context={currentPortrait.combatContext} />
      )}
    </VisualNovelContainer>
  );
};
```

### Portrait Display Component
```typescript
const PortraitDisplay: React.FC<PortraitDisplayProps> = ({ 
  portrait, 
  position, 
  animationState, 
  onClick 
}) => {
  const portraitRef = useRef<HTMLDivElement>(null);
  const emotionRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!portraitRef.current) return;
    
    // Play entrance animation
    const timeline = gsap.timeline();
    
    switch (animationState) {
      case 'entering':
        timeline
          .fromTo(portraitRef.current, {
            scale: 0,
            opacity: 0,
            x: position === 'left' ? -100 : position === 'right' ? 100 : 0,
            y: position === 'center' ? -50 : 0
          }, {
            scale: 1,
            opacity: 1,
            x: 0,
            y: 0,
            duration: 0.5,
            ease: 'back.out(1.7)'
          });
        break;
        
      case 'emoting':
        timeline
          .to(emotionRef.current, {
            scale: 1.1,
            duration: 0.2,
            ease: 'power2.out'
          })
          .to(emotionRef.current, {
            scale: 1,
            duration: 0.2,
            ease: 'power2.inOut'
          });
        break;
        
      case 'exiting':
        timeline
          .to(portraitRef.current, {
            scale: 0,
            opacity: 0,
            duration: 0.3,
            ease: 'power2.in'
          })
          .call(() => {
            // Clear portrait after animation
            dispatch(clearPortrait());
          });
        break;
    }
  }, [animationState, position]);
  
  return (
    <PortraitContainer
      ref={portraitRef}
      position={position}
      onClick={onClick}
      isClickable={displayMode === 'dialogue'}
    >
      <PortraitImage
        ref={emotionRef}
        src={getEmotionImage(portrait.portraitImage, portrait.emotion)}
        alt={`${portrait.characterName} - ${portrait.emotion}`}
      />
      <PortraitGlow emotion={portrait.emotion} />
      {portrait.combatContext && (
        <CombatEffects context={portrait.combatContext} />
      )}
    </PortraitContainer>
  );
};
```

### Dialogue Box Component
```typescript
const DialogueBox: React.FC<DialogueBoxProps> = ({ text, characterName }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  
  useEffect(() => {
    setDisplayedText('');
    setIsComplete(false);
    
    // Typewriter effect
    let index = 0;
    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(prev => prev + text[index]);
        index++;
      } else {
        setIsComplete(true);
        clearInterval(interval);
      }
    }, 30);
    
    return () => clearInterval(interval);
  }, [text]);
  
  return (
    <DialogueContainer>
      <CharacterName>{characterName}</CharacterName>
      <DialogueText isComplete={isComplete}>
        {displayedText}
        {!isComplete && <TypewriterCursor />}
      </DialogueText>
      {isComplete && <ContinueIndicator />}
    </DialogueContainer>
  );
};
```

### Combat Overlay Component
```typescript
const CombatOverlay: React.FC<CombatOverlayProps> = ({ context }) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!overlayRef.current || !context) return;
    
    const timeline = gsap.timeline();
    
    switch (context.triggerType) {
      case 'critical_hit':
        timeline
          .to(overlayRef.current, {
            scale: 1.2,
            duration: 0.2,
            ease: 'power2.out'
          })
          .to(overlayRef.current, {
            scale: 1,
            duration: 0.2,
            ease: 'power2.inOut'
          });
        break;
        
      case 'special_ability':
        timeline
          .to(overlayRef.current, {
            rotation: 5,
            duration: 0.1,
            ease: 'power2.out'
          })
          .to(overlayRef.current, {
            rotation: -5,
            duration: 0.1,
            ease: 'power2.inOut'
          })
          .to(overlayRef.current, {
            rotation: 0,
            duration: 0.1,
            ease: 'power2.inOut'
          });
        break;
    }
  }, [context]);
  
  return (
    <CombatOverlayContainer ref={overlayRef}>
      {context.triggerType === 'critical_hit' && (
        <CriticalHitEffect damage={context.damageAmount} />
      )}
      {context.triggerType === 'special_ability' && (
        <SpecialAbilityEffect abilityName={context.abilityName} />
      )}
      {context.oneLiner && (
        <OneLinerText>{context.oneLiner}</OneLinerText>
      )}
    </CombatOverlayContainer>
  );
};
```

## Integration with Combat System

### Combat Portrait Triggers
```typescript
class CombatPortraitManager {
  private static instance: CombatPortraitManager;
  
  static getInstance(): CombatPortraitManager {
    if (!CombatPortraitManager.instance) {
      CombatPortraitManager.instance = new CombatPortraitManager();
    }
    return CombatPortraitManager.instance;
  }
  
  triggerCriticalHit(character: CombatCharacter, damage: number): void {
    const oneLiners = [
      "Feel the power!",
      "That's how it's done!",
      "Critical strike!",
      "Perfect hit!"
    ];
    
    const context: CombatContext = {
      triggerType: 'critical_hit',
      targetCharacter: character.id,
      damageAmount: damage,
      oneLiner: oneLiners[Math.floor(Math.random() * oneLiners.length)]
    };
    
    dispatch(displayCombatPortraitAsync(context));
  }
  
  triggerSpecialAbility(character: CombatCharacter, ability: Ability): void {
    const context: CombatContext = {
      triggerType: 'special_ability',
      targetCharacter: character.id,
      abilityName: ability.name,
      oneLiner: ability.oneLiner
    };
    
    dispatch(displayCombatPortraitAsync(context));
  }
  
  triggerDamageTaken(character: CombatCharacter, damage: number): void {
    const context: CombatContext = {
      triggerType: 'damage_taken',
      targetCharacter: character.id,
      damageAmount: damage
    };
    
    dispatch(displayCombatPortraitAsync(context));
  }
  
  triggerVictory(character: CombatCharacter): void {
    const context: CombatContext = {
      triggerType: 'victory',
      targetCharacter: character.id,
      oneLiner: "Victory is ours!"
    };
    
    dispatch(displayCombatPortraitAsync(context));
  }
}
```

### Combat Integration
```typescript
const CombatScreen: React.FC = () => {
  const dispatch = useDispatch();
  const combatState = useSelector(selectCombatState);
  const visualNovelState = useSelector(selectVisualNovelState);
  
  const handleCombatAction = (action: CombatAction) => {
    // Process combat action
    const result = processCombatAction(action);
    
    // Trigger portrait displays based on results
    if (result.isCritical) {
      CombatPortraitManager.getInstance().triggerCriticalHit(
        result.attacker, 
        result.damage
      );
    }
    
    if (result.specialAbility) {
      CombatPortraitManager.getInstance().triggerSpecialAbility(
        result.attacker,
        result.specialAbility
      );
    }
    
    if (result.damageTaken > 0) {
      CombatPortraitManager.getInstance().triggerDamageTaken(
        result.target,
        result.damageTaken
      );
    }
  };
  
  return (
    <CombatContainer>
      <CombatDiorama />
      <CombatUI onAction={handleCombatAction} />
      <VisualNovelOverlay />
    </CombatContainer>
  );
};
```

## Emotion System

### Emotion Management
```typescript
class EmotionManager {
  private static instance: EmotionManager;
  private emotionMappings = new Map<string, string[]>();
  
  static getInstance(): EmotionManager {
    if (!EmotionManager.instance) {
      EmotionManager.instance = new EmotionManager();
    }
    return EmotionManager.instance;
  }
  
  getEmotionForContext(context: CombatContext): string {
    switch (context.triggerType) {
      case 'critical_hit':
        return 'determined';
      case 'special_ability':
        return 'focused';
      case 'damage_taken':
        return 'pain';
      case 'victory':
        return 'happy';
      case 'defeat':
        return 'sad';
      default:
        return 'neutral';
    }
  }
  
  getEmotionImage(baseImage: string, emotion: string): string {
    // Replace emotion suffix in image path
    const basePath = baseImage.replace(/_(neutral|happy|sad|angry|surprised|determined|fearful)\./, '_');
    return `${basePath}${emotion}.png`;
  }
  
  registerCharacterEmotions(characterId: string, emotions: string[]): void {
    this.emotionMappings.set(characterId, emotions);
  }
  
  getAvailableEmotions(characterId: string): string[] {
    return this.emotionMappings.get(characterId) || ['neutral'];
  }
}
```

## Audio Integration

### Portrait Audio System
```typescript
class PortraitAudioManager {
  private static instance: PortraitAudioManager;
  private audioContext: AudioContext;
  private audioCache = new Map<string, AudioBuffer>();
  
  static getInstance(): PortraitAudioManager {
    if (!PortraitAudioManager.instance) {
      PortraitAudioManager.instance = new PortraitAudioManager();
    }
    return PortraitAudioManager.instance;
  }
  
  async playPortraitAudio(audioFile: string): Promise<void> {
    try {
      const audioBuffer = await this.getAudioBuffer(audioFile);
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      source.start();
    } catch (error) {
      console.warn('Failed to play portrait audio:', error);
    }
  }
  
  async playEmotionSound(emotion: string): Promise<void> {
    const emotionSounds = {
      happy: 'happy_chime.mp3',
      sad: 'sad_moan.mp3',
      angry: 'angry_grunt.mp3',
      surprised: 'surprise_gasp.mp3',
      determined: 'determined_growl.mp3',
      fearful: 'fear_whimper.mp3'
    };
    
    const soundFile = emotionSounds[emotion as keyof typeof emotionSounds];
    if (soundFile) {
      await this.playPortraitAudio(soundFile);
    }
  }
  
  private async getAudioBuffer(audioFile: string): Promise<AudioBuffer> {
    if (this.audioCache.has(audioFile)) {
      return this.audioCache.get(audioFile)!;
    }
    
    const response = await fetch(audioFile);
    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    
    this.audioCache.set(audioFile, audioBuffer);
    return audioBuffer;
  }
}
```

## Styled Components

```typescript
const VisualNovelContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 1000;
  pointer-events: none;
`;

const BackgroundBlur = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
  pointer-events: none;
`;

const PortraitContainer = styled.div<{ position: string; isClickable: boolean }>`
  position: absolute;
  ${props => {
    switch (props.position) {
      case 'left':
        return `
          left: 50px;
          bottom: 100px;
        `;
      case 'right':
        return `
          right: 50px;
          bottom: 100px;
        `;
      case 'center':
        return `
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
        `;
      case 'fullscreen':
        return `
          left: 0;
          top: 0;
          width: 100%;
          height: 100%;
        `;
      default:
        return '';
    }
  }}
  cursor: ${props => props.isClickable ? 'pointer' : 'default'};
  pointer-events: auto;
`;

const PortraitImage = styled.img`
  max-width: 300px;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
`;

const PortraitGlow = styled.div<{ emotion: string }>`
  position: absolute;
  top: -10px;
  left: -10px;
  right: -10px;
  bottom: -10px;
  border-radius: 12px;
  background: ${props => getEmotionGlow(props.emotion)};
  z-index: -1;
  opacity: 0.6;
  animation: pulse 2s infinite;
  
  @keyframes pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
`;

const DialogueContainer = styled.div`
  position: absolute;
  bottom: 50px;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  max-width: 800px;
  background: rgba(0, 0, 0, 0.9);
  border: 2px solid ${props => props.theme.colors.primary};
  border-radius: 12px;
  padding: 1.5rem;
  pointer-events: auto;
`;

const CharacterName = styled.h3`
  color: ${props => props.theme.colors.accent};
  margin: 0 0 0.5rem 0;
  font-size: 1.2rem;
  font-weight: bold;
`;

const DialogueText = styled.p<{ isComplete: boolean }>`
  color: ${props => props.theme.colors.text};
  font-size: 1.1rem;
  line-height: 1.5;
  margin: 0;
  min-height: 2.5rem;
`;

const TypewriterCursor = styled.span`
  display: inline-block;
  width: 2px;
  height: 1.2em;
  background: ${props => props.theme.colors.accent};
  animation: blink 1s infinite;
  
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
`;

const ContinueIndicator = styled.div`
  position: absolute;
  bottom: 10px;
  right: 20px;
  width: 20px;
  height: 20px;
  border: 2px solid ${props => props.theme.colors.accent};
  border-top: none;
  border-left: none;
  transform: rotate(-45deg);
  animation: bounce 1s infinite;
  
  @keyframes bounce {
    0%, 20%, 50%, 80%, 100% { transform: rotate(-45deg) translateY(0); }
    40% { transform: rotate(-45deg) translateY(-5px); }
    60% { transform: rotate(-45deg) translateY(-3px); }
  }
`;

const CombatOverlayContainer = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
`;

const OneLinerText = styled.div`
  position: absolute;
  top: -50px;
  left: 50%;
  transform: translateX(-50%);
  color: ${props => props.theme.colors.accent};
  font-size: 1.5rem;
  font-weight: bold;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
`;
```

## Performance Optimizations

### Portrait Caching
```typescript
class PortraitCache {
  private cache = new Map<string, HTMLImageElement>();
  
  async preloadPortrait(portraitPath: string): Promise<void> {
    if (this.cache.has(portraitPath)) return;
    
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        this.cache.set(portraitPath, img);
        resolve();
      };
      img.onerror = reject;
      img.src = portraitPath;
    });
  }
  
  getPortrait(portraitPath: string): HTMLImageElement | null {
    return this.cache.get(portraitPath) || null;
  }
  
  preloadCharacterEmotions(characterId: string, basePath: string): void {
    const emotions = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'determined', 'fearful'];
    emotions.forEach(emotion => {
      const path = `${basePath}_${emotion}.png`;
      this.preloadPortrait(path).catch(console.warn);
    });
  }
}
```

### Animation Performance
```typescript
class VisualNovelPerformanceManager {
  private static instance: VisualNovelPerformanceManager;
  private frameRate: number = 60;
  private lastFrameTime: number = 0;
  
  static getInstance(): VisualNovelPerformanceManager {
    if (!VisualNovelPerformanceManager.instance) {
      VisualNovelPerformanceManager.instance = new VisualNovelPerformanceManager();
    }
    return VisualNovelPerformanceManager.instance;
  }
  
  shouldRender(currentTime: number): boolean {
    const deltaTime = currentTime - this.lastFrameTime;
    const targetFrameTime = 1000 / this.frameRate;
    
    if (deltaTime >= targetFrameTime) {
      this.lastFrameTime = currentTime;
      return true;
    }
    
    return false;
  }
  
  adjustQuality(performance: number): void {
    if (performance < 30) {
      this.frameRate = 30;
    } else if (performance < 45) {
      this.frameRate = 45;
    } else {
      this.frameRate = 60;
    }
  }
}
```

## Accessibility Features

```typescript
const useVisualNovelAccessibility = () => {
  const [isScreenReaderActive, setIsScreenReaderActive] = useState(false);
  
  useEffect(() => {
    // Check if screen reader is active
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setIsScreenReaderActive(mediaQuery.matches);
    
    const handleChange = (event: MediaQueryListEvent) => {
      setIsScreenReaderActive(event.matches);
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);
  
  const announcePortrait = (portrait: CharacterPortrait) => {
    if (isScreenReaderActive) {
      const announcement = `${portrait.characterName} appears with a ${portrait.emotion} expression. ${portrait.dialogue}`;
      // Use ARIA live region for screen reader announcement
      const liveRegion = document.getElementById('aria-live-region');
      if (liveRegion) {
        liveRegion.textContent = announcement;
      }
    }
  };
  
  return { isScreenReaderActive, announcePortrait };
};
```

## Testing Strategy

### Unit Tests
```typescript
describe('VisualNovelOverlay', () => {
  it('should display portrait when active', () => {
    const mockPortrait = {
      id: '1',
      characterName: 'Luke Skywalker',
      portraitImage: 'luke_neutral.png',
      emotion: 'determined',
      dialogue: 'May the Force be with you.'
    };
    
    render(<VisualNovelOverlay />);
    
    expect(screen.getByAltText('Luke Skywalker - determined')).toBeInTheDocument();
    expect(screen.getByText('May the Force be with you.')).toBeInTheDocument();
  });
  
  it('should trigger combat portrait on critical hit', () => {
    const mockContext = {
      triggerType: 'critical_hit',
      targetCharacter: 'luke',
      damageAmount: 25
    };
    
    render(<CombatScreen />);
    
    // Simulate critical hit
    fireEvent.click(screen.getByText('Attack'));
    
    expect(screen.getByText(/Critical strike!/)).toBeInTheDocument();
  });
});
```

### Integration Tests
```typescript
describe('Visual Novel Integration', () => {
  it('should integrate with combat system', async () => {
    const { store } = renderWithProviders(<CombatScreen />);
    
    // Perform combat action
    fireEvent.click(screen.getByText('Force Push'));
    
    // Wait for portrait to appear
    await waitFor(() => {
      const state = store.getState();
      expect(state.visualNovel.isActive).toBe(true);
      expect(state.visualNovel.currentPortrait).toBeTruthy();
    });
  });
});
```

## Success Metrics

1. **User Engagement**: Time spent in dialogue vs. combat
2. **Emotional Impact**: User feedback on character expressions and reactions
3. **Performance**: Frame rate during portrait animations
4. **Accessibility**: Screen reader usage and keyboard navigation
5. **Memory Usage**: Efficient portrait caching and loading
6. **User Satisfaction**: Feedback on hybrid visual novel/tactical experience

This implementation plan creates a unique hybrid experience that combines the emotional depth of visual novels with the tactical engagement of 3D combat, providing memorable character moments while maintaining the immersive Star Wars universe aesthetic established in the previous plans.
