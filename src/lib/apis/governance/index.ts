import { WEBUI_API_BASE_URL } from '$lib/constants';

export type GovernanceCapabilities = {
	can_use_private_chat: boolean;
	can_create_workspace: boolean;
	can_access_all_workspaces: boolean;
};

export const getGovernanceCapabilities = async (token: string): Promise<GovernanceCapabilities> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/governance/capabilities`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err?.message ?? String(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
