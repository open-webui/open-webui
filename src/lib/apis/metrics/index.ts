import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getDomains = async (token: string): Promise<string[]> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/metrics/domains`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get domains'}`);
		}
		const data = await res.json();
		return data.domains;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getTotalUsers = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/metrics/users?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/metrics/users`;

		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get users'}`);
		}
		const data = await res.json();
		return data.total_users;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyUsers = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/metrics/daily/users?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/metrics/daily/users`;
		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get daily users'}`);
		}
		const data = await res.json();
		return data.total_daily_users;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getTotalPrompts = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/metrics/prompts?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/metrics/prompts`;
		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get prompts'}`);
		}
		const data = await res.json();
		return data.total_prompts;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyPrompts = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/metrics/daily/prompts?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/metrics/daily/prompts`;
		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get Users'}`);
		}
		const data = await res.json();
		return data.total_daily_prompts;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getTotalTokens = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/metrics/tokens?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/metrics/tokens`;
		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get tokens'}`);
		}
		const data = await res.json();
		return data.total_tokens;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyTokens = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/metrics/daily/tokens?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/metrics/daily/tokens`;
		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get daily tokens'}`);
		}
		const data = await res.json();
		return data.total_daily_tokens;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};
