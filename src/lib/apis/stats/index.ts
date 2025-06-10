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

	let res;
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/stats/`, {
			method: 'GET',
			headers,
			credentials: 'include'
		});
		const data = await response.json();
		if (!response.ok) {
			throw data;
		}
		res = data;
		
	} catch (err: unknown) {
		console.log(err);
		error = err instanceof Error ? err.message : 'An unknown error occurred while fetching stats';
		res = null;
	}
	return { error, ...res };
};
