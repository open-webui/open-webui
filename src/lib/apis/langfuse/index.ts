import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MetricRow = {
	user: string;
	model: string;
	tokens: number;
	cost: number;
};

export type MyUsage = {
	month: number;
	year: number;
	total_tokens: number;
	total_cost: number;
};

export const getLangfuseMetrics = async (
	token: string,
	period: string = 'week',
	days?: number
): Promise<MetricRow[]> => {
	let error = null;

	const params = new URLSearchParams({ period });
	if (period === 'custom' && days) {
		params.set('days', String(days));
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/langfuse/metrics?${params}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
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

export const getMyLangfuseUsage = async (token: string): Promise<MyUsage> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/langfuse/my-usage`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
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
