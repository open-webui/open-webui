// Organization API functions for mAI environment-based usage tracking

const BASE_URL = '/api/v1/usage-tracking';

export const getClientUsageSummary = async (token: string) => {
	try {
		const response = await fetch(`${BASE_URL}/my-organization/usage-summary`, {
			method: 'GET',
			headers: {
				'Authorization': `Bearer ${token}`,
				'Content-Type': 'application/json'
			}
		});
		
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		
		return await response.json();
	} catch (error) {
		console.error('Failed to fetch usage summary:', error);
		return {
			success: false,
			error: error instanceof Error ? error.message : 'Unknown error',
			stats: {
				today: { tokens: 0, cost: 0, requests: 0, last_updated: 'Error loading data' },
				this_month: { tokens: 0, cost: 0, requests: 0, days_active: 0 },
				client_org_name: 'My Organization'
			},
			client_id: 'error'
		};
	}
};

export const getTodayUsage = async (token: string, _clientOrgId?: string) => {
	// DEPRECATED: This function is deprecated. Use getClientUsageSummary instead.
	console.warn('getTodayUsage is deprecated. Use getClientUsageSummary for daily breakdown data.');
	
	// Return mock data without making the deprecated API call
	return {
		success: false,
		deprecated: true,
		message: 'Real-time usage tracking has been simplified. Please use getClientUsageSummary for daily breakdown data.',
		alternative_function: 'getClientUsageSummary',
		today: { tokens: 0, cost: 0, requests: 0, last_updated: 'Deprecated - Use summary endpoint' }
	};
};

export const getUsageByUser = async (token: string, _clientOrgId?: string) => {
	try {
		const response = await fetch(`${BASE_URL}/my-organization/usage-by-user`, {
			method: 'GET',
			headers: {
				'Authorization': `Bearer ${token}`,
				'Content-Type': 'application/json'
			}
		});
		
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		
		return await response.json();
	} catch (error) {
		console.error('Failed to fetch usage by user:', error);
		return {
			success: false,
			error: error instanceof Error ? error.message : 'Unknown error',
			user_usage: []
		};
	}
};

export const getUsageByModel = async (token: string, _clientOrgId?: string) => {
	try {
		const response = await fetch(`${BASE_URL}/my-organization/usage-by-model`, {
			method: 'GET',
			headers: {
				'Authorization': `Bearer ${token}`,
				'Content-Type': 'application/json'
			}
		});
		
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		
		return await response.json();
	} catch (error) {
		console.error('Failed to fetch usage by model:', error);
		return {
			success: false,
			error: error instanceof Error ? error.message : 'Unknown error',
			model_usage: []
		};
	}
};

export const getMAIModelPricing = async () => {
	try {
		const response = await fetch(`${BASE_URL}/model-pricing`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		
		return await response.json();
	} catch (error) {
		console.error('Failed to fetch model pricing:', error);
		return {
			success: false,
			error: error instanceof Error ? error.message : 'Unknown error',
			models: []
		};
	}
};

export const getSubscriptionBilling = async (token: string, _clientOrgId?: string) => {
	try {
		const response = await fetch(`${BASE_URL}/my-organization/subscription-billing`, {
			method: 'GET',
			headers: {
				'Authorization': `Bearer ${token}`,
				'Content-Type': 'application/json'
			}
		});
		
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		
		return await response.json();
	} catch (error) {
		console.error('Failed to fetch subscription billing:', error);
		return {
			success: false,
			error: error instanceof Error ? error.message : 'Unknown error',
			subscription_data: null
		};
	}
};

export const getClientOrganizations = async (_token?: string) => {
	// This function is no longer needed in environment-based setup
	// Return empty array for backward compatibility
	return [];
};