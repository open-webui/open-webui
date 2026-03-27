import { writable } from 'svelte/store';

export const initialCollabState = {
  enabled: false,
  mode: 'idle',
  ribbonExpanded: false,
  phase: 'idle',
  overallProgress: 0,
  edge: {
    progress: 0,
    status: ''
  },
  cloud: {
    progress: 0,
    status: ''
  },
  split: {},
  network: {},
  error: null
};

export const collabState = writable({ ...initialCollabState });

export function resetCollabState() {
  collabState.set({ ...initialCollabState });
}

export function toggleCollabRibbon() {
  collabState.update((state) => ({
    ...state,
    ribbonExpanded: !state.ribbonExpanded
  }));
}

export function setCollabRibbonExpanded(value: boolean) {
  collabState.update((state) => ({
    ...state,
    ribbonExpanded: value
  }));
}

export function startMockCollabPreparation() {
  let progress = 0;

  collabState.set({
    ...initialCollabState,
    enabled: true,
    mode: 'prepare',
    ribbonExpanded: true,
    phase: 'preparing',
    overallProgress: 0
  });

  const timer = setInterval(() => {
    progress += 10;

    collabState.update((state) => ({
      ...state,
      overallProgress: progress,
      edge: {
        ...state.edge,
        progress: Math.min(progress + 10, 100),
        status: '边端准备中'
      },
      cloud: {
        ...state.cloud,
        progress: progress,
        status: '云端准备中'
      },
      phase: progress >= 100 ? 'completed' : 'preparing'
    }));

    if (progress >= 100) {
  clearInterval(timer);

  setTimeout(() => {
    collabState.update((state) => ({
      ...state,
      ribbonExpanded: false
    }));
  }, 800);
}
  }, 300);
}

export function applyCollabEvent(event: any) {
  collabState.update((state) => ({
    ...state,
    ...event
  }));
}