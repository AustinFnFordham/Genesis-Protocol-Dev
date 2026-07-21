# Sub-Tree Choice System Implementation Plan

## Overview
The Sub-Tree Choice System solves the UX challenge of choice node clutter by creating dedicated sub-tree screens for power selection. When a player selects a choice node on the main progression tree, they transition to a specialized screen where they can make their selection, followed by a satisfying animation that adds the chosen power to their action deck.

## Key Features
- **Main Tree Cleanliness**: Keeps the main progression tree focused and uncluttered
- **Dedicated Choice Screens**: Beautiful, themed sub-tree environments for each choice type
- **Cinematic Animations**: Satisfying visual feedback when powers are added to the deck
- **Deck Integration**: Seamless integration with the drag-and-drop card system
- **Themed Environments**: Different visual themes for Force powers, Tech powers, and other choices

## State Management Architecture

### Redux State Structure
```typescript
interface SubTreeState {
  isActive: boolean;
  currentNode: ChoiceNode | null;
  availableChoices: Choice[];
  selectedChoice: Choice | null;
  animationState: 'idle' | 'selecting' | 'confirming' | 'completing';
  environment: SubTreeEnvironment;
}

interface ChoiceNode {
  id: string;
  type: 'force_power' | 'tech_power' | 'feat' | 'skill';
  title: string;
  description: string;
  requirements: Requirement[];
  choices: Choice[];
}

interface Choice {
  id: string;
  name: string;
  description: string;
  icon: string;
  type: 'force_power' | 'tech_power' | 'feat' | 'skill';
  rarity: 'common' | 'uncommon' | 'rare' | 'legendary';
  visualEffects: VisualEffect[];
}

interface SubTreeEnvironment {
  type: 'force_vortex' | 'tech_lab' | 'training_ground' | 'meditation_chamber';
  background: string;
  particleEffects: ParticleEffect[];
  ambientAudio: string;
  lighting: LightingConfig;
}
```

### Redux Actions
```typescript
const subTreeSlice = createSlice({
  name: 'subTree',
  initialState,
  reducers: {
    openSubTree: (state, action: PayloadAction<ChoiceNode>) => {
      state.isActive = true;
      state.currentNode = action.payload;
      state.availableChoices = action.payload.choices;
      state.animationState = 'idle';
      state.environment = createEnvironmentForNode(action.payload);
    },
    selectChoice: (state, action: PayloadAction<string>) => {
      state.selectedChoice = state.availableChoices.find(
        choice => choice.id === action.payload
      ) || null;
      state.animationState = 'selecting';
    },
    confirmChoice: (state) => {
      state.animationState = 'confirming';
    },
    completeChoice: (state) => {
      state.animationState = 'completing';
    },
    closeSubTree: (state) => {
      state.isActive = false;
      state.currentNode = null;
      state.selectedChoice = null;
      state.animationState = 'idle';
    }
  }
});

export const {
  openSubTree,
  selectChoice,
  confirmChoice,
  completeChoice,
  closeSubTree
} = subTreeSlice.actions;
```

### Async Actions
```typescript
export const processChoiceAsync = createAsyncThunk(
  'subTree/processChoice',
  async (choiceId: string, { dispatch, getState }) => {
    const state = getState() as RootState;
    const choice = state.subTree.selectedChoice;
    
    if (!choice) throw new Error('No choice selected');
    
    // Add to character's abilities
    await dispatch(addAbilityToCharacterAsync(choice));
    
    // Add to action deck
    await dispatch(addCardToDeckAsync(choice));
    
    // Update progression tree
    await dispatch(unlockNodeAsync(state.subTree.currentNode!.id));
    
    return choice;
  }
);
```

## Component Architecture

### Main Sub-Tree Component
```typescript
const SubTreeScreen: React.FC = () => {
  const dispatch = useDispatch();
  const { isActive, currentNode, availableChoices, selectedChoice, animationState, environment } = useSelector(selectSubTreeState);
  
  const handleChoiceSelect = (choiceId: string) => {
    dispatch(selectChoice(choiceId));
  };
  
  const handleConfirm = () => {
    if (selectedChoice) {
      dispatch(processChoiceAsync(selectedChoice.id));
    }
  };
  
  if (!isActive) return null;
  
  return (
    <SubTreeContainer>
      <SubTreeBackground environment={environment} />
      <SubTreeContent>
        <ChoiceHeader node={currentNode} />
        <ChoiceGrid>
          {availableChoices.map(choice => (
            <ChoiceCard
              key={choice.id}
              choice={choice}
              isSelected={selectedChoice?.id === choice.id}
              onSelect={handleChoiceSelect}
            />
          ))}
        </ChoiceGrid>
        <ChoiceActions
          selectedChoice={selectedChoice}
          onConfirm={handleConfirm}
          onCancel={() => dispatch(closeSubTree())}
        />
      </SubTreeContent>
      <SubTreeAnimations state={animationState} choice={selectedChoice} />
    </SubTreeContainer>
  );
};
```

### Environment-Specific Components
```typescript
const ForceVortexEnvironment: React.FC<{ environment: SubTreeEnvironment }> = ({ environment }) => {
  const sceneRef = useRef<THREE.Scene>();
  const rendererRef = useRef<THREE.WebGLRenderer>();
  
  useEffect(() => {
    if (!sceneRef.current) return;
    
    // Create swirling vortex effect
    const vortexGeometry = new THREE.TorusGeometry(10, 2, 16, 100);
    const vortexMaterial = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        color: { value: new THREE.Color(0x0066ff) }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 color;
        varying vec2 vUv;
        
        void main() {
          float angle = atan(vUv.y - 0.5, vUv.x - 0.5);
          float radius = length(vUv - 0.5);
          float swirl = sin(angle * 8.0 + time * 2.0) * 0.5 + 0.5;
          gl_FragColor = vec4(color * swirl, 0.8);
        }
      `
    });
    
    const vortex = new THREE.Mesh(vortexGeometry, vortexMaterial);
    sceneRef.current.add(vortex);
    
    // Animation loop
    const animate = () => {
      vortexMaterial.uniforms.time.value += 0.01;
      rendererRef.current?.render(sceneRef.current!, camera);
      requestAnimationFrame(animate);
    };
    animate();
  }, [environment]);
  
  return <SubTreeViewport ref={sceneRef} />;
};

const TechLabEnvironment: React.FC<{ environment: SubTreeEnvironment }> = ({ environment }) => {
  return (
    <TechLabContainer>
      <HolographicProjector />
      <DataStreams />
      <CircuitPatterns />
    </TechLabContainer>
  );
};
```

### Choice Card Component
```typescript
const ChoiceCard: React.FC<ChoiceCardProps> = ({ choice, isSelected, onSelect }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  
  const handleClick = () => {
    onSelect(choice.id);
  };
  
  const handleHover = () => {
    if (cardRef.current) {
      gsap.to(cardRef.current, {
        scale: 1.05,
        duration: 0.2,
        ease: 'power2.out'
      });
    }
  };
  
  const handleUnhover = () => {
    if (cardRef.current) {
      gsap.to(cardRef.current, {
        scale: 1.0,
        duration: 0.2,
        ease: 'power2.out'
      });
    }
  };
  
  return (
    <ChoiceCardContainer
      ref={cardRef}
      isSelected={isSelected}
      rarity={choice.rarity}
      onClick={handleClick}
      onMouseEnter={handleHover}
      onMouseLeave={handleUnhover}
    >
      <ChoiceIcon src={choice.icon} alt={choice.name} />
      <ChoiceName>{choice.name}</ChoiceName>
      <ChoiceDescription>{choice.description}</ChoiceDescription>
      <RarityIndicator rarity={choice.rarity} />
      {isSelected && <SelectionGlow />}
    </ChoiceCardContainer>
  );
};
```

## Animation System

### Sub-Tree Animations
```typescript
class SubTreeAnimationManager {
  private static instance: SubTreeAnimationManager;
  
  static getInstance(): SubTreeAnimationManager {
    if (!SubTreeAnimationManager.instance) {
      SubTreeAnimationManager.instance = new SubTreeAnimationManager();
    }
    return SubTreeAnimationManager.instance;
  }
  
  playChoiceSelection(choiceCard: HTMLElement): void {
    gsap.timeline()
      .to(choiceCard, {
        scale: 1.1,
        duration: 0.3,
        ease: 'back.out(1.7)'
      })
      .to(choiceCard, {
        scale: 1.0,
        duration: 0.2,
        ease: 'power2.out'
      });
  }
  
  playChoiceConfirmation(choice: Choice): void {
    const timeline = gsap.timeline();
    
    // Create floating card effect
    const floatingCard = document.createElement('div');
    floatingCard.className = 'floating-choice-card';
    floatingCard.innerHTML = `
      <img src="${choice.icon}" alt="${choice.name}" />
      <span>${choice.name}</span>
    `;
    document.body.appendChild(floatingCard);
    
    // Animate card flying to action bar
    timeline
      .fromTo(floatingCard, {
        scale: 0,
        opacity: 0
      }, {
        scale: 1,
        opacity: 1,
        duration: 0.5,
        ease: 'back.out(1.7)'
      })
      .to(floatingCard, {
        x: '100vw',
        y: '-50vh',
        scale: 0.5,
        duration: 1.5,
        ease: 'power2.inOut'
      })
      .to(floatingCard, {
        opacity: 0,
        duration: 0.3
      }, '-=0.3')
      .call(() => {
        document.body.removeChild(floatingCard);
      });
  }
  
  playEnvironmentTransition(fromEnv: string, toEnv: string): void {
    const timeline = gsap.timeline();
    
    // Fade out current environment
    timeline.to('.sub-tree-background', {
      opacity: 0,
      duration: 0.5,
      ease: 'power2.inOut'
    })
    // Fade in new environment
    .to('.sub-tree-background', {
      opacity: 1,
      duration: 0.5,
      ease: 'power2.inOut'
    });
  }
}
```

## Integration with Existing Systems

### Progression Tree Integration
```typescript
const ProgressionTreeNode: React.FC<TreeNodeProps> = ({ node, onNodeClick }) => {
  const dispatch = useDispatch();
  
  const handleNodeClick = () => {
    if (node.type === 'choice') {
      // Open sub-tree instead of directly unlocking
      dispatch(openSubTree(node));
    } else {
      onNodeClick(node.id);
    }
  };
  
  return (
    <TreeNodeContainer onClick={handleNodeClick}>
      <NodeIcon type={node.type} />
      <NodeLabel>{node.title}</NodeLabel>
      {node.type === 'choice' && <ChoiceIndicator />}
    </TreeNodeContainer>
  );
};
```

### Action Deck Integration
```typescript
export const addCardToDeckAsync = createAsyncThunk(
  'actionDeck/addCard',
  async (choice: Choice, { dispatch }) => {
    // Create card from choice
    const card: ActionCard = {
      id: choice.id,
      name: choice.name,
      type: choice.type,
      icon: choice.icon,
      description: choice.description,
      rarity: choice.rarity,
      isNew: true
    };
    
    // Add to deck
    await dispatch(addCard(card));
    
    // Trigger new card animation
    dispatch(highlightNewCard(card.id));
    
    return card;
  }
);
```

## API Integration

### Sub-Tree API Service
```typescript
class SubTreeAPIService {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  async getChoiceNode(nodeId: string): Promise<ChoiceNode> {
    const response = await fetch(`${this.baseUrl}/choice-nodes/${nodeId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch choice node');
    }
    return response.json();
  }
  
  async getAvailableChoices(nodeId: string): Promise<Choice[]> {
    const response = await fetch(`${this.baseUrl}/choice-nodes/${nodeId}/choices`);
    if (!response.ok) {
      throw new Error('Failed to fetch available choices');
    }
    return response.json();
  }
  
  async confirmChoice(nodeId: string, choiceId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/choice-nodes/${nodeId}/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ choiceId })
    });
    
    if (!response.ok) {
      throw new Error('Failed to confirm choice');
    }
  }
}

export const subTreeAPIService = new SubTreeAPIService(process.env.REACT_APP_API_URL!);
```

## Styled Components

```typescript
const SubTreeContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
`;

const SubTreeBackground = styled.div<{ environment: SubTreeEnvironment }>`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: ${props => getEnvironmentBackground(props.environment)};
  opacity: 0.8;
`;

const SubTreeContent = styled.div`
  position: relative;
  z-index: 1;
  max-width: 1200px;
  max-height: 800px;
  background: rgba(0, 0, 0, 0.9);
  border-radius: 12px;
  padding: 2rem;
  border: 2px solid ${props => props.theme.colors.primary};
`;

const ChoiceGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin: 2rem 0;
`;

const ChoiceCardContainer = styled.div<{ isSelected: boolean; rarity: string }>`
  background: ${props => getRarityBackground(props.rarity)};
  border: 2px solid ${props => props.isSelected ? props.theme.colors.accent : 'transparent'};
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
`;

const ChoiceIcon = styled.img`
  width: 48px;
  height: 48px;
  margin-bottom: 0.5rem;
`;

const ChoiceName = styled.h3`
  color: ${props => props.theme.colors.text};
  margin: 0.5rem 0;
  font-size: 1.1rem;
`;

const ChoiceDescription = styled.p`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 0.9rem;
  line-height: 1.4;
`;

const SelectionGlow = styled.div`
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  border-radius: 10px;
  background: linear-gradient(45deg, #00ff88, #0088ff);
  z-index: -1;
  animation: pulse 2s infinite;
  
  @keyframes pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }
`;
```

## Performance Optimizations

### Environment Caching
```typescript
class EnvironmentCache {
  private cache = new Map<string, SubTreeEnvironment>();
  
  getEnvironment(nodeType: string): SubTreeEnvironment {
    if (this.cache.has(nodeType)) {
      return this.cache.get(nodeType)!;
    }
    
    const environment = this.createEnvironment(nodeType);
    this.cache.set(nodeType, environment);
    return environment;
  }
  
  private createEnvironment(nodeType: string): SubTreeEnvironment {
    switch (nodeType) {
      case 'force_power':
        return {
          type: 'force_vortex',
          background: 'linear-gradient(45deg, #000033, #003366)',
          particleEffects: ['force_energy', 'swirling_mist'],
          ambientAudio: 'force_ambient.mp3',
          lighting: { intensity: 0.8, color: '#0066ff' }
        };
      case 'tech_power':
        return {
          type: 'tech_lab',
          background: 'linear-gradient(45deg, #1a1a1a, #333333)',
          particleEffects: ['data_streams', 'circuit_patterns'],
          ambientAudio: 'tech_ambient.mp3',
          lighting: { intensity: 0.6, color: '#00ffff' }
        };
      default:
        return {
          type: 'training_ground',
          background: 'linear-gradient(45deg, #2a2a2a, #4a4a4a)',
          particleEffects: ['dust_particles'],
          ambientAudio: 'training_ambient.mp3',
          lighting: { intensity: 0.7, color: '#ffffff' }
        };
    }
  }
}
```

## Accessibility Features

```typescript
const useSubTreeKeyboardNavigation = (choices: Choice[], onSelect: (choiceId: string) => void) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex(prev => (prev + 1) % choices.length);
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex(prev => (prev - 1 + choices.length) % choices.length);
          break;
        case 'Enter':
        case ' ':
          event.preventDefault();
          onSelect(choices[selectedIndex].id);
          break;
        case 'Escape':
          event.preventDefault();
          // Close sub-tree
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [choices, selectedIndex, onSelect]);
  
  return selectedIndex;
};
```

## Testing Strategy

### Unit Tests
```typescript
describe('SubTreeScreen', () => {
  it('should render choice cards for available choices', () => {
    const mockChoices = [
      { id: '1', name: 'Force Push', type: 'force_power' },
      { id: '2', name: 'Force Lightning', type: 'force_power' }
    ];
    
    render(<SubTreeScreen />);
    
    expect(screen.getByText('Force Push')).toBeInTheDocument();
    expect(screen.getByText('Force Lightning')).toBeInTheDocument();
  });
  
  it('should trigger choice selection when card is clicked', () => {
    const mockOnSelect = jest.fn();
    render(<ChoiceCard choice={mockChoice} onSelect={mockOnSelect} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(mockOnSelect).toHaveBeenCalledWith(mockChoice.id);
  });
});
```

### Integration Tests
```typescript
describe('SubTree Integration', () => {
  it('should add selected choice to action deck', async () => {
    const { store } = renderWithProviders(<SubTreeScreen />);
    
    // Select a choice
    fireEvent.click(screen.getByText('Force Push'));
    fireEvent.click(screen.getByText('Confirm'));
    
    // Wait for async action to complete
    await waitFor(() => {
      const state = store.getState();
      expect(state.actionDeck.cards).toContainEqual(
        expect.objectContaining({ name: 'Force Push' })
      );
    });
  });
});
```

## Success Metrics

1. **User Engagement**: Time spent in sub-tree screens vs. main progression tree
2. **Choice Completion Rate**: Percentage of choice nodes that result in completed selections
3. **Animation Satisfaction**: User feedback on choice confirmation animations
4. **Performance**: Frame rate during sub-tree transitions and animations
5. **Accessibility**: Keyboard navigation usage and screen reader compatibility

This implementation plan provides a comprehensive solution for the choice node clutter problem while maintaining the immersive, diegetic interface aesthetic established in the previous plans.
