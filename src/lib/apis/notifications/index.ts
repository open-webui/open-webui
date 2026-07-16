import { WEBUI_API_BASE_URL } from '$lib/constants';

export type NotificationTarget = {
	id: string;
	type: 'webhook';
	name: string;
	enabled: boolean;
	events: string[];
	delivery: 'away' | 'always';
	config: {
		url?: string;
	};
	created_at?: number;
	updated_at?: number;
};

const jsonRequest = async (url: string, token: string, method = 'GET', body?: object) => {
	let error = null;

	const res = await fetch(url, {
		method,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getNotificationEvents = async (token: string) =>
	jsonRequest(`${WEBUI_API_BASE_URL}/notifications/events`, token);

export const getNotificationTargets = async (
	token: string
): Promise<{ targets: NotificationTarget[]; default_target_id: string | null }> =>
	jsonRequest(`${WEBUI_API_BASE_URL}/notifications/targets`, token);

export const createNotificationTarget = async (
	token: string,
	target: Partial<NotificationTarget>
) => jsonRequest(`${WEBUI_API_BASE_URL}/notifications/targets`, token, 'POST', target);

export const updateNotificationTarget = async (
	token: string,
	targetId: string,
	target: Partial<NotificationTarget>
) => jsonRequest(`${WEBUI_API_BASE_URL}/notifications/targets/${targetId}`, token, 'PUT', target);

export const deleteNotificationTarget = async (token: string, targetId: string) =>
	jsonRequest(`${WEBUI_API_BASE_URL}/notifications/targets/${targetId}`, token, 'DELETE');

export const setDefaultNotificationTarget = async (token: string, targetId: string) =>
	jsonRequest(`${WEBUI_API_BASE_URL}/notifications/targets/${targetId}/default`, token, 'PUT');

export const testNotificationTarget = async (token: string, targetId: string) =>
	jsonRequest(`${WEBUI_API_BASE_URL}/notifications/targets/${targetId}/test`, token, 'POST');
