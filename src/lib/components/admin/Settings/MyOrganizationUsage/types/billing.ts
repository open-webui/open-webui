/**
 * Subscription billing type definitions
 * Multi-tenant organization billing with proportional calculations
 */

export interface UserDetail {
	user_name: string;
	user_email: string;
	created_date: string;
	days_remaining_when_added: number;
	billing_proportion: number;
	monthly_cost_pln: number;
}

export interface TierBreakdown {
	tier_range: string;
	price_per_user_pln: number;
	is_current_tier: boolean;
}

export interface CurrentMonthBilling {
	month: number;
	year: number;
	total_users: number;
	current_tier_price_pln: number;
	total_cost_pln: number;
	tier_breakdown: TierBreakdown[];
	user_details: UserDetail[];
}

export interface SubscriptionData {
	current_month: CurrentMonthBilling;
}