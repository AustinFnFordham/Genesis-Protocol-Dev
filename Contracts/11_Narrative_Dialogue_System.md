# Narrative Dialogue System Implementation Plan

## Overview
Implement a sophisticated narrative dialogue system that transforms traditional RPG dialogue into an immersive, consequence-driven experience. This system will handle the 4-choice dialogue structure with standardized attitudes, dynamic consequences, and seamless integration with the game's narrative currency system.

## Core Concepts

### 1. Standardized 4-Choice System
- **Consistent Attitudes**: Each choice position represents a specific attitude (Compassionate, Domineering, Inquisitive, Pragmatic)
- **Visual Consistency**: Clean, cinematic UI with subtle color-coding and icons
- **Mechanical Standardization**: Structured data format for LLM integration

### 2. Consequence-Based Outcomes
- **Natural Consequences**: Outcomes appear after choices, not during selection
- **Narrative Currency**: Integration with Threat/Advantage system
- **Story Cards**: Major events create collectible story cards

### 3. Immersive Presentation
- **Cinematic Flow**: Dialogue feels like natural conversation
- **Contextual UI**: Information appears only when relevant
- **Visual Feedback**: Subtle animations and effects

## Technical Architecture

### State Management Integration

```typescript
// Redux slice for dialogue management
interface DialogueState {
  currentDialogue: DialogueNode | null;
  dialogueHistory: DialogueHistoryEntry[];
  activeChoices: Choice[];
  consequenceQueue: Consequence[];
  storyCards: StoryCard[];
  narrativeFlags: Record<string, boolean>;
  characterRelationships: RelationshipData;
  dialogueContext: DialogueContext;
}

interface DialogueNode {
  id: string;
  speaker: string;
  text: string;
  choices: Choice[];
  characterModel?: CharacterModelUpdate;
  environmentChange?: EnvironmentChange;
  audio?: AudioSettings;
  visualEffects?: VisualEffect[];
}

interface Choice {
  id: string;
  text: string;
  attitude: 'compassionate' | 'domineering' | 'inquisitive' | 'pragmatic';
  leadsToEventId: string;
  consequences?: Consequence[];
  requirements?: ChoiceRequirement[];
  hidden?: boolean;
}

interface Consequence {
  id: string;
  type: 'narrative_currency' | 'relationship_change' | 'story_flag' | 'item_gain' | 'nemesis_creation';
  data: any;
  displayText: string;
  visualEffect?: VisualEffect;
}

interface StoryCard {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  category: 'nemesis' | 'alliance' | 'mystery' | 'achievement';
  unlockedAt: Date;
  relatedEvents: string[];
}

const dialogueSlice = createSlice({
  name: 'dialogue',
  initialState,
  reducers: {
    startDialogue: (state, action) => {
      state.currentDialogue = action.payload;
      state.activeChoices = action.payload.choices;
    },
    makeChoice: (state, action) => {
      const choice = action.payload;
      state.dialogueHistory.push({
        dialogueId: state.currentDialogue!.id,
        choiceId: choice.id,
        timestamp: new Date().toISOString()
      });
      
      // Queue consequences
      if (choice.consequences) {
        state.consequenceQueue.push(...choice.consequences);
      }
    },
    loadNextDialogue: (state, action) => {
      state.currentDialogue = action.payload;
      state.activeChoices = action.payload.choices;
    },
    addConsequence: (state, action) => {
      state.consequenceQueue.push(action.payload);
    },
    processConsequence: (state, action) => {
      const consequence = action.payload;
      
      switch (consequence.type) {
        case 'narrative_currency':
          state.narrativeFlags[consequence.data.currency] = consequence.data.value;
          break;
        case 'story_flag':
          state.narrativeFlags[consequence.data.flag] = consequence.data.value;
          break;
        case 'nemesis_creation':
          state.storyCards.push({
            id: `nemesis_${Date.now()}`,
            title: 'A Rivalry Forged in Fire',
            description: consequence.data.description,
            imageUrl: consequence.data.imageUrl,
            category: 'nemesis',
            unlockedAt: new Date(),
            relatedEvents: [consequence.data.eventId]
          });
          break;
      }
      
      // Remove from queue
      state.consequenceQueue = state.consequenceQueue.filter(c => c.id !== consequence.id);
    },
    updateRelationship: (state, action) => {
      const { characterId, change } = action.payload;
      state.characterRelationships[characterId] = {
        ...state.characterRelationships[characterId],
        value: (state.characterRelationships[characterId]?.value || 0) + change
      };
    }
  }
});
```

### Dialogue Engine

```typescript
class DialogueEngine {
  private currentDialogue: DialogueNode | null;
  private dialogueHistory: DialogueHistoryEntry[];
  private consequenceProcessor: ConsequenceProcessor;
  private audioManager: DialogueAudioManager;
  private visualEffects: DialogueVisualEffects;
  
  constructor() {
    this.dialogueHistory = [];
    this.consequenceProcessor = new ConsequenceProcessor();
    this.audioManager = new DialogueAudioManager();
    this.visualEffects = new DialogueVisualEffects();
  }
  
  public async startDialogue(dialogueId: string): Promise<DialogueNode> {
    const dialogue = await this.loadDialogue(dialogueId);
    this.currentDialogue = dialogue;
    
    // Play dialogue audio if specified
    if (dialogue.audio) {
      await this.audioManager.playDialogueAudio(dialogue.audio);
    }
    
    // Apply visual effects
    if (dialogue.visualEffects) {
      await this.visualEffects.applyEffects(dialogue.visualEffects);
    }
    
    return dialogue;
  }
  
  public async makeChoice(choiceIndex: number): Promise<DialogueResult> {
    if (!this.currentDialogue) {
      throw new Error('No active dialogue');
    }
    
    const choice = this.currentDialogue.choices[choiceIndex];
    if (!choice) {
      throw new Error('Invalid choice index');
    }
    
    // Record choice in history
    this.dialogueHistory.push({
      dialogueId: this.currentDialogue.id,
      choiceId: choice.id,
      timestamp: new Date().toISOString()
    });
    
    // Process choice consequences
    const consequences = await this.processChoiceConsequences(choice);
    
    // Load next dialogue
    const nextDialogue = await this.loadDialogue(choice.leadsToEventId);
    
    return {
      consequences,
      nextDialogue,
      choice
    };
  }
  
  private async processChoiceConsequences(choice: Choice): Promise<Consequence[]> {
    const consequences: Consequence[] = [];
    
    if (choice.consequences) {
      for (const consequence of choice.consequences) {
        const processedConsequence = await this.consequenceProcessor.process(consequence);
        consequences.push(processedConsequence);
      }
    }
    
    return consequences;
  }
  
  private async loadDialogue(dialogueId: string): Promise<DialogueNode> {
    const response = await fetch(`/api/dialogue/${dialogueId}`);
    return response.json();
  }
}

class ConsequenceProcessor {
  public async process(consequence: Consequence): Promise<Consequence> {
    switch (consequence.type) {
      case 'narrative_currency':
        return this.processNarrativeCurrency(consequence);
      case 'relationship_change':
        return this.processRelationshipChange(consequence);
      case 'story_flag':
        return this.processStoryFlag(consequence);
      case 'nemesis_creation':
        return this.processNemesisCreation(consequence);
      default:
        return consequence;
    }
  }
  
  private async processNarrativeCurrency(consequence: Consequence): Promise<Consequence> {
    // Generate appropriate display text based on currency type
    const displayText = this.generateCurrencyDisplayText(consequence.data);
    
    return {
      ...consequence,
      displayText
    };
  }
  
  private async processNemesisCreation(consequence: Consequence): Promise<Consequence> {
    // Generate nemesis data
    const nemesisData = await this.generateNemesisData(consequence.data);
    
    return {
      ...consequence,
      data: nemesisData,
      displayText: 'You haven\'t seen the last of them...'
    };
  }
  
  private generateCurrencyDisplayText(data: any): string {
    switch (data.currency) {
      case 'threat':
        return 'You\'ve gained a loose end.';
      case 'advantage':
        return 'A new opportunity has opened.';
      case 'despair':
        return 'This will have consequences...';
      case 'triumph':
        return 'A legendary moment!';
      default:
        return data.displayText || 'Something has changed.';
    }
  }
}
```

### Audio Management System

```typescript
class DialogueAudioManager {
  private audioContext: AudioContext;
  private ambientTrack: HTMLAudioElement | null;
  private dialogueTracks: Map<string, HTMLAudioElement>;
  
  constructor() {
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    this.dialogueTracks = new Map();
  }
  
  public async playDialogueAudio(audioSettings: AudioSettings): Promise<void> {
    if (audioSettings.ambient) {
      await this.playAmbientTrack(audioSettings.ambient);
    }
    
    if (audioSettings.voice) {
      await this.playVoiceTrack(audioSettings.voice);
    }
    
    if (audioSettings.music) {
      await this.playMusicTrack(audioSettings.music);
    }
  }
  
  private async playAmbientTrack(trackUrl: string): Promise<void> {
    if (this.ambientTrack) {
      this.ambientTrack.pause();
    }
    
    this.ambientTrack = new Audio(trackUrl);
    this.ambientTrack.loop = true;
    this.ambientTrack.volume = 0.3;
    
    await this.ambientTrack.play();
  }
  
  private async playVoiceTrack(trackUrl: string): Promise<void> {
    const voiceTrack = new Audio(trackUrl);
    voiceTrack.volume = 0.8;
    
    await voiceTrack.play();
    
    // Store reference for potential interruption
    this.dialogueTracks.set(trackUrl, voiceTrack);
  }
  
  public stopAllDialogue(): void {
    this.dialogueTracks.forEach(track => track.pause());
    this.dialogueTracks.clear();
  }
}
```

### Visual Effects System

```typescript
class DialogueVisualEffects {
  private scene: THREE.Scene;
  private camera: THREE.Camera;
  
  constructor(scene: THREE.Scene, camera: THREE.Camera) {
    this.scene = scene;
    this.camera = camera;
  }
  
  public async applyEffects(effects: VisualEffect[]): Promise<void> {
    for (const effect of effects) {
      switch (effect.type) {
        case 'character_emotion':
          await this.applyCharacterEmotion(effect);
          break;
        case 'environment_change':
          await this.applyEnvironmentChange(effect);
          break;
        case 'lighting_change':
          await this.applyLightingChange(effect);
          break;
        case 'particle_effect':
          await this.applyParticleEffect(effect);
          break;
      }
    }
  }
  
  private async applyCharacterEmotion(effect: VisualEffect): Promise<void> {
    const character = this.scene.getObjectByName(effect.target);
    if (!character) return;
    
    // Apply emotion-based animation
    const emotionAnimation = this.getEmotionAnimation(effect.emotion);
    await gsap.to(character.rotation, {
      ...emotionAnimation,
      duration: 1.0,
      ease: "power2.out"
    });
  }
  
  private async applyLightingChange(effect: VisualEffect): Promise<void> {
    const lights = this.scene.children.filter(child => child.type === 'Light');
    
    await gsap.to(lights, {
      intensity: effect.intensity,
      duration: 2.0,
      ease: "power2.inOut"
    });
  }
  
  private getEmotionAnimation(emotion: string): any {
    switch (emotion) {
      case 'angry':
        return { x: 0.1, y: 0.2 };
      case 'sad':
        return { x: -0.1, y: -0.1 };
      case 'surprised':
        return { x: 0, y: 0.3 };
      default:
        return { x: 0, y: 0 };
    }
  }
}
```

### React Component Structure

```typescript
const DialogueScreen: React.FC = () => {
  const dispatch = useDispatch();
  const dialogue = useSelector(selectDialogue);
  const [dialogueEngine, setDialogueEngine] = useState<DialogueEngine | null>(null);
  const [consequenceDisplay, setConsequenceDisplay] = useState<Consequence | null>(null);
  
  useEffect(() => {
    const engine = new DialogueEngine();
    setDialogueEngine(engine);
    
    // Start initial dialogue
    if (dialogue.currentDialogue) {
      engine.startDialogue(dialogue.currentDialogue.id);
    }
  }, []);
  
  const handleChoice = async (choiceIndex: number) => {
    if (!dialogueEngine) return;
    
    const result = await dialogueEngine.makeChoice(choiceIndex);
    
    // Dispatch choice action
    dispatch(makeChoice(result.choice));
    
    // Show consequences
    if (result.consequences.length > 0) {
      setConsequenceDisplay(result.consequences[0]);
    }
    
    // Load next dialogue
    dispatch(loadNextDialogue(result.nextDialogue));
  };
  
  const handleConsequenceAcknowledge = () => {
    dispatch(processConsequence(consequenceDisplay!));
    setConsequenceDisplay(null);
  };
  
  return (
    <DialogueContainer>
      {dialogue.currentDialogue && (
        <DialoguePanel 
          dialogue={dialogue.currentDialogue}
          onChoice={handleChoice}
        />
      )}
      
      {consequenceDisplay && (
        <ConsequenceDisplay 
          consequence={consequenceDisplay}
          onAcknowledge={handleConsequenceAcknowledge}
        />
      )}
      
      <StoryCardsPanel 
        storyCards={dialogue.storyCards}
      />
    </DialogueContainer>
  );
};

const DialoguePanel: React.FC<DialoguePanelProps> = ({ dialogue, onChoice }) => {
  return (
    <DialoguePanelContainer>
      <SpeakerName>{dialogue.speaker}</SpeakerName>
      
      <DialogueText>{dialogue.text}</DialogueText>
      
      <ChoiceGrid>
        {dialogue.choices.map((choice, index) => (
          <ChoiceButton
            key={choice.id}
            choice={choice}
            position={index}
            onClick={() => onChoice(index)}
          />
        ))}
      </ChoiceGrid>
    </DialoguePanelContainer>
  );
};

const ChoiceButton: React.FC<ChoiceButtonProps> = ({ choice, position, onClick }) => {
  const attitudeConfig = getAttitudeConfig(choice.attitude);
  
  return (
    <ChoiceButtonContainer
      attitude={choice.attitude}
      position={position}
      onClick={onClick}
    >
      <AttitudeIcon icon={attitudeConfig.icon} />
      <ChoiceText>{choice.text}</ChoiceText>
    </ChoiceButtonContainer>
  );
};

const ConsequenceDisplay: React.FC<ConsequenceDisplayProps> = ({ consequence, onAcknowledge }) => {
  return (
    <ConsequenceOverlay>
      <ConsequenceCard>
        <ConsequenceText>{consequence.displayText}</ConsequenceText>
        <AcknowledgeButton onClick={onAcknowledge}>
          Continue
        </AcknowledgeButton>
      </ConsequenceCard>
    </ConsequenceOverlay>
  );
};

const StoryCardsPanel: React.FC<StoryCardsPanelProps> = ({ storyCards }) => {
  return (
    <StoryCardsContainer>
      <StoryCardsTitle>Your Story</StoryCardsTitle>
      <StoryCardsGrid>
        {storyCards.map(card => (
          <StoryCard
            key={card.id}
            card={card}
          />
        ))}
      </StoryCardsGrid>
    </StoryCardsContainer>
  );
};

const StoryCard: React.FC<StoryCardProps> = ({ card }) => {
  return (
    <StoryCardContainer category={card.category}>
      <StoryCardImage src={card.imageUrl} alt={card.title} />
      <StoryCardContent>
        <StoryCardTitle>{card.title}</StoryCardTitle>
        <StoryCardDescription>{card.description}</StoryCardDescription>
        <StoryCardDate>{formatDate(card.unlockedAt)}</StoryCardDate>
      </StoryCardContent>
    </StoryCardContainer>
  );
};
```

### Styled Components

```typescript
const DialoguePanelContainer = styled.div`
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  padding: 2rem;
  color: white;
  font-family: 'Star Wars', sans-serif;
`;

const ChoiceGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
`;

const ChoiceButtonContainer = styled.button<{ attitude: string; position: number }>`
  background: ${props => getAttitudeColor(props.attitude)};
  border: 2px solid ${props => getAttitudeBorderColor(props.attitude)};
  border-radius: 8px;
  padding: 1rem;
  color: white;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
  
  grid-area: ${props => getGridArea(props.position)};
`;

const ConsequenceOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ConsequenceCard = styled.div`
  background: linear-gradient(135deg, #2c3e50, #34495e);
  border: 2px solid #3498db;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  color: white;
  max-width: 400px;
  animation: slideIn 0.3s ease;
`;

const StoryCardsContainer = styled.div`
  position: fixed;
  top: 2rem;
  right: 2rem;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 12px;
  padding: 1rem;
  max-width: 300px;
`;

const StoryCardContainer = styled.div<{ category: string }>`
  background: ${props => getCategoryColor(props.category)};
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1rem;
  transition: transform 0.2s ease;
  
  &:hover {
    transform: scale(1.05);
  }
`;

// Utility functions
const getAttitudeConfig = (attitude: string) => {
  const configs = {
    compassionate: { icon: '❤️', color: '#3498db' },
    domineering: { icon: '⚔️', color: '#e74c3c' },
    inquisitive: { icon: '❓', color: '#f39c12' },
    pragmatic: { icon: '⚙️', color: '#95a5a6' }
  };
  return configs[attitude as keyof typeof configs];
};

const getGridArea = (position: number) => {
  const areas = ['1 / 1 / 2 / 2', '1 / 2 / 2 / 3', '2 / 1 / 3 / 2', '2 / 2 / 3 / 3'];
  return areas[position];
};

const getCategoryColor = (category: string) => {
  const colors = {
    nemesis: 'linear-gradient(135deg, #c0392b, #e74c3c)',
    alliance: 'linear-gradient(135deg, #27ae60, #2ecc71)',
    mystery: 'linear-gradient(135deg, #8e44ad, #9b59b6)',
    achievement: 'linear-gradient(135deg, #f39c12, #f1c40f)'
  };
  return colors[category as keyof typeof colors];
};
```

## Animation System

### Dialogue Animations

```typescript
class DialogueAnimations {
  public static async revealDialogue(dialogueElement: HTMLElement): Promise<void> {
    await gsap.fromTo(dialogueElement,
      { opacity: 0, y: 50 },
      { opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }
    );
  }
  
  public static async revealChoices(choiceElements: HTMLElement[]): Promise<void> {
    const timeline = gsap.timeline();
    
    choiceElements.forEach((element, index) => {
      timeline.fromTo(element,
        { opacity: 0, scale: 0.8 },
        { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.7)" },
        index * 0.1
      );
    });
    
    await timeline;
  }
  
  public static async showConsequence(consequenceElement: HTMLElement): Promise<void> {
    await gsap.fromTo(consequenceElement,
      { opacity: 0, scale: 0.5, rotation: -10 },
      { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: "back.out(1.7)" }
    );
  }
  
  public static async flipStoryCard(cardElement: HTMLElement): Promise<void> {
    await gsap.to(cardElement, {
      rotationY: 180,
      duration: 0.6,
      ease: "power2.inOut"
    });
  }
}
```

## API Integration

### Dialogue API Service

```typescript
class DialogueAPIService {
  private baseURL: string;
  
  constructor() {
    this.baseURL = '/api/dialogue';
  }
  
  async getDialogue(dialogueId: string): Promise<DialogueNode> {
    const response = await fetch(`${this.baseURL}/${dialogueId}`);
    return response.json();
  }
  
  async submitChoice(choiceData: ChoiceSubmission): Promise<DialogueResult> {
    const response = await fetch(`${this.baseURL}/choice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(choiceData)
    });
    return response.json();
  }
  
  async getStoryCards(characterId: string): Promise<StoryCard[]> {
    const response = await fetch(`${this.baseURL}/story-cards/${characterId}`);
    return response.json();
  }
  
  async updateRelationship(relationshipData: RelationshipUpdate): Promise<void> {
    await fetch(`${this.baseURL}/relationship`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(relationshipData)
    });
  }
}

// Redux Thunks
export const loadDialogueAsync = createAsyncThunk(
  'dialogue/loadDialogue',
  async (dialogueId: string) => {
    const api = new DialogueAPIService();
    return await api.getDialogue(dialogueId);
  }
);

export const submitChoiceAsync = createAsyncThunk(
  'dialogue/submitChoice',
  async (choiceData: ChoiceSubmission) => {
    const api = new DialogueAPIService();
    return await api.submitChoice(choiceData);
  }
);
```

## Implementation Phases

### Phase 1: Core Dialogue System (Weeks 1-2)
- Basic dialogue engine
- 4-choice system implementation
- Standardized attitude system

### Phase 2: Consequence System (Weeks 3-4)
- Consequence processing
- Narrative currency integration
- Story card system

### Phase 3: Visual and Audio (Weeks 5-6)
- UI implementation
- Audio integration
- Visual effects

### Phase 4: Polish and Integration (Weeks 7-8)
- Animation refinement
- Performance optimization
- Full integration testing

## Success Metrics

- **User Engagement**: Time spent in dialogue vs. traditional systems
- **Choice Diversity**: Distribution of attitude choices
- **Narrative Impact**: User feedback on consequence system
- **Performance**: Smooth dialogue transitions
- **Accessibility**: Full keyboard navigation support

## Future Enhancements

- **Voice Acting**: Professional voice acting for all dialogue
- **Dynamic Dialogue**: LLM-generated contextual responses
- **Multiplayer Dialogue**: Shared dialogue experiences
- **Mod Support**: User-created dialogue content
- **Analytics**: Detailed choice and consequence tracking
