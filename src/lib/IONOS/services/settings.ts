import type { Settings } from '$lib/stores';
import { get } from 'svelte/store';
import { settings } from '$lib/stores';
import { updateUserSettings } from '$lib/apis/users';

export type IonosSettings = Settings & {
	ionosProvidedFeedback?: boolean;
	ionosAgreedToTerms?: boolean;
};

export const updateSettings = async (newSettings: Partial<IonosSettings>): Promise<void> => {
	const updatedSettings: IonosSettings = {
		...get(settings),
		...newSettings,
	};

	await updateUserSettings(localStorage.token, { ui: updatedSettings });

	settings.set(updatedSettings);
};
