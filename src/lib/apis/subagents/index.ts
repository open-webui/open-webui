import { SUBAGENTS_API_BASE_URL } from '$lib/constants';

export type SubagentsConfig = {
	ENABLE_SUBAGENTS: boolean;
	SUBAGENT_DEFAULT_MODEL: string;
	SUBAGENT_SYSTEM_PROMPT: string;
	SUBAGENT_PARENT_PROMPT: string;
};

export type SubagentsConfigUpdate = Partial<SubagentsConfig>;

export const getSubagentsConfig = async (token: string): Promise<SubagentsConfig> => {
	let error: any = null;

	const res = await fetch(`${SUBAGENTS_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as SubagentsConfig;
};

export const updateSubagentsConfig = async (
	token: string,
	payload: SubagentsConfigUpdate
): Promise<SubagentsConfig> => {
	let error: any = null;

	const res = await fetch(`${SUBAGENTS_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...payload })
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as SubagentsConfig;
};
