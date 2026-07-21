# Relational Codex System Implementation Plan

## Overview
Transform the traditional flat journal/codex into an immersive, interactive 3D holographic mind map where information is connected through visual relationships. This system will make lore exploration engaging and help players understand the complex web of relationships in the Star Wars universe.

## Core Concepts

### 1. 3D Holographic Interface
- **Interactive Mind Map**: Information presented as connected nodes in 3D space
- **Holographic Aesthetics**: Star Wars-themed visual design with holographic effects
- **Spatial Navigation**: Players can explore information spatially

### 2. Relational Database
- **Connected Information**: All entries are linked through relationships
- **Dynamic Queries**: Real-time filtering and searching based on connections
- **Contextual Discovery**: Related information is always accessible

### 3. Interactive Exploration
- **Click-to-Explore**: Click on nodes to expand information
- **Relationship Visualization**: Lines show connections between entries
- **Filtering System**: Focus on specific types of relationships

## Technical Architecture

### State Management Integration

```typescript
// Redux slice for codex management
interface CodexState {
  entries: NormalizedCodexEntries;
  relationships: RelationshipMap;
  currentNode: string | null;
  selectedFilters: CodexFilter[];
  viewMode: 'explore' | 'search' | 'timeline';
  searchQuery: string;
  expandedNodes: Set<string>;
  navigationHistory: string[];
  holographicEffects: HolographicEffect[];
}

interface CodexEntry {
  id: string;
  type: 'character' | 'location' | 'faction' | 'event' | 'item' | 'species';
  title: string;
  description: string;
  imageUrl: string;
  position: THREE.Vector3;
  connections: string[];
  metadata: EntryMetadata;
  unlockConditions: UnlockCondition[];
  isUnlocked: boolean;
}

interface RelationshipMap {
  [entryId: string]: {
    [targetId: string]: RelationshipData;
  };
}

interface RelationshipData {
  type: 'ally' | 'enemy' | 'location' | 'event' | 'item' | 'faction';
  strength: number; // 0-1
  description: string;
  bidirectional: boolean;
  visualStyle: RelationshipVisualStyle;
}

interface CodexFilter {
  type: 'entry_type' | 'relationship_type' | 'faction' | 'timeline';
  value: string;
  active: boolean;
}

const codexSlice = createSlice({
  name: 'codex',
  initialState,
  reducers: {
    setCurrentNode: (state, action) => {
      state.currentNode = action.payload;
      state.navigationHistory.push(action.payload);
    },
    addEntry: (state, action) => {
      const entry = action.payload;
      state.entries[entry.id] = entry;
    },
    updateRelationship: (state, action) => {
      const { sourceId, targetId, relationship } = action.payload;
      if (!state.relationships[sourceId]) {
        state.relationships[sourceId] = {};
      }
      state.relationships[sourceId][targetId] = relationship;
    },
    setFilter: (state, action) => {
      const { filterType, value, active } = action.payload;
      const existingFilter = state.selectedFilters.find(f => f.type === filterType);
      
      if (existingFilter) {
        existingFilter.active = active;
        existingFilter.value = value;
      } else {
        state.selectedFilters.push({ type: filterType, value, active });
      }
    },
    expandNode: (state, action) => {
      state.expandedNodes.add(action.payload);
    },
    collapseNode: (state, action) => {
      state.expandedNodes.delete(action.payload);
    },
    setViewMode: (state, action) => {
      state.viewMode = action.payload;
    },
    setSearchQuery: (state, action) => {
      state.searchQuery = action.payload;
    }
  }
});
```

### 3D Holographic Scene Management

```typescript
class HolographicCodex {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private nodes: Map<string, CodexNode>;
  private connections: Map<string, ConnectionLine>;
  private holographicEffects: HolographicEffectManager;
  private interactionManager: InteractionManager;
  
  constructor(container: HTMLElement) {
    this.setupScene();
    this.setupCamera();
    this.setupRenderer(container);
    this.setupHolographicEffects();
    this.setupInteractionManager();
  }
  
  private setupScene(): void {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000011);
    
    // Add starfield background
    this.createStarfieldBackground();
  }
  
  private setupCamera(): void {
    this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    this.camera.position.set(0, 0, 10);
  }
  
  private setupRenderer(container: HTMLElement): void {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(this.renderer.domElement);
  }
  
  private setupHolographicEffects(): void {
    this.holographicEffects = new HolographicEffectManager(this.scene);
  }
  
  public async loadCodexData(entries: CodexEntry[], relationships: RelationshipMap): Promise<void> {
    // Clear existing nodes and connections
    this.clearScene();
    
    // Create nodes for all entries
    for (const entry of entries) {
      await this.createNode(entry);
    }
    
    // Create connections based on relationships
    for (const [sourceId, targets] of Object.entries(relationships)) {
      for (const [targetId, relationship] of Object.entries(targets)) {
        await this.createConnection(sourceId, targetId, relationship);
      }
    }
    
    // Apply initial layout
    this.applyForceDirectedLayout();
  }
  
  private async createNode(entry: CodexEntry): Promise<void> {
    const node = new CodexNode(entry);
    this.nodes.set(entry.id, node);
    this.scene.add(node.mesh);
    
    // Add holographic effects
    this.holographicEffects.addNodeEffects(node);
  }
  
  private async createConnection(sourceId: string, targetId: string, relationship: RelationshipData): Promise<void> {
    const sourceNode = this.nodes.get(sourceId);
    const targetNode = this.nodes.get(targetId);
    
    if (!sourceNode || !targetNode) return;
    
    const connection = new ConnectionLine(sourceNode, targetNode, relationship);
    this.connections.set(`${sourceId}-${targetId}`, connection);
    this.scene.add(connection.mesh);
  }
  
  public selectNode(nodeId: string): void {
    // Deselect current node
    if (this.currentSelectedNode) {
      this.currentSelectedNode.setSelected(false);
    }
    
    // Select new node
    const node = this.nodes.get(nodeId);
    if (node) {
      node.setSelected(true);
      this.currentSelectedNode = node;
      
      // Focus camera on node
      this.focusCameraOnNode(node);
    }
  }
  
  public filterNodes(filters: CodexFilter[]): void {
    const activeFilters = filters.filter(f => f.active);
    
    this.nodes.forEach(node => {
      const shouldShow = this.evaluateFilters(node.entry, activeFilters);
      node.setVisible(shouldShow);
    });
    
    this.connections.forEach(connection => {
      const sourceVisible = connection.sourceNode.isVisible();
      const targetVisible = connection.targetNode.isVisible();
      connection.setVisible(sourceVisible && targetVisible);
    });
  }
  
  private evaluateFilters(entry: CodexEntry, filters: CodexFilter[]): boolean {
    return filters.every(filter => {
      switch (filter.type) {
        case 'entry_type':
          return entry.type === filter.value;
        case 'faction':
          return entry.metadata.faction === filter.value;
        case 'timeline':
          return this.isInTimeline(entry, filter.value);
        default:
          return true;
      }
    });
  }
  
  private focusCameraOnNode(node: CodexNode): void {
    const targetPosition = node.mesh.position.clone();
    targetPosition.z += 5;
    
    gsap.to(this.camera.position, {
      x: targetPosition.x,
      y: targetPosition.y,
      z: targetPosition.z,
      duration: 1.0,
      ease: "power2.inOut"
    });
  }
}

class CodexNode {
  public mesh: THREE.Group;
  public entry: CodexEntry;
  private isSelected: boolean;
  private isVisible: boolean;
  private holographicMaterial: THREE.ShaderMaterial;
  
  constructor(entry: CodexEntry) {
    this.entry = entry;
    this.isSelected = false;
    this.isVisible = true;
    this.mesh = new THREE.Group();
    
    this.createNodeMesh();
    this.createHolographicEffects();
  }
  
  private createNodeMesh(): void {
    // Create base geometry based on entry type
    const geometry = this.getGeometryForType(this.entry.type);
    const material = this.createHolographicMaterial();
    
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(this.entry.position);
    this.mesh.add(mesh);
    
    // Add selection indicator
    this.addSelectionIndicator();
  }
  
  private getGeometryForType(type: string): THREE.BufferGeometry {
    switch (type) {
      case 'character':
        return new THREE.SphereGeometry(0.5, 16, 16);
      case 'location':
        return new THREE.BoxGeometry(0.8, 0.8, 0.8);
      case 'faction':
        return new THREE.ConeGeometry(0.4, 1.0, 8);
      case 'event':
        return new THREE.OctahedronGeometry(0.4);
      case 'item':
        return new THREE.CylinderGeometry(0.3, 0.3, 0.6, 8);
      case 'species':
        return new THREE.TetrahedronGeometry(0.4);
      default:
        return new THREE.SphereGeometry(0.4, 8, 8);
    }
  }
  
  private createHolographicMaterial(): THREE.ShaderMaterial {
    return new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        color: { value: new THREE.Color(0x00ffff) },
        opacity: { value: 0.8 }
      },
      vertexShader: `
        varying vec3 vPosition;
        void main() {
          vPosition = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 color;
        uniform float opacity;
        varying vec3 vPosition;
        
        void main() {
          float pulse = sin(time * 2.0) * 0.1 + 0.9;
          vec3 finalColor = color * pulse;
          gl_FragColor = vec4(finalColor, opacity);
        }
      `,
      transparent: true,
      side: THREE.DoubleSide
    });
  }
  
  private addSelectionIndicator(): void {
    const indicatorGeometry = new THREE.RingGeometry(0.6, 0.7, 16);
    const indicatorMaterial = new THREE.MeshBasicMaterial({
      color: 0xffff00,
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide
    });
    
    const indicator = new THREE.Mesh(indicatorGeometry, indicatorMaterial);
    indicator.visible = false;
    indicator.name = 'selection_indicator';
    this.mesh.add(indicator);
  }
  
  public setSelected(selected: boolean): void {
    this.isSelected = selected;
    const indicator = this.mesh.getObjectByName('selection_indicator');
    if (indicator) {
      indicator.visible = selected;
    }
  }
  
  public setVisible(visible: boolean): void {
    this.isVisible = visible;
    this.mesh.visible = visible;
  }
  
  public update(time: number): void {
    // Update holographic material time uniform
    if (this.holographicMaterial) {
      this.holographicMaterial.uniforms.time.value = time;
    }
    
    // Rotate node slowly
    this.mesh.rotation.y += 0.01;
  }
}

class ConnectionLine {
  public mesh: THREE.Group;
  public sourceNode: CodexNode;
  public targetNode: CodexNode;
  public relationship: RelationshipData;
  
  constructor(sourceNode: CodexNode, targetNode: CodexNode, relationship: RelationshipData) {
    this.sourceNode = sourceNode;
    this.targetNode = targetNode;
    this.relationship = relationship;
    this.mesh = new THREE.Group();
    
    this.createConnectionLine();
  }
  
  private createConnectionLine(): void {
    const sourcePos = this.sourceNode.mesh.position;
    const targetPos = this.targetNode.mesh.position;
    
    // Create line geometry
    const points = [sourcePos, targetPos];
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    
    // Create holographic line material
    const material = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        color: { value: this.getRelationshipColor() },
        opacity: { value: 0.6 * this.relationship.strength }
      },
      vertexShader: `
        void main() {
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 color;
        uniform float opacity;
        
        void main() {
          float pulse = sin(time * 3.0) * 0.2 + 0.8;
          gl_FragColor = vec4(color * pulse, opacity);
        }
      `,
      transparent: true,
      linewidth: 2
    });
    
    const line = new THREE.Line(geometry, material);
    this.mesh.add(line);
    
    // Add arrow indicator for directional relationships
    if (!this.relationship.bidirectional) {
      this.addDirectionalArrow();
    }
  }
  
  private getRelationshipColor(): THREE.Color {
    switch (this.relationship.type) {
      case 'ally':
        return new THREE.Color(0x00ff00);
      case 'enemy':
        return new THREE.Color(0xff0000);
      case 'location':
        return new THREE.Color(0x0000ff);
      case 'event':
        return new THREE.Color(0xffff00);
      case 'item':
        return new THREE.Color(0xff00ff);
      case 'faction':
        return new THREE.Color(0x00ffff);
      default:
        return new THREE.Color(0xffffff);
    }
  }
  
  private addDirectionalArrow(): void {
    // Create arrow geometry pointing from source to target
    const arrowGeometry = new THREE.ConeGeometry(0.1, 0.3, 8);
    const arrowMaterial = new THREE.MeshBasicMaterial({
      color: this.getRelationshipColor(),
      transparent: true,
      opacity: 0.8
    });
    
    const arrow = new THREE.Mesh(arrowGeometry, arrowMaterial);
    
    // Position arrow at midpoint
    const sourcePos = this.sourceNode.mesh.position;
    const targetPos = this.targetNode.mesh.position;
    const midpoint = sourcePos.clone().lerp(targetPos, 0.5);
    arrow.position.copy(midpoint);
    
    // Orient arrow towards target
    arrow.lookAt(targetPos);
    
    this.mesh.add(arrow);
  }
  
  public setVisible(visible: boolean): void {
    this.mesh.visible = visible;
  }
  
  public update(time: number): void {
    // Update line material time uniform
    this.mesh.children.forEach(child => {
      if (child instanceof THREE.Line && child.material instanceof THREE.ShaderMaterial) {
        child.material.uniforms.time.value = time;
      }
    });
  }
}
```

### React Component Structure

```typescript
const CodexScreen: React.FC = () => {
  const dispatch = useDispatch();
  const codex = useSelector(selectCodex);
  const [holographicCodex, setHolographicCodex] = useState<HolographicCodex | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<CodexEntry | null>(null);
  
  useEffect(() => {
    const container = document.getElementById('codex-container') as HTMLElement;
    const codexInstance = new HolographicCodex(container);
    setHolographicCodex(codexInstance);
    
    // Load initial data
    codexInstance.loadCodexData(Object.values(codex.entries), codex.relationships);
  }, []);
  
  useEffect(() => {
    if (holographicCodex && codex.currentNode) {
      holographicCodex.selectNode(codex.currentNode);
      const entry = codex.entries[codex.currentNode];
      setSelectedEntry(entry);
    }
  }, [codex.currentNode, holographicCodex]);
  
  useEffect(() => {
    if (holographicCodex) {
      holographicCodex.filterNodes(codex.selectedFilters);
    }
  }, [codex.selectedFilters, holographicCodex]);
  
  const handleNodeClick = (nodeId: string) => {
    dispatch(setCurrentNode(nodeId));
  };
  
  const handleFilterChange = (filterType: string, value: string, active: boolean) => {
    dispatch(setFilter({ filterType, value, active }));
  };
  
  const handleSearch = (query: string) => {
    dispatch(setSearchQuery(query));
  };
  
  return (
    <CodexContainer>
      <CodexViewport id="codex-container" />
      
      <CodexSidebar>
        <SearchBar 
          value={codex.searchQuery}
          onChange={handleSearch}
        />
        
        <FilterPanel 
          filters={codex.selectedFilters}
          onFilterChange={handleFilterChange}
        />
        
        {selectedEntry && (
          <EntryDetails 
            entry={selectedEntry}
            relationships={codex.relationships[selectedEntry.id] || {}}
          />
        )}
      </CodexSidebar>
      
      <CodexControls>
        <ViewModeSelector 
          mode={codex.viewMode}
          onModeChange={(mode) => dispatch(setViewMode(mode))}
        />
        
        <NavigationControls 
          history={codex.navigationHistory}
          onNavigate={(nodeId) => dispatch(setCurrentNode(nodeId))}
        />
      </CodexControls>
    </CodexContainer>
  );
};

const SearchBar: React.FC<SearchBarProps> = ({ value, onChange }) => {
  return (
    <SearchContainer>
      <SearchInput 
        type="text"
        placeholder="Search the codex..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <SearchIcon>🔍</SearchIcon>
    </SearchContainer>
  );
};

const FilterPanel: React.FC<FilterPanelProps> = ({ filters, onFilterChange }) => {
  return (
    <FilterContainer>
      <FilterTitle>Filters</FilterTitle>
      
      <FilterGroup>
        <FilterLabel>Entry Type</FilterLabel>
        {['character', 'location', 'faction', 'event', 'item', 'species'].map(type => (
          <FilterCheckbox
            key={type}
            checked={filters.some(f => f.type === 'entry_type' && f.value === type && f.active)}
            onChange={(checked) => onFilterChange('entry_type', type, checked)}
            label={type.charAt(0).toUpperCase() + type.slice(1)}
          />
        ))}
      </FilterGroup>
      
      <FilterGroup>
        <FilterLabel>Relationship Type</FilterLabel>
        {['ally', 'enemy', 'location', 'event', 'item', 'faction'].map(type => (
          <FilterCheckbox
            key={type}
            checked={filters.some(f => f.type === 'relationship_type' && f.value === type && f.active)}
            onChange={(checked) => onFilterChange('relationship_type', type, checked)}
            label={type.charAt(0).toUpperCase() + type.slice(1)}
          />
        ))}
      </FilterGroup>
    </FilterContainer>
  );
};

const EntryDetails: React.FC<EntryDetailsProps> = ({ entry, relationships }) => {
  return (
    <EntryDetailsContainer>
      <EntryHeader>
        <EntryImage src={entry.imageUrl} alt={entry.title} />
        <EntryTitle>{entry.title}</EntryTitle>
        <EntryType>{entry.type}</EntryType>
      </EntryHeader>
      
      <EntryDescription>{entry.description}</EntryDescription>
      
      <RelationshipsSection>
        <RelationshipsTitle>Connections</RelationshipsTitle>
        {Object.entries(relationships).map(([targetId, relationship]) => (
          <RelationshipItem
            key={targetId}
            relationship={relationship}
            targetId={targetId}
          />
        ))}
      </RelationshipsSection>
      
      <EntryMetadata>
        <MetadataItem>
          <MetadataLabel>Faction:</MetadataLabel>
          <MetadataValue>{entry.metadata.faction}</MetadataValue>
        </MetadataItem>
        <MetadataItem>
          <MetadataLabel>Timeline:</MetadataLabel>
          <MetadataValue>{entry.metadata.timeline}</MetadataValue>
        </MetadataItem>
      </EntryMetadata>
    </EntryDetailsContainer>
  );
};

const RelationshipItem: React.FC<RelationshipItemProps> = ({ relationship, targetId }) => {
  return (
    <RelationshipItemContainer>
      <RelationshipType type={relationship.type}>
        {relationship.type}
      </RelationshipType>
      <RelationshipDescription>
        {relationship.description}
      </RelationshipDescription>
      <RelationshipStrength strength={relationship.strength} />
    </RelationshipItemContainer>
  );
};
```

### Styled Components

```typescript
const CodexContainer = styled.div`
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #0a0a0a, #1a1a2e);
  color: #00ffff;
  font-family: 'Star Wars', monospace;
`;

const CodexViewport = styled.div`
  flex: 1;
  position: relative;
  overflow: hidden;
`;

const CodexSidebar = styled.div`
  width: 350px;
  background: rgba(0, 0, 0, 0.8);
  border-left: 2px solid #00ffff;
  padding: 1rem;
  overflow-y: auto;
`;

const SearchContainer = styled.div`
  position: relative;
  margin-bottom: 1rem;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 0.5rem 2rem 0.5rem 1rem;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid #00ffff;
  border-radius: 4px;
  color: #00ffff;
  font-family: inherit;
  
  &::placeholder {
    color: rgba(0, 255, 255, 0.5);
  }
`;

const FilterContainer = styled.div`
  margin-bottom: 2rem;
`;

const FilterTitle = styled.h3`
  margin: 0 0 1rem 0;
  color: #00ffff;
  font-size: 1.2rem;
`;

const FilterGroup = styled.div`
  margin-bottom: 1rem;
`;

const FilterLabel = styled.div`
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #00ffff;
`;

const FilterCheckbox = styled.label<{ checked: boolean }>`
  display: flex;
  align-items: center;
  margin-bottom: 0.25rem;
  cursor: pointer;
  color: ${props => props.checked ? '#00ffff' : 'rgba(0, 255, 255, 0.6)'};
  
  input {
    margin-right: 0.5rem;
    accent-color: #00ffff;
  }
`;

const EntryDetailsContainer = styled.div`
  background: rgba(0, 255, 255, 0.05);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 8px;
  padding: 1rem;
`;

const EntryHeader = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
`;

const EntryImage = styled.img`
  width: 60px;
  height: 60px;
  border-radius: 50%;
  margin-right: 1rem;
  border: 2px solid #00ffff;
`;

const EntryTitle = styled.h2`
  margin: 0;
  color: #00ffff;
  font-size: 1.5rem;
`;

const EntryType = styled.span`
  background: rgba(0, 255, 255, 0.2);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  margin-left: auto;
`;

const EntryDescription = styled.p`
  color: rgba(0, 255, 255, 0.8);
  line-height: 1.5;
  margin-bottom: 1rem;
`;

const RelationshipsSection = styled.div`
  margin-bottom: 1rem;
`;

const RelationshipsTitle = styled.h4`
  margin: 0 0 0.5rem 0;
  color: #00ffff;
`;

const RelationshipItemContainer = styled.div`
  background: rgba(0, 255, 255, 0.05);
  border: 1px solid rgba(0, 255, 255, 0.1);
  border-radius: 4px;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
`;

const RelationshipType = styled.span<{ type: string }>`
  background: ${props => getRelationshipColor(props.type)};
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  margin-right: 0.5rem;
`;

const RelationshipDescription = styled.div`
  color: rgba(0, 255, 255, 0.8);
  font-size: 0.9rem;
  margin: 0.25rem 0;
`;

const RelationshipStrength = styled.div<{ strength: number }>`
  width: 100%;
  height: 4px;
  background: rgba(0, 255, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
  
  &::after {
    content: '';
    display: block;
    width: ${props => props.strength * 100}%;
    height: 100%;
    background: #00ffff;
    transition: width 0.3s ease;
  }
`;

// Utility function
const getRelationshipColor = (type: string): string => {
  const colors = {
    ally: '#27ae60',
    enemy: '#e74c3c',
    location: '#3498db',
    event: '#f39c12',
    item: '#9b59b6',
    faction: '#00ffff'
  };
  return colors[type as keyof typeof colors] || '#95a5a6';
};
```

## Animation System

### Holographic Effects

```typescript
class HolographicEffectManager {
  private scene: THREE.Scene;
  private effects: Map<string, HolographicEffect>;
  
  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.effects = new Map();
  }
  
  public addNodeEffects(node: CodexNode): void {
    // Add pulsing glow effect
    const glowEffect = new GlowEffect(node.mesh.position);
    this.effects.set(`glow_${node.entry.id}`, glowEffect);
    this.scene.add(glowEffect.mesh);
    
    // Add particle system
    const particleEffect = new ParticleEffect(node.mesh.position);
    this.effects.set(`particles_${node.entry.id}`, particleEffect);
    this.scene.add(particleEffect.mesh);
  }
  
  public update(time: number): void {
    this.effects.forEach(effect => {
      effect.update(time);
    });
  }
}

class GlowEffect {
  public mesh: THREE.Mesh;
  
  constructor(position: THREE.Vector3) {
    const geometry = new THREE.SphereGeometry(0.8, 16, 16);
    const material = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        color: { value: new THREE.Color(0x00ffff) }
      },
      vertexShader: `
        void main() {
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 color;
        
        void main() {
          float pulse = sin(time * 2.0) * 0.3 + 0.7;
          gl_FragColor = vec4(color, pulse * 0.3);
        }
      `,
      transparent: true,
      side: THREE.BackSide
    });
    
    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.position.copy(position);
  }
  
  public update(time: number): void {
    if (this.mesh.material instanceof THREE.ShaderMaterial) {
      this.mesh.material.uniforms.time.value = time;
    }
  }
}

class ParticleEffect {
  public mesh: THREE.Points;
  private particles: Float32Array;
  
  constructor(position: THREE.Vector3) {
    const particleCount = 50;
    this.particles = new Float32Array(particleCount * 3);
    
    for (let i = 0; i < particleCount; i++) {
      this.particles[i * 3] = (Math.random() - 0.5) * 2;
      this.particles[i * 3 + 1] = (Math.random() - 0.5) * 2;
      this.particles[i * 3 + 2] = (Math.random() - 0.5) * 2;
    }
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(this.particles, 3));
    
    const material = new THREE.PointsMaterial({
      color: 0x00ffff,
      size: 0.05,
      transparent: true,
      opacity: 0.6
    });
    
    this.mesh = new THREE.Points(geometry, material);
    this.mesh.position.copy(position);
  }
  
  public update(time: number): void {
    // Animate particles
    for (let i = 0; i < this.particles.length; i += 3) {
      this.particles[i + 1] += Math.sin(time + i) * 0.01;
    }
    
    this.mesh.geometry.attributes.position.needsUpdate = true;
  }
}
```

## API Integration

### Codex API Service

```typescript
class CodexAPIService {
  private baseURL: string;
  
  constructor() {
    this.baseURL = '/api/codex';
  }
  
  async getCodexEntries(): Promise<CodexEntry[]> {
    const response = await fetch(`${this.baseURL}/entries`);
    return response.json();
  }
  
  async getRelationships(): Promise<RelationshipMap> {
    const response = await fetch(`${this.baseURL}/relationships`);
    return response.json();
  }
  
  async searchEntries(query: string): Promise<CodexEntry[]> {
    const response = await fetch(`${this.baseURL}/search?q=${encodeURIComponent(query)}`);
    return response.json();
  }
  
  async getEntryDetails(entryId: string): Promise<CodexEntry> {
    const response = await fetch(`${this.baseURL}/entries/${entryId}`);
    return response.json();
  }
  
  async unlockEntry(entryId: string): Promise<void> {
    await fetch(`${this.baseURL}/entries/${entryId}/unlock`, {
      method: 'POST'
    });
  }
}

// Redux Thunks
export const loadCodexDataAsync = createAsyncThunk(
  'codex/loadData',
  async () => {
    const api = new CodexAPIService();
    const [entries, relationships] = await Promise.all([
      api.getCodexEntries(),
      api.getRelationships()
    ]);
    return { entries, relationships };
  }
);

export const searchEntriesAsync = createAsyncThunk(
  'codex/searchEntries',
  async (query: string) => {
    const api = new CodexAPIService();
    return await api.searchEntries(query);
  }
);
```

## Implementation Phases

### Phase 1: Core 3D System (Weeks 1-2)
- Basic 3D scene setup
- Node and connection rendering
- Basic interaction system

### Phase 2: Holographic Effects (Weeks 3-4)
- Holographic materials and shaders
- Particle effects and animations
- Visual polish

### Phase 3: Interaction and UI (Weeks 5-6)
- React component integration
- Search and filtering
- Entry details panel

### Phase 4: Polish and Integration (Weeks 7-8)
- Performance optimization
- Animation refinement
- Full integration testing

## Success Metrics

- **User Engagement**: Time spent exploring codex vs. traditional journal
- **Information Discovery**: Number of connections explored per session
- **Visual Appeal**: User feedback on holographic interface
- **Performance**: Smooth 60fps with complex node networks
- **Usability**: Ease of finding and understanding relationships

## Future Enhancements

- **Voice Narration**: Audio descriptions for entries
- **Timeline View**: Temporal visualization of events
- **Collaborative Annotations**: Player-created notes and connections
- **Dynamic Content**: Real-time updates based on game events
- **Export Features**: Share codex discoveries with other players
