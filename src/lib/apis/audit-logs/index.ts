import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface AuditUser {
	id: string;
	name: string;
	email: string;
	role?: string;
}

export interface AuditLogItemSummary {
	id: string;
	created_at: number;
	user?: AuditUser | null;
	verb: string;
	request_path: string;
	response_status_code: number;
	source_ip?: string | null;
	audit_level: string;
	request_captured: boolean;
	response_captured: boolean;
	request_truncated: boolean;
	response_truncated: boolean;
}

export interface AuditLogDetail extends AuditLogItemSummary {
	user_snapshot?: AuditUser | null;
	request_uri?: string;
	user_agent?: string;
	request_object?: string | null;
	request_model?: string | null;
	request_extra?: any | null;
	request_skill_ids?: string[] | null;
	request_tool_ids?: string[] | null;
	request_response_format?: any | null;
	request_extra_body?: any | null;
	request_system_messages?: any[] | null;
	request_user_messages?: any[] | null;
	response_object?: string | null;
	response_id?: string | null;
	response_model?: string | null;
	response_finish_reasons?: string[] | null;
}

export interface AuditLogQueryParams {
	start_at?: number;
	end_at?: number;
	q?: string;
	user_id?: string;
	endpoint?: string;
	request_model?: string;
	response_model?: string;
	request_skill_ids?: string[];
	status_classes?: string[];
	source_ip?: string;
	body_state?: string[];
	order_by?: string;
	direction?: string;
	page?: number;
	limit?: number;
}

export interface AuditLogFacets {
	endpoints: string[];
	request_models: string[];
	response_models: string[];
	request_skill_ids: string[];
	status_classes: string[];
}

export const getAuditLogs = async (
	token: string = '',
	params: AuditLogQueryParams = {}
): Promise<{ items: AuditLogItemSummary[]; total: number } | null> => {
	let error = null;

	const searchParams = new URLSearchParams();

	if (params.start_at) searchParams.append('start_at', params.start_at.toString());
	if (params.end_at) searchParams.append('end_at', params.end_at.toString());
	if (params.q) searchParams.append('q', params.q);
	if (params.user_id) searchParams.append('user_id', params.user_id);
	if (params.endpoint) searchParams.append('endpoint', params.endpoint);
	if (params.request_model) searchParams.append('request_model', params.request_model);
	if (params.response_model) searchParams.append('response_model', params.response_model);
	if (params.request_skill_ids && params.request_skill_ids.length > 0) {
		searchParams.append('request_skill_ids', params.request_skill_ids.join(','));
	}
	if (params.status_classes && params.status_classes.length > 0) {
		searchParams.append('status_classes', params.status_classes.join(','));
	}
	if (params.source_ip) searchParams.append('source_ip', params.source_ip);
	if (params.body_state && params.body_state.length > 0) {
		searchParams.append('body_state', params.body_state.join(','));
	}
	if (params.order_by) searchParams.append('order_by', params.order_by);
	if (params.direction) searchParams.append('direction', params.direction);
	if (params.page) searchParams.append('page', params.page.toString());
	if (params.limit) searchParams.append('limit', params.limit.toString());

	const res = await fetch(`${WEBUI_API_BASE_URL}/audit-logs?${searchParams.toString()}`, {
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
			error = err.detail || err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAuditLogById = async (
	token: string = '',
	id: string
): Promise<AuditLogDetail | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/audit-logs/${encodeURIComponent(id)}`, {
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
			error = err.detail || err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAuditLogFacets = async (
	token: string = '',
	startAt?: number,
	endAt?: number
): Promise<AuditLogFacets | null> => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (startAt) searchParams.append('start_at', startAt.toString());
	if (endAt) searchParams.append('end_at', endAt.toString());

	const res = await fetch(`${WEBUI_API_BASE_URL}/audit-logs/facets?${searchParams.toString()}`, {
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
			error = err.detail || err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
