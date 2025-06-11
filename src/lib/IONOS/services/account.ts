import { get } from 'svelte/store';
import { config } from '$lib/stores';
import { deleteAccount as deleteAccountApi } from '$lib/IONOS/apis/users';
import { signout } from '$lib/services/auths';

export const resetPassword = async (): Promise<void> => {
	const passwordResetUrl = get(config)?.features?.ionos_password_reset_url ?? null;
	await signout(passwordResetUrl);
};

export const deleteAccount = async (): Promise<void> => {
	const token = localStorage.token;
	await deleteAccountApi(token);
	await signout();
};
