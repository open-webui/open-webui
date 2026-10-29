import { WEBUI_API_BASE_URL } from '$lib/constants';

export type SessionScope = {
	startDate: number | null;
	endDate: number | null;
	groupId: string | null;
};
export type Session = {
	id: string;
	title: string;
	user_id: string | null;
	user_name: string | null;
	folder_name: string | null;
	kind: string | null;
	forked_from?: string | null;
	messages: number;
	responses: number;
	prompts: number;
	recorded_responses: number;
	complete_responses: number;
	tokens: number;
	cache_read?: number | null;
	cache_write?: number | null;
	cache_read_responses?: number;
	cache_write_responses?: number;
	errors: number;
	started_at: number | null;
	last_active: number | null;
	span_seconds: number | null;
	model_id: string | null;
	model_count: number;
};
export type SessionMessage = {
	id: string;
	role: string;
	model_id: string | null;
	parent_id: string | null;
	created_at: number;
	done: boolean;
	preview: string | null;
	preview_truncated: boolean | null;
	error: string | null;
	tokens: number | null;
	output_count: number;
};
export type SessionEvent = {
	index: number;
	type: string | null;
	name: string | null;
	call_id: string | null;
	status: string | null;
	error_type?: string | null;
	started_at: number | null;
	ended_at: number | null;
	duration_seconds: number | null;
	details: string | null;
	truncated: boolean | null;
};
export const SESSION_TOKEN_RANGES = [
	{ min: 0, max: 1, label: '0' },
	{ min: 1, max: 1000, label: '<1K' },
	{ min: 1000, max: 10000, label: '1K–<10K' },
	{ min: 10000, max: 100000, label: '10K–<100K' },
	{ min: 100000, max: 1000000, label: '100K–<1M' },
	{ min: 1000000, max: null, label: '≥1M' }
];
export type SessionOverview = {
	token_distribution: number[];
	unrecorded_sessions: number;
	max_tokens: number;
	sessions: number;
	tokens: number;
	prompts: number;
	responses: number;
	errors: number;
	recorded_responses: number;
	complete_responses: number;
	start: number | null;
	end: number | null;
};
export type SessionOrder =
	| 'title'
	| 'user'
	| 'recent'
	| 'tokens'
	| 'responses'
	| 'errors'
	| 'duration';
export type Page<T> = { items: T[]; has_more: boolean };

async function request<T>(
	token: string,
	path: string,
	scope: SessionScope,
	params: Record<string, string | number | boolean>,
	signal: AbortSignal
): Promise<T> {
	const query = new URLSearchParams();
	if (scope.startDate !== null) query.set('start_date', String(scope.startDate));
	if (scope.endDate !== null) query.set('end_date', String(scope.endDate));
	if (scope.groupId) query.set('group_id', scope.groupId);
	for (const [key, value] of Object.entries(params))
		if (value !== '') query.set(key, String(value));
	const response = await fetch(`${WEBUI_API_BASE_URL}/analytics/sessions${path}?${query}`, {
		headers: { authorization: `Bearer ${token}` },
		signal
	});
	if (!response.ok) throw new Error(`Unable to load session analytics (${response.status})`);
	return response.json();
}

export const getSessions = (
	token: string,
	scope: SessionScope,
	params: {
		query: string;
		model_id: string;
		hide_subagents: boolean;
		order_by: SessionOrder;
		direction: 'asc' | 'desc';
		include_summary: boolean;
		token_min?: number;
		token_max?: number;
		skip: number;
		limit: number;
	},
	signal: AbortSignal
) => request<Page<Session> & { overview?: SessionOverview }>(token, '', scope, params, signal);
export const getSessionMessages = (
	token: string,
	id: string,
	scope: SessionScope,
	skip: number,
	signal: AbortSignal
) =>
	request<Page<SessionMessage> & { session: Session }>(
		token,
		`/${encodeURIComponent(id)}`,
		scope,
		{ skip, limit: 25 },
		signal
	);
export const getSessionEvents = (
	token: string,
	id: string,
	messageId: string,
	scope: SessionScope,
	skip: number,
	signal: AbortSignal,
	limit = 20
) =>
	request<Page<SessionEvent>>(
		token,
		`/${encodeURIComponent(id)}/messages/${encodeURIComponent(messageId)}/events`,
		scope,
		{ skip, limit },
		signal
	);

export type TraceItem = Omit<SessionEvent, 'details' | 'truncated'> & {
	message_id: string;
	result_index: number | null;
	created_at: number;
	model_id: string | null;
};
export type UsageBar = {
	first: number;
	last: number;
	offset: number;
	input_tokens: number | null;
	output_tokens: number | null;
	recorded: number;
	complete: number;
	errors: number;
	model_id: string | null;
};
export type SessionChart = {
	timed_operations: number;
	duration_operations: number;
	usage: UsageBar[];
	start: number | null;
	end: number | null;
	max_duration: number | null;
};
export type TraceView = 'all' | 'tools' | 'errors';
export const getSessionTrace = (
	token: string,
	id: string,
	scope: SessionScope,
	skip: number,
	view: TraceView,
	signal: AbortSignal,
	includeChart = false
) =>
	request<Page<TraceItem> & { session: Session; chart?: SessionChart }>(
		token,
		`/${encodeURIComponent(id)}/trace`,
		scope,
		{ skip, limit: 50, view, include_chart: includeChart },
		signal
	);
