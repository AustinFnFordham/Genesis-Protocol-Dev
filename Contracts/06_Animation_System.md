# Animation System Implementation Plan

## Overview
This document outlines the implementation of a comprehensive animation system that provides smooth, performant visual feedback across all UI components, enhancing the user experience with Star Wars-themed animations and effects.

## Animation Architecture

### Core Animation System
```typescript
interface AnimationConfig {
  id: string;
  type: 'fade' | 'slide' | 'scale' | 'rotate' | 'particle' | 'energy' | 'custom';
  duration: number;
  easing: string;
  delay?: number;
  repeat?: number;
  yoyo?: boolean;
  onComplete?: () => void;
  onUpdate?: (progress: number) => void;
}

interface AnimationState {
  activeAnimations: Map<string, AnimationConfig>;
  queuedAnimations: AnimationConfig[];
  globalSettings: {
    enabled: boolean;
    performanceMode: 'high' | 'medium' | 'low';
    reducedMotion: boolean;
  };
}

class AnimationManager {
  private static instance: AnimationManager;
  private state: AnimationState;
  private gsap: typeof gsap;
  
  private constructor() {
    this.state = {
      activeAnimations: new Map(),
      queuedAnimations: [],
      globalSettings: {
        enabled: true,
        performanceMode: 'high',
        reducedMotion: false,
      },
    };
    
    this.setupGSAP();
    this.setupPerformanceMonitoring();
  }
  
  static getInstance(): AnimationManager {
    if (!AnimationManager.instance) {
      AnimationManager.instance = new AnimationManager();
    }
    return AnimationManager.instance;
  }
  
  private setupGSAP() {
    // Configure GSAP with performance optimizations
    gsap.config({
      nullTargetWarn: false,
      autoSleep: 60,
      force3D: true,
    });
    
    // Register custom easing functions
    gsap.registerEase('forceIn', [0.25, 0.46, 0.45, 0.94]);
    gsap.registerEase('forceOut', [0.55, 0.055, 0.675, 0.19]);
    gsap.registerEase('lightsaber', [0.68, -0.55, 0.265, 1.55]);
  }
  
  private setupPerformanceMonitoring() {
    // Monitor frame rate and adjust animation quality
    let frameCount = 0;
    let lastTime = performance.now();
    
    const monitorPerformance = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime - lastTime >= 1000) {
        const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        
        if (fps < 30) {
          this.state.globalSettings.performanceMode = 'low';
        } else if (fps < 50) {
          this.state.globalSettings.performanceMode = 'medium';
        } else {
          this.state.globalSettings.performanceMode = 'high';
        }
        
        frameCount = 0;
        lastTime = currentTime;
      }
      
      requestAnimationFrame(monitorPerformance);
    };
    
    requestAnimationFrame(monitorPerformance);
  }
  
  play(config: AnimationConfig): Promise<void> {
    return new Promise((resolve) => {
      if (!this.state.globalSettings.enabled) {
        resolve();
        return;
      }
      
      const element = document.querySelector(`[data-animation-id="${config.id}"]`);
      if (!element) {
        resolve();
        return;
      }
      
      const timeline = gsap.timeline({
        onComplete: () => {
          this.state.activeAnimations.delete(config.id);
          config.onComplete?.();
          resolve();
        },
        onUpdate: config.onUpdate,
      });
      
      this.state.activeAnimations.set(config.id, config);
      
      switch (config.type) {
        case 'fade':
          this.playFadeAnimation(timeline, element, config);
          break;
        case 'slide':
          this.playSlideAnimation(timeline, element, config);
          break;
        case 'scale':
          this.playScaleAnimation(timeline, element, config);
          break;
        case 'particle':
          this.playParticleAnimation(timeline, element, config);
          break;
        case 'energy':
          this.playEnergyAnimation(timeline, element, config);
          break;
        case 'custom':
          this.playCustomAnimation(timeline, element, config);
          break;
      }
    });
  }
  
  private playFadeAnimation(timeline: gsap.core.Timeline, element: Element, config: AnimationConfig) {
    timeline.fromTo(element, 
      { opacity: 0 },
      { 
        opacity: 1, 
        duration: config.duration,
        ease: config.easing,
        delay: config.delay,
      }
    );
  }
  
  private playSlideAnimation(timeline: gsap.core.Timeline, element: Element, config: AnimationConfig) {
    timeline.fromTo(element,
      { x: -100, opacity: 0 },
      {
        x: 0,
        opacity: 1,
        duration: config.duration,
        ease: config.easing,
        delay: config.delay,
      }
    );
  }
  
  private playScaleAnimation(timeline: gsap.core.Timeline, element: Element, config: AnimationConfig) {
    timeline.fromTo(element,
      { scale: 0, opacity: 0 },
      {
        scale: 1,
        opacity: 1,
        duration: config.duration,
        ease: config.easing,
        delay: config.delay,
      }
    );
  }
}
```

## Star Wars Themed Animations

### Lightsaber Effects
```typescript
class LightsaberAnimations {
  static ignite(element: HTMLElement, color: string = '#4A90E2') {
    const blade = element.querySelector('.lightsaber-blade');
    const hilt = element.querySelector('.lightsaber-hilt');
    
    if (!blade || !hilt) return;
    
    // Create ignition effect
    const ignitionEffect = document.createElement('div');
    ignitionEffect.className = 'ignition-effect';
    ignitionEffect.style.cssText = `
      position: absolute;
      width: 100%;
      height: 100%;
      background: radial-gradient(circle, ${color} 0%, transparent 70%);
      opacity: 0;
      pointer-events: none;
    `;
    
    element.appendChild(ignitionEffect);
    
    // Animate ignition
    gsap.timeline()
      .set(blade, { scaleY: 0, opacity: 0 })
      .set(hilt, { rotation: -45 })
      .to(ignitionEffect, {
        opacity: 1,
        scale: 1.5,
        duration: 0.2,
        ease: 'power2.out',
      })
      .to(ignitionEffect, {
        opacity: 0,
        scale: 2,
        duration: 0.3,
        ease: 'power2.in',
      }, '-=0.1')
      .to(blade, {
        scaleY: 1,
        opacity: 1,
        duration: 0.4,
        ease: 'lightsaber',
      }, '-=0.2')
      .to(hilt, {
        rotation: 0,
        duration: 0.3,
        ease: 'forceOut',
      }, '-=0.3')
      .call(() => ignitionEffect.remove());
  }
  
  static extinguish(element: HTMLElement) {
    const blade = element.querySelector('.lightsaber-blade');
    const hilt = element.querySelector('.lightsaber-hilt');
    
    if (!blade || !hilt) return;
    
    gsap.timeline()
      .to(blade, {
        scaleY: 0,
        opacity: 0,
        duration: 0.3,
        ease: 'power2.in',
      })
      .to(hilt, {
        rotation: -45,
        duration: 0.2,
        ease: 'forceIn',
      }, '-=0.2');
  }
  
  static swing(element: HTMLElement, direction: 'left' | 'right' | 'up' | 'down') {
    const rotations = {
      left: -45,
      right: 45,
      up: -30,
      down: 30,
    };
    
    gsap.timeline()
      .to(element, {
        rotation: rotations[direction],
        duration: 0.2,
        ease: 'power2.out',
      })
      .to(element, {
        rotation: 0,
        duration: 0.3,
        ease: 'forceOut',
      });
  }
}
```

### Force Power Animations
```typescript
class ForceAnimations {
  static forcePush(element: HTMLElement, target: HTMLElement) {
    // Create force wave effect
    const forceWave = document.createElement('div');
    forceWave.className = 'force-wave';
    forceWave.style.cssText = `
      position: absolute;
      width: 100px;
      height: 100px;
      border: 2px solid #4A90E2;
      border-radius: 50%;
      opacity: 0;
      pointer-events: none;
    `;
    
    document.body.appendChild(forceWave);
    
    const elementRect = element.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    
    gsap.set(forceWave, {
      x: elementRect.left + elementRect.width / 2,
      y: elementRect.top + elementRect.height / 2,
    });
    
    gsap.timeline()
      .to(forceWave, {
        scale: 3,
        opacity: 1,
        duration: 0.3,
        ease: 'power2.out',
      })
      .to(forceWave, {
        x: targetRect.left + targetRect.width / 2,
        y: targetRect.top + targetRect.height / 2,
        scale: 1,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.in',
      })
      .to(target, {
        x: targetRect.left + 100,
        duration: 0.3,
        ease: 'power2.out',
      }, '-=0.3')
      .call(() => forceWave.remove());
  }
  
  static forceLightning(element: HTMLElement, target: HTMLElement) {
    // Create lightning effect
    const lightning = document.createElement('div');
    lightning.className = 'force-lightning';
    lightning.style.cssText = `
      position: absolute;
      width: 4px;
      height: 100px;
      background: linear-gradient(to bottom, #BD10E0, #4A90E2);
      opacity: 0;
      pointer-events: none;
      filter: blur(1px);
    `;
    
    document.body.appendChild(lightning);
    
    const elementRect = element.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    
    gsap.set(lightning, {
      x: elementRect.left + elementRect.width / 2,
      y: elementRect.top + elementRect.height / 2,
      rotation: Math.atan2(
        targetRect.top - elementRect.top,
        targetRect.left - elementRect.left
      ) * 180 / Math.PI,
    });
    
    gsap.timeline()
      .to(lightning, {
        opacity: 1,
        scaleY: 1,
        duration: 0.1,
        ease: 'power2.out',
      })
      .to(lightning, {
        scaleY: 0,
        opacity: 0,
        duration: 0.1,
        ease: 'power2.in',
      })
      .to(target, {
        scale: 1.1,
        duration: 0.1,
        ease: 'power2.out',
      }, '-=0.1')
      .to(target, {
        scale: 1,
        duration: 0.1,
        ease: 'power2.in',
      })
      .call(() => lightning.remove());
  }
  
  static mindTrick(element: HTMLElement, target: HTMLElement) {
    // Create mind trick effect
    const mindEffect = document.createElement('div');
    mindEffect.className = 'mind-trick-effect';
    mindEffect.style.cssText = `
      position: absolute;
      width: 50px;
      height: 50px;
      background: radial-gradient(circle, #9B59B6 0%, transparent 70%);
      opacity: 0;
      pointer-events: none;
      border-radius: 50%;
    `;
    
    document.body.appendChild(mindEffect);
    
    const targetRect = target.getBoundingClientRect();
    
    gsap.set(mindEffect, {
      x: targetRect.left + targetRect.width / 2,
      y: targetRect.top + targetRect.height / 2,
    });
    
    gsap.timeline()
      .to(mindEffect, {
        scale: 2,
        opacity: 1,
        duration: 0.3,
        ease: 'power2.out',
      })
      .to(mindEffect, {
        scale: 0,
        opacity: 0,
        duration: 0.3,
        ease: 'power2.in',
      })
      .to(target, {
        rotation: 360,
        duration: 0.6,
        ease: 'power2.inOut',
      }, '-=0.6')
      .call(() => mindEffect.remove());
  }
}
```

## UI Component Animations

### Page Transitions
```typescript
class PageTransitionAnimations {
  static slideInFromRight(element: HTMLElement) {
    gsap.fromTo(element,
      { x: '100%', opacity: 0 },
      {
        x: '0%',
        opacity: 1,
        duration: 0.5,
        ease: 'forceOut',
      }
    );
  }
  
  static slideInFromLeft(element: HTMLElement) {
    gsap.fromTo(element,
      { x: '-100%', opacity: 0 },
      {
        x: '0%',
        opacity: 1,
        duration: 0.5,
        ease: 'forceOut',
      }
    );
  }
  
  static fadeIn(element: HTMLElement) {
    gsap.fromTo(element,
      { opacity: 0, scale: 0.95 },
      {
        opacity: 1,
        scale: 1,
        duration: 0.4,
        ease: 'forceOut',
      }
    );
  }
  
  static slideOutToRight(element: HTMLElement): Promise<void> {
    return new Promise((resolve) => {
      gsap.to(element, {
        x: '100%',
        opacity: 0,
        duration: 0.5,
        ease: 'forceIn',
        onComplete: resolve,
      });
    });
  }
}
```

### Card Animations
```typescript
class CardAnimations {
  static dealCard(element: HTMLElement, index: number, total: number) {
    gsap.set(element, {
      x: -200,
      y: -100,
      rotation: -45,
      opacity: 0,
    });
    
    gsap.to(element, {
      x: 0,
      y: 0,
      rotation: 0,
      opacity: 1,
      duration: 0.6,
      delay: index * 0.1,
      ease: 'forceOut',
    });
  }
  
  static flipCard(element: HTMLElement) {
    const front = element.querySelector('.card-front');
    const back = element.querySelector('.card-back');
    
    if (!front || !back) return;
    
    gsap.timeline()
      .to(element, {
        rotationY: 90,
        duration: 0.3,
        ease: 'power2.in',
      })
      .set(front, { opacity: 0 })
      .set(back, { opacity: 1 })
      .to(element, {
        rotationY: 0,
        duration: 0.3,
        ease: 'power2.out',
      });
  }
  
  static hoverCard(element: HTMLElement) {
    gsap.to(element, {
      scale: 1.05,
      y: -10,
      duration: 0.2,
      ease: 'power2.out',
    });
  }
  
  static unhoverCard(element: HTMLElement) {
    gsap.to(element, {
      scale: 1,
      y: 0,
      duration: 0.2,
      ease: 'power2.out',
    });
  }
}
```

### Progression Tree Animations
```typescript
class ProgressionTreeAnimations {
  static unlockNode(element: HTMLElement, theme: ClassTheme) {
    // Create unlock effect
    const unlockEffect = document.createElement('div');
    unlockEffect.className = 'unlock-effect';
    unlockEffect.style.cssText = `
      position: absolute;
      width: 100%;
      height: 100%;
      border: 2px solid ${theme.colorPalette.primary};
      border-radius: 50%;
      opacity: 0;
      pointer-events: none;
    `;
    
    element.appendChild(unlockEffect);
    
    gsap.timeline()
      .to(unlockEffect, {
        scale: 1.5,
        opacity: 1,
        duration: 0.3,
        ease: 'power2.out',
      })
      .to(unlockEffect, {
        scale: 0,
        opacity: 0,
        duration: 0.3,
        ease: 'power2.in',
      })
      .to(element, {
        scale: 1.2,
        duration: 0.2,
        ease: 'power2.out',
      }, '-=0.3')
      .to(element, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.in',
      })
      .call(() => unlockEffect.remove());
  }
  
  static connectNodes(fromElement: HTMLElement, toElement: HTMLElement, theme: ClassTheme) {
    // Create connection line
    const connection = document.createElement('div');
    connection.className = 'node-connection';
    connection.style.cssText = `
      position: absolute;
      height: 2px;
      background: ${theme.nodeConnections};
      opacity: 0;
      pointer-events: none;
      transform-origin: left center;
    `;
    
    document.body.appendChild(connection);
    
    const fromRect = fromElement.getBoundingClientRect();
    const toRect = toElement.getBoundingClientRect();
    
    const distance = Math.sqrt(
      Math.pow(toRect.left - fromRect.left, 2) + 
      Math.pow(toRect.top - fromRect.top, 2)
    );
    
    const angle = Math.atan2(
      toRect.top - fromRect.top,
      toRect.left - fromRect.left
    ) * 180 / Math.PI;
    
    gsap.set(connection, {
      x: fromRect.left + fromRect.width / 2,
      y: fromRect.top + fromRect.height / 2,
      width: 0,
      rotation: angle,
    });
    
    gsap.timeline()
      .to(connection, {
        width: distance,
        opacity: 1,
        duration: 0.5,
        ease: 'power2.out',
      })
      .to(connection, {
        opacity: 0.7,
        duration: 0.2,
        ease: 'power2.in',
      });
  }
}
```

## Performance Optimizations

### Animation Pooling
```typescript
class AnimationPool {
  private pools: Map<string, HTMLElement[]> = new Map();
  private maxPoolSize = 20;
  
  getElement(type: string): HTMLElement {
    if (!this.pools.has(type)) {
      this.pools.set(type, []);
    }
    
    const pool = this.pools.get(type)!;
    
    if (pool.length > 0) {
      return pool.pop()!;
    }
    
    return this.createElement(type);
  }
  
  returnElement(element: HTMLElement, type: string) {
    if (!this.pools.has(type)) {
      this.pools.set(type, []);
    }
    
    const pool = this.pools.get(type)!;
    
    if (pool.length < this.maxPoolSize) {
      // Reset element state
      element.style.cssText = '';
      element.className = '';
      pool.push(element);
    } else {
      element.remove();
    }
  }
  
  private createElement(type: string): HTMLElement {
    const element = document.createElement('div');
    element.className = `animation-element ${type}`;
    return element;
  }
}
```

### Reduced Motion Support
```typescript
class AccessibilityAnimations {
  static checkReducedMotion(): boolean {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  
  static getAccessibleDuration(baseDuration: number): number {
    if (this.checkReducedMotion()) {
      return Math.min(baseDuration * 0.5, 0.3);
    }
    return baseDuration;
  }
  
  static getAccessibleEasing(baseEasing: string): string {
    if (this.checkReducedMotion()) {
      return 'power2.out';
    }
    return baseEasing;
  }
}
```

## Integration with React Components

### Animation Hooks
```typescript
const useAnimation = () => {
  const animationManager = AnimationManager.getInstance();
  
  const animate = useCallback((config: AnimationConfig) => {
    return animationManager.play(config);
  }, []);
  
  const animateIn = useCallback((elementRef: RefObject<HTMLElement>, type: string = 'fade') => {
    if (elementRef.current) {
      elementRef.current.setAttribute('data-animation-id', `animate-in-${Date.now()}`);
      
      return animate({
        id: `animate-in-${Date.now()}`,
        type: type as any,
        duration: 0.4,
        easing: 'forceOut',
      });
    }
  }, [animate]);
  
  const animateOut = useCallback((elementRef: RefObject<HTMLElement>, type: string = 'fade') => {
    if (elementRef.current) {
      elementRef.current.setAttribute('data-animation-id', `animate-out-${Date.now()}`);
      
      return animate({
        id: `animate-out-${Date.now()}`,
        type: type as any,
        duration: 0.3,
        easing: 'forceIn',
      });
    }
  }, [animate]);
  
  return { animate, animateIn, animateOut };
};
```

This animation system provides a comprehensive, performant solution for creating engaging visual feedback across all UI components while maintaining accessibility and performance standards.
