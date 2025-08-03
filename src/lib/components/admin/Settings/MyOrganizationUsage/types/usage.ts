/**
 * Usage tracking type definitions
 * Daily batch processing data structures from OpenRouter integration
 */

export interface CurrentMonthUsage {
	month: string;
	total_tokens: number;
	total_cost: number;
	total_cost_pln: number;
	days_with_usage: number;
	days_in_month: number;
	usage_percentage: number;
	exchange_rate_info?: ExchangeRateInfo;
}

export interface DailyBreakdown {
	date: string;
	day_name: string;
	tokens: number;
	cost: number;
	cost_pln: number;
	primary_model: string;
	last_activity: string;
}

export interface TopModel {
	model_name: string;
	total_tokens: number;
}

export interface MonthlySummary {
	total_unique_users: number;
	top_models: TopModel[];
}

export interface ExchangeRateInfo {
	usd_pln: number;
	effective_date: string;
}

export interface UsageData {
	current_month: CurrentMonthUsage;
	daily_breakdown: DailyBreakdown[];
	monthly_summary: MonthlySummary;
	client_org_name: string;
	pln_conversion_available?: boolean;
}

export interface UserUsage {
	user_id: string;
	user_email: string;
	total_tokens: number;
	markup_cost: number;
	cost_pln: number;
	days_active: number;
}

export interface ModelUsage {
	model_name: string;
	provider: string;
	total_tokens: number;
	markup_cost: number;
	cost_pln: number;
	days_used: number;
}

export interface LoadingState {
	loading: boolean;
	error?: string;
}

export type TabType = 'stats' | 'users' | 'models' | 'subscription' | 'pricing';