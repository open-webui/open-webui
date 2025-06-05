import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getStatsData = async (token?: string) => {
	let error = null;

	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};

	// Only add authorization header if token is provided
	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/stats/`, {
		method: 'GET',
		headers,
		credentials: 'include'
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
}; 