import { WEBUI_API_BASE_URL } from '$lib/constants';

export type TopTokenUser = {
	user_id: string;
	name?: string | null;
	tokens: number;
	calls: number;
	cost: number;
};

export type TopExpensiveCall = {
	trace_id: string;
	timestamp: string;
	model: string | null;
	cost_usd: number;
};

export type TopSlowCall = {
	trace_id: string;
	timestamp: string;
	model: string | null;
	latency_ms: number;
};

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
	top_token_users?: TopTokenUser[];
	top_expensive?: TopExpensiveCall[];
	top_slow?: TopSlowCall[];
};

export type TraceObservation = {
	name: string;
	latency_ms: number;
};

export type TraceDetail = {
	trace_id: string;
	timestamp: string;
	user: { id: string; name?: string | null; email?: string | null } | null;
	model: string | null;
	input_preview: string;
	output_preview: string;
	total_tokens: number;
	input_tokens: number;
	output_tokens: number;
	total_cost_usd: number;
	latency_ms: number;
	observations: TraceObservation[];
	langfuse_url: string | null;
};

export const getTraceDetail = async (token: string, traceId: string): Promise<TraceDetail> => {
	let error: any = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/analytics/trace/${encodeURIComponent(traceId)}`, {
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
