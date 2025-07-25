import { WEBUI_API_BASE_URL } from '$lib/constants';

//////////////////////////
// Client Organizations API
//////////////////////////

export const getOpenRouterClientSettings = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/settings`, {
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateOpenRouterClientSettings = async (token: string, settings: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/settings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(settings)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getClientOrganizations = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/clients`, {
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

export const createClientOrganization = async (token: string, clientData: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/clients`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(clientData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateClientOrganization = async (token: string, clientId: string, updates: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/clients/${clientId}`, {
		method: 'PATCH',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(updates)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deactivateClientOrganization = async (token: string, clientId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/clients/${clientId}`, {
		method: 'DELETE',
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUserMappings = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/user-mappings`, {
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

export const createUserMapping = async (token: string, mappingData: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/user-mappings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(mappingData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deactivateUserMapping = async (token: string, userId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/user-mappings/${userId}`, {
		method: 'DELETE',
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getClientUsageSummary = async (token: string, clientId?: string) => {
	let error = null;

	// Use the my-organization endpoint for regular users
	const url = clientId 
		? `${WEBUI_API_BASE_URL}/client-organizations/usage/summary?client_id=${clientId}`
		: `${WEBUI_API_BASE_URL}/client-organizations/usage/my-organization`;

	const res = await fetch(url, {
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getTodayUsage = async (token: string, clientId: string) => {
	let error = null;

	// Use the my-organization endpoint for 'current' client ID
	const url = clientId === 'current'
		? `${WEBUI_API_BASE_URL}/client-organizations/usage/my-organization/today`
		: `${WEBUI_API_BASE_URL}/client-organizations/usage/today?client_id=${clientId}`;

	const res = await fetch(url, {
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBillingSummary = async (token: string, daysBack: number = 30) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client-organizations/usage/billing?days_back=${daysBack}`, {
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
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUsageByUser = async (token: string, clientId: string, startDate?: string, endDate?: string) => {
	let error = null;
	let url = `${WEBUI_API_BASE_URL}/client-organizations/usage/by-user/${clientId}`;
	
	const params = new URLSearchParams();
	if (startDate) params.append('start_date', startDate);
	if (endDate) params.append('end_date', endDate);
	if (params.toString()) url += `?${params.toString()}`;

	const res = await fetch(url, {
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
			console.log(err);
			error = err.detail ?? 'Failed to fetch user usage';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

//////////////////////////
// OpenRouter Direct API
//////////////////////////

/**
 * Fetch model pricing directly from OpenRouter API
 * Based on RAG research: GET https://openrouter.ai/api/v1/models
 * Returns comprehensive model data with pricing information
 */
export const getOpenRouterModelPricing = async () => {
	let error = null;

	const res = await fetch('https://openrouter.ai/api/v1/models', {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
			// No authorization required - public API endpoint
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log('OpenRouter API error:', err);
			error = err.detail ?? 'Failed to fetch OpenRouter models';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Get filtered model pricing for mAI's 12 configured models with 1.3x markup
 * Based on the production configuration from scripts/openrouter/production_fix.py
 */
export const getMAIModelPricing = async () => {
	const MARKUP_RATE = 1.3;
	const MAI_MODEL_IDS = [
		'anthropic/claude-sonnet-4',
		'google/gemini-2.5-flash',
		'google/gemini-2.5-pro',
		'deepseek/deepseek-chat-v3-0324',
		'anthropic/claude-3.7-sonnet',
		'google/gemini-2.5-flash-lite-preview-06-17',
		'openai/gpt-4.1',
		'x-ai/grok-4',
		'openai/gpt-4o-mini',
		'openai/o4-mini-high',
		'openai/o3',
		'openai/chatgpt-4o-latest'
	];

	try {
		const openRouterData = await getOpenRouterModelPricing();
		
		if (!openRouterData?.data) {
			throw new Error('Invalid OpenRouter API response');
		}

		// Filter and transform models for mAI
		const maiModels = openRouterData.data
			.filter(model => MAI_MODEL_IDS.includes(model.id))
			.map(model => {
				const pricing = model.pricing || {};
				const basePromptPrice = parseFloat(pricing.prompt || '0');
				const baseCompletionPrice = parseFloat(pricing.completion || '0');

				return {
					id: model.id,
					name: model.name || model.id.split('/')[1],
					provider: model.id.split('/')[0],
					price_per_million_input: (basePromptPrice * MARKUP_RATE) * 1000000,
					price_per_million_output: (baseCompletionPrice * MARKUP_RATE) * 1000000,
					context_length: model.context_length || 0,
					category: categorizeModel(model.id, basePromptPrice),
					description: model.description || '',
					created: model.created || 0
				};
			});

		return {
			success: true,
			models: maiModels,
			markup_rate: MARKUP_RATE,
			total_models: maiModels.length,
			last_updated: new Date().toISOString()
		};

	} catch (error) {
		console.error('Failed to fetch mAI model pricing:', error);
		throw error;
	}
};

/**
 * Categorize model based on ID and pricing
 * Helper function for model classification
 */
function categorizeModel(modelId: string, promptPrice: number): string {
	if (modelId.includes('deepseek') || modelId.includes('gpt-4o-mini') || modelId.includes('flash-lite')) {
		return 'Budget';
	}
	if (modelId.includes('claude-sonnet-4') || modelId.includes('gemini-2.5-pro') || modelId.includes('gpt-4.1') || modelId.includes('grok')) {
		return 'Premium';
	}
	if (modelId.includes('flash') && !modelId.includes('lite')) {
		return 'Fast';
	}
	if (modelId.includes('/o3')) {
		return 'Reasoning';
	}
	return 'Standard';
}

export const getUsageByModel = async (token: string, clientId: string, startDate?: string, endDate?: string) => {
	let error = null;
	let url = `${WEBUI_API_BASE_URL}/client-organizations/usage/by-model/${clientId}`;
	
	const params = new URLSearchParams();
	if (startDate) params.append('start_date', startDate);
	if (endDate) params.append('end_date', endDate);
	if (params.toString()) url += `?${params.toString()}`;

	const res = await fetch(url, {
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
			console.log(err);
			error = err.detail ?? 'Failed to fetch model usage';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};