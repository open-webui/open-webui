import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getDomains = async (token: string): Promise<string[]> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/users/domains`, {
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
			? `${WEBUI_API_BASE_URL}/users/count?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/users/count`;

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
		return data || 0;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyUsers = async (token: string, domain?: string): Promise<number> => {
	try {
		const url = domain
			? `${WEBUI_API_BASE_URL}/users/daily/count?domain=${encodeURIComponent(domain)}`
			: `${WEBUI_API_BASE_URL}/users/daily/count`;
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
		return data || 0;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getHistoricalUsers = async (
	token: string,
	days: number = 7,
	domain?: string
): Promise<Array<{ date: string; count: number }>> => {
	try {
		// Build URL with proper domain handling
		let url = `${WEBUI_API_BASE_URL}/users/enrollment/historical?days=${days}`;

		if (domain) {
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

export const getHistoricalDailyUsers = async (
	token: string,
	days: number = 7,
	domain?: string
): Promise<Array<{ date: string; count: number }>> => {
	try {
		// Build URL with proper domain handling
		let url = `${WEBUI_API_BASE_URL}/users/daily/historical?days=${days}`;

		if (domain) {
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
		return data.historical_daily_users || [];
	} catch (err) {
		console.error('Error fetching historical users:', err);
		return generateFallbackDates(days);
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

export const getModels = async (token: string): Promise<string[]> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/metrics/models`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get models'}`);
		}
		const data = await res.json();
		return data.models;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getModelPrompts = async (
	token: string,
	model?: string,
	domain?: string
): Promise<number> => {
	try {
		let url = `${WEBUI_API_BASE_URL}/metrics/models/prompts`;
		const params = new URLSearchParams();

		if (model !== null && model !== undefined) {
			params.append('model', model);
		}

		if (domain !== null && domain !== undefined) {
			params.append('domain', domain);
		}

		if (params.toString()) {
			url += `?${params.toString()}`;
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
				return 0;
			}
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get model prompts'}`);
		}
		const data = await res.json();
		return data.total_prompts || 0;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getModelDailyPrompts = async (
	token: string,
	model?: string,
	domain?: string
): Promise<number> => {
	try {
		let url = `${WEBUI_API_BASE_URL}/metrics/models/daily/prompts`;
		const params = new URLSearchParams();

		if (model !== null && model !== undefined) {
			params.append('model', model);
		}

		if (domain !== null && domain !== undefined) {
			params.append('domain', domain);
		}

		if (params.toString()) {
			url += `?${params.toString()}`;
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
				return 0;
			}
			const error = await res.json();
			throw new Error(
				`Error ${res.status}: ${error.detail || 'Failed to get model daily prompts'}`
			);
		}
		const data = await res.json();
		return data.total_daily_prompts || 0;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getModelHistoricalPrompts = async (
	token: string,
	days: number = 7,
	model?: string,
	domain?: string
): Promise<any[]> => {
	try {
		let url = `${WEBUI_API_BASE_URL}/metrics/models/historical/prompts?days=${days}`;

		if (model !== null && model !== undefined) {
			url += `&model=${encodeURIComponent(model)}`;
		}

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
			throw new Error(
				`Error ${res.status}: ${error.detail || 'Failed to get model historical prompts'}`
			);
		}
		const data = await res.json();
		return data.historical_prompts || [];
	} catch (err) {
		console.error('Error fetching model historical prompts:', err);
		return generateFallbackDates(days);
	}
};

// New functions for enhanced metrics
export const getRangeMetrics = async (
	token: string,
	startDate: string,
	endDate: string,
	domain?: string,
	model?: string
): Promise<any> => {
	try {
		let url = `${WEBUI_API_BASE_URL}/metrics/range/users?start_date=${startDate}&end_date=${endDate}`;

		if (domain) {
			url += `&domain=${encodeURIComponent(domain)}`;
		}

		if (model) {
			url += `&model=${encodeURIComponent(model)}`;
		}

		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get range metrics'}`);
		}

		return await res.json();
	} catch (err) {
		console.error('Error fetching range metrics:', err);
		throw new Error(err.message || 'An unexpected error occurred');
	}
};
