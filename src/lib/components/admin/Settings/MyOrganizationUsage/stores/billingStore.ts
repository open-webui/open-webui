/**
 * Billing data store
 * State management for subscription billing information
 */

import { writable } from 'svelte/store';
import type { SubscriptionData, LoadingState } from '../types';

interface BillingState {
	subscriptionData: SubscriptionData | null;
	loading: LoadingState;
}

const initialState: BillingState = {
	subscriptionData: null,
	loading: { loading: false }
};

export const billingStore = writable<BillingState>(initialState);

export const billingActions = {
	/**
	 * Set subscription data
	 */
	setSubscriptionData: (data: SubscriptionData) => {
		billingStore.update(state => ({
			...state,
			subscriptionData: data
		}));
	},

	/**
	 * Set loading state
	 */
	setLoading: (loading: boolean, error?: string) => {
		billingStore.update(state => ({
			...state,
			loading: { loading, error }
		}));
	},

	/**
	 * Clear all data
	 */
	clear: () => {
		billingStore.set(initialState);
	},

	/**
	 * Reset error state
	 */
	clearError: () => {
		billingStore.update(state => ({
			...state,
			loading: { ...state.loading, error: undefined }
		}));
	}
};