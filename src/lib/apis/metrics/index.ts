import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';
import { error } from '@sveltejs/kit';

export const getDomains = async (token: string): Promise<string[]> => {
	try {
		const [usersRes, metricsRes] = await Promise.all([
			canchatAPI(`${WEBUI_API_BASE_PATH}/users/domains`, {
				method: 'GET'
			}),
			canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/domains`, {
				method: 'GET'
			})
		]);

		if (usersRes.status != 200) {
			const error = await usersRes.data;
			throw new Error(`Error ${usersRes.status}: ${error.detail || 'Failed to get user domains'}`);
		}
		if (metricsRes.status != 200) {
			const error = await metricsRes.data;
			throw new Error(
				`Error ${metricsRes.status}: ${error.detail || 'Failed to get metrics domains'}`
			);
		}

		const usersData = await usersRes.data;
		const metricsData = await metricsRes.data;

		const allDomains = [
			...(Array.isArray(usersData.domains) ? usersData.domains : []),
			...(Array.isArray(metricsData.domains) ? metricsData.domains : [])
		];

		// Return unique domains
		return Array.from(new Set(allDomains));
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getTotalUsers = async (token: string, domain?: string): Promise<number> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/count`, {
			method: 'GET',
			params: {
				domain: domain
			}
		})
			.then((res) => {
				return res.data || 0;
			})
			.catch((err) => {
				if (err.resposnse.status === 404) {
					return 0;
				}

				const error = err;
				throw new Error(
					`Error ${error.response.status}: ${error.response.data || 'Failed to get users'}`
				);
			});

		return res;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyUsers = async (token: string, domain?: string): Promise<number> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/daily/count`, {
			method: 'GET',
			params: {
				domain: domain
			}
		})
			.then((res) => {
				return res.data || 0;
			})
			.catch((err) => {
				if (err.resposnse.status === 404) {
					return 0;
				}

				const error = err;
				throw new Error(
					`Error ${error.response.status}: ${error.response.data || 'Failed to get daily users'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/enrollment/historical`, {
			method: 'GET',
			params: {
				days: days,
				domain: domain
			}
		})
			.then((res) => {
				return res.data || [];
			})
			.catch((err) => {
				if (err.resposnse.status === 404) {
					return generateFallbackDates(days);
				}

				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get historical users'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/historical/users/daily`, {
			method: 'GET',
			params: {
				days: days,
				domain: domain
			}
		})
			.then((res) => {
				return res.data.historical_daily_users || [];
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return generateFallbackDates(days);
				}

				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get historical daily users'}`
				);
			});

		return res;
	} catch (err) {
		console.error('Error fetching historical users:', err);
		return generateFallbackDates(days);
	}
};

export const getTotalPrompts = async (token: string, domain?: string): Promise<number> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/prompts`, {
			method: 'GET',
			params: {
				domain: domain
			}
		})
			.then((res) => {
				return res.data.total_prompts || 0;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return 0;
				}

				throw new Error(
					`Error ${err.response.status}: ${err.response.detail || 'Failed to get prompts'}`
				);
			});

		return res;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyPrompts = async (token: string, domain?: string): Promise<number> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/daily/prompts`, {
			method: 'GET',
			params: {
				domain: domain
			}
		})
			.then((res) => {
				return res.data.total_daily_prompts || 0;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return 0;
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get Users'}`
				);
			});

		return res;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getTotalTokens = async (token: string, domain?: string): Promise<number> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/tokens`, {
			method: 'GET',
			params: {
				domain: domain
			}
		})
			.then((res) => {
				return res.data.total_token || 0;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return 0;
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get tokens'}`
				);
			});

		return res;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyTokens = async (token: string, domain?: string): Promise<number> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/daily/tokens`, {
			method: 'GET',
			params: {
				domain: domain
			}
		})
			.then((res) => {
				return res.data.total_daily_tokens || 0;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return 0;
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get daily tokens'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/historical/prompts`, {
			method: 'GET',
			params: {
				days: days,
				domain: domain
			}
		})
			.then((res) => {
				return res.data.historical_prompts || [];
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return generateFallbackDates(days);
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get historical prompts'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/historical/tokens`, {
			method: 'GET',
			params: {
				days: days,
				domain: domain
			}
		})
			.then((res) => {
				return res.data.historical_tokens || [];
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return generateFallbackDates(days);
				}

				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get historical tokens'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/models`, {
			method: 'GET'
		})
			.then((res) => {
				return res.data.models;
			})
			.catch((err) => {
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get models'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/models/prompts`, {
			method: 'GET',
			params: {
				model: model,
				domain: domain
			}
		})
			.then((res) => {
				return res.data.total_prompts || 0;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return 0;
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get model prompts'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/models/daily/prompts`, {
			method: 'GET',
			params: {
				model: model,
				domain: domain
			}
		})
			.then((res) => {
				return res.data.total_daily_prompts || 0;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return 0;
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get model daily prompts'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/models/historical/prompts`, {
			method: 'GET',
			params: {
				days: days,
				model: model,
				domain: domain
			}
		})
			.then((res) => {
				return res.data.historical_prompts || [];
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return generateFallbackDates(days);
				}

				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get model historical prompts'}`
				);
			});

		return res;
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
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/range/users`, {
			method: 'GET',
			params: {
				startDate: startDate,
				endDate: endDate,
				domain: domain,
				model: model
			}
		})
			.then((res) => {
				return res.data;
			})
			.catch((err) => {
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get range metrics'}`
				);
			});

		return res;
	} catch (err) {
		console.error('Error fetching range metrics:', err);
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getInterPromptLatencyHistogram = async (
	token: string,
	domain?: string,
	model?: string
): Promise<{
	bins: string[];
	counts: number[];
	total_latencies: number;
}> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/inter-prompt-latency`, {
			method: 'GET',
			params: {
				domain: domain,
				model: model
			}
		})
			.then((res) => {
				return res.data;
			})
			.catch((err) => {
				if (err.response.status === 404) {
					return { bins: [], counts: [], total_latencies: 0 };
				}
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get inter-prompt latency histogram'}`
				);
			});

		return res;
	} catch (err) {
		console.error('Error fetching inter-prompt latency histogram:', err);
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const exportMetricsData = async (
	token: string,
	startDate: string,
	endDate: string,
	domain?: string
): Promise<Blob> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/export`, {
			method: 'POST',
			params: {
				startDate: startDate,
				endDate: endDate,
				domain: domain
			},
			responseType: 'blob'
		})
			.then((res) => {
				return res.data;
			})
			.catch((err) => {
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to export metrics data'}`
				);
			});

		return res;
	} catch (err) {
		console.error('Error exporting metrics data:', err);
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getExportLogs = async (token: string): Promise<any[]> => {
	try {
		const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/metrics/export/logs`, {
			method: 'GET'
		})
			.then((res) => {
				return res.data.export_logs || [];
			})
			.catch((err) => {
				throw new Error(
					`Error ${err.response.status}: ${err.response.data || 'Failed to get export logs'}`
				);
			});

		return res;
	} catch (err) {
		console.error('Error fetching export logs:', err);
		throw new Error(err.message || 'An unexpected error occurred');
	}
};
