import { get } from 'svelte/store';
import { config } from '$lib/stores';
import { signout } from '$lib/services/auths';

export const resetPassword = async (): void => {
	const passwordResetUrl = get(config)?.features?.ionos_password_reset_url ?? null;
	await signout(passwordResetUrl);
};
