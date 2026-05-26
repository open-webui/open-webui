import { WEBUI_API_BASE_URL } from '$lib/constants';
import { get } from 'svelte/store';
import { socket } from '$lib/stores';

export type ApiFetchMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface ApiFetchOptions {
	method?: ApiFetchMethod;
	body?: unknown;
	signal?: AbortSignal;
	headers?: Record<string, string>;
	sessionId?: string | null;
	baseUrl?: string;
	parseJson?: boolean;
}

export interface ApiErrorShape {
	status: number;
	detail: string;
	raw: unknown;
}

export class ApiError extends Error {
	status: number;
	detail: string;
	raw: unknown;

	constructor(shape: ApiErrorShape) {
		super(shape.detail);
		this.name = 'ApiError';
		this.status = shape.status;
		this.detail = shape.detail;
		this.raw = shape.raw;
	}
}

// Defensive replacement for the codebase-wide `'detail' in err` pattern,
// which throws on null/string/number errors (e.g. when fetch itself rejects).
export const extractErrorDetail = (err: unknown): string => {
	if (err == null) return 'Unknown error';
	if (typeof err === 'string') return err;
	if (err instanceof Error) return err.message;
	if (typeof err === 'object') {
		const o = err as Record<string, unknown>;
		const detail = o.detail ?? o.message ?? o.error;
		if (typeof detail === 'string') return detail;
		if (detail && typeof detail === 'object') {
			try {
				return JSON.stringify(detail);
			} catch {
				return String(detail);
			}
		}
		try {
			return JSON.stringify(o);
		} catch {
			return String(o);
		}
	}
	return String(err);
};

const buildSessionHeader = (sessionId?: string | null): Record<string, string> => {
	if (sessionId === null) return {};
	if (sessionId) return { 'X-Session-Id': sessionId };
	const sid = get(socket)?.id;
	return sid ? { 'X-Session-Id': sid } : {};
};

export async function apiFetch<T = unknown>(
	token: string | null | undefined,
	path: string,
	options: ApiFetchOptions = {}
): Promise<T> {
	const {
		method = 'GET',
		body,
		signal,
		headers,
		sessionId,
		baseUrl = WEBUI_API_BASE_URL,
		parseJson = true
	} = options;

	const url = path.startsWith('http') ? path : `${baseUrl}${path}`;

	const finalHeaders: Record<string, string> = {
		Accept: 'application/json',
		...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
		...(token ? { Authorization: `Bearer ${token}` } : {}),
		...buildSessionHeader(sessionId),
		...(headers ?? {})
	};

	let res: Response;
	try {
		res = await fetch(url, {
			method,
			headers: finalHeaders,
			signal,
			...(body !== undefined ? { body: JSON.stringify(body) } : {})
		});
	} catch (err) {
		throw new ApiError({
			status: 0,
			detail: extractErrorDetail(err),
			raw: err
		});
	}

	if (!res.ok) {
		let raw: unknown = null;
		try {
			raw = await res.json();
		} catch {
			try {
				raw = await res.text();
			} catch {
				raw = null;
			}
		}
		throw new ApiError({
			status: res.status,
			detail: extractErrorDetail(raw) || res.statusText || `HTTP ${res.status}`,
			raw
		});
	}

	if (!parseJson || res.status === 204) {
		return undefined as T;
	}

	try {
		return (await res.json()) as T;
	} catch (err) {
		throw new ApiError({
			status: res.status,
			detail: extractErrorDetail(err),
			raw: err
		});
	}
}
