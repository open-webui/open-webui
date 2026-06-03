import { WEBUI_API_BASE_URL } from '$lib/constants';

type Json = Record<string, any>;

const request = async (
	token: string,
	path: string,
	method: 'GET' | 'POST' | 'DELETE' = 'GET',
	body: Json | null = null
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/subscriptions${path}`, {
		method,
		headers: {
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
			error = err.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ── User-facing ──────────────────────────────────────────────

export const getSubscriptionTiers = (token: string) => request(token, '/tiers');

export const getSubscriptionChains = (token: string) => request(token, '/chains');

export const getMySubscription = (token: string) => request(token, '/me');

export const subscribe = (token: string, tier_id: string, chain_id: string) =>
	request(token, '/subscribe', 'POST', { tier_id, chain_id });

export const getSubscriptionOrder = (token: string, orderId: string) =>
	request(token, `/order/${encodeURIComponent(orderId)}`);

export const getMyOrders = (token: string) => request(token, '/orders');

// ── Admin ────────────────────────────────────────────────────

export const getAdminTiers = (token: string) => request(token, '/admin/tiers');

export const upsertTier = (token: string, tier: Json) =>
	request(token, '/admin/tiers', 'POST', tier);

export const deleteTier = (token: string, tierId: string) =>
	request(token, `/admin/tiers/${encodeURIComponent(tierId)}`, 'DELETE');

export const seedTiers = (token: string) => request(token, '/admin/seed', 'POST');

export const getAdminSubscriptions = (token: string) => request(token, '/admin/subscriptions');
