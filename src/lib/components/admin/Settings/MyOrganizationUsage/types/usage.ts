/**
 * Usage tracking type definitions
 * Daily batch processing data structures from OpenRouter integration
 */

export interface CurrentMonthUsage {
	month: string;
	total_tokens: number;
	total_cost: number;
	total_cost_pln: number;
	total_requests: number;
	days_with_usage: number;
	days_in_month: number;
	usage_percentage: number;
}

export interface DailyBreakdown {
	date: string;
	day_name: string;
	tokens: number;
	cost: number;
	cost_pln: number;
	requests: number;
	primary_model: string;
	last_activity: string;
}

export interface MonthlySummary {
	average_daily_tokens: number;
	average_daily_cost: number;
	average_usage_day_tokens: number;
	busiest_day: string | null;
	highest_cost_day: string | null;
	total_unique_users: number;
	most_used_model: string | null;
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
	exchange_rate_info?: ExchangeRateInfo;
	pln_conversion_available?: boolean;
}

export interface UserUsage {
	user_id: string;
	total_tokens: number;
	total_requests: number;
	markup_cost: number;
	cost_pln: number;
	days_active: number;
}

export interface ModelUsage {
	model_name: string;
	provider: string;
	total_tokens: number;
	total_requests: number;
	markup_cost: number;
	cost_pln: number;
	days_used: number;
}

export interface LoadingState {
	loading: boolean;
	error?: string;
}

export type TabType = 'stats' | 'users' | 'models' | 'subscription' | 'pricing';