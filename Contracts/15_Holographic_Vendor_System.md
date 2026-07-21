# Holographic Vendor System Implementation Plan

## Overview
The Holographic Vendor System transforms the traditional shopping experience into an immersive, diegetic interface. Instead of generic menus, players interact with 3D holographic projectors that display spinning item models, allowing them to inspect items from all angles before purchase. This creates a memorable, visually stunning shopping experience that feels like a real Star Wars universe interaction.

## Key Features
- **3D Holographic Displays**: Interactive spinning item models with real-time inspection
- **Diegetic Interface**: In-world holographic projectors instead of traditional menus
- **Immersive Environments**: Full 3D vendor shop environments with ambient details
- **Interactive Item Inspection**: Rotate, zoom, and examine items before purchase
- **Cinematic Purchase Animations**: Satisfying visual feedback when items are acquired
- **Vendor Personalities**: Unique vendor characters with distinct shop environments
- **Audio-Visual Integration**: Ambient shop sounds and holographic audio effects

## State Management Architecture

### Redux State Structure
```typescript
interface VendorState {
  isActive: boolean;
  currentVendor: Vendor | null;
  availableItems: VendorItem[];
  selectedItem: VendorItem | null;
  inspectionMode: boolean;
  holographicDisplay: HolographicDisplay;
  purchaseState: 'idle' | 'inspecting' | 'confirming' | 'processing' | 'completing';
  shopEnvironment: ShopEnvironment;
}

interface Vendor {
  id: string;
  name: string;
  species: string;
  personality: VendorPersonality;
  shopType: 'arms_dealer' | 'tech_merchant' | 'general_store' | 'black_market';
  location: ShopLocation;
  inventory: VendorItem[];
  dialogue: VendorDialogue;
}

interface VendorItem {
  id: string;
  name: string;
  description: string;
  price: number;
  rarity: 'common' | 'uncommon' | 'rare' | 'legendary';
  category: 'weapon' | 'armor' | 'tech' | 'consumable' | 'gear';
  model3D: string;
  holographicEffects: HolographicEffect[];
  stats: ItemStats;
  vendorComment: string;
}

interface HolographicDisplay {
  isActive: boolean;
  currentItem: VendorItem | null;
  rotation: { x: number; y: number; z: number };
  zoom: number;
  lighting: HolographicLighting;
  particleEffects: ParticleEffect[];
}

interface ShopEnvironment {
  type: 'rodian_shop' | 'tech_lab' | 'cantina' | 'underground_market';
  background: string;
  ambientAudio: string;
  lighting: LightingConfig;
  interactiveElements: InteractiveElement[];
  vendorModel: VendorModel;
}
```

### Redux Actions
```typescript
const vendorSlice = createSlice({
  name: 'vendor',
  initialState,
  reducers: {
    openVendor: (state, action: PayloadAction<Vendor>) => {
      state.isActive = true;
      state.currentVendor = action.payload;
      state.availableItems = action.payload.inventory;
      state.purchaseState = 'idle';
      state.shopEnvironment = createShopEnvironment(action.payload);
    },
    selectItem: (state, action: PayloadAction<string>) => {
      state.selectedItem = state.availableItems.find(
        item => item.id === action.payload
      ) || null;
      state.inspectionMode = true;
      state.holographicDisplay.isActive = true;
      state.holographicDisplay.currentItem = state.selectedItem;
    },
    rotateHologram: (state, action: PayloadAction<{ x: number; y: number; z: number }>) => {
      state.holographicDisplay.rotation = action.payload;
    },
    zoomHologram: (state, action: PayloadAction<number>) => {
      state.holographicDisplay.zoom = action.payload;
    },
    confirmPurchase: (state) => {
      state.purchaseState = 'confirming';
    },
    processPurchase: (state) => {
      state.purchaseState = 'processing';
    },
    completePurchase: (state) => {
      state.purchaseState = 'completing';
    },
    closeVendor: (state) => {
      state.isActive = false;
      state.currentVendor = null;
      state.selectedItem = null;
      state.inspectionMode = false;
      state.holographicDisplay.isActive = false;
      state.purchaseState = 'idle';
    }
  }
});

export const {
  openVendor,
  selectItem,
  rotateHologram,
  zoomHologram,
  confirmPurchase,
  processPurchase,
  completePurchase,
  closeVendor
} = vendorSlice.actions;
```

### Async Actions
```typescript
export const purchaseItemAsync = createAsyncThunk(
  'vendor/purchaseItem',
  async (itemId: string, { dispatch, getState }) => {
    const state = getState() as RootState;
    const item = state.vendor.selectedItem;
    const vendor = state.vendor.currentVendor;
    
    if (!item || !vendor) throw new Error('No item or vendor selected');
    
    // Check if player has enough credits
    const playerCredits = state.character.credits;
    if (playerCredits < item.price) {
      throw new Error('Insufficient credits');
    }
    
    // Process purchase
    await dispatch(processPurchase());
    
    // Deduct credits
    await dispatch(updateCreditsAsync(-item.price));
    
    // Add item to inventory
    await dispatch(addItemToInventoryAsync(item));
    
    // Update vendor inventory
    await dispatch(removeItemFromVendorAsync(itemId));
    
    // Complete purchase
    await dispatch(completePurchase());
    
    return item;
  }
);
```

## Component Architecture

### Main Vendor Screen
```typescript
const VendorScreen: React.FC = () => {
  const dispatch = useDispatch();
  const { 
    isActive, 
    currentVendor, 
    availableItems, 
    selectedItem, 
    inspectionMode, 
    holographicDisplay, 
    purchaseState, 
    shopEnvironment 
  } = useSelector(selectVendorState);
  
  const handleItemSelect = (itemId: string) => {
    dispatch(selectItem(itemId));
  };
  
  const handlePurchase = () => {
    if (selectedItem) {
      dispatch(purchaseItemAsync(selectedItem.id));
    }
  };
  
  if (!isActive) return null;
  
  return (
    <VendorContainer>
      <ShopEnvironment environment={shopEnvironment} />
      <VendorInterface>
        <VendorHeader vendor={currentVendor} />
        <ItemGrid>
          {availableItems.map(item => (
            <ItemCard
              key={item.id}
              item={item}
              isSelected={selectedItem?.id === item.id}
              onSelect={handleItemSelect}
            />
          ))}
        </ItemGrid>
        <VendorActions
          selectedItem={selectedItem}
          purchaseState={purchaseState}
          onPurchase={handlePurchase}
          onClose={() => dispatch(closeVendor())}
        />
      </VendorInterface>
      {inspectionMode && (
        <HolographicDisplay
          display={holographicDisplay}
          onRotate={(rotation) => dispatch(rotateHologram(rotation))}
          onZoom={(zoom) => dispatch(zoomHologram(zoom))}
        />
      )}
      <PurchaseAnimations state={purchaseState} item={selectedItem} />
    </VendorContainer>
  );
};
```

### Holographic Display Component
```typescript
const HolographicDisplay: React.FC<HolographicDisplayProps> = ({ 
  display, 
  onRotate, 
  onZoom 
}) => {
  const sceneRef = useRef<THREE.Scene>();
  const rendererRef = useRef<THREE.WebGLRenderer>();
  const itemRef = useRef<THREE.Group>();
  
  useEffect(() => {
    if (!sceneRef.current || !display.currentItem) return;
    
    // Load 3D model
    const loader = new GLTFLoader();
    loader.load(display.currentItem.model3D, (gltf) => {
      if (itemRef.current) {
        sceneRef.current!.remove(itemRef.current);
      }
      
      itemRef.current = gltf.scene;
      sceneRef.current!.add(itemRef.current);
      
      // Apply holographic material
      itemRef.current.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.material = createHolographicMaterial(display.currentItem!.rarity);
        }
      });
    });
  }, [display.currentItem]);
  
  useEffect(() => {
    if (!itemRef.current) return;
    
    // Apply rotation
    itemRef.current.rotation.set(
      display.rotation.x,
      display.rotation.y,
      display.rotation.z
    );
    
    // Apply zoom
    itemRef.current.scale.setScalar(display.zoom);
  }, [display.rotation, display.zoom]);
  
  const handleMouseMove = (event: React.MouseEvent) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    
    onRotate({
      x: y * Math.PI,
      y: x * Math.PI,
      z: 0
    });
  };
  
  const handleWheel = (event: React.WheelEvent) => {
    const zoomDelta = event.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.5, Math.min(2.0, display.zoom * zoomDelta));
    onZoom(newZoom);
  };
  
  return (
    <HolographicContainer>
      <HolographicViewport
        ref={sceneRef}
        onMouseMove={handleMouseMove}
        onWheel={handleWheel}
      />
      <HolographicControls>
        <ItemInfo item={display.currentItem} />
        <HolographicEffects effects={display.particleEffects} />
      </HolographicControls>
    </HolographicContainer>
  );
};
```

### Shop Environment Components
```typescript
const RodianShopEnvironment: React.FC<{ environment: ShopEnvironment }> = ({ environment }) => {
  const sceneRef = useRef<THREE.Scene>();
  
  useEffect(() => {
    if (!sceneRef.current) return;
    
    // Create shop interior
    const shopGeometry = new THREE.BoxGeometry(20, 10, 15);
    const shopMaterial = new THREE.MeshLambertMaterial({ 
      color: 0x2a2a2a,
      transparent: true,
      opacity: 0.8
    });
    const shop = new THREE.Mesh(shopGeometry, shopMaterial);
    sceneRef.current.add(shop);
    
    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    sceneRef.current.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    sceneRef.current.add(directionalLight);
    
    // Add holographic projector
    const projectorGeometry = new THREE.CylinderGeometry(1, 1, 0.5, 8);
    const projectorMaterial = new THREE.MeshPhongMaterial({ 
      color: 0x00ffff,
      emissive: 0x004444
    });
    const projector = new THREE.Mesh(projectorGeometry, projectorMaterial);
    projector.position.set(0, -2, 0);
    sceneRef.current.add(projector);
    
    // Add particle effects
    const particleSystem = createShopParticles();
    sceneRef.current.add(particleSystem);
  }, [environment]);
  
  return <ShopViewport ref={sceneRef} />;
};

const TechLabEnvironment: React.FC<{ environment: ShopEnvironment }> = ({ environment }) => {
  return (
    <TechLabContainer>
      <DataTerminals />
      <CircuitWalls />
      <HolographicProjectors />
      <AmbientLighting />
    </TechLabContainer>
  );
};
```

### Item Card Component
```typescript
const ItemCard: React.FC<ItemCardProps> = ({ item, isSelected, onSelect }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  
  const handleClick = () => {
    onSelect(item.id);
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
    <ItemCardContainer
      ref={cardRef}
      isSelected={isSelected}
      rarity={item.rarity}
      onClick={handleClick}
      onMouseEnter={handleHover}
      onMouseLeave={handleUnhover}
    >
      <ItemThumbnail src={item.model3D} alt={item.name} />
      <ItemName>{item.name}</ItemName>
      <ItemPrice>{item.price} credits</ItemPrice>
      <RarityIndicator rarity={item.rarity} />
      <VendorComment>{item.vendorComment}</VendorComment>
      {isSelected && <SelectionGlow />}
    </ItemCardContainer>
  );
};
```

## Animation System

### Vendor Animations
```typescript
class VendorAnimationManager {
  private static instance: VendorAnimationManager;
  
  static getInstance(): VendorAnimationManager {
    if (!VendorAnimationManager.instance) {
      VendorAnimationManager.instance = new VendorAnimationManager();
    }
    return VendorAnimationManager.instance;
  }
  
  playItemSelection(itemCard: HTMLElement): void {
    gsap.timeline()
      .to(itemCard, {
        scale: 1.1,
        duration: 0.3,
        ease: 'back.out(1.7)'
      })
      .to(itemCard, {
        scale: 1.0,
        duration: 0.2,
        ease: 'power2.out'
      });
  }
  
  playHologramActivation(projector: HTMLElement): void {
    gsap.timeline()
      .to(projector, {
        scale: 1.2,
        duration: 0.5,
        ease: 'power2.out'
      })
      .to(projector, {
        scale: 1.0,
        duration: 0.3,
        ease: 'power2.inOut'
      });
  }
  
  playPurchaseAnimation(item: VendorItem): void {
    const timeline = gsap.timeline();
    
    // Create floating item effect
    const floatingItem = document.createElement('div');
    floatingItem.className = 'floating-purchase-item';
    floatingItem.innerHTML = `
      <img src="${item.model3D}" alt="${item.name}" />
      <span>${item.name}</span>
    `;
    document.body.appendChild(floatingItem);
    
    // Animate item flying to inventory
    timeline
      .fromTo(floatingItem, {
        scale: 0,
        opacity: 0
      }, {
        scale: 1,
        opacity: 1,
        duration: 0.5,
        ease: 'back.out(1.7)'
      })
      .to(floatingItem, {
        x: '-100vw',
        y: '50vh',
        scale: 0.5,
        duration: 1.5,
        ease: 'power2.inOut'
      })
      .to(floatingItem, {
        opacity: 0,
        duration: 0.3
      }, '-=0.3')
      .call(() => {
        document.body.removeChild(floatingItem);
      });
  }
  
  playVendorGreeting(vendor: Vendor): void {
    const timeline = gsap.timeline();
    
    // Animate vendor model
    timeline.to('.vendor-model', {
      rotationY: Math.PI * 2,
      duration: 1,
      ease: 'power2.inOut'
    });
    
    // Play vendor audio
    const audio = new Audio(vendor.dialogue.greeting);
    audio.play();
  }
}
```

## Holographic Material System

```typescript
class HolographicMaterialManager {
  static createHolographicMaterial(rarity: string): THREE.ShaderMaterial {
    const color = this.getRarityColor(rarity);
    
    return new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        color: { value: new THREE.Color(color) },
        intensity: { value: 1.0 }
      },
      vertexShader: `
        varying vec3 vPosition;
        varying vec3 vNormal;
        
        void main() {
          vPosition = position;
          vNormal = normal;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float time;
        uniform vec3 color;
        uniform float intensity;
        varying vec3 vPosition;
        varying vec3 vNormal;
        
        void main() {
          float fresnel = pow(1.0 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
          float scanline = sin(vPosition.y * 50.0 + time * 5.0) * 0.5 + 0.5;
          float flicker = sin(time * 10.0) * 0.1 + 0.9;
          
          vec3 finalColor = color * intensity * fresnel * scanline * flicker;
          gl_FragColor = vec4(finalColor, 0.8);
        }
      `,
      transparent: true,
      side: THREE.DoubleSide
    });
  }
  
  private static getRarityColor(rarity: string): number {
    switch (rarity) {
      case 'common': return 0x888888;
      case 'uncommon': return 0x00ff00;
      case 'rare': return 0x0088ff;
      case 'legendary': return 0xffaa00;
      default: return 0xffffff;
    }
  }
}
```

## Integration with Existing Systems

### Inventory Integration
```typescript
export const addItemToInventoryAsync = createAsyncThunk(
  'inventory/addItem',
  async (item: VendorItem, { dispatch }) => {
    // Convert vendor item to inventory item
    const inventoryItem: InventoryItem = {
      id: item.id,
      name: item.name,
      description: item.description,
      category: item.category,
      rarity: item.rarity,
      model3D: item.model3D,
      stats: item.stats,
      condition: 100,
      modifications: []
    };
    
    // Add to inventory
    await dispatch(addInventoryItem(inventoryItem));
    
    // Update inventory diorama
    await dispatch(updateInventoryDiorama());
    
    return inventoryItem;
  }
);
```

### Character Credits Integration
```typescript
export const updateCreditsAsync = createAsyncThunk(
  'character/updateCredits',
  async (amount: number, { dispatch, getState }) => {
    const state = getState() as RootState;
    const currentCredits = state.character.credits;
    const newCredits = Math.max(0, currentCredits + amount);
    
    // Update character state
    await dispatch(updateCharacterCredits(newCredits));
    
    // Show credit change animation
    if (amount < 0) {
      dispatch(showCreditLossAnimation(Math.abs(amount)));
    } else {
      dispatch(showCreditGainAnimation(amount));
    }
    
    return newCredits;
  }
);
```

## API Integration

### Vendor API Service
```typescript
class VendorAPIService {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  async getVendor(vendorId: string): Promise<Vendor> {
    const response = await fetch(`${this.baseUrl}/vendors/${vendorId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch vendor');
    }
    return response.json();
  }
  
  async getVendorInventory(vendorId: string): Promise<VendorItem[]> {
    const response = await fetch(`${this.baseUrl}/vendors/${vendorId}/inventory`);
    if (!response.ok) {
      throw new Error('Failed to fetch vendor inventory');
    }
    return response.json();
  }
  
  async purchaseItem(vendorId: string, itemId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/vendors/${vendorId}/purchase`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ itemId })
    });
    
    if (!response.ok) {
      throw new Error('Failed to purchase item');
    }
  }
  
  async getVendorDialogue(vendorId: string, context: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/vendors/${vendorId}/dialogue?context=${context}`);
    if (!response.ok) {
      throw new Error('Failed to fetch vendor dialogue');
    }
    return response.json();
  }
}

export const vendorAPIService = new VendorAPIService(process.env.REACT_APP_API_URL!);
```

## Styled Components

```typescript
const VendorContainer = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
`;

const ShopEnvironment = styled.div<{ environment: ShopEnvironment }>`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: ${props => getEnvironmentBackground(props.environment)};
  opacity: 0.6;
`;

const VendorInterface = styled.div`
  position: relative;
  z-index: 1;
  max-width: 1400px;
  max-height: 900px;
  background: rgba(0, 0, 0, 0.95);
  border-radius: 12px;
  padding: 2rem;
  border: 2px solid ${props => props.theme.colors.primary};
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 2rem;
`;

const ItemGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  max-height: 600px;
  overflow-y: auto;
`;

const ItemCardContainer = styled.div<{ isSelected: boolean; rarity: string }>`
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

const HolographicContainer = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  height: 400px;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 12px;
  border: 2px solid ${props => props.theme.colors.accent};
  display: flex;
  flex-direction: column;
`;

const HolographicViewport = styled.div`
  flex: 1;
  position: relative;
  cursor: grab;
  
  &:active {
    cursor: grabbing;
  }
`;

const ItemThumbnail = styled.img`
  width: 64px;
  height: 64px;
  margin-bottom: 0.5rem;
  border-radius: 4px;
`;

const ItemName = styled.h3`
  color: ${props => props.theme.colors.text};
  margin: 0.5rem 0;
  font-size: 1rem;
`;

const ItemPrice = styled.div`
  color: ${props => props.theme.colors.accent};
  font-weight: bold;
  font-size: 0.9rem;
`;

const VendorComment = styled.p`
  color: ${props => props.theme.colors.textSecondary};
  font-size: 0.8rem;
  font-style: italic;
  margin-top: 0.5rem;
`;
```

## Performance Optimizations

### Model Caching
```typescript
class VendorModelCache {
  private cache = new Map<string, THREE.Group>();
  
  async getModel(modelPath: string): Promise<THREE.Group> {
    if (this.cache.has(modelPath)) {
      return this.cache.get(modelPath)!.clone();
    }
    
    const loader = new GLTFLoader();
    const model = await new Promise<THREE.Group>((resolve, reject) => {
      loader.load(modelPath, resolve, undefined, reject);
    });
    
    this.cache.set(modelPath, model);
    return model.clone();
  }
  
  preloadModels(modelPaths: string[]): void {
    modelPaths.forEach(path => {
      this.getModel(path).catch(console.error);
    });
  }
}
```

### Holographic Performance
```typescript
class HolographicPerformanceManager {
  private static instance: HolographicPerformanceManager;
  private frameRate: number = 60;
  private lastFrameTime: number = 0;
  
  static getInstance(): HolographicPerformanceManager {
    if (!HolographicPerformanceManager.instance) {
      HolographicPerformanceManager.instance = new HolographicPerformanceManager();
    }
    return HolographicPerformanceManager.instance;
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
const useVendorKeyboardNavigation = (items: VendorItem[], onSelect: (itemId: string) => void) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex(prev => (prev + 1) % items.length);
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex(prev => (prev - 1 + items.length) % items.length);
          break;
        case 'Enter':
        case ' ':
          event.preventDefault();
          onSelect(items[selectedIndex].id);
          break;
        case 'Escape':
          event.preventDefault();
          // Close vendor
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [items, selectedIndex, onSelect]);
  
  return selectedIndex;
};
```

## Testing Strategy

### Unit Tests
```typescript
describe('VendorScreen', () => {
  it('should render vendor items in grid', () => {
    const mockItems = [
      { id: '1', name: 'Blaster Rifle', price: 1000 },
      { id: '2', name: 'Vibrosword', price: 500 }
    ];
    
    render(<VendorScreen />);
    
    expect(screen.getByText('Blaster Rifle')).toBeInTheDocument();
    expect(screen.getByText('Vibrosword')).toBeInTheDocument();
  });
  
  it('should activate holographic display when item is selected', () => {
    const mockOnSelect = jest.fn();
    render(<ItemCard item={mockItem} onSelect={mockOnSelect} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(mockOnSelect).toHaveBeenCalledWith(mockItem.id);
  });
});
```

### Integration Tests
```typescript
describe('Vendor Integration', () => {
  it('should process purchase and update inventory', async () => {
    const { store } = renderWithProviders(<VendorScreen />);
    
    // Select and purchase item
    fireEvent.click(screen.getByText('Blaster Rifle'));
    fireEvent.click(screen.getByText('Purchase'));
    
    // Wait for async action to complete
    await waitFor(() => {
      const state = store.getState();
      expect(state.inventory.items).toContainEqual(
        expect.objectContaining({ name: 'Blaster Rifle' })
      );
      expect(state.character.credits).toBeLessThan(initialCredits);
    });
  });
});
```

## Success Metrics

1. **User Engagement**: Time spent in vendor screens vs. traditional menus
2. **Purchase Completion Rate**: Percentage of item selections that result in purchases
3. **Holographic Interaction**: Usage of rotation and zoom features
4. **Performance**: Frame rate during holographic rendering
5. **User Satisfaction**: Feedback on immersive shopping experience
6. **Accessibility**: Keyboard navigation usage and screen reader compatibility

This implementation plan transforms the shopping experience into an immersive, diegetic interface that feels like a real Star Wars universe interaction, while maintaining the technical excellence and accessibility standards established in the previous plans.
