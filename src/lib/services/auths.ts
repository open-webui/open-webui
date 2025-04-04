import { get } from 'svelte/store';
import { config, user } from '$lib/stores';
import { userSignOut } from '$lib/apis/auths';

export async function signout(response) {
	const signoutResponse = await userSignOut();

	if (!signoutResponse?.status) {
		throw new Error('Signout was not successful');
	}

	user.set(null);
	localStorage.removeItem('token');

	if (get(config)?.oauth?.providers?.oidc && !signoutResponse?.end_session_endpoint) {
		throw new Error('OIDC configured but no end_session_endpoint sent');
	}

	const postSignoutLocation = signoutResponse?.end_session_endpoint ?? '/auth';

	location.href = postSignoutLocation;
};
