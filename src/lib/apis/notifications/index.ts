import { WEBUI_API_BASE_URL } from '$lib/constants';

export type NotificationTarget = {
	id: string;
	type: 'webhook' | 'webpush';
	is_default?: boolean;
	enabled: boolean;
	events: string[];
	delivery: 'away' | 'always';
	config: {
		url?: string;
		url_masked?: string;
	};
	created_at?: number;
	updated_at?: number;
};

export type NotificationEvent = {
	event: string;
	label: string;
	description?: string;
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

export const getNotificationEvents = async (token: string): Promise<NotificationEvent[]> => {
	const data = await jsonRequest(`${WEBUI_API_BASE_URL}/notifications/events`, token);
	return data?.events ?? data ?? [];
};

export const getNotificationTargets = async (
	token: string
): Promise<{ targets: NotificationTarget[] }> =>
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

export const getWebPushPublicKey = async (token: string): Promise<string> => {
	const data = await jsonRequest(`${WEBUI_API_BASE_URL}/notifications/webpush/public-key`, token);
	return data?.public_key ?? '';
};

export const createWebPushSubscription = async (
	token: string,
	subscription: { endpoint: string; keys: { p256dh: string; auth: string } }
) =>
	jsonRequest(
		`${WEBUI_API_BASE_URL}/notifications/webpush/subscriptions`,
		token,
		'POST',
		subscription
	);

export const getWebPushSubscriptions = async (token: string): Promise<string[]> => {
	const data = await jsonRequest(
		`${WEBUI_API_BASE_URL}/notifications/webpush/subscriptions`,
		token
	);
	return data?.endpoints ?? [];
};

export const deleteWebPushSubscription = async (token: string, endpoint: string) =>
	jsonRequest(
		`${WEBUI_API_BASE_URL}/notifications/webpush/subscriptions/unsubscribe`,
		token,
		'POST',
		{
			endpoint
		}
	);

export const getPushSubscription = async (): Promise<PushSubscription | null> => {
	if (!('serviceWorker' in navigator)) {
		return null;
	}
	const registration = await navigator.serviceWorker.getRegistration('/');
	return (await registration?.pushManager?.getSubscription()) ?? null;
};

// Best-effort removal of this device's push subscription, e.g. on sign-out
export const disableWebPushOnDevice = async (token: string) => {
	try {
		const subscription = await getPushSubscription();
		if (subscription) {
			await deleteWebPushSubscription(token, subscription.endpoint).catch(() => {});
			await subscription.unsubscribe();
		}
	} catch {
		// ignore; the server prunes dead subscriptions on delivery
	}
};
