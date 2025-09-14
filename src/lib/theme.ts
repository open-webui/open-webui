import type { Theme } from '$lib/types';
import { writable } from 'svelte/store';
import { get } from 'svelte/store';
import { page } from '$app/stores';
import { theme as themeStore, codeMirrorTheme } from '$lib/stores';
import variables from '$lib/themes/variables.json';
import { WEBUI_VERSION } from '$lib/constants';

export const currentThemeStore = writable<Theme | undefined>(undefined);
export const liveThemeStore = writable<Theme | undefined>(undefined);
export const communityThemes = writable<Map<string, Theme>>(new Map());

let currentTheme: Theme | undefined;
let currentStylesheet: HTMLStyleElement | undefined;
let currentResizeObserver: ResizeObserver | undefined;
let currentAnimation: Theme['animation'] | undefined;

const cleanupTheme = () => {
  // Always try to stop any running animation
  if (currentAnimation && typeof currentAnimation.stop === 'function') {
    currentAnimation.stop();
  }
  currentAnimation = undefined;

  // Always try to find and remove a theme canvas
  const canvas = document.querySelector(`[id$='-canvas']`);
  if (canvas) {
    canvas.remove();
  }

  // Always try to disconnect an observer
  if (currentResizeObserver) {
    currentResizeObserver.disconnect();
    currentResizeObserver = undefined;
  }

  // Remove old stylesheet
  if (currentStylesheet) {
    currentStylesheet.remove();
    currentStylesheet = undefined;
  }

  // Cleanup main container styles
  if (currentTheme) {
    const mainContainer = document.getElementById('main-container');
    if (mainContainer) {
      mainContainer.classList.remove(`${currentTheme.id}-bg`);
      mainContainer.style.backgroundImage = 'none';

      const gradientLayer = document.getElementById('theme-gradient-layer');
      if (gradientLayer) {
        gradientLayer.remove();
      }
    }
  }

  // Cleanup base class and CSS variables
  document.documentElement.classList.remove('light', 'dark', 'oled-dark', 'her');
  for (const variable of variables) {
    document.documentElement.style.removeProperty(variable.name);
  }
};

let onElementReadyInterval: NodeJS.Timeout | undefined = undefined;

const onElementReady = (selector: string, callback: () => void) => {
  if (onElementReadyInterval) {
    clearInterval(onElementReadyInterval);
  }

  const interval = setInterval(() => {
    const element = document.querySelector(selector);
    if (element) {
      clearInterval(interval);
      onElementReadyInterval = undefined;
      callback();
    }
  }, 50);
  onElementReadyInterval = interval;

  setTimeout(() => {
    if (onElementReadyInterval === interval) {
      clearInterval(interval);
      onElementReadyInterval = undefined;
    }
  }, 5000);
};


export const themes = writable<Map<string, Theme>>(
  new Map([
    ['system', { id: 'system', name: 'System', base: 'light', emoji: '⚙️', metaThemeColor: '#ffffff' }],
    [
      'dark',
      {
        id: 'dark',
        name: 'Dark',
        base: 'dark',
        emoji: '🌑',
        metaThemeColor: '#171717',
        variables: {
          '--color-gray-800': '#333',
          '--color-gray-850': '#262626',
          '--color-gray-900': '#171717',
          '--color-gray-950': '#0d0d0d'
        }
      }
    ],
    ['light', { id: 'light', name: 'Light', base: 'light', emoji: '☀️', metaThemeColor: '#ffffff' }],
    [
      'oled-dark',
      {
        id: 'oled-dark',
        name: 'OLED Dark',
        base: 'oled-dark',
        emoji: '🌃',
        metaThemeColor: '#000000',
        variables: {
          '--color-gray-800': '#000',
          '--color-gray-850': '#000',
          '--color-gray-900': '#000',
          '--color-gray-950': '#000'
        }
      }
    ],
    ['her', { id: 'her', name: 'Her', base: 'her', emoji: '🌷', metaThemeColor: '#983724' }]
  ])
);

export const loadCommunityThemes = () => {
  const themes = localStorage.getItem('communityThemes');
  if (themes) {
    communityThemes.set(new Map(Object.entries(JSON.parse(themes))));
  }
};

loadCommunityThemes();

const saveCommunityThemes = (themes: Map<string, Theme>) => {
  localStorage.setItem('communityThemes', JSON.stringify(Object.fromEntries(themes)));
};

export const addCommunityTheme = (theme: Theme) => {
  if (!theme.targetWebUIVersion) {
    theme.targetWebUIVersion = WEBUI_VERSION;
  }
  const newThemes = new Map(get(communityThemes));
  newThemes.set(theme.id, theme);
  communityThemes.set(newThemes);
  saveCommunityThemes(newThemes);
};

export const updateCommunityTheme = (theme: Theme) => {
  const newThemes = new Map(get(communityThemes));
  if (newThemes.has(theme.id)) {
    newThemes.set(theme.id, theme);
    communityThemes.set(newThemes);
    saveCommunityThemes(newThemes);
  }
};

export const removeCommunityTheme = (themeId: string) => {
  const currentThemeId = localStorage.getItem('theme');
  if (currentThemeId === themeId) {
    const themeToDelete = get(communityThemes).get(themeId);
    if (themeToDelete) {
      const baseTheme = themeToDelete.base ?? 'system';
      themeStore.set(baseTheme);
      localStorage.setItem('theme', baseTheme);
      applyTheme(baseTheme);
    }
  }

  const newThemes = new Map(get(communityThemes));
  newThemes.delete(themeId);
  communityThemes.set(newThemes);
  saveCommunityThemes(newThemes);
};

export const isNewerVersion = (oldVer: string, newVer: string) => {
  const oldParts = oldVer.split('.').map(Number);
  const newParts = newVer.split('.').map(Number);
  for (let i = 0; i < Math.max(oldParts.length, newParts.length); i++) {
    const oldPart = oldParts[i] || 0;
    const newPart = newParts[i] || 0;
    if (newPart > oldPart) return true;
    if (newPart < oldPart) return false;
  }
  return false;
};

export const checkForThemeUpdates = async () => {
  const themes = get(communityThemes);
  for (const [id, theme] of themes.entries()) {
    if (theme.sourceUrl && theme.version) {
      try {
        const res = await fetch(theme.sourceUrl);
        if (res.ok) {
          const latestTheme = await res.json();
          if (latestTheme.version && isNewerVersion(theme.version, latestTheme.version)) {
            toast.info(`A new version (v${latestTheme.version}) is available for the theme "${theme.name}".`, {
              duration: 10000
            });
          }
        }
      } catch (error) {
        console.error(`Failed to check for update for theme ${theme.name}:`, error);
      }
    }
  }
};

const _applyThemeStyles = (theme: Theme) => {
  console.log('Applying theme:', theme);
  if (theme.css && (!theme.toggles || theme.toggles.customCss)) {
    currentStylesheet = document.createElement('style');
    currentStylesheet.id = `${theme.id}-stylesheet`;
    currentStylesheet.innerHTML = theme.css;
    document.head.appendChild(currentStylesheet);
  }

  onElementReady('#main-container', () => {
    const mainContainer = document.getElementById('main-container');

    if (mainContainer) {

      // Handle Gradient
      if (
        theme.gradient &&
        (!theme.toggles || typeof theme.toggles.gradient === 'undefined' || theme.toggles.gradient) &&
        theme.gradient.enabled &&
        theme.gradient.colors.length > 0
      ) {
        const { colors, direction, intensity } = theme.gradient;
        const alpha = (intensity ?? 100) / 100;
        const rgbaColors = colors.map((hex) => {
          if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
            let c = hex.substring(1).split('');
            if (c.length === 3) {
              c = [c[0], c[0], c[1], c[1], c[2], c[2]];
            }
            c = '0x' + c.join('');
            const r = (c >> 16) & 255;
            const g = (c >> 8) & 255;
            const b = c & 255;
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
          }
          return `rgba(0, 0, 0, ${alpha})`;
        });
        const gradientCss = `linear-gradient(${direction}deg, ${rgbaColors.join(', ')})`;

        const gradientLayer = document.createElement('div');
        gradientLayer.id = 'theme-gradient-layer';
        gradientLayer.style.position = 'absolute';
        gradientLayer.style.top = '0';
        gradientLayer.style.left = '0';
        gradientLayer.style.width = '100%';
        gradientLayer.style.height = '100%';
        gradientLayer.style.zIndex = '3';
        gradientLayer.style.backgroundImage = gradientCss;
        mainContainer.prepend(gradientLayer);
      } else {
        mainContainer.style.backgroundImage = 'none';
      }

      mainContainer.classList.add(`${theme.id}-bg`);
      if (theme.animationScript && (!theme.toggles || theme.toggles.animationScript)) {
        const canvas = document.createElement('canvas');
        canvas.id = `${theme.id}-canvas`;
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.zIndex = '0';
        canvas.style.pointerEvents = 'none';
        canvas.style.opacity = '0';
        canvas.style.transition = 'opacity 0.5s ease-in-out';
        mainContainer.prepend(canvas);

        try {
          const blob = new Blob([theme.animationScript], { type: 'application/javascript' });
          const workerUrl = URL.createObjectURL(blob);
          const worker = new Worker(workerUrl);

          const offscreen = canvas.transferControlToOffscreen();

          const rect = mainContainer.getBoundingClientRect();
          worker.postMessage(
            { type: 'init', canvas: offscreen, width: rect.width, height: rect.height },
            [offscreen]
          );

          currentResizeObserver = new ResizeObserver((entries) => {
            if (entries.length > 0) {
              const entry = entries[0];
              worker.postMessage({
                type: 'resize',
                width: entry.contentRect.width,
                height: entry.contentRect.height
              });
            }
          });
          currentResizeObserver.observe(mainContainer);

          mainContainer.addEventListener('mousemove', (e) => {
            const rect = mainContainer.getBoundingClientRect();
            worker.postMessage({
              type: 'mousemove',
              x: e.clientX - rect.left,
              y: e.clientY - rect.top
            });
          });

          currentAnimation = {
            start: () => {},
            stop: () => {
              worker.terminate();
              URL.revokeObjectURL(workerUrl);
              if (currentResizeObserver) {
                currentResizeObserver.disconnect();
              }
            }
          };
        } catch (e) {
          console.error('Failed to start animation worker:', e);
        }

        setTimeout(() => {
          window.dispatchEvent(new Event('resize'));
          canvas.style.opacity = '1';
        }, 100);
      } else if (theme.animation && typeof theme.animation.start === 'function') {
        const canvas = document.createElement('canvas');
        canvas.id = `${theme.id}-canvas`;
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.zIndex = '0';
        canvas.style.pointerEvents = 'none';
        canvas.style.opacity = '0';
        canvas.style.transition = 'opacity 0.5s ease-in-out';
        mainContainer.prepend(canvas);

        currentAnimation = theme.animation;
        currentAnimation.start(canvas);

        setTimeout(() => {
          window.dispatchEvent(new Event('resize'));
          canvas.style.opacity = '1';
        }, 100);
      }
    }
  });

  let resolvedBase = theme.base;
  if (theme.id === 'system' || theme.base === 'system') {
    resolvedBase = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  // Apply variables from base theme
  const allThemes = new Map([...get(themes), ...get(communityThemes)]);
  const baseThemeObject = allThemes.get(resolvedBase);
  if (baseThemeObject?.variables) {
    for (const [key, value] of Object.entries(baseThemeObject.variables)) {
      document.documentElement.style.setProperty(key, value);
    }
  }

  // Apply variables from current theme (override base)
  if (theme.variables && (!theme.toggles || theme.toggles.cssVariables)) {
    for (const [key, value] of Object.entries(theme.variables)) {
      document.documentElement.style.setProperty(key, value);
    }
  }

  // Apply classes
  if (resolvedBase === 'light' || resolvedBase === 'her') {
    document.documentElement.classList.add('light');
  } else {
    document.documentElement.classList.add('dark');
  }

  if (resolvedBase === 'oled-dark') {
    document.documentElement.classList.add('oled-dark');
  }

  if (resolvedBase === 'her') {
    document.documentElement.classList.add('her');
  }

  const metaThemeColorEl = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColorEl) {
    if (theme.id === 'system') {
      const systemThemeName = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      const systemTheme = get(themes).get(systemThemeName);
      metaThemeColorEl.setAttribute('content', systemTheme?.metaThemeColor ?? '#ffffff');
    } else {
      metaThemeColorEl.setAttribute('content', theme.metaThemeColor ?? '#ffffff');
    }
  }
};

export const applyTheme = async (themeInput: string | Theme, isLiveUpdate = false) => {
  cleanupTheme();

  // Reset codemirror theme to default
  codeMirrorTheme.set('one-dark');

  let theme: Theme | undefined;
  if (typeof themeInput === 'string') {
    theme = get(themes).get(themeInput) ?? get(communityThemes).get(themeInput);
  } else {
    theme = themeInput;
  }

  if (!theme) {
    return;
  }

  const themeToApply = { ...theme };

  if (themeToApply.toggles && !themeToApply.toggles.tsParticles) {
    themeToApply.tsparticlesConfig = undefined;
  } else if (themeToApply.tsparticlesConfig) {
    themeToApply.tsparticlesConfig.fpsLimit = 120;
    themeToApply.tsparticlesConfig.pauseOnBlur = true;
    themeToApply.tsparticlesConfig.pauseOnOutsideViewport = true;
    themeToApply.tsparticlesConfig.interactivity = {
      ...themeToApply.tsparticlesConfig.interactivity,
      events: {
        ...themeToApply.tsparticlesConfig.interactivity?.events,
        onClick: {
          ...themeToApply.tsparticlesConfig.interactivity?.events?.onClick,
          enable: false
        }
      }
    };
  }

  // Update currentTheme for cleanup purposes, even on live updates
  currentTheme = themeToApply;
  liveThemeStore.set(currentTheme);

  if (!isLiveUpdate) {
    currentThemeStore.set(currentTheme);
  }

  _applyThemeStyles(themeToApply);

  if (themeToApply.codeMirrorTheme) {
    codeMirrorTheme.set(themeToApply.codeMirrorTheme);
  }

  if (typeof window !== 'undefined' && window.applyTheme) {
    window.applyTheme();
  }
};
