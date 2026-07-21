# Visual Inventory System Implementation Plan

## Overview
Transform the traditional grid-based inventory into an immersive, diorama-style visual experience that feels like exploring a starship's locker or crew quarters. This system will make inventory management engaging and visually appealing while maintaining functionality.

## Core Concepts

### 1. Diorama-Based Layout
- **Starship Locker Theme**: Items are placed in realistic locations within a 3D environment
- **Dynamic Positioning**: Equipment appears on appropriate stands, racks, and storage areas
- **Environmental Storytelling**: The layout tells a story about the character's gear and lifestyle

### 2. Visual State Reflection
- **Equipment Condition**: Items visually reflect their current state (damage, modifications, etc.)
- **Real-time Updates**: Changes in equipment status are immediately visible
- **Interactive Elements**: Items can be examined, modified, and equipped through direct interaction

## Technical Architecture

### State Management Integration

```typescript
// Redux slice for inventory management
interface InventoryState {
  items: NormalizedInventory;
  equippedItems: EquippedItems;
  itemConditions: Record<string, ItemCondition>;
  dioramaLayout: DioramaLayout;
  selectedItem: string | null;
  interactionMode: 'view' | 'equip' | 'modify' | 'repair';
}

interface ItemCondition {
  durability: number;
  modifications: Modification[];
  visualEffects: VisualEffect[];
  needsRepair: boolean;
}

interface DioramaLayout {
  zones: {
    armorStand: InventoryZone;
    weaponRack: InventoryZone;
    footlocker: InventoryZone;
    workbench: InventoryZone;
    displayCase: InventoryZone;
  };
  itemPositions: Record<string, ItemPosition>;
}

const inventorySlice = createSlice({
  name: 'inventory',
  initialState,
  reducers: {
    updateItemCondition: (state, action) => {
      const { itemId, condition } = action.payload;
      state.itemConditions[itemId] = condition;
    },
    setDioramaLayout: (state, action) => {
      state.dioramaLayout = action.payload;
    },
    selectItem: (state, action) => {
      state.selectedItem = action.payload;
    },
    setInteractionMode: (state, action) => {
      state.interactionMode = action.payload;
    }
  }
});
```

### 3D Scene Management

```typescript
class InventoryDiorama {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private zones: Map<string, InventoryZone>;
  private itemModels: Map<string, THREE.Group>;
  
  constructor(container: HTMLElement) {
    this.setupScene();
    this.setupLighting();
    this.createZones();
    this.setupInteractions();
  }
  
  private setupScene(): void {
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    
    // Add starship interior background
    this.createStarshipInterior();
  }
  
  private createZones(): void {
    this.zones = new Map();
    
    // Armor Stand Zone
    this.zones.set('armorStand', new InventoryZone({
      position: new THREE.Vector3(-3, 0, 0),
      size: new THREE.Vector3(2, 3, 1),
      type: 'armor',
      visualStyle: 'stand'
    }));
    
    // Weapon Rack Zone
    this.zones.set('weaponRack', new InventoryZone({
      position: new THREE.Vector3(3, 0, 0),
      size: new THREE.Vector3(2, 2, 0.5),
      type: 'weapon',
      visualStyle: 'rack'
    }));
    
    // Footlocker Zone
    this.zones.set('footlocker', new InventoryZone({
      position: new THREE.Vector3(0, -2, 0),
      size: new THREE.Vector3(3, 1, 2),
      type: 'consumable',
      visualStyle: 'container'
    }));
  }
  
  public updateItemVisual(itemId: string, condition: ItemCondition): void {
    const itemModel = this.itemModels.get(itemId);
    if (!itemModel) return;
    
    // Apply visual effects based on condition
    this.applyDamageEffects(itemModel, condition);
    this.applyModificationEffects(itemModel, condition.modifications);
    this.applyRepairEffects(itemModel, condition.needsRepair);
  }
  
  private applyDamageEffects(model: THREE.Group, condition: ItemCondition): void {
    const damageLevel = 1 - (condition.durability / 100);
    
    // Add scorch marks, dents, etc.
    if (damageLevel > 0.3) {
      this.addScorchMarks(model, damageLevel);
    }
    
    if (damageLevel > 0.6) {
      this.addDents(model, damageLevel);
    }
  }
}
```

### React Component Structure

```typescript
const InventoryScreen: React.FC = () => {
  const dispatch = useDispatch();
  const inventory = useSelector(selectInventory);
  const selectedItem = useSelector(selectSelectedItem);
  const interactionMode = useSelector(selectInteractionMode);
  
  const [dioramaRef, setDioramaRef] = useState<InventoryDiorama | null>(null);
  
  useEffect(() => {
    if (dioramaRef) {
      dioramaRef.updateLayout(inventory.dioramaLayout);
    }
  }, [inventory.dioramaLayout, dioramaRef]);
  
  const handleItemClick = (itemId: string) => {
    dispatch(selectItem(itemId));
    dispatch(setInteractionMode('view'));
  };
  
  const handleItemEquip = (itemId: string) => {
    dispatch(equipItemAsync({ itemId, characterId: inventory.characterId }));
  };
  
  return (
    <InventoryContainer>
      <DioramaViewport ref={setDioramaRef} />
      
      <InventoryControls>
        <InteractionModeSelector 
          mode={interactionMode}
          onModeChange={(mode) => dispatch(setInteractionMode(mode))}
        />
        
        {selectedItem && (
          <ItemDetailsPanel 
            item={inventory.items[selectedItem]}
            condition={inventory.itemConditions[selectedItem]}
            onEquip={handleItemEquip}
            onModify={handleItemModify}
            onRepair={handleItemRepair}
          />
        )}
      </InventoryControls>
      
      <InventoryStats>
        <WeightIndicator current={inventory.totalWeight} max={inventory.maxWeight} />
        <CreditsDisplay amount={inventory.credits} />
      </InventoryStats>
    </InventoryContainer>
  );
};
```

## Visual Effects System

### Damage Visualization

```typescript
class DamageVisualizer {
  private static createScorchMark(intensity: number): THREE.Mesh {
    const geometry = new THREE.PlaneGeometry(0.1, 0.1);
    const material = new THREE.MeshBasicMaterial({
      color: 0x333333,
      transparent: true,
      opacity: intensity * 0.8
    });
    
    const scorchMark = new THREE.Mesh(geometry, material);
    scorchMark.rotation.z = Math.random() * Math.PI * 2;
    
    return scorchMark;
  }
  
  private static createDent(intensity: number): THREE.Mesh {
    const geometry = new THREE.SphereGeometry(0.05, 8, 6);
    const material = new THREE.MeshBasicMaterial({
      color: 0x666666,
      transparent: true,
      opacity: intensity * 0.6
    });
    
    const dent = new THREE.Mesh(geometry, material);
    dent.scale.set(1, 0.3, 1);
    
    return dent;
  }
}
```

### Modification Visualization

```typescript
class ModificationVisualizer {
  public static applyModification(model: THREE.Group, modification: Modification): void {
    switch (modification.type) {
      case 'scope':
        this.addScope(model, modification);
        break;
      case 'barrel':
        this.addBarrel(model, modification);
        break;
      case 'grip':
        this.addGrip(model, modification);
        break;
      case 'armor_plating':
        this.addArmorPlating(model, modification);
        break;
    }
  }
  
  private static addScope(model: THREE.Group, modification: Modification): void {
    const scopeGeometry = new THREE.CylinderGeometry(0.02, 0.02, 0.1, 8);
    const scopeMaterial = new THREE.MeshPhongMaterial({ color: 0x444444 });
    const scope = new THREE.Mesh(scopeGeometry, scopeMaterial);
    
    scope.position.set(0, 0.05, 0.1);
    scope.rotation.x = Math.PI / 2;
    
    model.add(scope);
  }
}
```

## Animation System

### Item Interaction Animations

```typescript
class InventoryAnimations {
  public static async highlightItem(item: THREE.Group): Promise<void> {
    const originalScale = item.scale.clone();
    const targetScale = originalScale.clone().multiplyScalar(1.1);
    
    await gsap.to(item.scale, {
      x: targetScale.x,
      y: targetScale.y,
      z: targetScale.z,
      duration: 0.3,
      ease: "power2.out"
    });
    
    await gsap.to(item.scale, {
      x: originalScale.x,
      y: originalScale.y,
      z: originalScale.z,
      duration: 0.2,
      ease: "power2.in"
    });
  }
  
  public static async equipItem(item: THREE.Group, targetPosition: THREE.Vector3): Promise<void> {
    const originalPosition = item.position.clone();
    
    await gsap.to(item.position, {
      x: targetPosition.x,
      y: targetPosition.y,
      z: targetPosition.z,
      duration: 0.5,
      ease: "power2.inOut"
    });
    
    await gsap.to(item.rotation, {
      y: Math.PI * 2,
      duration: 0.3,
      ease: "power2.out"
    });
  }
  
  public static async showDamageEffect(item: THREE.Group, damageLevel: number): Promise<void> {
    const flashMaterial = new THREE.MeshBasicMaterial({
      color: 0xff0000,
      transparent: true,
      opacity: 0.5
    });
    
    const flashMesh = new THREE.Mesh(item.geometry, flashMaterial);
    item.add(flashMesh);
    
    await gsap.to(flashMaterial, {
      opacity: 0,
      duration: 0.5,
      ease: "power2.out"
    });
    
    item.remove(flashMesh);
  }
}
```

## API Integration

### Inventory API Service

```typescript
class InventoryAPIService {
  private baseURL: string;
  
  constructor() {
    this.baseURL = '/api/inventory';
  }
  
  async getInventory(characterId: string): Promise<InventoryData> {
    const response = await fetch(`${this.baseURL}/${characterId}`);
    return response.json();
  }
  
  async updateItemCondition(itemId: string, condition: ItemCondition): Promise<void> {
    await fetch(`${this.baseURL}/items/${itemId}/condition`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(condition)
    });
  }
  
  async equipItem(characterId: string, itemId: string, slot: string): Promise<void> {
    await fetch(`${this.baseURL}/${characterId}/equip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ itemId, slot })
    });
  }
  
  async repairItem(itemId: string): Promise<ItemCondition> {
    const response = await fetch(`${this.baseURL}/items/${itemId}/repair`, {
      method: 'POST'
    });
    return response.json();
  }
}

// Redux Thunk for inventory operations
export const loadInventoryAsync = createAsyncThunk(
  'inventory/loadInventory',
  async (characterId: string) => {
    const api = new InventoryAPIService();
    return await api.getInventory(characterId);
  }
);

export const repairItemAsync = createAsyncThunk(
  'inventory/repairItem',
  async (itemId: string) => {
    const api = new InventoryAPIService();
    const condition = await api.repairItem(itemId);
    return { itemId, condition };
  }
);
```

## Performance Optimizations

### Model Caching and LOD

```typescript
class InventoryModelCache {
  private static cache = new Map<string, THREE.Group>();
  private static loadingPromises = new Map<string, Promise<THREE.Group>>();
  
  public static async getModel(itemType: string, quality: 'high' | 'medium' | 'low' = 'medium'): Promise<THREE.Group> {
    const cacheKey = `${itemType}_${quality}`;
    
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!.clone();
    }
    
    if (this.loadingPromises.has(cacheKey)) {
      return await this.loadingPromises.get(cacheKey)!;
    }
    
    const loadingPromise = this.loadModel(itemType, quality);
    this.loadingPromises.set(cacheKey, loadingPromise);
    
    const model = await loadingPromise;
    this.cache.set(cacheKey, model);
    this.loadingPromises.delete(cacheKey);
    
    return model.clone();
  }
  
  private static async loadModel(itemType: string, quality: string): Promise<THREE.Group> {
    const loader = new GLTFLoader();
    const url = `/models/inventory/${itemType}_${quality}.gltf`;
    
    return new Promise((resolve, reject) => {
      loader.load(url, resolve, undefined, reject);
    });
  }
}
```

## Accessibility Features

### Keyboard Navigation

```typescript
const useInventoryKeyboardNavigation = (items: string[], onItemSelect: (itemId: string) => void) => {
  const [focusedIndex, setFocusedIndex] = useState(0);
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowRight':
          setFocusedIndex(prev => Math.min(prev + 1, items.length - 1));
          break;
        case 'ArrowLeft':
          setFocusedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter':
        case ' ':
          onItemSelect(items[focusedIndex]);
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [items, focusedIndex, onItemSelect]);
  
  return focusedIndex;
};
```

## Implementation Phases

### Phase 1: Core Diorama System (Weeks 1-2)
- Basic 3D scene setup with zones
- Item placement and positioning
- Basic interaction system

### Phase 2: Visual Effects (Weeks 3-4)
- Damage visualization system
- Modification display
- Basic animations

### Phase 3: Advanced Features (Weeks 5-6)
- Advanced interaction modes
- Repair system
- Performance optimizations

### Phase 4: Polish and Integration (Weeks 7-8)
- Accessibility features
- Animation refinements
- Integration with character sheet

## Success Metrics

- **User Engagement**: Time spent in inventory vs. traditional grid
- **Visual Appeal**: User feedback on immersive experience
- **Performance**: Maintain 60fps with complex scenes
- **Accessibility**: Full keyboard navigation support
- **Functionality**: All inventory operations preserved

## Future Enhancements

- **Custom Diorama Themes**: Different environments (cantina, temple, etc.)
- **Item Crafting Integration**: Visual crafting workbench
- **Trading Interface**: Visual trade negotiations
- **Loot Display**: Animated loot drops and rewards
- **Social Features**: Share inventory setups with other players
