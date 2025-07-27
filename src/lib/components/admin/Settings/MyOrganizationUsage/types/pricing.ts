/**
 * Model pricing type definitions
 * Dynamic pricing from OpenRouter API with fallback data
 */

export interface ModelPricing {
	id: string;
	name: string;
	provider: string;
	price_per_million_input: number;
	price_per_million_output: number;
	context_length: number;
	category: 'Budget' | 'Standard' | 'Premium' | 'Fast' | 'Reasoning';
}

export interface ModelPricingResponse {
	success: boolean;
	models: ModelPricing[];
}

export type PricingCategory = ModelPricing['category'];