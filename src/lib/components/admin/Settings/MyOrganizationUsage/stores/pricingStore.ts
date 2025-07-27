/**
 * Pricing data store
 * State management for model pricing information
 */

import { writable } from 'svelte/store';
import type { ModelPricing, LoadingState } from '../types';

interface PricingState {
	modelPricingData: ModelPricing[];
	loading: LoadingState;
}

const initialState: PricingState = {
	modelPricingData: [],
	loading: { loading: false }
};

export const pricingStore = writable<PricingState>(initialState);

export const pricingActions = {
	/**
	 * Set pricing data
	 */
	setPricingData: (data: ModelPricing[]) => {
		pricingStore.update(state => ({
			...state,
			modelPricingData: data
		}));
	},

	/**
	 * Set loading state
	 */
	setLoading: (loading: boolean, error?: string) => {
		pricingStore.update(state => ({
			...state,
			loading: { loading, error }
		}));
	},

	/**
	 * Clear all data
	 */
	clear: () => {
		pricingStore.set(initialState);
	},

	/**
	 * Reset error state
	 */
	clearError: () => {
		pricingStore.update(state => ({
			...state,
			loading: { ...state.loading, error: undefined }
		}));
	}
};