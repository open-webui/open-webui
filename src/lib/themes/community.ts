/**
 * @file This module handles all logic related to community themes.
 * This includes loading themes from local storage, adding, updating,
 * and removing them, as well as checking for updates from remote sources.
 */

import type { Theme } from '$lib/types';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { WEBUI_VERSION } from '$lib/constants';

import { communityThemes, themeUpdates, themeUpdateErrors, themes } from '$lib/stores/theme';
import { theme as themeStore } from '$lib/stores';
import { applyTheme } from '$lib/themes/apply';

export const loadCommunityThemes = () => {
	const themes = localStorage.getItem('communityThemes');
	if (themes) {
		communityThemes.set(new Map(Object.entries(JSON.parse(themes))));
	}
};

loadCommunityThemes();

const saveCommunityThemes = (themes: Map<string, Theme>): boolean => {
	try {
		localStorage.setItem('communityThemes', JSON.stringify(Object.fromEntries(themes)));
		return true;
	} catch (e) {
		if (e instanceof DOMException && e.name === 'QuotaExceededError') {
			toast.error('Storage quota exceeded. Please remove some themes to free up space.');
		} else {
			toast.error('An unknown error occurred while saving themes.');
		}
		return false;
	}
};

export const addCommunityTheme = (theme: Theme): boolean => {
	if (!theme.targetWebUIVersion) {
		theme.targetWebUIVersion = WEBUI_VERSION;
	}
	const originalThemes = get(communityThemes);
	const newThemes = new Map(originalThemes);
	newThemes.set(theme.id, theme);
	communityThemes.set(newThemes);

	const success = saveCommunityThemes(newThemes);

	if (!success) {
		communityThemes.set(originalThemes);
	}
	return success;
};

export const updateCommunityTheme = (theme: Theme): boolean => {
	const originalThemes = get(communityThemes);
	if (originalThemes.has(theme.id)) {
		const newThemes = new Map(originalThemes);
		newThemes.set(theme.id, theme);
		communityThemes.set(newThemes);

		const success = saveCommunityThemes(newThemes);

		if (!success) {
			communityThemes.set(originalThemes);
		}
		return success;
	}
	return false;
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

	communityThemes.update((themes) => {
		themes.delete(themeId);
		return themes;
	});
	saveCommunityThemes(get(communityThemes));
};

const _fetchTheme = async (url: string): Promise<[Theme | null, string | null]> => {
	try {
		const res = await fetch(url);
		if (!res.ok) {
			const errorText = `${res.status} ${res.statusText}`;
			console.error(`Failed to fetch theme from ${url}: ${errorText}`);
			return [null, errorText];
		}
		const theme = await res.json();
		return [theme, null];
	} catch (error) {
		console.error(`Failed to fetch theme from ${url}:`, error);
		return [null, error.message];
	}
};

export const updateCommunityThemeFromUrl = async (theme: Theme) => {
	if (!theme.sourceUrl) {
		toast.error(`Theme "${theme.name}" does not have a source URL.`);
		return;
	}

	const [latestTheme, error] = await _fetchTheme(theme.sourceUrl);

	if (latestTheme) {
		const existingTheme = get(communityThemes).get(theme.id);
		if (existingTheme?.toggles) {
			latestTheme.toggles = { ...existingTheme.toggles, ...(latestTheme.toggles ?? {}) };
		}

		updateCommunityTheme(latestTheme);
		toast.success(`Theme "${theme.name}" updated successfully to v${latestTheme.version}!`);

		const currentThemeId = localStorage.getItem('theme');
		if (currentThemeId === theme.id) {
			applyTheme(latestTheme);
		}

		const updates = get(themeUpdates);
		updates.delete(theme.id);
		themeUpdates.set(updates);
	} else {
		toast.error(`Failed to update theme "${theme.name}": ${error}`);
	}
};

export const retryThemeUpdateCheck = async (theme: Theme) => {
	if (!theme.sourceUrl) {
		toast.error(`Theme "${theme.name}" does not have a source URL.`);
		return;
	}

	const [latestTheme, error] = await _fetchTheme(theme.sourceUrl);

	if (latestTheme) {
		// Clear the error for this theme
		const errors = get(themeUpdateErrors);
		errors.delete(theme.id);
		themeUpdateErrors.set(errors);

		// Check for a new version and update the themeUpdates store
		if (latestTheme.version && isNewerVersion(theme.version, latestTheme.version)) {
			const updates = get(themeUpdates);
			updates.set(theme.id, latestTheme);
			themeUpdates.set(updates);
			toast.success(`Update found for theme "${theme.name}"!`);
		} else {
			toast.success(`Theme "${theme.name}" is up to date.`);
		}
	} else {
		// Update the error message in the store
		const errors = get(themeUpdateErrors);
		errors.set(theme.id, error);
		themeUpdateErrors.set(errors);
		toast.error(`Failed to check for update for theme "${theme.name}": ${error}`);
	}
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

const getDismissedThemeIds = (): string[] => {
	return JSON.parse(sessionStorage.getItem('dismissedThemeIds') ?? '[]');
};

const addDismissedThemeId = (id: string) => {
	const ids = getDismissedThemeIds();
	sessionStorage.setItem('dismissedThemeIds', JSON.stringify([...ids, id]));
};

export const checkForThemeUpdates = async (manual = false) => {
	const themes = get(communityThemes);
	const dismissedThemeIds = getDismissedThemeIds();
	const updates = new Map<string, Theme>();
	const errors = new Map<string, string>();
	let updatesFound = 0;

	// Clear previous errors before checking
	themeUpdateErrors.set(new Map());

	for (const [id, theme] of themes.entries()) {
		if (theme.sourceUrl && theme.version) {
			const [latestTheme, error] = await _fetchTheme(theme.sourceUrl);

			if (latestTheme) {
				if (latestTheme.version && isNewerVersion(theme.version, latestTheme.version)) {
					updates.set(id, latestTheme);
					updatesFound++;

					if (!dismissedThemeIds.includes(id)) {
						toast.info(
							`A new version (v${latestTheme.version}) is available for the theme "${theme.name}", which is on version ${theme.version}.`,
							{
								duration: 10000,
								action: {
									label: 'Update',
									onClick: () => {
										updateCommunityThemeFromUrl(theme);
									}
								},
								onDismiss: () => {
									addDismissedThemeId(id);
								}
							}
						);
					}
				}
			} else {
				errors.set(id, error);
				if (manual) {
					toast.error(`Failed to check for update for theme "${theme.name}": ${error}`);
				}
			}
		}
	}
	themeUpdates.set(updates);
	themeUpdateErrors.set(errors);

	if (manual) {
		if (updatesFound === 0) {
			toast.success('All community themes are up to date.');
		} else if (updatesFound === 1) {
			toast.success('Found 1 theme update.');
		} else {
			toast.success(`Found ${updatesFound} theme updates.`);
		}
	} else {
		if (errors.size > 0) {
			const hasDismissed = sessionStorage.getItem('hasDismissedUpdateErrors') === 'true';
			if (!hasDismissed) {
				toast.error(
					`Failed to check for updates for ${errors.size} theme(s). See Themes settings for details.`,
					{
						onDismiss: () => {
							sessionStorage.setItem('hasDismissedUpdateErrors', 'true');
						}
					}
				);
			}
		}
	}
};
