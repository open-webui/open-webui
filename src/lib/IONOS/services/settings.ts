import type { Settings } from '$lib/stores';
import { get } from 'svelte/store';
import { settings } from '$lib/stores';
import { updateUserSettings } from '$lib/apis/users';

export const updateSettings = async (newSettings: Partial<Settings>): Promise<void> => {
	const updatedSettings: Settings = {
		...get(settings),
		...newSettings,
	};

	await updateUserSettings(localStorage.token, { ui: updatedSettings });

	settings.set(updatedSettings);
};
