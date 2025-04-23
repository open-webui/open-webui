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
			if (res.status === 404) {
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get users'}`);
		}
		const data = await res.json();
		return data.total_users || 0;
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
			if (res.status === 404) {
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get daily users'}`);
		}
		const data = await res.json();
		return data.total_daily_users || 0;
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
			// Return 0 instead of throwing an error if we get a 404
			if (res.status === 404) {
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get prompts'}`);
		}
		const data = await res.json();
		return data.total_prompts || 0; // Ensure we return 0 if null/undefined
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
			if (res.status === 404) {
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get Users'}`);
		}
		const data = await res.json();
		return data.total_daily_prompts || 0;
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
			if (res.status === 404) {
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get tokens'}`);
		}
		const data = await res.json();
		return data.total_tokens || 0;
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
			if (res.status === 404) {
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get daily tokens'}`);
		}
		const data = await res.json();
		return data.total_daily_tokens || 0;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getHistoricalUsers = async (
	token: string,
	days: number = 7,
	domain?: string
): Promise<any[]> => {
	try {
		// Build URL with proper domain handling
		let url = `${WEBUI_API_BASE_URL}/metrics/historical/users?days=${days}`;

		// Only add domain parameter if it's not null or undefined
		if (domain !== null && domain !== undefined) {
			url += `&domain=${encodeURIComponent(domain)}`;
		}

		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			if (res.status === 404) {
				return generateFallbackDates(days);
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get historical users'}`);
		}
		const data = await res.json();
		return data.historical_users || [];
	} catch (err) {
		console.error('Error fetching historical users:', err);
		return generateFallbackDates(days);
	}
};

export const getHistoricalPrompts = async (
	token: string,
	days: number = 7,
	domain?: string
): Promise<any[]> => {
	try {
		// Build URL with proper domain handling
		let url = `${WEBUI_API_BASE_URL}/metrics/historical/prompts?days=${days}`;

		// Only add domain parameter if it's not null or undefined
		if (domain !== null && domain !== undefined) {
			url += `&domain=${encodeURIComponent(domain)}`;
		}

		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			if (res.status === 404) {
				return generateFallbackDates(days);
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get historical prompts'}`);
		}
		const data = await res.json();
		return data.historical_prompts || [];
	} catch (err) {
		console.error('Error fetching historical prompts:', err);
		return generateFallbackDates(days);
	}
};

export const getHistoricalTokens = async (
	token: string,
	days: number = 7,
	domain?: string
): Promise<any[]> => {
	try {
		// Build URL with proper domain handling
		let url = `${WEBUI_API_BASE_URL}/metrics/historical/tokens?days=${days}`;

		// Only add domain parameter if it's not null or undefined
		if (domain !== null && domain !== undefined) {
			url += `&domain=${encodeURIComponent(domain)}`;
		}

		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			if (res.status === 404) {
				return generateFallbackDates(days);
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get historical tokens'}`);
		}
		const data = await res.json();
		return data.historical_tokens || [];
	} catch (err) {
		console.error('Error fetching historical tokens:', err);
		return generateFallbackDates(days);
	}
};

// Helper to generate fallback dates when API fails
function generateFallbackDates(days: number = 7): Array<{ date: string; count: number }> {
	return Array.from({ length: days }, (_, i) => {
		const date = new Date();
		date.setDate(date.getDate() - (days - 1) + i);
		return {
			date: date.toISOString().split('T')[0],
			count: 0
		};
	});
}
