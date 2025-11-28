import { WEBUI_API_BASE_URL } from '$lib/constants';

export type UserModelCredentialForm = {
	name?: string;
	model_id: string;
	base_url?: string;
	api_key: string;
	config?: object;
};

// WEBUI_API_BASE_URL 已包含 /api 或 /api/v1 前缀，这里仅追加 user/models
const BASE = `${WEBUI_API_BASE_URL}/user/models`;

export const listUserModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(BASE, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createUserModel = async (token: string, body: UserModelCredentialForm) => {
	let error = null;

	const res = await fetch(BASE, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateUserModel = async (
	token: string,
	id: string,
	body: UserModelCredentialForm
) => {
	let error = null;

	const res = await fetch(`${BASE}/${id}`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteUserModel = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${BASE}/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
