/**
 * Organization Usage Service
 * API abstraction for usage tracking data with error handling
 */

import { 
	getClientUsageSummary, 
	getUsageByUser, 
	getUsageByModel, 
	getSubscriptionBilling 
} from '$lib/apis/organizations';
import type { UsageData, UserUsage, ModelUsage, SubscriptionData } from '../types';

export class OrganizationUsageService {
	private static readonly REQUEST_TIMEOUT = 10000; // 10 seconds

	/**
	 * Create timeout promise for API requests
	 */
	private static createTimeoutPromise(): Promise<never> {
		return new Promise((_, reject) => 
			setTimeout(() => reject(new Error('Request timeout')), this.REQUEST_TIMEOUT)
		);
	}

	/**
	 * Get usage summary with timeout protection
	 */
	static async getUsageSummary(token: string): Promise<{
		success: boolean;
		data?: UsageData;
		clientId?: string;
		error?: string;
	}> {
		try {
			const response = await Promise.race([
				getClientUsageSummary(token),
				this.createTimeoutPromise()
			]);

			// Debug: Log raw API response
			console.log('🔍 Service - Raw API response:', response);
			console.log('🔍 Service - response.stats:', response?.stats);
			console.log('🔍 Service - response.stats.monthly_summary:', response?.stats?.monthly_summary);

			if (response?.success && response.stats) {
				return {
					success: true,
					data: response.stats,
					clientId: response.client_id !== 'current' ? response.client_id : undefined
				};
			}

			return {
				success: false,
				error: 'Invalid response from usage summary API'
			};
		} catch (error) {
			console.error('Failed to load usage data:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown error'
			};
		}
	}

	/**
	 * Get per-user usage data
	 */
	static async getUserUsage(token: string, clientId: string): Promise<{
		success: boolean;
		data?: UserUsage[];
		error?: string;
	}> {
		try {
			const response = await getUsageByUser(token, clientId);
			
			// Debug: Log the actual API response
			console.log('🔍 getUserUsage - Raw API response:', response);
			console.log('🔍 getUserUsage - response.success:', response?.success);
			console.log('🔍 getUserUsage - response.user_usage:', response?.user_usage);
			
			// Accept response if it has user_usage array (even if success is false)
			if (response && Array.isArray(response.user_usage)) {
				return {
					success: true,
					data: response.user_usage
				};
			}

			return {
				success: false,
				error: 'Invalid response from user usage API'
			};
		} catch (error) {
			console.error('Failed to load user usage:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown error'
			};
		}
	}

	/**
	 * Get per-model usage data
	 */
	static async getModelUsage(token: string, clientId: string): Promise<{
		success: boolean;
		data?: ModelUsage[];
		error?: string;
	}> {
		try {
			const response = await getUsageByModel(token, clientId);
			
			if (response?.success && response.model_usage) {
				return {
					success: true,
					data: response.model_usage
				};
			}

			return {
				success: false,
				error: 'Invalid response from model usage API'
			};
		} catch (error) {
			console.error('Failed to load model usage:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown error'
			};
		}
	}

	/**
	 * Get subscription billing data
	 */
	static async getSubscriptionBilling(token: string, clientId: string): Promise<{
		success: boolean;
		data?: SubscriptionData;
		error?: string;
	}> {
		try {
			const response = await getSubscriptionBilling(token, clientId);
			
			if (response?.success && response.subscription_data) {
				return {
					success: true,
					data: response.subscription_data
				};
			}

			return {
				success: false,
				error: 'Invalid response from subscription API'
			};
		} catch (error) {
			console.error('Failed to load subscription data:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown error'
			};
		}
	}

	/**
	 * Create empty usage data for error states
	 */
	static createEmptyUsageData(errorMsg: string = 'No Data'): UsageData {
		return {
			current_month: {
				month: errorMsg,
				total_tokens: 0,
				total_cost: 0,
				total_cost_pln: 0,
				total_requests: 0,
				days_with_usage: 0,
				days_in_month: new Date().getDate(),
				usage_percentage: 0
			},
			daily_breakdown: [],
			monthly_summary: {
				total_unique_users: 0,
				top_models: []
			},
			client_org_name: errorMsg
		};
	}
}