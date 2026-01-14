/**
 * Dashboard API Client
 * Generic, tenant-configurable dashboard API client
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export type TenantDashboardInfo = {
	id: string;
	display_name: string;
};

export type MetricDefinition = {
	column: string;
	label: string;
};

export type TenantDashboardConfig = {
	id: string;
	display_name: string;
	available_lines: string[];
	available_systems: string[];
	line_systems?: Record<string, string[]>;
	metrics: Record<string, MetricDefinition>;
	default_period_days: number;
};

export type OverviewMetric = {
	device_id: string;
	line: string | null;
	system: string | null;
	total_units: number;
	defect_count: number;
	dpmo: number;
	change_percent: number;
};

export type OverviewResponse = {
	tenant_id: string;
	metrics: OverviewMetric[];
	period_days: number;
};

export type LineMetrics = {
	tenant_id: string;
	line_id: string;
	system: string;
	device_id: string | null;
	avg_fps: number;
	metrics: Record<string, number>;
};

export type Incident = {
	time: string;
	device_id: string;
	line_id: string;
	system: string;
	inc_hits: number;
	down: number;
	inverted: number;
	down_conf: number;
	inverted_conf: number;
	uuid: string | null;
	image_url: string | null;
};

export type IncidentsResponse = {
	tenant_id: string;
	line_id: string;
	incidents: Incident[];
	total: number;
};

export type TimeSeriesPoint = {
	time: string;
	value: number;
};

export type TimeSeriesResponse = {
	tenant_id: string;
	line_id: string;
	metric: string;
	data: TimeSeriesPoint[];
	period_days: number;
};

export type IntensityStats = {
	time: string;
	ring: number;
	average_intensity: number;
	min_intensity: number;
	max_intensity: number;
	median_intensity: number;
	std_deviation: number;
};

export type IntensityResponse = {
	tenant_id: string;
	line_id: string;
	data: IntensityStats[];
};

export type PartialRingData = {
	ring_percentage: number;
	count: number;
};

export type PartialRingResponse = {
	tenant_id: string;
	line_id: string;
	data: PartialRingData[];
};

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Get list of available tenant dashboards
 */
export const getAvailableDashboards = async (token: string): Promise<TenantDashboardInfo[]> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/tenants`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch dashboards' }));
		throw new Error(error.detail || 'Failed to fetch dashboards');
	}

	const data = await res.json();
	return data.tenants;
};

/**
 * Get configuration for a specific tenant dashboard
 */
export const getTenantConfig = async (
	token: string,
	tenantId: string
): Promise<TenantDashboardConfig> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch tenant config' }));
		throw new Error(error.detail || 'Failed to fetch tenant config');
	}

	return res.json();
};

/**
 * Get overview metrics for a tenant
 */
export const getOverview = async (
	token: string,
	tenantId: string,
	days: number = 7
): Promise<OverviewResponse> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/overview?days=${days}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch overview' }));
		throw new Error(error.detail || 'Failed to fetch overview');
	}

	return res.json();
};

/**
 * Get detailed metrics for a specific line
 */
export const getLineMetrics = async (
	token: string,
	tenantId: string,
	lineId: string,
	system: string = 'uvbc',
	days: number = 7
): Promise<LineMetrics> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/lines/${lineId}/metrics?system=${system}&days=${days}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch line metrics' }));
		throw new Error(error.detail || 'Failed to fetch line metrics');
	}

	return res.json();
};

/**
 * Get incidents for a line
 */
export const getIncidents = async (
	token: string,
	tenantId: string,
	lineId: string,
	options: {
		system?: string;
		limit?: number;
		largeOnly?: boolean;
		days?: number;
	} = {}
): Promise<IncidentsResponse> => {
	const { system = 'washer', limit = 50, largeOnly = false, days = 7 } = options;

	const params = new URLSearchParams({
		system,
		limit: limit.toString(),
		large_only: largeOnly.toString(),
		days: days.toString()
	});

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/lines/${lineId}/incidents?${params}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch incidents' }));
		throw new Error(error.detail || 'Failed to fetch incidents');
	}

	return res.json();
};

/**
 * Get time series data for charting
 */
export const getTimeSeries = async (
	token: string,
	tenantId: string,
	lineId: string,
	metric: string = 'down',
	system: string = 'uvbc',
	days: number = 14
): Promise<TimeSeriesResponse> => {
	const params = new URLSearchParams({
		metric,
		system,
		days: days.toString()
	});

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/lines/${lineId}/timeseries?${params}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch time series' }));
		throw new Error(error.detail || 'Failed to fetch time series');
	}

	return res.json();
};

/**
 * Get UVBC intensity data
 */
export const getUVBCIntensity = async (
	token: string,
	tenantId: string,
	lineId: string,
	days: number = 7
): Promise<IntensityResponse> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/uvbc/${lineId}/intensity?days=${days}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch UVBC intensity' }));
		throw new Error(error.detail || 'Failed to fetch UVBC intensity');
	}

	return res.json();
};

/**
 * Get partial ring data
 */
export const getPartialRings = async (
	token: string,
	tenantId: string,
	lineId: string,
	days: number = 7
): Promise<PartialRingResponse> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/dashboard/tenants/${tenantId}/uvbc/${lineId}/partials?days=${days}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to fetch partial rings' }));
		throw new Error(error.detail || 'Failed to fetch partial rings');
	}

	return res.json();
};

/**
 * Clear dashboard cache (admin only)
 */
export const clearDashboardCache = async (token: string): Promise<{ status: string; message: string }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/cache/clear`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Failed to clear cache' }));
		throw new Error(error.detail || 'Failed to clear cache');
	}

	return res.json();
};
