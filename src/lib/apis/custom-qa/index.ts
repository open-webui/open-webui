import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface CustomQARequest {
	user_query: string;
	file_ids?: string[];
	collection_names?: string[];
	session_id?: string;
	chat_history?: Array<{ role: string; content: string }>;
}

export interface CustomQAResponse {
	response: string;
	sources?: Array<Record<string, any>>;
	metadata?: Record<string, any>;
}

export interface CustomQAConfig {
	enabled: boolean;
}

export const getCustomQAConfig = async (token: string): Promise<CustomQAConfig> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/custom-qa/config`, {
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
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateCustomQAConfig = async (
	token: string,
	config: CustomQAConfig
): Promise<CustomQAConfig> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/custom-qa/config`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const queryCustomQA = async (
	token: string,
	request: CustomQARequest
): Promise<CustomQAResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/custom-qa/query`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(request)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const queryCustomQASingleFile = async (
	token: string,
	fileId: string,
	request: CustomQARequest
): Promise<CustomQAResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/custom-qa/query/files/${fileId}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(request)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const queryCustomQASingleCollection = async (
	token: string,
	collectionName: string,
	request: CustomQARequest
): Promise<CustomQAResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/custom-qa/query/collection/${collectionName}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(request)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
