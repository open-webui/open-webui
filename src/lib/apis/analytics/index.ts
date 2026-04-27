import { WEBUI_API_BASE_URL } from '$lib/constants';

export type AnalyticsSummary = {
	days: number;
	total_messages: number;
	sampled_messages: number;
	today_cost_usd: number;
	p95_latency_ms: number;
	active_users: number;
	error_rate: number;
	top_models: { model: string; count: number }[];
	daily: { date: string; cost: number }[];
};

export const getAnalyticsSummary = async (
	token: string,
	days: 1 | 7 | 30 = 7
): Promise<AnalyticsSummary> => {
	let error: any = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/summary?days=${days}`, {
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
			error = err.detail || err.message;
			return null;
		});

	if (error) throw error;
	return res;
};
