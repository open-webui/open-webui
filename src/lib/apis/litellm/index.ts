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
			error = `LiteLLM: ${err?.error?.message ?? 'Network Problem'}`;
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

export const getLiteLLMModelInfo = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${LITELLM_API_BASE_URL}/model/info`, {
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
			error = `LiteLLM: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	const models = Array.isArray(res) ? res : res?.data ?? null;

	return models;
};

type AddLiteLLMModelForm = {
	name: string;
	model: string;
	api_base: string;
	api_key: string;
	rpm: string;
};

export const addLiteLLMModel = async (token: string = '', payload: AddLiteLLMModelForm) => {
	let error = null;

	const res = await fetch(`${LITELLM_API_BASE_URL}/model/new`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			model_name: payload.name,
			litellm_params: {
				model: payload.model,
				...(payload.api_base === '' ? {} : { api_base: payload.api_base }),
				...(payload.api_key === '' ? {} : { api_key: payload.api_key }),
				...(isNaN(parseInt(payload.rpm)) ? {} : { rpm: parseInt(payload.rpm) })
			}
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = `LiteLLM: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteLiteLLMModel = async (token: string = '', id: string) => {
	let error = null;

	const res = await fetch(`${LITELLM_API_BASE_URL}/model/delete`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			id: id
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = `LiteLLM: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};
