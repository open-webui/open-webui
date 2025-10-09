// src/lib/stores/ttsStore.js
import { writable } from 'svelte/store';

// This store will hold the HTMLAudioElement instance that is currently playing.
export const activeTTSAudio = writable(null);