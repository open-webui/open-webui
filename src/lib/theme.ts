import type { Theme } from '$lib/types';
import { writable } from 'svelte/store';
import { get } from 'svelte/store';
import { theme as themeStore, codeMirrorTheme } from '$lib/stores';
import variables from '$lib/themes/variables.json';
import { WEBUI_VERSION } from '$lib/constants';

export const currentThemeStore = writable<Theme | undefined>(undefined);
export const liveThemeStore = writable<Theme | undefined>(undefined);
export const communityThemes = writable<Map<string, Theme>>(new Map());

declare global {
  interface Window {
    particlesJS: any;
    pJSDom: any[];
  }
}

const initParticlesJS = (config: any) => {
  let retries = 0;
  const maxRetries = 10;
  const interval = 200; // ms

  const tryInit = () => {
    if (typeof window.particlesJS !== 'undefined') {
      window.particlesJS('particles-js', config);
    } else if (retries < maxRetries) {
      retries++;
      setTimeout(tryInit, interval);
    } else {
      console.error('particles.js failed to load after multiple retries.');
    }
  };

  tryInit();
};

const startParticlesJS = (mainContainer: HTMLElement, theme: any) => {
  const particlesDiv = document.createElement('div');
  particlesDiv.id = 'particles-js';
  particlesDiv.style.position = 'absolute';
  particlesDiv.style.top = '0';
  particlesDiv.style.left = '0';
  particlesDiv.style.width = '100%';
  particlesDiv.style.height = '100%';
  particlesDiv.style.zIndex = '0';
  particlesDiv.style.pointerEvents = 'none';
  particlesDiv.style.opacity = '0';
  particlesDiv.style.transition = 'opacity 0.5s ease-in-out';
  mainContainer.prepend(particlesDiv);

  // Deep copy the theme object to avoid modifying the original
  const themeCopy = JSON.parse(JSON.stringify(theme));

  // Handle 8-digit hex colors with alpha channel
  if (
    themeCopy.particles?.color?.value &&
    typeof themeCopy.particles.color.value === 'string' &&
    themeCopy.particles.color.value.length === 9 &&
    themeCopy.particles.color.value.startsWith('#')
  ) {
    const hexColor = themeCopy.particles.color.value;
    const alpha = parseInt(hexColor.slice(7, 9), 16) / 255;
    themeCopy.particles.color.value = hexColor.slice(0, 7);
    if (themeCopy.particles.opacity) {
      themeCopy.particles.opacity.value = alpha;
    } else {
      themeCopy.particles.opacity = { value: alpha };
    }
  }

  themeCopy.interactivity = {
    ...themeCopy.interactivity,
    events: {
      ...themeCopy.interactivity?.events,
      onclick: {
        ...themeCopy.interactivity?.events?.onclick,
        enable: false
      }
    }
  };

  initParticlesJS(themeCopy);
};

const stopParticlesJS = () => {
  if (window.pJSDom && window.pJSDom.length > 0) {
    window.pJSDom[0].pJS.fn.vendors.destroypJS();
    window.pJSDom = [];
  }
  const particlesDiv = document.getElementById('particles-js');
  if (particlesDiv) particlesDiv.remove();
};

let currentTheme: Theme | undefined;
let currentStylesheet: HTMLStyleElement | undefined;
let currentResizeObserver: ResizeObserver | undefined;

const cleanupTheme = () => {
  if (currentTheme) {
    // Cleanup animations and particles
    if (currentResizeObserver) {
      currentResizeObserver.disconnect();
      currentResizeObserver = undefined;
    }
    if (currentTheme.animation && typeof currentTheme.animation.stop === 'function') {
      currentTheme.animation.stop();
      const canvas = document.getElementById(`${currentTheme.id}-canvas`);
      if (canvas) canvas.remove();
    }
    if (currentTheme.particleConfig) {
      stopParticlesJS();
    }
    if (currentStylesheet) {
      currentStylesheet.remove();
      currentStylesheet = undefined;
    }
    const mainContainer = document.getElementById('main-container');
    if (mainContainer) {
      mainContainer.classList.remove(`${currentTheme.id}-bg`);
    }

    // Cleanup base class and CSS variables
    document.documentElement.classList.remove('light', 'dark', 'oled-dark', 'her');
    for (const variable of variables) {
      document.documentElement.style.removeProperty(variable.name);
    }
  }
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
  const mainContainer = document.getElementById('main-container');

  if (theme.css) {
    currentStylesheet = document.createElement('style');
    currentStylesheet.id = `${theme.id}-stylesheet`;
    currentStylesheet.innerHTML = theme.css;
    document.head.appendChild(currentStylesheet);
  }

  if (mainContainer) {
    mainContainer.classList.add(`${theme.id}-bg`);
    if (theme.particleConfig && Object.keys(theme.particleConfig).length > 0) {
      startParticlesJS(mainContainer, theme.particleConfig);
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
        const particlesDiv = document.getElementById('particles-js');
        if (particlesDiv) particlesDiv.style.opacity = '1';
      }, 100);
    } else if (theme.animationScript) {
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

        theme.animation = {
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
    } else if (theme.animation) {
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
      theme.animation.start(canvas);
      setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
        canvas.style.opacity = '1';
      }, 100);
    }
  }

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
  if (theme.variables) {
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

  let theme: Theme | undefined;
  if (typeof themeInput === 'string') {
    theme = get(themes).get(themeInput) ?? get(communityThemes).get(themeInput);
  } else {
    theme = themeInput;
  }

  if (!theme) {
    return;
  }

  if (theme.tsparticlesConfig) {
    theme.tsparticlesConfig.interactivity = {
      ...theme.tsparticlesConfig.interactivity,
      events: {
        ...theme.tsparticlesConfig.interactivity?.events,
        onClick: {
          ...theme.tsparticlesConfig.interactivity?.events?.onClick,
          enable: false,
        },
      },
    };
  }

  // Update currentTheme for cleanup purposes, even on live updates
  currentTheme = theme;
  liveThemeStore.set(currentTheme);

  if (!isLiveUpdate) {
    currentThemeStore.set(currentTheme);
  }

  _applyThemeStyles(theme);

  if (theme.codeMirrorTheme) {
    codeMirrorTheme.set(theme.codeMirrorTheme);
  }

  if (typeof window !== 'undefined' && window.applyTheme) {
    window.applyTheme();
  }
};
