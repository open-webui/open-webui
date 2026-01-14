<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { get } from 'svelte/store';

	import MetricCard from './Cards/MetricCard.svelte';
	import DPMOCard from './Cards/DPMOCard.svelte';
	import ToggleBar from './Toggle/ToggleBar.svelte';
	import ChipBar from './Toggle/ChipBar.svelte';
	import LineChart from './Charts/LineChart.svelte';

	import {
		getAvailableDashboards,
		getTenantConfig,
		getOverview,
		getLineMetrics,
		getTimeSeries,
		type TenantDashboardConfig,
		type OverviewMetric,
		type LineMetrics as LineMetricsType,
		type TimeSeriesPoint
	} from '$lib/apis/dashboard';

	import {
		selectedTenantId,
		selectedLine,
		selectedSystem,
		selectedSecondaryOption,
		dateRange,
		chartColors
	} from '$lib/stores/dashboard';

	const i18n = getContext('i18n');

	// Props
	export let token: string;

	// Local state
	let isDark = false;
	let loading = true;
	let error: string | null = null;
	let overviewLoading = false;
	let overviewError: string | null = null;
	let lineLoading = false;
	let lineError: string | null = null;
	let lineRequestId = 0;

	let availableTenants: { id: string; display_name: string }[] = [];
	let tenantConfig: TenantDashboardConfig | null = null;
	let overviewMetrics: OverviewMetric[] = [];
	let lineMetrics: LineMetricsType | null = null;
	let timeSeriesData: TimeSeriesPoint[] = [];

	// Computed
	$: currentDays = $dateRange.days;
	$: tenantChips = availableTenants.map((t) => ({ id: t.id, label: t.display_name }));
	$: supportedSystemsForLine =
		$selectedLine && tenantConfig?.line_systems?.[$selectedLine]
			? tenantConfig.line_systems[$selectedLine]
			: tenantConfig?.available_systems || [];
	$: systemOptions = supportedSystemsForLine.map((s) => s.toUpperCase());
	$: lineOptions = tenantConfig?.available_lines || [];
	$: secondaryOptions = ['Metrics', 'Orientation', 'Coating', 'System'];

	// Theme detection
	onMount(() => {
		isDark = document.documentElement.classList.contains('dark');

		const observer = new MutationObserver(() => {
			isDark = document.documentElement.classList.contains('dark');
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});

		loadDashboard();

		return () => observer.disconnect();
	});

	async function loadDashboard() {
		loading = true;
		error = null;

		try {
			// Load available tenants
			availableTenants = await getAvailableDashboards(token);

			// Load tenant config
			if ($selectedTenantId) {
				tenantConfig = await getTenantConfig(token, $selectedTenantId);

				// Set default line if not set
				if (!$selectedLine && tenantConfig.available_lines.length > 0) {
					selectedLine.set(tenantConfig.available_lines[0]);
				}

				// Ensure selected system is valid for the selected line
				const lineId = $selectedLine;
				const supportedSystems =
					(lineId && tenantConfig.line_systems?.[lineId]) || tenantConfig.available_systems || [];
				const desiredSystem = $selectedSystem.toLowerCase();
				if (!supportedSystems.includes(desiredSystem)) {
					selectedSystem.set(supportedSystems[0] || tenantConfig.available_systems[0] || 'uvbc');
				}

				// Load overview
				await loadOverview();

				// Load line metrics if line selected
				if ($selectedLine) {
					await loadLineData();
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load dashboard';
			console.error('Dashboard load error:', e);
		} finally {
			loading = false;
		}
	}

	async function loadOverview() {
		overviewLoading = true;
		overviewError = null;
		try {
			const response = await getOverview(token, $selectedTenantId, currentDays);
			overviewMetrics = response.metrics;
		} catch (e) {
			overviewError = e instanceof Error ? e.message : 'Failed to load overview';
			console.error('Failed to load overview:', e);
		} finally {
			overviewLoading = false;
		}
	}

	async function loadLineData() {
		const tenantId = $selectedTenantId;
		const lineId = $selectedLine;
		const system = $selectedSystem.toLowerCase();
		const days = currentDays;

		if (!tenantId || !lineId) return;

		const requestId = ++lineRequestId;
		lineLoading = true;
		lineError = null;
		lineMetrics = null;
		timeSeriesData = [];

		try {
			const [metrics, ts] = await Promise.all([
				getLineMetrics(token, tenantId, lineId, system, days),
				getTimeSeries(token, tenantId, lineId, 'down', system, 14)
			]);

			if (requestId !== lineRequestId) return;

			lineMetrics = metrics;
			timeSeriesData = ts.data;
		} catch (e) {
			if (requestId !== lineRequestId) return;
			lineError = e instanceof Error ? e.message : 'Failed to load line data';
			console.error('Failed to load line data:', e);
		} finally {
			if (requestId === lineRequestId) lineLoading = false;
		}
	}

	function handleTenantChange(tenantId: string) {
		selectedTenantId.set(tenantId);
		selectedLine.set(null);
		loadDashboard();
	}

	async function handleLineChange(line: string) {
		selectedLine.set(line);

		// Ensure selected system is valid for this line
		const supportedSystems = tenantConfig?.line_systems?.[line] || tenantConfig?.available_systems || [];
		if (supportedSystems.length > 0 && !supportedSystems.includes($selectedSystem.toLowerCase())) {
			selectedSystem.set(supportedSystems[0]);
		}

		await loadLineData();
	}

	async function handleSystemChange(system: string) {
		selectedSystem.set(system.toLowerCase());
		await loadLineData();
	}

	function handleSecondaryChange(option: string) {
		selectedSecondaryOption.set(option.toLowerCase());
	}

	function handleDaysChange(days: number) {
		dateRange.update((d) => ({
			...d,
			days,
			start: new Date(Date.now() - days * 24 * 60 * 60 * 1000)
		}));
		loadOverview();
		loadLineData();
	}
</script>

<div class="w-full h-full overflow-y-auto {isDark ? 'bg-gray-900' : 'bg-gray-50'}">
	<div class="p-6 space-y-6">
		<!-- Header -->
		<div class="flex flex-col gap-4">
			<div class="flex items-center justify-between">
				<h1 class="text-2xl font-bold {isDark ? 'text-white' : 'text-gray-900'}">
					{tenantConfig?.display_name || 'Quality Dashboard'}
				</h1>
				<div class="flex items-center gap-2">
					<select
						class="px-3 py-1.5 text-sm rounded-lg border {isDark
							? 'bg-gray-800 border-gray-700 text-white'
							: 'bg-white border-gray-300 text-gray-900'}"
						value={currentDays}
						on:change={(e) => handleDaysChange(parseInt(e.currentTarget.value))}
					>
						<option value={7}>Last 7 days</option>
						<option value={14}>Last 14 days</option>
						<option value={30}>Last 30 days</option>
					</select>
				</div>
			</div>

			<!-- Tenant selector -->
			{#if availableTenants.length > 1}
				<ChipBar
					chips={tenantChips}
					selected={$selectedTenantId}
					onSelect={handleTenantChange}
					{isDark}
				/>
			{/if}
		</div>

		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5CC9D3]"></div>
			</div>
		{:else if error}
			<div
				class="p-4 rounded-lg {isDark ? 'bg-red-900/50 text-red-200' : 'bg-red-50 text-red-700'}"
			>
				{error}
			</div>
		{:else}
			<!-- Overview Section -->
			<div class="space-y-4">
				<h2 class="text-lg font-semibold {isDark ? 'text-white' : 'text-gray-900'}">
					Overview
				</h2>
				{#if overviewLoading}
					<div class="flex items-center justify-center h-24">
						<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-[#5CC9D3]"></div>
					</div>
				{:else if overviewError}
					<div
						class="p-3 rounded-lg {isDark ? 'bg-red-900/50 text-red-200' : 'bg-red-50 text-red-700'}"
					>
						{overviewError}
					</div>
				{:else}
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
						{#each overviewMetrics as metric}
							<DPMOCard
								line={metric.line || metric.device_id || 'Unknown'}
								system={metric.system}
								dpmo={metric.dpmo}
								totalUnits={metric.total_units}
								changePercent={metric.change_percent}
								{isDark}
								onClick={() => metric.line && handleLineChange(metric.line)}
							/>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Line Details Section -->
			{#if $selectedLine && tenantConfig}
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold {isDark ? 'text-white' : 'text-gray-900'}">
							Line Details: {$selectedLine}
						</h2>
					</div>

					<!-- System Toggle -->
					{#if systemOptions.length > 1}
						<ToggleBar
							options={systemOptions}
							selected={$selectedSystem.toUpperCase()}
							onSelect={handleSystemChange}
							{isDark}
						/>
					{/if}

					<!-- Line Selector -->
					<div class="flex gap-2 flex-wrap">
						{#each lineOptions as line}
							<button
								class="px-3 py-1.5 text-sm rounded-lg border transition-all {$selectedLine === line
									? 'bg-[#5CC9D3] text-white border-[#5CC9D3]'
									: isDark
										? 'bg-gray-800 text-gray-300 border-gray-700 hover:border-[#5CC9D3]'
										: 'bg-white text-gray-700 border-gray-300 hover:border-[#5CC9D3]'}"
								on:click={() => handleLineChange(line)}
							>
								{line}
							</button>
						{/each}
					</div>

					<!-- Secondary Options -->
					<ToggleBar
						options={secondaryOptions}
						selected={$selectedSecondaryOption.charAt(0).toUpperCase() + $selectedSecondaryOption.slice(1)}
						onSelect={handleSecondaryChange}
						{isDark}
						size="sm"
					/>

					<!-- Metrics Cards -->
					{#if lineLoading}
						<div class="flex items-center justify-center h-24">
							<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-[#5CC9D3]"></div>
						</div>
					{:else if lineError}
						<div
							class="p-3 rounded-lg {isDark ? 'bg-red-900/50 text-red-200' : 'bg-red-50 text-red-700'}"
						>
							{lineError}
						</div>
					{:else if lineMetrics}
						{#if $selectedSystem.toLowerCase() === 'washer'}
							<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
								<MetricCard label="Total Units" value={lineMetrics.metrics?.total ?? 0} {isDark} />
								<MetricCard label="Down" value={lineMetrics.metrics?.down ?? 0} {isDark} />
								<MetricCard label="Inverted" value={lineMetrics.metrics?.inverted ?? 0} {isDark} />
								<MetricCard label="Avg FPS" value={lineMetrics.avg_fps} {isDark} />
							</div>
						{:else}
							<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-4">
								<MetricCard label="Total Units" value={lineMetrics.metrics?.total ?? 0} {isDark} />
								<MetricCard
									label="UV Down"
									value={lineMetrics.metrics?.down ?? 0}
									chipValue={(lineMetrics.metrics?.down ?? 0) > 0 && (lineMetrics.metrics?.total ?? 0) > 0
										? `${(((lineMetrics.metrics?.down ?? 0) / (lineMetrics.metrics?.total ?? 0)) * 100).toFixed(2)}%`
										: null}
									chipColor="red"
									{isDark}
								/>
								<MetricCard label="Edge" value={lineMetrics.metrics?.edge ?? 0} {isDark} />
								<MetricCard label="Inverted" value={lineMetrics.metrics?.inverted ?? 0} {isDark} />
								<MetricCard label="No Coats" value={lineMetrics.metrics?.no_coats ?? 0} {isDark} />
								<MetricCard label="Partials" value={lineMetrics.metrics?.partials ?? 0} {isDark} />
								<MetricCard label="Blobs" value={lineMetrics.metrics?.blobs ?? 0} {isDark} />
							</div>
						{/if}

						<!-- Chart Section -->
						<div
							class="p-4 rounded-lg border {isDark
								? 'bg-gray-800/50 border-gray-700/50'
								: 'bg-white border-gray-200'}"
						>
							<LineChart
								title={$selectedSystem.toLowerCase() === 'washer' ? 'Down Trend' : 'UV Down Trend'}
								subtitle="Last 14 days"
								data={timeSeriesData}
								color={chartColors.primary}
								{isDark}
								height={250}
							/>
						</div>
					{/if}

				</div>
			{/if}
		{/if}
	</div>
</div>
