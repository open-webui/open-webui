/**
 * Dashboard State Stores
 * Svelte stores for managing dashboard state and cached data
 */

import { writable, derived } from 'svelte/store';
import type {
	TenantDashboardConfig,
	OverviewMetric,
	LineMetrics,
	Incident,
	TimeSeriesPoint
} from '$lib/apis/dashboard';

// =============================================================================
// DASHBOARD SELECTION STATE
// =============================================================================

/** Currently selected tenant dashboard ID */
export const selectedTenantId = writable<string>('rmmc');

/** Currently selected line within the tenant */
export const selectedLine = writable<string | null>(null);

/** Currently selected system (uvbc, washer, etc.) */
export const selectedSystem = writable<string>('uvbc');

/** Currently selected secondary view option */
export const selectedSecondaryOption = writable<string>('metrics');

/** Date range for queries */
export const dateRange = writable<{ start: Date; end: Date; days: number }>({
	start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
	end: new Date(),
	days: 7
});

// =============================================================================
// TENANT CONFIGURATION CACHE
// =============================================================================

/** Cached tenant configurations */
export const tenantConfigCache = writable<Record<string, TenantDashboardConfig>>({});

/** Current tenant config (derived) */
export const currentTenantConfig = derived(
	[selectedTenantId, tenantConfigCache],
	([$selectedTenantId, $tenantConfigCache]) => {
		return $tenantConfigCache[$selectedTenantId] || null;
	}
);

// =============================================================================
// DATA CACHES
// =============================================================================

/** Cached overview metrics by tenant */
export const overviewCache = writable<Record<string, OverviewMetric[]>>({});

/** Current overview metrics (derived) */
export const currentOverview = derived(
	[selectedTenantId, overviewCache],
	([$selectedTenantId, $overviewCache]) => {
		return $overviewCache[$selectedTenantId] || [];
	}
);

/** Cached line metrics by tenant/line/system key */
export const lineMetricsCache = writable<Record<string, LineMetrics>>({});

/** Helper to get cache key for line metrics */
export const getLineMetricsCacheKey = (tenantId: string, lineId: string, system: string): string =>
	`${tenantId}:${lineId}:${system}`;

/** Cached incidents by tenant/line/system key */
export const incidentsCache = writable<Record<string, Incident[]>>({});

/** Helper to get cache key for incidents */
export const getIncidentsCacheKey = (tenantId: string, lineId: string, system: string): string =>
	`${tenantId}:${lineId}:${system}`;

/** Cached time series data by tenant/line/metric key */
export const timeSeriesCache = writable<Record<string, TimeSeriesPoint[]>>({});

/** Helper to get cache key for time series */
export const getTimeSeriesCacheKey = (
	tenantId: string,
	lineId: string,
	system: string,
	metric: string
): string => `${tenantId}:${lineId}:${system}:${metric}`;

// =============================================================================
// LOADING STATES
// =============================================================================

/** Loading state for overview data */
export const overviewLoading = writable<boolean>(false);

/** Loading state for line metrics */
export const lineMetricsLoading = writable<boolean>(false);

/** Loading state for incidents */
export const incidentsLoading = writable<boolean>(false);

/** Loading state for time series */
export const timeSeriesLoading = writable<boolean>(false);

// =============================================================================
// ERROR STATES
// =============================================================================

/** Error message for dashboard operations */
export const dashboardError = writable<string | null>(null);

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Reset all dashboard state to defaults
 */
export const resetDashboardState = () => {
	selectedTenantId.set('rmmc');
	selectedLine.set(null);
	selectedSystem.set('uvbc');
	selectedSecondaryOption.set('metrics');
	dateRange.set({
		start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
		end: new Date(),
		days: 7
	});
	dashboardError.set(null);
};

/**
 * Clear all cached data
 */
export const clearDashboardCaches = () => {
	tenantConfigCache.set({});
	overviewCache.set({});
	lineMetricsCache.set({});
	incidentsCache.set({});
	timeSeriesCache.set({});
};

/**
 * Set date range by days
 */
export const setDateRangeByDays = (days: number) => {
	const end = new Date();
	const start = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
	dateRange.set({ start, end, days });
};

// =============================================================================
// UI STATE
// =============================================================================

/** Whether dark mode is enabled */
export const isDarkMode = writable<boolean>(false);

/** Chart color palette */
export const chartColors = {
	primary: '#5CC9D3',
	secondary: '#F9A620',
	danger: '#dc2626',
	success: '#22c55e',
	line1: '#5CC9D3',
	line2: '#F9A620',
	line3: '#dc2626',
	line4: '#22c55e',
	line5: '#8b5cf6',
	line6: '#ec4899'
};
