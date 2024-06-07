import {HATTO_LLM_API_BASE_URL} from '$lib/constants';

export const chunkText = async (model: string, content: string, extra_tokens: number = 0) => {
	let error = null;

	const res = await fetch(`${HATTO_LLM_API_BASE_URL}/tool/chunk-text`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${localStorage.token}`
		},
		body: JSON.stringify({
			model, content, extra_tokens
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res.data;
};