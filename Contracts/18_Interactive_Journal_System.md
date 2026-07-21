# Interactive Journal System Implementation Plan

## Overview
The Interactive Journal System transforms the traditional text-based journal into an engaging, visual scrapbook experience. Story cards serve as interactive gateways to detailed journal entries, allowing players to explore their campaign history through beautiful, themed cards that flip and expand to reveal rich narrative content. This system makes exploring story history as engaging as playing the game itself.

## Key Features
- **Story Card Gateways**: Interactive cards that serve as entry points to journal content
- **Visual Scrapbook Design**: Beautiful, themed cards representing major story milestones
- **Flip Animations**: Satisfying card flip and expand animations
- **Themed Card Styles**: Different visual themes for different story types
- **Rich Content Display**: Detailed journal entries with images, dialogue, and consequences
- **Search and Filter**: Easy navigation through story history
- **Achievement Integration**: Visual indicators for completed story arcs
- **Shareable Moments**: Ability to share favorite story moments

## State Management Architecture

### Redux State Structure
```typescript
interface JournalState {
  storyCards: StoryCard[];
  selectedCard: StoryCard | null;
  journalEntries: JournalEntry[];
  filters: JournalFilters;
  viewMode: 'cards' | 'timeline' | 'search';
  isCardExpanded: boolean;
  animationState: 'idle' | 'flipping' | 'expanding' | 'loading';
  searchQuery: string;
  sortOrder: 'chronological' | 'thematic' | 'achievement';
}

interface StoryCard {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  storyType: 'main_quest' | 'side_quest' | 'character_arc' | 'world_event' | 'achievement';
  theme: 'jedi' | 'sith' | 'smuggler' | 'bounty_hunter' | 'imperial' | 'rebel';
  cardImage: string;
  cardBackground: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'legendary';
  unlockDate: Date;
  isCompleted: boolean;
  completionDate?: Date;
  journalEntries: string[]; // IDs of related journal entries
  achievements: string[]; // IDs of related achievements
  tags: string[];
  cardEffects: CardEffect[];
}

interface JournalEntry {
  id: string;
  storyCardId: string;
  title: string;
  content: string;
  timestamp: Date;
  location: string;
  participants: string[];
  images: JournalImage[];
  dialogue: DialogueEntry[];
  consequences: Consequence[];
  choices: PlayerChoice[];
  mood: 'triumphant' | 'somber' | 'mysterious' | 'tense' | 'joyful';
  isUnlocked: boolean;
}

interface CardEffect {
  type: 'glow' | 'particle' | 'hologram' | 'weather';
  intensity: number;
  color: string;
  animation: string;
}

interface JournalFilters {
  storyTypes: string[];
  themes: string[];
  dateRange: { start: Date; end: Date };
  participants: string[];
  locations: string[];
  completionStatus: 'all' | 'completed' | 'in_progress';
}
```

### Redux Actions
```typescript
const journalSlice = createSlice({
  name: 'journal',
  initialState,
  reducers: {
    loadStoryCards: (state, action: PayloadAction<StoryCard[]>) => {
      state.storyCards = action.payload;
    },
    selectStoryCard: (state, action: PayloadAction<string>) => {
      const card = state.storyCards.find(c => c.id === action.payload);
      state.selectedCard = card || null;
      state.isCardExpanded = false;
      state.animationState = 'idle';
    },
    expandCard: (state) => {
      state.isCardExpanded = true;
      state.animationState = 'expanding';
    },
    collapseCard: (state) => {
      state.isCardExpanded = false;
      state.animationState = 'idle';
    },
    flipCard: (state) => {
      state.animationState = 'flipping';
    },
    setViewMode: (state, action: PayloadAction<'cards' | 'timeline' | 'search'>) => {
      state.viewMode = action.payload;
    },
    updateFilters: (state, action: PayloadAction<Partial<JournalFilters>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    setSortOrder: (state, action: PayloadAction<'chronological' | 'thematic' | 'achievement'>) => {
      state.sortOrder = action.payload;
    },
    unlockStoryCard: (state, action: PayloadAction<string>) => {
      const card = state.storyCards.find(c => c.id === action.payload);
      if (card) {
        card.isUnlocked = true;
        card.unlockDate = new Date();
      }
    },
    completeStoryCard: (state, action: PayloadAction<string>) => {
      const card = state.storyCards.find(c => c.id === action.payload);
      if (card) {
        card.isCompleted = true;
        card.completionDate = new Date();
      }
    }
  }
});

export const {
  loadStoryCards,
  selectStoryCard,
  expandCard,
  collapseCard,
  flipCard,
  setViewMode,
  updateFilters,
  setSearchQuery,
  setSortOrder,
  unlockStoryCard,
  completeStoryCard
} = journalSlice.actions;
```

### Async Actions
```typescript
export const loadJournalDataAsync = createAsyncThunk(
  'journal/loadData',
  async (_, { dispatch }) => {
    // Load story cards and journal entries
    const [storyCards, journalEntries] = await Promise.all([
      journalAPIService.getStoryCards(),
      journalAPIService.getJournalEntries()
    ]);
    
    dispatch(loadStoryCards(storyCards));
    dispatch(loadJournalEntries(journalEntries));
    
    return { storyCards, journalEntries };
  }
);

export const expandStoryCardAsync = createAsyncThunk(
  'journal/expandCard',
  async (cardId: string, { dispatch, getState }) => {
    const state = getState() as RootState;
    const card = state.journal.storyCards.find(c => c.id === cardId);
    
    if (!card) throw new Error('Story card not found');
    
    // Load detailed journal entries for this card
    const journalEntries = await journalAPIService.getJournalEntriesForCard(cardId);
    
    // Update state
    dispatch(selectStoryCard(cardId));
    dispatch(expandCard());
    
    return journalEntries;
  }
);
```

## Component Architecture

### Main Journal Screen
```typescript
const JournalScreen: React.FC = () => {
  const dispatch = useDispatch();
  const { 
    storyCards, 
    selectedCard, 
    viewMode, 
    filters, 
    searchQuery, 
    sortOrder,
    isCardExpanded,
    animationState 
  } = useSelector(selectJournalState);
  
  const handleCardSelect = (cardId: string) => {
    dispatch(selectStoryCard(cardId));
  };
  
  const handleCardExpand = (cardId: string) => {
    dispatch(expandStoryCardAsync(cardId));
  };
  
  const handleViewModeChange = (mode: 'cards' | 'timeline' | 'search') => {
    dispatch(setViewMode(mode));
  };
  
  const filteredCards = useMemo(() => {
    return filterStoryCards(storyCards, filters, searchQuery, sortOrder);
  }, [storyCards, filters, searchQuery, sortOrder]);
  
  return (
    <JournalContainer>
      <JournalHeader>
        <JournalTitle>Campaign Journal</JournalTitle>
        <ViewModeSelector
          currentMode={viewMode}
          onModeChange={handleViewModeChange}
        />
        <JournalSearch
          query={searchQuery}
          onQueryChange={(query) => dispatch(setSearchQuery(query))}
        />
      </JournalHeader>
      
      <JournalContent>
        {viewMode === 'cards' && (
          <StoryCardGrid>
            {filteredCards.map(card => (
              <StoryCard
                key={card.id}
                card={card}
                isSelected={selectedCard?.id === card.id}
                onSelect={handleCardSelect}
                onExpand={handleCardExpand}
              />
            ))}
          </StoryCardGrid>
        )}
        
        {viewMode === 'timeline' && (
          <TimelineView cards={filteredCards} />
        )}
        
        {viewMode === 'search' && (
          <SearchResults cards={filteredCards} />
        )}
      </JournalContent>
      
      {selectedCard && isCardExpanded && (
        <ExpandedCardView
          card={selectedCard}
          animationState={animationState}
          onCollapse={() => dispatch(collapseCard())}
        />
      )}
    </JournalContainer>
  );
};
```

### Story Card Component
```typescript
const StoryCard: React.FC<StoryCardProps> = ({ 
  card, 
  isSelected, 
  onSelect, 
  onExpand 
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const dispatch = useDispatch();
  
  const handleClick = () => {
    onSelect(card.id);
  };
  
  const handleDoubleClick = () => {
    onExpand(card.id);
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
    <CardContainer
      ref={cardRef}
      theme={card.theme}
      rarity={card.rarity}
      isSelected={isSelected}
      isCompleted={card.isCompleted}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onMouseEnter={handleHover}
      onMouseLeave={handleUnhover}
    >
      <CardBackground background={card.cardBackground} />
      <CardImage src={card.cardImage} alt={card.title} />
      <CardContent>
        <CardTitle>{card.title}</CardTitle>
        <CardSubtitle>{card.subtitle}</CardSubtitle>
        <CardDescription>{card.description}</CardDescription>
        <CardMeta>
          <CardType>{card.storyType}</CardType>
          <CardDate>{formatDate(card.unlockDate)}</CardDate>
        </CardMeta>
      </CardContent>
      
      {card.isCompleted && <CompletionBadge />}
      {card.cardEffects.map((effect, index) => (
        <CardEffect key={index} effect={effect} />
      ))}
      
      {isSelected && <SelectionGlow />}
    </CardContainer>
  );
};
```

### Expanded Card View Component
```typescript
const ExpandedCardView: React.FC<ExpandedCardViewProps> = ({ 
  card, 
  animationState, 
  onCollapse 
}) => {
  const expandedRef = useRef<HTMLDivElement>(null);
  const { journalEntries } = useSelector(selectJournalState);
  
  useEffect(() => {
    if (!expandedRef.current) return;
    
    const timeline = gsap.timeline();
    
    switch (animationState) {
      case 'expanding':
        timeline
          .fromTo(expandedRef.current, {
            scale: 0.8,
            opacity: 0
          }, {
            scale: 1,
            opacity: 1,
            duration: 0.5,
            ease: 'back.out(1.7)'
          });
        break;
        
      case 'flipping':
        timeline
          .to(expandedRef.current, {
            rotationY: 90,
            duration: 0.3,
            ease: 'power2.inOut'
          })
          .to(expandedRef.current, {
            rotationY: 0,
            duration: 0.3,
            ease: 'power2.inOut'
          });
        break;
    }
  }, [animationState]);
  
  const cardEntries = journalEntries.filter(entry => 
    card.journalEntries.includes(entry.id)
  );
  
  return (
    <ExpandedCardContainer ref={expandedRef}>
      <ExpandedCardHeader>
        <ExpandedCardTitle>{card.title}</ExpandedCardTitle>
        <CloseButton onClick={onCollapse}>×</CloseButton>
      </ExpandedCardHeader>
      
      <ExpandedCardContent>
        <CardDetails card={card} />
        <JournalEntriesList entries={cardEntries} />
        <RelatedAchievements card={card} />
      </ExpandedCardContent>
    </ExpandedCardContainer>
  );
};
```

### Journal Entry Component
```typescript
const JournalEntry: React.FC<JournalEntryProps> = ({ entry }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const handleToggle = () => {
    setIsExpanded(!isExpanded);
  };
  
  return (
    <EntryContainer mood={entry.mood}>
      <EntryHeader>
        <EntryTitle>{entry.title}</EntryTitle>
        <EntryTimestamp>{formatTimestamp(entry.timestamp)}</EntryTimestamp>
        <EntryLocation>{entry.location}</EntryLocation>
      </EntryHeader>
      
      <EntryContent isExpanded={isExpanded}>
        <EntryText>{entry.content}</EntryText>
        
        {entry.images.length > 0 && (
          <EntryImages>
            {entry.images.map((image, index) => (
              <EntryImage key={index} src={image.url} alt={image.caption} />
            ))}
          </EntryImages>
        )}
        
        {entry.dialogue.length > 0 && (
          <EntryDialogue>
            {entry.dialogue.map((line, index) => (
              <DialogueLine key={index} line={line} />
            ))}
          </EntryDialogue>
        )}
        
        {entry.consequences.length > 0 && (
          <EntryConsequences>
            {entry.consequences.map((consequence, index) => (
              <ConsequenceItem key={index} consequence={consequence} />
            ))}
          </EntryConsequences>
        )}
      </EntryContent>
      
      <EntryFooter>
        <EntryParticipants participants={entry.participants} />
        <ExpandButton onClick={handleToggle}>
          {isExpanded ? 'Show Less' : 'Show More'}
        </ExpandButton>
      </EntryFooter>
    </EntryContainer>
  );
};
```

## Card Theme System

### Theme Factory
```typescript
class CardThemeFactory {
  static createTheme(theme: string): CardTheme {
    const themes = {
      jedi: {
        background: 'linear-gradient(135deg, #1a4a6b, #2d7da0)',
        borderColor: '#4a9eff',
        textColor: '#ffffff',
        accentColor: '#00d4ff',
        particleColor: '#4a9eff',
        effects: ['force_glow', 'wisdom_particles']
      },
      sith: {
        background: 'linear-gradient(135deg, #4a1a1a, #8b0000)',
        borderColor: '#ff4444',
        textColor: '#ffffff',
        accentColor: '#ff0000',
        particleColor: '#ff4444',
        effects: ['dark_aura', 'power_particles']
      },
      smuggler: {
        background: 'linear-gradient(135deg, #2a4a2a, #4a7a4a)',
        borderColor: '#7dce7d',
        textColor: '#ffffff',
        accentColor: '#00ff00',
        particleColor: '#7dce7d',
        effects: ['stealth_shadow', 'credits_sparkle']
      },
      bounty_hunter: {
        background: 'linear-gradient(135deg, #4a2a1a, #7a4a2a)',
        borderColor: '#ffaa44',
        textColor: '#ffffff',
        accentColor: '#ff8800',
        particleColor: '#ffaa44',
        effects: ['target_reticle', 'bounty_glow']
      },
      imperial: {
        background: 'linear-gradient(135deg, #1a1a4a, #2a2a7a)',
        borderColor: '#4444ff',
        textColor: '#ffffff',
        accentColor: '#0088ff',
        particleColor: '#4444ff',
        effects: ['order_lines', 'authority_glow']
      },
      rebel: {
        background: 'linear-gradient(135deg, #4a1a4a, #7a2a7a)',
        borderColor: '#ff44ff',
        textColor: '#ffffff',
        accentColor: '#ff0088',
        particleColor: '#ff44ff',
        effects: ['freedom_sparkles', 'hope_glow']
      }
    };
    
    return themes[theme as keyof typeof themes] || themes.jedi;
  }
  
  static getRarityStyle(rarity: string): RarityStyle {
    const rarityStyles = {
      common: {
        borderWidth: 1,
        glowIntensity: 0.3,
        particleCount: 5
      },
      uncommon: {
        borderWidth: 2,
        glowIntensity: 0.5,
        particleCount: 10
      },
      rare: {
        borderWidth: 3,
        glowIntensity: 0.7,
        particleCount: 15
      },
      legendary: {
        borderWidth: 4,
        glowIntensity: 1.0,
        particleCount: 25
      }
    };
    
    return rarityStyles[rarity as keyof typeof rarityStyles] || rarityStyles.common;
  }
}
```

## Animation System

### Card Animations
```typescript
class CardAnimationManager {
  private static instance: CardAnimationManager;
  
  static getInstance(): CardAnimationManager {
    if (!CardAnimationManager.instance) {
      CardAnimationManager.instance = new CardAnimationManager();
    }
    return CardAnimationManager.instance;
  }
  
  playCardFlip(cardElement: HTMLElement): void {
    gsap.timeline()
      .to(cardElement, {
        rotationY: 90,
        duration: 0.3,
        ease: 'power2.inOut'
      })
      .to(cardElement, {
        rotationY: 0,
        duration: 0.3,
        ease: 'power2.inOut'
      });
  }
  
  playCardExpand(cardElement: HTMLElement): void {
    gsap.timeline()
      .to(cardElement, {
        scale: 1.1,
        duration: 0.2,
        ease: 'power2.out'
      })
      .to(cardElement, {
        scale: 1.0,
        duration: 0.2,
        ease: 'power2.inOut'
      });
  }
  
  playCardUnlock(cardElement: HTMLElement): void {
    const timeline = gsap.timeline();
    
    // Create unlock particles
    const particles = Array.from({ length: 10 }, (_, i) => {
      const particle = document.createElement('div');
      particle.className = 'unlock-particle';
      particle.style.setProperty('--delay', `${i * 0.1}s`);
      particle.style.setProperty('--angle', `${i * 36}deg`);
      return particle;
    });
    
    particles.forEach(particle => {
      cardElement.appendChild(particle);
    });
    
    timeline
      .to(cardElement, {
        scale: 1.2,
        duration: 0.3,
        ease: 'back.out(1.7)'
      })
      .to(cardElement, {
        scale: 1.0,
        duration: 0.2,
        ease: 'power2.inOut'
      })
      .to('.unlock-particle', {
        scale: 0,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.out',
        stagger: 0.05
      })
      .call(() => {
        particles.forEach(particle => {
          cardElement.removeChild(particle);
        });
      });
  }
  
  playCardCompletion(cardElement: HTMLElement): void {
    gsap.timeline()
      .to(cardElement, {
        boxShadow: '0 0 30px rgba(255, 215, 0, 0.8)',
        duration: 0.5,
        ease: 'power2.out'
      })
      .to(cardElement, {
        boxShadow: '0 0 10px rgba(255, 215, 0, 0.4)',
        duration: 0.5,
        ease: 'power2.inOut'
      });
  }
}
```

## Integration with Existing Systems

### Campaign System Integration
```typescript
export const unlockStoryCardAsync = createAsyncThunk(
  'journal/unlockStoryCard',
  async (cardId: string, { dispatch, getState }) => {
    const state = getState() as RootState;
    const card = state.journal.storyCards.find(c => c.id === cardId);
    
    if (!card) throw new Error('Story card not found');
    
    // Unlock the card
    await dispatch(unlockStoryCard(cardId));
    
    // Trigger unlock animation
    const cardElement = document.querySelector(`[data-card-id="${cardId}"]`);
    if (cardElement) {
      CardAnimationManager.getInstance().playCardUnlock(cardElement as HTMLElement);
    }
    
    // Check for related achievements
    if (card.achievements.length > 0) {
      card.achievements.forEach(achievementId => {
        dispatch(checkAchievementUnlock(achievementId));
      });
    }
    
    return card;
  }
);
```

### Achievement System Integration
```typescript
export const completeStoryCardAsync = createAsyncThunk(
  'journal/completeStoryCard',
  async (cardId: string, { dispatch, getState }) => {
    const state = getState() as RootState;
    const card = state.journal.storyCards.find(c => c.id === cardId);
    
    if (!card) throw new Error('Story card not found');
    
    // Complete the card
    await dispatch(completeStoryCard(cardId));
    
    // Trigger completion animation
    const cardElement = document.querySelector(`[data-card-id="${cardId}"]`);
    if (cardElement) {
      CardAnimationManager.getInstance().playCardCompletion(cardElement as HTMLElement);
    }
    
    // Award experience or other rewards
    if (card.storyType === 'main_quest') {
      dispatch(awardExperience(1000));
    } else if (card.storyType === 'side_quest') {
      dispatch(awardExperience(500));
    }
    
    return card;
  }
);
```

## Styled Components

```typescript
const JournalContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #0a0a0a, #1a1a1a);
  color: ${props => props.theme.colors.text};
`;

const JournalHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: rgba(0, 0, 0, 0.8);
  border-bottom: 2px solid ${props => props.theme.colors.primary};
`;

const JournalTitle = styled.h1`
  color: ${props => props.theme.colors.accent};
  font-size: 2rem;
  font-weight: bold;
  margin: 0;
`;

const JournalContent = styled.div`
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
`;

const StoryCardGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  padding: 1rem;
`;

const CardContainer = styled.div<{ 
  theme: string; 
  rarity: string; 
  isSelected: boolean; 
  isCompleted: boolean; 
}>`
  position: relative;
  width: 300px;
  height: 400px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  transform-style: preserve-3d;
  
  background: ${props => CardThemeFactory.createTheme(props.theme).background};
  border: ${props => CardThemeFactory.getRarityStyle(props.rarity).borderWidth}px solid 
    ${props => CardThemeFactory.createTheme(props.theme).borderColor};
  
  ${props => props.isSelected && `
    transform: scale(1.05);
    box-shadow: 0 0 20px ${CardThemeFactory.createTheme(props.theme).accentColor};
  `}
  
  ${props => props.isCompleted && `
    &::after {
      content: '';
      position: absolute;
      top: -5px;
      right: -5px;
      width: 20px;
      height: 20px;
      background: #FFD700;
      border-radius: 50%;
      animation: completionGlow 2s infinite;
    }
  `}
  
  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  }
  
  @keyframes completionGlow {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.7; transform: scale(1.2); }
  }
`;

const CardBackground = styled.div<{ background: string }>`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: ${props => props.background};
  border-radius: inherit;
  opacity: 0.8;
`;

const CardImage = styled.img`
  position: absolute;
  top: 20px;
  left: 20px;
  right: 20px;
  height: 200px;
  object-fit: cover;
  border-radius: 8px;
`;

const CardContent = styled.div`
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  color: ${props => props.theme.colors.text};
`;

const CardTitle = styled.h3`
  font-size: 1.2rem;
  font-weight: bold;
  margin: 0 0 0.5rem 0;
  color: ${props => props.theme.colors.accent};
`;

const CardSubtitle = styled.h4`
  font-size: 1rem;
  margin: 0 0 0.5rem 0;
  opacity: 0.8;
`;

const CardDescription = styled.p`
  font-size: 0.9rem;
  line-height: 1.4;
  margin: 0 0 1rem 0;
  opacity: 0.9;
`;

const CardMeta = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  opacity: 0.7;
`;

const CompletionBadge = styled.div`
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  background: #FFD700;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
  font-weight: bold;
  font-size: 1.2rem;
`;

const ExpandedCardContainer = styled.div`
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80vw;
  max-width: 1200px;
  height: 80vh;
  background: rgba(0, 0, 0, 0.95);
  border: 2px solid ${props => props.theme.colors.primary};
  border-radius: 12px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
`;

const ExpandedCardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  border-bottom: 1px solid ${props => props.theme.colors.primary};
`;

const ExpandedCardTitle = styled.h2`
  color: ${props => props.theme.colors.accent};
  margin: 0;
  font-size: 1.5rem;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: ${props => props.theme.colors.text};
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:hover {
    color: ${props => props.theme.colors.accent};
  }
`;

const ExpandedCardContent = styled.div`
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
`;

const EntryContainer = styled.div<{ mood: string }>`
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  border-left: 4px solid ${props => getMoodColor(props.mood)};
`;

const EntryTitle = styled.h3`
  color: ${props => props.theme.colors.accent};
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
`;

const EntryTimestamp = styled.div`
  font-size: 0.8rem;
  opacity: 0.7;
  margin-bottom: 0.5rem;
`;

const EntryLocation = styled.div`
  font-size: 0.8rem;
  opacity: 0.7;
  margin-bottom: 1rem;
`;

const EntryText = styled.p`
  line-height: 1.6;
  margin: 0 0 1rem 0;
`;

const EntryImages = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  overflow-x: auto;
`;

const EntryImage = styled.img`
  width: 150px;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid ${props => props.theme.colors.primary};
`;

const EntryDialogue = styled.div`
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1rem;
`;

const DialogueLine = styled.div`
  margin-bottom: 0.5rem;
  font-style: italic;
  
  &::before {
    content: '"';
  }
  
  &::after {
    content: '"';
  }
`;

const EntryConsequences = styled.div`
  background: rgba(255, 215, 0, 0.1);
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1rem;
  border-left: 3px solid #FFD700;
`;

const ConsequenceItem = styled.div`
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: #FFD700;
`;

const EntryFooter = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
`;

const ExpandButton = styled.button`
  background: ${props => props.theme.colors.primary};
  color: ${props => props.theme.colors.text};
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  
  &:hover {
    background: ${props => props.theme.colors.accent};
  }
`;
```

## Performance Optimizations

### Card Virtualization
```typescript
class CardVirtualizationManager {
  private static instance: CardVirtualizationManager;
  private visibleCards = new Set<string>();
  private cardCache = new Map<string, HTMLElement>();
  
  static getInstance(): CardVirtualizationManager {
    if (!CardVirtualizationManager.instance) {
      CardVirtualizationManager.instance = new CardVirtualizationManager();
    }
    return CardVirtualizationManager.instance;
  }
  
  updateVisibleCards(container: HTMLElement, cards: StoryCard[]): void {
    const containerRect = container.getBoundingClientRect();
    const buffer = 100; // Buffer zone for smooth scrolling
    
    cards.forEach(card => {
      const cardElement = document.querySelector(`[data-card-id="${card.id}"]`) as HTMLElement;
      if (!cardElement) return;
      
      const cardRect = cardElement.getBoundingClientRect();
      const isVisible = (
        cardRect.top < containerRect.bottom + buffer &&
        cardRect.bottom > containerRect.top - buffer
      );
      
      if (isVisible) {
        this.visibleCards.add(card.id);
        this.loadCardContent(card);
      } else {
        this.visibleCards.delete(card.id);
        this.unloadCardContent(card);
      }
    });
  }
  
  private loadCardContent(card: StoryCard): void {
    // Load high-resolution images and effects for visible cards
    const cardElement = document.querySelector(`[data-card-id="${card.id}"]`) as HTMLElement;
    if (cardElement && !this.cardCache.has(card.id)) {
      this.cardCache.set(card.id, cardElement);
      
      // Load high-res image
      const img = cardElement.querySelector('img') as HTMLImageElement;
      if (img && img.src !== card.cardImage) {
        img.src = card.cardImage;
      }
    }
  }
  
  private unloadCardContent(card: StoryCard): void {
    // Unload high-resolution content for off-screen cards
    const cardElement = this.cardCache.get(card.id);
    if (cardElement) {
      const img = cardElement.querySelector('img') as HTMLImageElement;
      if (img) {
        img.src = card.cardImage.replace('_high', '_low'); // Use low-res version
      }
    }
  }
}
```

### Image Lazy Loading
```typescript
class ImageLazyLoader {
  private static instance: ImageLazyLoader;
  private loadedImages = new Set<string>();
  private loadingQueue: string[] = [];
  
  static getInstance(): ImageLazyLoader {
    if (!ImageLazyLoader.instance) {
      ImageLazyLoader.instance = new ImageLazyLoader();
    }
    return ImageLazyLoader.instance;
  }
  
  loadImage(imageUrl: string, priority: 'high' | 'low' = 'low'): Promise<void> {
    if (this.loadedImages.has(imageUrl)) {
      return Promise.resolve();
    }
    
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        this.loadedImages.add(imageUrl);
        resolve();
      };
      img.onerror = reject;
      img.src = imageUrl;
      
      if (priority === 'high') {
        this.loadingQueue.unshift(imageUrl);
      } else {
        this.loadingQueue.push(imageUrl);
      }
    });
  }
  
  preloadImages(imageUrls: string[]): void {
    imageUrls.forEach(url => {
      this.loadImage(url, 'low').catch(console.warn);
    });
  }
}
```

## Accessibility Features

```typescript
const useJournalAccessibility = () => {
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
  
  const announceCardUnlock = (card: StoryCard) => {
    if (isScreenReaderActive) {
      const announcement = `New story card unlocked: ${card.title}. ${card.description}`;
      // Use ARIA live region for screen reader announcement
      const liveRegion = document.getElementById('aria-live-region');
      if (liveRegion) {
        liveRegion.textContent = announcement;
      }
    }
  };
  
  const announceCardCompletion = (card: StoryCard) => {
    if (isScreenReaderActive) {
      const announcement = `Story card completed: ${card.title}`;
      const liveRegion = document.getElementById('aria-live-region');
      if (liveRegion) {
        liveRegion.textContent = announcement;
      }
    }
  };
  
  return { isScreenReaderActive, announceCardUnlock, announceCardCompletion };
};
```

## Testing Strategy

### Unit Tests
```typescript
describe('JournalScreen', () => {
  it('should render story cards in grid', () => {
    const mockCards = [
      { id: '1', title: 'The Fall of Inquisitor Karth', storyType: 'main_quest' },
      { id: '2', title: 'Smuggler\'s Run', storyType: 'side_quest' }
    ];
    
    render(<JournalScreen />);
    
    expect(screen.getByText('The Fall of Inquisitor Karth')).toBeInTheDocument();
    expect(screen.getByText('Smuggler\'s Run')).toBeInTheDocument();
  });
  
  it('should expand card when double-clicked', () => {
    const mockCard = { id: '1', title: 'Test Card' };
    const mockOnExpand = jest.fn();
    
    render(<StoryCard card={mockCard} onExpand={mockOnExpand} />);
    
    fireEvent.doubleClick(screen.getByText('Test Card'));
    
    expect(mockOnExpand).toHaveBeenCalledWith('1');
  });
});
```

### Integration Tests
```typescript
describe('Journal Integration', () => {
  it('should load journal data on mount', async () => {
    const { store } = renderWithProviders(<JournalScreen />);
    
    // Wait for async data loading
    await waitFor(() => {
      const state = store.getState();
      expect(state.journal.storyCards).toHaveLength(2);
      expect(state.journal.journalEntries).toHaveLength(5);
    });
  });
  
  it('should filter cards based on search query', async () => {
    const { store } = renderWithProviders(<JournalScreen />);
    
    // Set search query
    store.dispatch(setSearchQuery('Inquisitor'));
    
    // Wait for filtering
    await waitFor(() => {
      const state = store.getState();
      const filteredCards = filterStoryCards(
        state.journal.storyCards,
        state.journal.filters,
        state.journal.searchQuery,
        state.journal.sortOrder
      );
      expect(filteredCards).toHaveLength(1);
      expect(filteredCards[0].title).toContain('Inquisitor');
    });
  });
});
```

## Success Metrics

1. **User Engagement**: Time spent exploring journal content
2. **Story Completion**: Rate of story card unlocking and completion
3. **Navigation Efficiency**: Time to find specific story content
4. **Visual Appeal**: User feedback on card design and animations
5. **Performance**: Load times for journal content and images
6. **Accessibility**: Usage by screen reader and keyboard navigation users

This implementation plan transforms the traditional journal into an engaging, visual experience that makes exploring campaign history as enjoyable as playing the game itself, while maintaining the immersive Star Wars universe aesthetic established in the previous plans.
