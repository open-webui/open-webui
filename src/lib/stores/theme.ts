/**
 * @file This module contains all the Svelte stores related to the theming system.
 * It serves as the single source of truth for the theme state.
 */

import type { Theme } from '$lib/types';
import { writable } from 'svelte/store';
import defaultThemes from '$lib/themes/default.json';

// Main theme stores
export const themes = writable<Map<string, Theme>>(new Map(Object.entries(defaultThemes)));
export const communityThemes = writable<Map<string, Theme>>(new Map());

// Live theme stores
export const currentThemeStore = writable<Theme | undefined>(undefined);
export const liveThemeStore = writable<Theme | undefined>(undefined);

// Theme update stores
export const themeUpdates = writable<Map<string, Theme>>(new Map());
export const themeUpdateErrors = writable<Map<string, string>>(new Map());
