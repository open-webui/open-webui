/**
 * Pricing Service
 * Model pricing data management with fallback support
 */

import { getMAIModelPricing } from '$lib/apis/organizations';
import type { ModelPricing, ModelPricingResponse } from '../types';

export class PricingService {
	/**
	 * Fallback pricing data for when API fails
	 */
	private static readonly FALLBACK_PRICING: ModelPricing[] = [
		{
			id: 'anthropic/claude-sonnet-4',
			name: 'Claude Sonnet 4',
			provider: 'Anthropic',
			price_per_million_input: 8.00,
			price_per_million_output: 24.00,
			context_length: 1000000,
			category: 'Premium'
		},
		{
			id: 'google/gemini-2.5-flash',
			name: 'Gemini 2.5 Flash',
			provider: 'Google',
			price_per_million_input: 1.50,
			price_per_million_output: 6.00,
			context_length: 2000000,
			category: 'Fast'
		},
		{
			id: 'google/gemini-2.5-pro',
			name: 'Gemini 2.5 Pro',
			provider: 'Google',
			price_per_million_input: 3.00,
			price_per_million_output: 12.00,
			context_length: 2000000,
			category: 'Premium'
		},
		{
			id: 'deepseek/deepseek-chat-v3-0324',
			name: 'DeepSeek Chat v3',
			provider: 'DeepSeek',
			price_per_million_input: 0.14,
			price_per_million_output: 0.28,
			context_length: 128000,
			category: 'Budget'
		},
		{
			id: 'anthropic/claude-3.7-sonnet',
			name: 'Claude 3.7 Sonnet',
			provider: 'Anthropic',
			price_per_million_input: 6.00,
			price_per_million_output: 18.00,
			context_length: 200000,
			category: 'Premium'
		},
		{
			id: 'google/gemini-2.5-flash-lite-preview-06-17',
			name: 'Gemini 2.5 Flash Lite',
			provider: 'Google',
			price_per_million_input: 0.50,
			price_per_million_output: 2.00,
			context_length: 1000000,
			category: 'Budget'
		},
		{
			id: 'openai/gpt-4.1',
			name: 'GPT-4.1',
			provider: 'OpenAI',
			price_per_million_input: 10.00,
			price_per_million_output: 30.00,
			context_length: 128000,
			category: 'Premium'
		},
		{
			id: 'x-ai/grok-4',
			name: 'Grok 4',
			provider: 'xAI',
			price_per_million_input: 8.00,
			price_per_million_output: 24.00,
			context_length: 131072,
			category: 'Premium'
		},
		{
			id: 'openai/gpt-4o-mini',
			name: 'GPT-4o Mini',
			provider: 'OpenAI',
			price_per_million_input: 0.15,
			price_per_million_output: 0.60,
			context_length: 128000,
			category: 'Budget'
		},
		{
			id: 'openai/o4-mini-high',
			name: 'O4 Mini High',
			provider: 'OpenAI',
			price_per_million_input: 3.00,
			price_per_million_output: 12.00,
			context_length: 128000,
			category: 'Standard'
		},
		{
			id: 'openai/o3',
			name: 'O3',
			provider: 'OpenAI',
			price_per_million_input: 60.00,
			price_per_million_output: 240.00,
			context_length: 200000,
			category: 'Reasoning'
		},
		{
			id: 'openai/chatgpt-4o-latest',
			name: 'ChatGPT-4o Latest',
			provider: 'OpenAI',
			price_per_million_input: 5.00,
			price_per_million_output: 15.00,
			context_length: 128000,
			category: 'Standard'
		}
	];

	/**
	 * Load model pricing with fallback support
	 */
	static async getModelPricing(): Promise<{
		success: boolean;
		data: ModelPricing[];
		error?: string;
	}> {
		try {
			console.log('[DEBUG] PricingService: Starting getModelPricing()');
			const response: ModelPricingResponse = await getMAIModelPricing();
			console.log('[DEBUG] PricingService: API response:', response);
			
			// Check if we have valid models data (success=true and non-empty models array)
			if (response?.success && response.models && response.models.length > 0) {
				console.log('[DEBUG] PricingService: Using API data, models count:', response.models.length);
				return {
					success: true,
					data: response.models
				};
			}

			// Use fallback data if API failed or returned empty models
			// Backend returns success=false when using fallback, or models could be empty array
			console.log('[DEBUG] PricingService: Using fallback data, fallback count:', this.FALLBACK_PRICING.length);
			const fallbackData = response?.models && response.models.length > 0 ? response.models : this.FALLBACK_PRICING;
			console.log('[DEBUG] PricingService: Final fallback data count:', fallbackData.length);
			return {
				success: true,
				data: fallbackData
			};
		} catch (error) {
			console.error('Failed to load model pricing:', error);
			console.log('[DEBUG] PricingService: Using fallback after error, count:', this.FALLBACK_PRICING.length);
			return {
				success: true, // Still success with fallback data
				data: this.FALLBACK_PRICING,
				error: error instanceof Error ? error.message : 'Unknown error'
			};
		}
	}

	/**
	 * Get available pricing categories
	 */
	static getCategories(): string[] {
		return ['Budget', 'Standard', 'Premium', 'Fast', 'Reasoning'];
	}

	/**
	 * Filter models by category
	 */
	static filterByCategory(models: ModelPricing[], category: string): ModelPricing[] {
		return models.filter(model => model.category === category);
	}

	/**
	 * Get category color class for UI
	 */
	static getCategoryColorClass(category: string): string {
		switch (category) {
			case 'Budget': return 'bg-green-100 text-green-800';
			case 'Standard': return 'bg-blue-100 text-blue-800';
			case 'Premium': return 'bg-purple-100 text-purple-800';
			case 'Fast': return 'bg-orange-100 text-orange-800';
			case 'Reasoning': return 'bg-red-100 text-red-800';
			default: return 'bg-gray-100 text-gray-800';
		}
	}
}