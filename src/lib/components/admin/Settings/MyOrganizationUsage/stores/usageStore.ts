/**
 * Usage data store
 * Centralized state management for usage statistics
 */

import { writable } from 'svelte/store';
import type { UsageData, UserUsage, ModelUsage, LoadingState, TabType } from '../types';

interface UsageState {
	usageData: UsageData | null;
	userUsageData: UserUsage[];
	modelUsageData: ModelUsage[];
	clientOrgId: string | null;
	clientOrgIdValidated: boolean;
	activeTab: TabType;
	loading: LoadingState;
}

const initialState: UsageState = {
	usageData: null,
	userUsageData: [],
	modelUsageData: [],
	clientOrgId: null,
	clientOrgIdValidated: false,
	activeTab: 'stats',
	loading: { loading: false }
};

export const usageStore = writable<UsageState>(initialState);

export const usageActions = {
	/**
	 * Set usage data from API response
	 */
	setUsageData: (data: UsageData, clientId?: string) => {
		usageStore.update(state => ({
			...state,
			usageData: data,
			clientOrgId: clientId || null,
			clientOrgIdValidated: Boolean(clientId && clientId !== 'current')
		}));
	},

	/**
	 * Set user usage data
	 */
	setUserUsageData: (data: UserUsage[]) => {
		usageStore.update(state => ({
			...state,
			userUsageData: data
		}));
	},

	/**
	 * Set model usage data
	 */
	setModelUsageData: (data: ModelUsage[]) => {
		usageStore.update(state => ({
			...state,
			modelUsageData: data
		}));
	},

	/**
	 * Set active tab
	 */
	setActiveTab: (tab: TabType) => {
		usageStore.update(state => ({
			...state,
			activeTab: tab
		}));
	},

	/**
	 * Set loading state
	 */
	setLoading: (loading: boolean, error?: string) => {
		usageStore.update(state => ({
			...state,
			loading: { loading, error }
		}));
	},

	/**
	 * Clear all data (for logout or refresh)
	 */
	clear: () => {
		usageStore.set(initialState);
	},

	/**
	 * Reset error state
	 */
	clearError: () => {
		usageStore.update(state => ({
			...state,
			loading: { ...state.loading, error: undefined }
		}));
	}
};