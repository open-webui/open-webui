import { LITELLM_API_BASE_URL } from '$lib/constants';

export const getLiteLLMModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${LITELLM_API_BASE_URL}/v1/models`, {
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
			console.log(err);
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	const models = Array.isArray(res) ? res : res?.data ?? null;

	return models
		? models
				.map((model) => ({
					id: model.id,
					name: model.name ?? model.id,
					external: true,
					source: 'litellm'
				}))
				.sort((a, b) => {
					return a.name.localeCompare(b.name);
				})
		: models;
};
