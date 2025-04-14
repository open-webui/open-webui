import { get } from 'svelte/store';
import { config } from '$lib/stores';
import { userSignOut } from '$lib/apis/auths';

export async function signout() {
	const signoutResponse = await userSignOut();

	if (!signoutResponse?.status) {
		throw new Error('Signout was not successful');
	}

	localStorage.removeItem('token');

	const isOidcConfigured = !!get(config)?.oauth?.providers?.oidc;
	const oidcEndSessionEndpoint = signoutResponse?.end_session_endpoint ?? null;
	const logoutEndpoint = get(config)?.features?.ionos_logout_url ?? null;

	if (isOidcConfigured && !oidcEndSessionEndpoint && !logoutEndpoint) {
		throw new Error('OIDC configured but no end_session_endpoint sent');
	}

	const postLogoutRedirectTarget = new URL('/explore', location.href).toString();

	if (logoutEndpoint !== null && logoutEndpoint !== '') {
		const logoutEndpointUrl = new URL(logoutEndpoint);

		// The user should come back to the startpage (explore) after logout finished
		logoutEndpointUrl.searchParams.set('redirect_url', postLogoutRedirectTarget);

		location.href = logoutEndpointUrl.toString();
	} else if (oidcEndSessionEndpoint !== null) {
		location.href = oidcEndSessionEndpoint;
	} else {
		location.href = '/auth';
	}
};
