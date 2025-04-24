import type { Settings } from '$lib/stores';
import { get } from 'svelte/store';
import { settings } from '$lib/stores';
import { updateUserSettings } from '$lib/apis/users';

export const updateSettings = async (newSettings: Settings): Promise<void> => {
	const updatedSettings: Settings = {
		...get(settings),
		...newSettings,
	};

	settings.set(updatedSettings);

	await updateUserSettings(localStorage.token, { ui: updatedSettings });
};
