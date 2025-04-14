import { get } from 'svelte/store';
import { config } from '$lib/stores';
import { userSignOut } from '$lib/apis/auths';

export async function signout(postLogoutRedirectTargetOverride: string|null = null) {
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

	// The user should come back to the startpage (explore) after logout finished
	let postLogoutRedirectTarget = new URL('/explore', location.href).toString();

	if (postLogoutRedirectTargetOverride !== null && postLogoutRedirectTargetOverride !== '') {
		postLogoutRedirectTarget = postLogoutRedirectTargetOverride;
	}

	if (logoutEndpoint !== null && logoutEndpoint !== '') {
		const logoutEndpointUrl = new URL(logoutEndpoint);

		logoutEndpointUrl.searchParams.set('redirect_url', postLogoutRedirectTarget);

		location.href = logoutEndpointUrl.toString();
	} else if (oidcEndSessionEndpoint !== null) {
		const logoutEndpointUrl = new URL(oidcEndSessionEndpoint);

		logoutEndpointUrl.searchParams.set('post_logout_redirect_uri', postLogoutRedirectTarget);

		location.href = logoutEndpointUrl.toString();
	} else {
		location.href = '/auth';
	}
};
