import { WEBUI_API_BASE_URL } from '$lib/constants';

export type CreditsDomain = 'audio' | 'photo' | 'video' | 'music';

export type CreditsPackage = {
	package_code: string;
	credits: number;
	label: string;
	price_label: string;
	enabled: boolean;
};

export type DomainCreditsStatus = {
	enforced: boolean;
	unit: string;
	cost?: number | null;
	free_used: number;
	free_limit: number;
	free_remaining: number;
	paid_balance: number;
	paid_remaining: number;
	total_remaining: number;
	packages: CreditsPackage[];
};

export type CreditsStatus = {
	redis_available: boolean;
	domains: Record<string, DomainCreditsStatus>;
};

export const getCreditsStatus = async (token: string): Promise<CreditsStatus> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/credits/status`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as CreditsStatus;
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res!;
};

export const createCreditsCheckout = async (
	token: string,
	packageCode: string,
	domain: CreditsDomain = 'audio'
): Promise<{ url: string }> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/credits/checkout`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ package_code: packageCode, domain })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as { url: string };
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res!;
};

export type AdminCreditsUserRow = {
	user_id: string;
	email?: string | null;
	username?: string | null;
	role?: string | null;
	domains: Record<string, DomainCreditsStatus>;
	total_purchased_credits_audio: number;
	total_used_credits_audio: number;
	last_credit_activity_audio?: number | null;
};

export type AdminCreditsUsersResponse = {
	redis_available: boolean;
	users: AdminCreditsUserRow[];
	total: number;
};

export type AdminCreditsDomainStats = {
	unit: string;
	cost?: number | null;
	total_free_remaining?: number | null;
	total_paid_balance?: number | null;
	total_remaining?: number | null;
};

export type AdminCreditsStatsResponse = {
	redis_available: boolean;
	total_users: number;
	domains: Record<string, AdminCreditsDomainStats>;
	total_purchased_credits_audio: number;
	total_used_credits_audio: number;
	total_credits_issued_audio?: number | null;
	total_revenue_by_currency_minor?: Record<string, number> | null;
};

export type AdminCreditsPurchase = {
	purchase_id: string;
	credits: number;
	price_minor?: number | null;
	currency?: string | null;
	payment_provider?: string | null;
	purchase_date: number;
	status?: string | null;
	package_code?: string | null;
};

export type AdminCreditsUserDetailResponse = {
	redis_available: boolean;
	user: {
		id: string;
		email?: string | null;
		username?: string | null;
		name?: string | null;
		role?: string | null;
	};
	domains: Record<string, DomainCreditsStatus>;
	total_purchased_credits_audio: number;
	total_used_credits_audio: number;
	last_credit_activity_audio?: number | null;
	purchases_audio: AdminCreditsPurchase[];
};

export const getAdminCreditsUsers = async (
	token: string,
	query = '',
	page = 1,
	limit = 50
): Promise<AdminCreditsUsersResponse> => {
	let error: string | null = null;

	const searchParams = new URLSearchParams();
	searchParams.set('page', `${page}`);
	searchParams.set('limit', `${limit}`);
	if (query) searchParams.set('query', query);

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/credits/users?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as AdminCreditsUsersResponse;
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) throw error;
	return res!;
};

export const getAdminCreditsStats = async (token: string): Promise<AdminCreditsStatsResponse> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/credits/stats`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as AdminCreditsStatsResponse;
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) throw error;
	return res!;
};

export const getAdminCreditsUser = async (
	token: string,
	userId: string
): Promise<AdminCreditsUserDetailResponse> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/credits/users/${userId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as AdminCreditsUserDetailResponse;
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) throw error;
	return res!;
};
