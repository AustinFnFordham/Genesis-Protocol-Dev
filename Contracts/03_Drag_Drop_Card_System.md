# Drag & Drop Card System Implementation Plan

## Overview
This document outlines the implementation of a sophisticated drag and drop card system for managing skills, powers, tech powers, and other character elements with visual feedback, animations, and intelligent drop zones.

## Card System Architecture

### Card Types & Visual Design
```typescript
interface CardConfig {
  type: 'skill' | 'power' | 'tech-power' | 'feat' | 'equipment' | 'force-power';
  rarity: 'common' | 'uncommon' | 'rare' | 'legendary';
  size: 'small' | 'medium' | 'large';
  visualStyle: {
    borderColor: string;
    backgroundColor: string;
    glowColor: string;
    icon: string;
    pattern: string;
  };
}

const CARD_TYPES = {
  skill: {
    rarity: 'common',
    size: 'medium',
    visualStyle: {
      borderColor: '#50E3C2',
      backgroundColor: '#1A4A3A',
      glowColor: '#50E3C2',
      icon: 'book',
      pattern: 'skill-pattern',
    },
  },
  
  power: {
    rarity: 'uncommon',
    size: 'large',
    visualStyle: {
      borderColor: '#F5A623',
      backgroundColor: '#8B4513',
      glowColor: '#F5A623',
      icon: 'lightning',
      pattern: 'power-pattern',
    },
  },
  
  'force-power': {
    rarity: 'rare',
    size: 'large',
    visualStyle: {
      borderColor: '#BD10E0',
      backgroundColor: '#4A0A5F',
      glowColor: '#BD10E0',
      icon: 'force',
      pattern: 'force-pattern',
    },
  },
  
  'tech-power': {
    rarity: 'uncommon',
    size: 'medium',
    visualStyle: {
      borderColor: '#3498DB',
      backgroundColor: '#1A3A5F',
      glowColor: '#3498DB',
      icon: 'gear',
      pattern: 'tech-pattern',
    },
  },
};
```

### Card Component Structure
```typescript
interface CardProps {
  id: string;
  type: CardType;
  data: CardData;
  isDraggable: boolean;
  isSelected: boolean;
  onDragStart: (cardId: string) => void;
  onDragEnd: () => void;
  onClick: (cardId: string) => void;
}

const Card: React.FC<CardProps> = ({
  id,
  type,
  data,
  isDraggable,
  isSelected,
  onDragStart,
  onDragEnd,
  onClick,
}) => {
  const config = CARD_TYPES[type];
  const [isDragging, setIsDragging] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  
  const cardStyle = {
    ...config.visualStyle,
    transform: isDragging ? 'scale(1.05) rotate(5deg)' : 'scale(1)',
    boxShadow: isSelected 
      ? `0 0 20px ${config.visualStyle.glowColor}` 
      : isHovered 
        ? `0 5px 15px rgba(0,0,0,0.3)` 
        : '0 2px 8px rgba(0,0,0,0.2)',
    opacity: isDragging ? 0.8 : 1,
  };
  
  return (
    <div
      className={`card ${type} ${isDraggable ? 'draggable' : ''} ${isSelected ? 'selected' : ''}`}
      style={cardStyle}
      draggable={isDraggable}
      onDragStart={(e) => {
        setIsDragging(true);
        onDragStart(id);
        e.dataTransfer.setData('application/json', JSON.stringify({ id, type, data }));
        e.dataTransfer.effectAllowed = 'move';
      }}
      onDragEnd={() => {
        setIsDragging(false);
        onDragEnd();
      }}
      onClick={() => onClick(id)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="card-header">
        <div className="card-icon">{config.visualStyle.icon}</div>
        <div className="card-title">{data.name}</div>
        <div className="card-rarity">{config.rarity}</div>
      </div>
      
      <div className="card-content">
        <div className="card-description">{data.description}</div>
        {data.level && <div className="card-level">Level {data.level}</div>}
        {data.cost && <div className="card-cost">{data.cost}</div>}
      </div>
      
      <div className="card-footer">
        {data.tags && (
          <div className="card-tags">
            {data.tags.map(tag => (
              <span key={tag} className="card-tag">{tag}</span>
            ))}
          </div>
        )}
      </div>
      
      {isDragging && <div className="card-drag-ghost" />}
    </div>
  );
};
```

## Drag & Drop System

### Drag State Management
```typescript
interface DragState {
  isDragging: boolean;
  draggedCard: {
    id: string;
    type: CardType;
    data: CardData;
  } | null;
  dragSource: {
    containerId: string;
    position: number;
  } | null;
  dropTargets: DropTarget[];
  dragPreview: {
    x: number;
    y: number;
    rotation: number;
  };
}

const useDragDrop = () => {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    draggedCard: null,
    dragSource: null,
    dropTargets: [],
    dragPreview: { x: 0, y: 0, rotation: 0 },
  });
  
  const startDrag = (cardId: string, type: CardType, data: CardData, source: string, position: number) => {
    setDragState(prev => ({
      ...prev,
      isDragging: true,
      draggedCard: { id: cardId, type, data },
      dragSource: { containerId: source, position },
    }));
  };
  
  const updateDragPreview = (x: number, y: number) => {
    setDragState(prev => ({
      ...prev,
      dragPreview: { x, y, rotation: Math.sin(Date.now() * 0.01) * 2 },
    }));
  };
  
  const endDrag = () => {
    setDragState(prev => ({
      ...prev,
      isDragging: false,
      draggedCard: null,
      dragSource: null,
      dropTargets: [],
    }));
  };
  
  return { dragState, startDrag, updateDragPreview, endDrag };
};
```

### Drop Zone System
```typescript
interface DropZone {
  id: string;
  type: CardType[];
  position: { x: number; y: number; width: number; height: number };
  isActive: boolean;
  isValidTarget: boolean;
  visualFeedback: 'none' | 'valid' | 'invalid' | 'highlight';
}

const DropZone: React.FC<DropZoneProps> = ({
  id,
  acceptedTypes,
  children,
  onDrop,
  onDragOver,
  onDragLeave,
}) => {
  const { dragState } = useDragDrop();
  const [isDragOver, setIsDragOver] = useState(false);
  
  const isValidTarget = dragState.draggedCard && acceptedTypes.includes(dragState.draggedCard.type);
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
    onDragOver?.(e);
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const cardData = JSON.parse(e.dataTransfer.getData('application/json'));
    if (isValidTarget) {
      onDrop(cardData);
    }
  };
  
  const dropZoneStyle = {
    border: isDragOver && isValidTarget ? `2px dashed ${CARD_TYPES[dragState.draggedCard?.type || 'skill'].visualStyle.glowColor}` : '2px dashed transparent',
    backgroundColor: isDragOver && isValidTarget ? 'rgba(74, 144, 226, 0.1)' : 'transparent',
    transform: isDragOver && isValidTarget ? 'scale(1.02)' : 'scale(1)',
  };
  
  return (
    <div
      className={`drop-zone ${isDragOver && isValidTarget ? 'valid-target' : ''}`}
      style={dropZoneStyle}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragLeave={() => setIsDragOver(false)}
    >
      {children}
    </div>
  );
};
```

## Power Scaling System

### Power Level Visualization
```typescript
interface PowerScalingProps {
  power: Power;
  currentLevel: number;
  maxLevel: number;
  onLevelChange: (level: number) => void;
}

const PowerScalingCard: React.FC<PowerScalingProps> = ({
  power,
  currentLevel,
  maxLevel,
  onLevelChange,
}) => {
  const [isScaling, setIsScaling] = useState(false);
  
  const scalingEffects = power.scaling_effects?.[currentLevel] || [];
  const nextLevelEffects = power.scaling_effects?.[currentLevel + 1] || [];
  
  const handleLevelIncrease = () => {
    if (currentLevel < maxLevel) {
      setIsScaling(true);
      
      // Animate power card scaling up
      gsap.timeline()
        .to('.power-card', {
          scale: 1.1,
          duration: 0.2,
          ease: 'power2.out',
        })
        .to('.power-card', {
          scale: 1,
          duration: 0.2,
          ease: 'power2.in',
          onComplete: () => {
            setIsScaling(false);
            onLevelChange(currentLevel + 1);
          },
        });
    }
  };
  
  return (
    <div className={`power-scaling-card ${isScaling ? 'scaling' : ''}`}>
      <div className="power-header">
        <h3>{power.name}</h3>
        <div className="power-level-indicator">
          <span className="current-level">{currentLevel}</span>
          <span className="level-separator">/</span>
          <span className="max-level">{maxLevel}</span>
        </div>
      </div>
      
      <div className="power-effects">
        <div className="current-effects">
          <h4>Current Effects (Level {currentLevel})</h4>
          {scalingEffects.map((effect, index) => (
            <div key={index} className="effect-item">
              {effect.description}
            </div>
          ))}
        </div>
        
        {currentLevel < maxLevel && (
          <div className="next-level-preview">
            <h4>Next Level Preview</h4>
            {nextLevelEffects.map((effect, index) => (
              <div key={index} className="effect-item preview">
                {effect.description}
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="power-controls">
        <button
          className="level-up-btn"
          onClick={handleLevelIncrease}
          disabled={currentLevel >= maxLevel}
        >
          Increase Level
        </button>
        
        <div className="level-slider">
          <input
            type="range"
            min="1"
            max={maxLevel}
            value={currentLevel}
            onChange={(e) => onLevelChange(parseInt(e.target.value))}
          />
        </div>
      </div>
    </div>
  );
};
```

## Container Management

### Card Container System
```typescript
interface CardContainerProps {
  id: string;
  title: string;
  acceptedTypes: CardType[];
  cards: CardData[];
  maxCards?: number;
  onCardAdd: (card: CardData) => void;
  onCardRemove: (cardId: string) => void;
  onCardReorder: (fromIndex: number, toIndex: number) => void;
}

const CardContainer: React.FC<CardContainerProps> = ({
  id,
  title,
  acceptedTypes,
  cards,
  maxCards,
  onCardAdd,
  onCardRemove,
  onCardReorder,
}) => {
  const { dragState } = useDragDrop();
  const [isDragOver, setIsDragOver] = useState(false);
  
  const handleDrop = (cardData: any) => {
    if (maxCards && cards.length >= maxCards) {
      // Show error: container full
      return;
    }
    
    onCardAdd(cardData);
  };
  
  const handleCardRemove = (cardId: string) => {
    onCardRemove(cardId);
  };
  
  const handleCardReorder = (fromIndex: number, toIndex: number) => {
    onCardReorder(fromIndex, toIndex);
  };
  
  return (
    <DropZone
      id={id}
      acceptedTypes={acceptedTypes}
      onDrop={handleDrop}
    >
      <div className="card-container">
        <div className="container-header">
          <h3>{title}</h3>
          <span className="card-count">
            {cards.length}{maxCards ? `/${maxCards}` : ''}
          </span>
        </div>
        
        <div className="cards-grid">
          {cards.map((card, index) => (
            <Card
              key={card.id}
              id={card.id}
              type={card.type}
              data={card}
              isDraggable={true}
              isSelected={false}
              onDragStart={(cardId) => {
                // Handle drag start
              }}
              onDragEnd={() => {
                // Handle drag end
              }}
              onClick={(cardId) => {
                // Handle card click
              }}
            />
          ))}
        </div>
        
        {maxCards && cards.length >= maxCards && (
          <div className="container-full-indicator">
            Container Full
          </div>
        )}
      </div>
    </DropZone>
  );
};
```

## Animation System

### Drag Animations
```typescript
const useDragAnimations = () => {
  const animateDragStart = (cardElement: HTMLElement) => {
    gsap.timeline()
      .to(cardElement, {
        scale: 1.05,
        rotation: 5,
        duration: 0.2,
        ease: 'power2.out',
      })
      .to(cardElement, {
        boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
        duration: 0.2,
        ease: 'power2.out',
      });
  };
  
  const animateDragEnd = (cardElement: HTMLElement) => {
    gsap.timeline()
      .to(cardElement, {
        scale: 1,
        rotation: 0,
        duration: 0.3,
        ease: 'power2.out',
      })
      .to(cardElement, {
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        duration: 0.3,
        ease: 'power2.out',
      });
  };
  
  const animateCardDrop = (cardElement: HTMLElement, targetElement: HTMLElement) => {
    const targetRect = targetElement.getBoundingClientRect();
    const cardRect = cardElement.getBoundingClientRect();
    
    gsap.timeline()
      .to(cardElement, {
        x: targetRect.left - cardRect.left,
        y: targetRect.top - cardRect.top,
        scale: 0.8,
        duration: 0.4,
        ease: 'power2.inOut',
      })
      .to(targetElement, {
        scale: 1.1,
        duration: 0.2,
        ease: 'power2.out',
      })
      .to(targetElement, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.in',
      });
  };
  
  return { animateDragStart, animateDragEnd, animateCardDrop };
};
```

## Integration with Character System

### Character Sheet Integration
```typescript
const CharacterSheet: React.FC = () => {
  const { character } = useSelector(selectCharacter);
  const dispatch = useDispatch();
  
  const handlePowerAdd = (power: Power) => {
    dispatch(characterActions.addPower({ powerId: power.id }));
  };
  
  const handleSkillAdd = (skill: Skill) => {
    dispatch(characterActions.addSkill({ skillId: skill.id }));
  };
  
  return (
    <div className="character-sheet">
      <div className="character-header">
        <CharacterPortrait character={character} />
        <CharacterStats stats={character.stats} />
      </div>
      
      <div className="character-content">
        <div className="skills-section">
          <CardContainer
            id="skills"
            title="Skills"
            acceptedTypes={['skill']}
            cards={character.skills}
            onCardAdd={handleSkillAdd}
            onCardRemove={(skillId) => dispatch(characterActions.removeSkill({ skillId }))}
            onCardReorder={(from, to) => dispatch(characterActions.reorderSkills({ from, to }))}
          />
        </div>
        
        <div className="powers-section">
          <CardContainer
            id="powers"
            title="Powers"
            acceptedTypes={['power', 'force-power', 'tech-power']}
            cards={character.powers}
            maxCards={character.maxPowers}
            onCardAdd={handlePowerAdd}
            onCardRemove={(powerId) => dispatch(characterActions.removePower({ powerId }))}
            onCardReorder={(from, to) => dispatch(characterActions.reorderPowers({ from, to }))}
          />
        </div>
      </div>
    </div>
  );
};
```

This drag and drop card system provides a rich, interactive experience for managing character abilities while maintaining visual consistency and providing clear feedback to users.
