# Progression Tree System Implementation Plan

## Overview
This document outlines the implementation of the visual progression tree system, including node types, class theming, multiclassing support, and interactive features.

## Visual Design System

### Node Types & Visual Language
```typescript
interface NodeVisualConfig {
  shape: 'square' | 'circle' | 'hexagon' | 'diamond';
  size: 'small' | 'medium' | 'large';
  glowColor: string;
  borderColor: string;
  fillColor: string;
  icon: string;
}

const NODE_TYPES = {
  // Core Class Features (Automatic unlocks)
  CORE_FEATURE: {
    shape: 'large-square',
    glowColor: '#4A90E2',
    borderColor: '#2E5C8A',
    fillColor: '#1A3A5F',
    icon: 'star',
  },
  
  // Optional Talents
  TALENT: {
    shape: 'circle',
    glowColor: '#F5A623',
    borderColor: '#D68910',
    fillColor: '#8B4513',
    icon: 'lightning',
  },
  
  // Major Choice Points (Subclasses)
  CHOICE_POINT: {
    shape: 'hexagon',
    glowColor: '#7ED321',
    borderColor: '#5A9E1A',
    fillColor: '#2D4A1A',
    icon: 'branch',
  },
  
  // Force Powers
  FORCE_POWER: {
    shape: 'diamond',
    glowColor: '#BD10E0',
    borderColor: '#8B0A9E',
    fillColor: '#4A0A5F',
    icon: 'force',
  },
  
  // Skill Proficiencies
  SKILL: {
    shape: 'circle',
    glowColor: '#50E3C2',
    borderColor: '#2E8B57',
    fillColor: '#1A4A3A',
    icon: 'book',
  },
};
```

### Class-Specific Theming
```typescript
interface ClassTheme {
  background: string;
  nodeConnections: string;
  ambientEffects: string[];
  colorPalette: {
    primary: string;
    secondary: string;
    accent: string;
    highlight: string;
  };
}

const CLASS_THEMES = {
  fighter: {
    background: 'linear-gradient(135deg, #2C3E50 0%, #34495E 100%)',
    nodeConnections: '#E74C3C',
    ambientEffects: ['sparks', 'metal-glow'],
    colorPalette: {
      primary: '#E74C3C',
      secondary: '#C0392B',
      accent: '#F39C12',
      highlight: '#ECF0F1',
    },
  },
  
  consular: {
    background: 'radial-gradient(circle, #2C3E50 0%, #1A252F 100%)',
    nodeConnections: '#3498DB',
    ambientEffects: ['force-wisps', 'temple-aura'],
    colorPalette: {
      primary: '#3498DB',
      secondary: '#2980B9',
      accent: '#9B59B6',
      highlight: '#ECF0F1',
    },
  },
  
  operative: {
    background: 'linear-gradient(45deg, #2C3E50 0%, #34495E 50%, #2C3E50 100%)',
    nodeConnections: '#27AE60',
    ambientEffects: ['stealth-particles', 'hologram-flicker'],
    colorPalette: {
      primary: '#27AE60',
      secondary: '#229954',
      accent: '#F39C12',
      highlight: '#ECF0F1',
    },
  },
};
```

## Component Architecture

### Main Tree Component
```typescript
interface ProgressionTreeProps {
  classId: string;
  tree: ProgressionTree;
  availableNodes: string[];
  selectedNodes: string[];
  onNodeClick: (nodeId: string) => void;
  onNodeHover: (nodeId: string) => void;
}

const ProgressionTree: React.FC<ProgressionTreeProps> = ({
  classId,
  tree,
  availableNodes,
  selectedNodes,
  onNodeClick,
  onNodeHover,
}) => {
  const theme = CLASS_THEMES[classId];
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Render tree with theme
    renderTree(ctx, tree, theme, {
      availableNodes,
      selectedNodes,
      onNodeClick,
      onNodeHover,
    });
  }, [tree, theme, availableNodes, selectedNodes]);
  
  return (
    <div className="progression-tree-container">
      <canvas
        ref={canvasRef}
        className="progression-tree-canvas"
        style={{
          background: theme.background,
        }}
      />
      <div className="tree-controls">
        <button onClick={() => zoomIn()}>Zoom In</button>
        <button onClick={() => zoomOut()}>Zoom Out</button>
        <button onClick={() => resetView()}>Reset View</button>
      </div>
    </div>
  );
};
```

### Node Component
```typescript
interface TreeNodeProps {
  node: ProgressionNode;
  isAvailable: boolean;
  isSelected: boolean;
  theme: ClassTheme;
  onClick: () => void;
  onHover: () => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  isAvailable,
  isSelected,
  theme,
  onClick,
  onHover,
}) => {
  const nodeConfig = NODE_TYPES[node.type];
  const [isHovered, setIsHovered] = useState(false);
  
  const nodeStyle = {
    ...nodeConfig,
    opacity: isAvailable ? 1 : 0.3,
    transform: isSelected ? 'scale(1.1)' : 'scale(1)',
    filter: isHovered ? 'brightness(1.2)' : 'brightness(1)',
  };
  
  return (
    <div
      className={`tree-node ${node.type} ${isAvailable ? 'available' : 'locked'} ${isSelected ? 'selected' : ''}`}
      style={nodeStyle}
      onClick={isAvailable ? onClick : undefined}
      onMouseEnter={() => {
        setIsHovered(true);
        onHover();
      }}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="node-icon">{nodeConfig.icon}</div>
      <div className="node-label">{node.name}</div>
      {isHovered && (
        <div className="node-tooltip">
          <h4>{node.name}</h4>
          <p>{node.description}</p>
          {node.prerequisites && (
            <div className="prerequisites">
              <strong>Prerequisites:</strong> {node.prerequisites}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

## Animation System

### Node Unlock Animation
```typescript
const unlockNodeAnimation = (nodeId: string, theme: ClassTheme) => {
  const node = document.querySelector(`[data-node-id="${nodeId}"]`);
  if (!node) return;
  
  // Create energy flow effect
  const energyFlow = document.createElement('div');
  energyFlow.className = 'energy-flow';
  energyFlow.style.cssText = `
    position: absolute;
    background: linear-gradient(90deg, transparent, ${theme.colorPalette.primary}, transparent);
    height: 2px;
    animation: energyFlow 1s ease-in-out;
  `;
  
  // Add glow effect
  node.style.boxShadow = `0 0 20px ${theme.colorPalette.primary}`;
  node.style.transform = 'scale(1.2)';
  
  // Animate node activation
  gsap.timeline()
    .to(node, {
      scale: 1.2,
      duration: 0.3,
      ease: 'power2.out',
    })
    .to(node, {
      scale: 1,
      duration: 0.2,
      ease: 'power2.in',
    })
    .to(node, {
      boxShadow: `0 0 10px ${theme.colorPalette.primary}`,
      duration: 0.5,
      ease: 'power2.out',
    });
};
```

### Level Up Sequence
```typescript
const levelUpAnimation = (classId: string, newNodes: string[]) => {
  const theme = CLASS_THEMES[classId];
  
  // Create level up overlay
  const overlay = document.createElement('div');
  overlay.className = 'level-up-overlay';
  overlay.innerHTML = `
    <div class="level-up-content">
      <h2>Level Up!</h2>
      <p>Choose your new abilities</p>
    </div>
  `;
  
  // Animate available nodes
  newNodes.forEach((nodeId, index) => {
    const node = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (node) {
      gsap.to(node, {
        scale: 1.1,
        boxShadow: `0 0 15px ${theme.colorPalette.highlight}`,
        duration: 0.5,
        delay: index * 0.2,
        ease: 'power2.out',
        yoyo: true,
        repeat: -1,
      });
    }
  });
};
```

## Multiclassing Support

### Tab System
```typescript
const MulticlassTabs: React.FC<{ classes: string[]; activeClass: string; onTabChange: (classId: string) => void }> = ({
  classes,
  activeClass,
  onTabChange,
}) => {
  return (
    <div className="multiclass-tabs">
      {classes.map(classId => (
        <button
          key={classId}
          className={`class-tab ${activeClass === classId ? 'active' : ''}`}
          onClick={() => onTabChange(classId)}
          style={{
            background: CLASS_THEMES[classId].colorPalette.primary,
          }}
        >
          <span className="class-icon">{getClassIcon(classId)}</span>
          <span className="class-name">{getClassName(classId)}</span>
        </button>
      ))}
    </div>
  );
};
```

### Cross-Class Connections
```typescript
interface CrossClassConnection {
  fromClass: string;
  toClass: string;
  fromNode: string;
  toNode: string;
  connectionType: 'prerequisite' | 'synergy' | 'unlock';
}

const renderCrossClassConnections = (connections: CrossClassConnection[]) => {
  connections.forEach(connection => {
    const fromNode = document.querySelector(`[data-node-id="${connection.fromNode}"]`);
    const toNode = document.querySelector(`[data-node-id="${connection.toNode}"]`);
    
    if (fromNode && toNode) {
      drawConnection(fromNode, toNode, {
        color: '#F39C12',
        style: 'dashed',
        width: 2,
      });
    }
  });
};
```

## Performance Optimization

### Canvas Rendering
```typescript
class TreeRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private nodes: Map<string, TreeNode> = new Map();
  private connections: Connection[] = [];
  
  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.setupCanvas();
  }
  
  private setupCanvas() {
    // Set up high DPI support
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
  }
  
  render(tree: ProgressionTree, theme: ClassTheme, state: TreeState) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Render connections first
    this.renderConnections(theme);
    
    // Render nodes
    this.renderNodes(state);
    
    // Render ambient effects
    this.renderAmbientEffects(theme);
  }
  
  private renderConnections(theme: ClassTheme) {
    this.connections.forEach(connection => {
      this.ctx.strokeStyle = theme.nodeConnections;
      this.ctx.lineWidth = 2;
      this.ctx.setLineDash([5, 5]);
      this.ctx.beginPath();
      this.ctx.moveTo(connection.from.x, connection.from.y);
      this.ctx.lineTo(connection.to.x, connection.to.y);
      this.ctx.stroke();
    });
  }
}
```

## Accessibility Features

### Keyboard Navigation
```typescript
const useKeyboardNavigation = (nodes: string[], onNodeSelect: (nodeId: string) => void) => {
  const [focusedNode, setFocusedNode] = useState<string | null>(null);
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!focusedNode) return;
      
      const currentIndex = nodes.indexOf(focusedNode);
      let nextIndex = currentIndex;
      
      switch (event.key) {
        case 'ArrowRight':
          nextIndex = (currentIndex + 1) % nodes.length;
          break;
        case 'ArrowLeft':
          nextIndex = currentIndex === 0 ? nodes.length - 1 : currentIndex - 1;
          break;
        case 'Enter':
        case ' ':
          onNodeSelect(focusedNode);
          break;
      }
      
      if (nextIndex !== currentIndex) {
        setFocusedNode(nodes[nextIndex]);
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [focusedNode, nodes, onNodeSelect]);
  
  return { focusedNode, setFocusedNode };
};
```

### Screen Reader Support
```typescript
const TreeNode: React.FC<TreeNodeProps> = ({ node, isAvailable, isSelected, onClick }) => {
  return (
    <div
      role="button"
      tabIndex={isAvailable ? 0 : -1}
      aria-label={`${node.name} - ${isAvailable ? 'Available' : 'Locked'} node`}
      aria-describedby={`node-description-${node.id}`}
      onClick={isAvailable ? onClick : undefined}
    >
      <div className="node-content">
        <span className="sr-only">{node.name}</span>
        <div className="node-icon" aria-hidden="true">
          {getNodeIcon(node.type)}
        </div>
      </div>
      <div id={`node-description-${node.id}`} className="sr-only">
        {node.description}
        {node.prerequisites && ` Prerequisites: ${node.prerequisites}`}
      </div>
    </div>
  );
};
```

This implementation provides a rich, interactive progression tree system that's both visually appealing and functionally robust, supporting all the features outlined in the UI ideas while maintaining performance and accessibility.
