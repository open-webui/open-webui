import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MfaChallenge = {
	next_step: 'enroll' | 'verify' | 'recover';
	challenge_token: string;
	expires_in: number;
};

export const mfaRequest = async (
	path:
		| 'status'
		| 'challenge'
		| 'enroll/start'
		| 'enroll/confirm'
		| 'verify'
		| 'replace'
		| 'recovery/codes'
		| 'recover',
	body?: Record<string, unknown>,
	token?: string
) => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/auths/mfa/${path}`, {
		method: path === 'status' ? 'GET' : 'POST',
		credentials: 'same-origin',
		cache: 'no-store',
		headers: {
			'Content-Type': 'application/json',
			...(token ? { Authorization: `Bearer ${token}` } : {})
		},
		...(body ? { body: JSON.stringify(body) } : {})
	});
	const result = await response.json();
	if (!response.ok) throw new Error(result.detail || 'Authentication failed. Please try again.');
	return result;
};
