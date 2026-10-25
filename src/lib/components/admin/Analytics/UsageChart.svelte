<script context="module" lang="ts">
	export type UsageBucket = {
		date: string;
		models: Record<string, number>;
		start?: string;
		end?: string;
		previous?: { models: Record<string, number>; start: string; end: string };
	};

	export const comparisonChange = (current: number, previous: number) =>
		previous === 0 ? (current === 0 ? 0 : null) : ((current - previous) / previous) * 100;

	export const usageShare = (value: number, total: number) => {
		if (total <= 0 || value <= 0) return '0%';
		const share = (value / total) * 100;
		return share < 0.1 ? '<0.1%' : `${share.toFixed(1)}%`;
	};

	export const chartSeries = (data: UsageBucket[], modelId: string | null = null) =>
		data
			.map((bucket) => ({
				...bucket,
				models: modelId ? { [modelId]: bucket.models[modelId] ?? 0 } : bucket.models,
				// Calendar keys have no timezone. UTC is only a plotting coordinate, not a query timestamp.
				time: Date.parse(
					`${bucket.date.length === 10 ? `${bucket.date}T00:00` : bucket.date.replace(' ', 'T')}Z`
				),
				value: modelId
					? (bucket.models[modelId] ?? 0)
					: Object.values(bucket.models).reduce((total, value) => total + value, 0)
			}))
			.sort((a, b) => a.time - b.time);

	export const chartCeiling = (max: number) => {
		if (max <= 4) return 4;
		const step = 10 ** Math.floor(Math.log10(max));
		return Math.ceil(max / step) * step;
	};

	export const modelTotals = (data: UsageBucket[]) => {
		const totals: Record<string, number> = Object.create(null);
		for (const bucket of data) {
			for (const [id, value] of Object.entries(bucket.models))
				totals[id] = (totals[id] ?? 0) + value;
		}
		return totals;
	};

	// Identity-based colors remain stable when the range, metric, or ranking changes.
	export const modelColor = (id: string) => {
		let hash = 0;
		for (const character of id) hash = (Math.imul(hash, 31) + character.charCodeAt(0)) | 0;
		return `hsl(${((hash % 360) + 360) % 360} 65% 52%)`;
	};

	export const intervalMinutes = {
		'10m': 10,
		hourly: 60,
		'3h': 180,
		'6h': 360,
		daily: 1440
	} as const;
	export type UsageInterval = keyof typeof intervalMinutes;

	export const defaultInterval = (period: string): UsageInterval =>
		period === '24h' ? '10m' : period === '7d' ? 'hourly' : period === '30d' ? '6h' : 'daily';

	export const intervalBreakdown = (
		models: Record<string, number>,
		modelIds: string[],
		modelId: string | null = null
	) => (modelId === null ? modelIds : [modelId]).map((id) => ({ id, value: models[id] ?? 0 }));
</script>

<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import tippy, { type Instance } from 'tippy.js';
	import dayjs from 'dayjs';

	export let data: UsageBucket[] = [];
	export let compare = false;
	export let granularity: UsageInterval = 'daily';
	export let metricLabel = '';
	export let modelNames: Record<string, string> = {};
	export let selectedModel: string | null = null;
	export let view: 'volume' | 'activity' = 'volume';
	const i18n = getContext<any>('i18n');
	let active: number | null = null;
	let keyboardIndex = 0;
	let plot: HTMLDivElement;
	let chartWidth = 0;
	const activityRowHeight = 28;
	let activityViewport: HTMLDivElement;
	let activityScrollTop = 0;
	let activityHeight = 336;
	let activityWidth = 0;
	let legendExpanded = false;
	$: legendColumns = Math.max(1, Math.floor((chartWidth + 16) / 256));
	$: legendLimit = legendColumns * 2 - 1;
	$: legendIds = legendExpanded ? ids : ids.slice(0, legendLimit);
	let tooltip: Instance | undefined;
	let tooltipContent: HTMLDivElement;
	let tooltipId = '';
	let anchor: HTMLElement | null = null;
	let activeModel: string | null = null;
	$: {
		data;
		selectedModel;
		view;
		compare;
		tooltip?.hide();
		active = null;
		activeModel = null;
		keyboardIndex = 0;
		resetActivityScroll();
	}
	$: totals = modelTotals(data);
	$: comparing = compare && view === 'volume';
	$: previousData = comparing
		? data.map((bucket) => ({ ...bucket, models: bucket.previous?.models ?? {} }))
		: [];
	$: previousTotals = modelTotals(previousData);
	$: ids = [...new Set([...Object.keys(totals), ...Object.keys(previousTotals)])].sort(
		(a, b) => (totals[b] ?? 0) - (totals[a] ?? 0) || a.localeCompare(b)
	);
	$: visibleIds = selectedModel ? [selectedModel] : ids;
	$: series = chartSeries(data, selectedModel);
	$: previousSeries = chartSeries(previousData, selectedModel);
	$: ceiling = chartCeiling(
		[...series, ...previousSeries].reduce((max, point) => Math.max(max, point.value), 0)
	);
	$: step = intervalMinutes[granularity] * 60000;
	$: start = series[0]?.time ?? 0;
	$: span = Math.max(step, (series[series.length - 1]?.time ?? start) - start + step);
	$: barWidth = Math.min((100 * step) / span, 12);
	$: hovered = active !== null ? series[active] : null;
	$: previousHovered = active !== null ? previousSeries[active] : null;
	$: change =
		hovered && previousHovered ? comparisonChange(hovered.value, previousHovered.value) : null;
	$: lineColor = selectedModel ? modelColor(selectedModel) : 'currentColor';
	$: linePaths = [series, previousSeries].map((points) =>
		points
			.map(
				(point) =>
					`${((point.time - start + step / 2) / span) * 100},${100 - (point.value / ceiling) * 100}`
			)
			.join(' ')
	);
	$: tooltipRows = hovered ? intervalBreakdown(hovered.models, visibleIds, activeModel) : [];
	$: hoveredModels = hovered ? data.find((bucket) => bucket.date === hovered.date)?.models : null;
	$: labels = [
		...new Set(
			chartWidth >= 480
				? [0, Math.floor((series.length - 1) / 2), series.length - 1]
				: [0, series.length - 1]
		)
	].filter((i) => i >= 0 && i < series.length);
	$: activityStart = Math.max(0, Math.floor(activityScrollTop / activityRowHeight) - 2);
	$: activityEnd = Math.min(
		visibleIds.length,
		Math.ceil((activityScrollTop + activityHeight) / activityRowHeight) + 2
	);
	$: getActivityLanes = activityLaneWindow(series);
	$: lanes = getActivityLanes(
		view === 'activity' ? visibleIds.slice(activityStart, activityEnd) : []
	);
	$: stacks =
		view === 'volume'
			? series.map((point) => visibleIds.filter((id) => (point.models[id] ?? 0) > 0))
			: [];
	$: activityPositions = series.map((point) => (point.time - start) / span);
	const name = (id: string) => modelNames[id] || id;
	$: numberFormat = new Intl.NumberFormat($i18n.language, {
		notation: 'compact',
		maximumFractionDigits: 1
	});
	const number = (value: number) => numberFormat.format(value);
	const dateLabel = (date: string) =>
		dayjs(date)
			.locale($i18n.language)
			.format(granularity === 'daily' ? 'MMM D' : 'MMM D, HH:mm');
	const position = (time: number) => ((time - start + step / 2) / span) * 100;
	function resetActivityScroll() {
		activityScrollTop = 0;
		if (activityViewport) activityViewport.scrollTop = 0;
	}

	// Preserve overlapping rows so scrolling only prepares and draws newly visible models.
	function activityLaneWindow(points: ReturnType<typeof chartSeries>) {
		type Lane = { id: string; peak: number; values: number[] };
		let cache = new Map<string, Lane>();
		return (ids: string[]) => {
			const next = new Map<string, Lane>();
			const lanes = ids.map((id) => {
				let lane = cache.get(id);
				if (!lane) {
					const values = points.map((point) => point.models[id] ?? 0);
					lane = { id, peak: values.reduce((peak, value) => Math.max(peak, value), 0), values };
				}
				next.set(id, lane);
				return lane;
			});
			cache = next;
			return lanes;
		};
	}
	async function navigate(event: KeyboardEvent, index: number) {
		const buttons = plot.querySelectorAll<HTMLButtonElement>('button[data-point]');
		const destinations: Record<string, number> = {
			ArrowRight: index + 1,
			ArrowLeft: index - 1,
			Home: 0,
			End: buttons.length - 1
		};
		if (view === 'activity') {
			destinations.ArrowDown = index + series.length;
			destinations.ArrowUp = index - series.length;
			destinations.End = visibleIds.length * series.length - 1;
		}
		const next = destinations[event.key];
		if (next === undefined) return;
		event.preventDefault();
		keyboardIndex = Math.max(
			0,
			Math.min((view === 'activity' ? visibleIds.length * series.length : buttons.length) - 1, next)
		);
		if (view === 'activity') {
			const row = Math.floor(keyboardIndex / series.length);
			const top = row * activityRowHeight;
			activityScrollTop = Math.max(
				top + activityRowHeight - activityHeight,
				Math.min(activityScrollTop, top)
			);
			activityViewport.scrollTop = activityScrollTop;
			await tick();
			const button = plot.querySelector<HTMLButtonElement>(`button[data-row="${row}"]`);
			button?.focus();
			showTooltip({ currentTarget: button }, keyboardIndex % series.length, visibleIds[row]);
		} else buttons[keyboardIndex]?.focus();
	}

	// One canvas and focus target per lane avoids a DOM element for every model/date pair.
	function drawActivity(
		canvas: HTMLCanvasElement,
		options: {
			lane: { id: string; peak: number; values: number[] };
			positions: number[];
			cellWidth: number;
			width: number;
		}
	) {
		function draw() {
			const { lane, positions, cellWidth } = options;
			const width = canvas.clientWidth;
			const height = canvas.clientHeight;
			const scale = window.devicePixelRatio || 1;
			canvas.width = Math.round(width * scale);
			canvas.height = Math.round(height * scale);
			const context = canvas.getContext('2d');
			if (!context) return;
			context.scale(scale, scale);
			context.fillStyle = modelColor(lane.id);
			lane.values.forEach((value, index) => {
				if (value <= 0) return;
				context.globalAlpha = 0.25 + (0.75 * value) / lane.peak;
				context.fillRect(positions[index] * width, 0, cellWidth * width, height);
			});
		}
		draw();
		return {
			update(next: typeof options) {
				if (
					next.lane === options.lane &&
					next.positions === options.positions &&
					next.cellWidth === options.cellWidth &&
					next.width === options.width
				)
					return;
				options = next;
				draw();
			},
			destroy() {
				canvas.width = 0;
				canvas.height = 0;
			}
		};
	}

	function hoverActivity(event: MouseEvent, id: string) {
		const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
		const time = start + Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * span;
		let low = 0;
		let high = series.length - 1;
		while (low < high) {
			const mid = Math.ceil((low + high) / 2);
			if (series[mid].time <= time) low = mid;
			else high = mid - 1;
		}
		if (time >= series[low].time + step && time < start + span) {
			hideTooltip();
			return;
		}
		if (active !== low || activeModel !== id) showTooltip(event, low, id);
	}

	onMount(() => {
		tooltip = tippy(plot, {
			content: tooltipContent,
			trigger: 'manual',
			theme: 'dark',
			arrow: false,
			placement: 'right-start',
			offset: [0, 12],
			popperOptions: {
				modifiers: [{ name: 'flip', options: { fallbackPlacements: ['left-start', 'top'] } }]
			},
			duration: 0,
			interactive: true,
			maxWidth: 'min(20rem, calc(100vw - 1rem))',
			appendTo: () => document.body,
			aria: { content: null, expanded: false },
			onHidden: () => {
				active = null;
				activeModel = null;
			},
			getReferenceClientRect: () => {
				const rect = (anchor ?? plot).getBoundingClientRect();
				const height = tooltip?.popper.offsetHeight || tooltipContent.offsetHeight;
				return new DOMRect(
					rect.x +
						rect.width *
							(view === 'activity' && active !== null ? position(series[active].time) / 100 : 0.5),
					plot.getBoundingClientRect().top - height / 2,
					0,
					0
				);
			}
		});
		tooltipId = tooltip.popper.id;
		return () => tooltip?.destroy();
	});
	async function showTooltip(
		event: { currentTarget: EventTarget | null },
		index: number,
		modelId: string | null = null
	) {
		anchor = event.currentTarget as HTMLElement;
		activeModel = modelId;
		active = index;
		await tick();
		if (
			active !== index ||
			activeModel !== modelId ||
			!anchor?.isConnected ||
			tooltip?.state.isDestroyed
		)
			return;
		tooltip?.clearDelayTimeouts();
		tooltip?.show();
		tooltip?.popperInstance?.update();
	}
	function leaveTooltip(event: MouseEvent) {
		tooltip?.hideWithInteractivity(event);
	}
	function hideTooltip() {
		tooltip?.hide();
		active = null;
		activeModel = null;
	}
	const intervalLabel = (date: string) => {
		const start = dayjs(date).locale($i18n.language);
		if (granularity === 'daily') return start.format('MMM D, YYYY');
		const end = start.add(intervalMinutes[granularity], 'minute');
		return `${start.format('MMM D, YYYY · HH:mm')}–${end.format(start.isSame(end, 'day') ? 'HH:mm' : 'MMM D, HH:mm')}`;
	};
	const comparisonInterval = (start: string, end: string) => {
		const from = dayjs(start).locale($i18n.language);
		const to = dayjs(end).locale($i18n.language);
		return `${from.format('MMM D, YYYY · HH:mm')}–${to.format(from.isSame(to, 'day') ? 'HH:mm' : 'MMM D, HH:mm')}`;
	};

	function isolate(id: string | null) {
		selectedModel = selectedModel === id ? null : id;
		active = null;
		keyboardIndex = 0;
	}
</script>

<svelte:window
	on:keydown|capture={(event) => {
		if (event.key === 'Escape' && tooltip?.state.isVisible) {
			event.stopPropagation();
			hideTooltip();
		}
	}}
/>

<div
	bind:clientWidth={chartWidth}
	class="min-w-0 text-xs font-normal text-gray-500 dark:text-gray-400"
>
	<div
		class="h-5 mb-2 flex min-w-0 items-center justify-between gap-3 text-[0.6875rem] tabular-nums"
		aria-live="polite"
		aria-atomic="true"
	>
		<span
			class="truncate"
			title={hovered ? dateLabel(hovered.date) : selectedModel ? name(selectedModel) : undefined}
			>{hovered
				? dateLabel(hovered.date)
				: selectedModel
					? name(selectedModel)
					: $i18n.t('All models')}</span
		>
		{#if comparing}
			<span class="flex shrink-0 items-center gap-3 text-[0.625rem]">
				<span class="flex items-center gap-1.5"
					><svg width="16" height="8" aria-hidden="true" class="text-gray-900 dark:text-gray-200"
						><path d="M0 4H16" stroke={lineColor} stroke-width="1.5" /></svg
					>{$i18n.t('Current')}</span
				>
				<span class="flex items-center gap-1.5"
					><svg
						width="16"
						height="8"
						aria-hidden="true"
						class="text-gray-900 dark:text-gray-200 opacity-50"
						><path d="M0 4H16" stroke={lineColor} stroke-width="1.5" stroke-dasharray="4 3" /></svg
					>{$i18n.t('Previous')}</span
				>
			</span>
		{:else}<span class="shrink-0 whitespace-nowrap"
				>{hovered
					? `${hovered.value.toLocaleString($i18n.language)} ${metricLabel.toLocaleLowerCase($i18n.language)}`
					: metricLabel}</span
			>{/if}
	</div>
	<div
		bind:this={plot}
		class="relative"
		role="group"
		aria-label={`${metricLabel} — ${$i18n.t('Use arrow keys to explore the chart')}`}
	>
		{#if view === 'volume'}
			<div class="relative h-40 pl-12">
				{#each [ceiling, ceiling * 0.75, ceiling / 2, ceiling * 0.25, 0] as tick}
					<div
						class="absolute inset-x-0 flex items-center gap-2 pointer-events-none translate-y-1/2"
						style:bottom={`${(tick / ceiling) * 100}%`}
					>
						<span class="w-10 shrink-0 text-right text-[0.6875rem] tabular-nums"
							>{number(tick)}</span
						>
						<span class="h-px flex-1 bg-gray-100 dark:bg-gray-850/50"></span>
					</div>
				{/each}
				<div class="relative h-full">
					{#if comparing}
						<svg
							class="pointer-events-none absolute inset-0 h-full w-full overflow-visible text-gray-900 dark:text-gray-200"
							viewBox="0 0 100 100"
							preserveAspectRatio="none"
							aria-hidden="true"
						>
							<polyline
								points={linePaths[1]}
								fill="none"
								stroke={lineColor}
								stroke-width="1.5"
								stroke-dasharray="4 4"
								opacity="0.5"
								vector-effect="non-scaling-stroke"
							/>
							<polyline
								points={linePaths[0]}
								fill="none"
								stroke={lineColor}
								stroke-width="1.5"
								stroke-linejoin="round"
								vector-effect="non-scaling-stroke"
							/>
						</svg>
					{/if}
					{#each series as point, index (point.date)}
						<button
							type="button"
							data-point
							class="absolute bottom-0 top-0 flex justify-center items-end focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
							style:left={`${position(point.time)}%`}
							style:width={`${comparing ? (100 * step) / span : barWidth}%`}
							style:transform="translateX(-50%)"
							tabindex={keyboardIndex === index ? 0 : -1}
							aria-describedby={active === index && activeModel === null ? tooltipId : undefined}
							aria-label={comparing && point.previous && point.start && point.end
								? `${$i18n.t('Current')}: ${comparisonInterval(point.start, point.end)}, ${point.value.toLocaleString($i18n.language)} ${metricLabel}. ${$i18n.t('Previous')}: ${comparisonInterval(point.previous.start, point.previous.end)}, ${previousSeries[index].value.toLocaleString($i18n.language)} ${metricLabel}`
								: `${dateLabel(point.date)}: ${point.value.toLocaleString($i18n.language)} ${metricLabel}. ${stacks[index].map((id) => `${name(id)}: ${point.models[id].toLocaleString($i18n.language)}`).join(', ')}`}
							on:mouseenter={(event) => showTooltip(event, index)}
							on:mouseleave={leaveTooltip}
							on:focus={(event) => {
								keyboardIndex = index;
								showTooltip(event, index);
							}}
							on:blur={hideTooltip}
							on:click={(event) => showTooltip(event, index)}
							on:keydown={(event) => navigate(event, index)}
						>
							{#if comparing}
								{#if active === index || series.length === 1}
									{#each [point.value, previousSeries[index].value] as value, period}
										<span
											class="absolute left-1/2 size-1.5 rounded-full bg-current text-gray-900 dark:text-gray-200"
											style:bottom={`${(value / ceiling) * 100}%`}
											style:transform="translate(-50%, 50%)"
											style:background-color={lineColor}
											style:opacity={period === 0 ? 1 : 0.5}
										></span>
									{/each}
								{/if}
							{:else}<span
									class="w-3/4 max-w-12 h-full flex flex-col-reverse justify-start"
									style:opacity={active === null || active === index ? 1 : 0.45}
								>
									{#each stacks[index] as id}
										<span
											class="block shrink-0 w-full"
											style:height={`${(point.models[id] / ceiling) * 100}%`}
											style:background-color={modelColor(id)}
										></span>
									{/each}
								</span>{/if}
						</button>
					{/each}
				</div>
			</div>
		{:else}
			<div
				bind:this={activityViewport}
				bind:clientHeight={activityHeight}
				bind:clientWidth={activityWidth}
				class="overflow-y-auto overscroll-contain"
				style:height={`${Math.min(visibleIds.length * activityRowHeight, 336)}px`}
				style:max-height="50vh"
				on:scroll={() => {
					if (activityScrollTop !== activityViewport.scrollTop) {
						activityScrollTop = activityViewport.scrollTop;
						hideTooltip();
					}
				}}
			>
				<div
					style:padding-top={`${activityStart * activityRowHeight}px`}
					style:padding-bottom={`${(visibleIds.length - activityEnd) * activityRowHeight}px`}
				>
					{#each lanes as lane, offset (lane.id)}
						{@const row = activityStart + offset}
						{@const index =
							Math.floor(keyboardIndex / series.length) === row ? keyboardIndex % series.length : 0}
						<div
							class="grid grid-cols-[7rem_minmax(0,1fr)] gap-2 items-center"
							style:height={`${activityRowHeight}px`}
						>
							<button
								type="button"
								class="text-left truncate py-1"
								title={name(lane.id)}
								aria-pressed={selectedModel === lane.id}
								on:click={() => isolate(lane.id)}>{name(lane.id)}</button
							>
							<button
								type="button"
								data-point
								data-row={row}
								class="relative h-6 bg-gray-100/70 dark:bg-gray-850/40 focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
								tabindex={Math.floor(keyboardIndex / series.length) === row ||
								(row === activityStart &&
									(Math.floor(keyboardIndex / series.length) < activityStart ||
										Math.floor(keyboardIndex / series.length) >= activityEnd))
									? 0
									: -1}
								aria-label={`${name(lane.id)}, ${dateLabel(series[index].date)}: ${lane.values[index].toLocaleString($i18n.language)} ${metricLabel}`}
								aria-describedby={activeModel === lane.id ? tooltipId : undefined}
								on:mousemove={(event) => hoverActivity(event, lane.id)}
								on:mouseleave={leaveTooltip}
								on:focus={(event) => {
									keyboardIndex = row * series.length + index;
									showTooltip(event, index, lane.id);
								}}
								on:blur={hideTooltip}
								on:click={(event) => hoverActivity(event, lane.id)}
								on:keydown={(event) => navigate(event, row * series.length + index)}
							>
								<canvas
									class="absolute inset-0 w-full h-full pointer-events-none"
									aria-hidden="true"
									use:drawActivity={{
										lane,
										positions: activityPositions,
										cellWidth: step / span,
										width: activityWidth
									}}
								></canvas>
							</button>
						</div>
					{/each}
				</div>
			</div>
		{/if}
		{#if hovered}
			<div
				class="pointer-events-none absolute inset-y-0 right-0 z-10"
				style:left={view === 'volume' ? '3rem' : '7.5rem'}
				style:right={view === 'activity' ? `${chartWidth - activityWidth}px` : '0'}
				aria-hidden="true"
			>
				<div
					class="absolute inset-y-0 w-px bg-gray-400/70 dark:bg-gray-300/70"
					style:left={`${position(hovered.time)}%`}
					style:transform="translateX(-50%)"
				></div>
			</div>
		{/if}
	</div>
	<div
		class="relative mt-2 h-4 text-[0.625rem] tabular-nums"
		style:margin-left={view === 'volume' ? '3rem' : '7.5rem'}
		style:margin-right={view === 'activity' ? `${chartWidth - activityWidth}px` : '0'}
	>
		{#each labels as index}
			<span
				class="absolute whitespace-nowrap"
				style:left={`${position(series[index].time)}%`}
				style:transform={series.length === 1
					? 'translateX(-50%)'
					: index === 0
						? 'none'
						: index === series.length - 1
							? 'translateX(-100%)'
							: 'translateX(-50%)'}>{dateLabel(series[index].date)}</span
			>
		{/each}
	</div>
	<div
		class="mt-2 grid items-center gap-x-4 gap-y-1 text-[0.6875rem]"
		style:grid-template-columns={`repeat(${legendColumns}, minmax(0, 1fr))`}
	>
		<button
			type="button"
			class="py-1 text-left"
			class:text-gray-900={selectedModel === null}
			class:dark:text-gray-200={selectedModel === null}
			aria-pressed={selectedModel === null}
			on:click={() => isolate(null)}>{$i18n.t('All models')}</button
		>
		{#each legendIds as id (id)}
			<button
				type="button"
				class="flex min-w-0 max-w-full items-center gap-1.5 py-1 text-left hover:text-gray-900 dark:hover:text-gray-100"
				style:opacity={selectedModel && selectedModel !== id ? 0.45 : 1}
				aria-label={`${name(id)} — ${$i18n.t('Select to isolate model')}`}
				aria-pressed={selectedModel === id}
				on:click={() => isolate(id)}
			>
				<span class="size-2 shrink-0" style:background-color={modelColor(id)}></span>
				<span class="max-w-40 truncate" title={name(id)}>{name(id)}</span>
				<span
					class="ml-auto w-14 shrink-0 text-right tabular-nums text-gray-400 dark:text-gray-500"
					title={(hovered ? (hoveredModels?.[id] ?? 0) : (totals[id] ?? 0)).toLocaleString(
						$i18n.language
					)}>{number(hovered ? (hoveredModels?.[id] ?? 0) : (totals[id] ?? 0))}</span
				>
			</button>
		{/each}
	</div>
	{#if ids.length > legendLimit}
		<button
			type="button"
			class="mt-1 py-1 text-[0.6875rem] hover:text-gray-900 dark:hover:text-gray-100"
			aria-expanded={legendExpanded}
			on:click={() => (legendExpanded = !legendExpanded)}
			>{legendExpanded ? $i18n.t('Show less') : $i18n.t('Show more')}</button
		>
	{/if}
	<p class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-500">
		{view === 'activity'
			? $i18n.t('Intensity relative to each model’s peak. Blank means no recorded usage.')
			: $i18n.t('Select a model to isolate it.')} · {$i18n.t('Server time')}
	</p>
</div>

<div class="hidden">
	<div
		bind:this={tooltipContent}
		class="w-64 max-w-full py-0.5 text-[0.625rem] leading-4 font-normal text-gray-100"
	>
		{#if hovered}
			{#if comparing && hovered.previous && previousHovered && hovered.start && hovered.end}
				<div class="truncate text-gray-400">
					{selectedModel ? name(selectedModel) : $i18n.t('All models')} · {metricLabel}
				</div>
				<div class="mt-1 space-y-0.5">
					{#each [{ label: $i18n.t('Current'), start: hovered.start, end: hovered.end, value: hovered.value }, { label: $i18n.t('Previous'), start: hovered.previous.start, end: hovered.previous.end, value: previousHovered.value }] as period, index}
						<div class="flex h-4 items-center justify-between gap-3">
							<span
								class="flex min-w-0 items-center gap-1.5"
								title={`${period.label}: ${period.start} – ${period.end}`}
							>
								<svg width="12" height="8" class="shrink-0" aria-hidden="true"
									><path
										d="M0 4H12"
										stroke={selectedModel ? modelColor(selectedModel) : 'currentColor'}
										stroke-width="1.5"
										stroke-dasharray={index === 1 ? '3 2' : undefined}
										opacity={index === 1 ? 0.5 : 1}
									/></svg
								>
								<span class="truncate text-gray-400"
									>{comparisonInterval(period.start, period.end)}</span
								>
							</span>
							<span class="shrink-0 tabular-nums"
								>{period.value.toLocaleString($i18n.language)}</span
							>
						</div>
					{/each}
					<div class="flex h-4 items-center justify-between gap-3 text-gray-400">
						<span>{$i18n.t('Change')}</span><span class="tabular-nums"
							>{change === null
								? $i18n.t('No previous usage')
								: `${change > 0 ? '+' : ''}${change.toLocaleString($i18n.language, { maximumFractionDigits: 1 })}%`}</span
						>
					</div>
				</div>
			{:else}
				<div class="truncate text-gray-400" title={intervalLabel(hovered.date)}>
					{intervalLabel(hovered.date)}
				</div>
				<div class="mt-1 max-h-48 overflow-y-auto scrollbar-hidden space-y-0.5">
					{#each tooltipRows as row (row.id)}
						<div
							class="flex h-4 items-center justify-between gap-3"
							class:text-gray-500={row.value === 0}
						>
							<span class="flex min-w-0 items-center gap-1.5"
								><span class="size-1.5 shrink-0" style:background-color={modelColor(row.id)}
								></span><span class="min-w-0 truncate" title={name(row.id)}>{name(row.id)}</span
								></span
							>
							<span class="shrink-0 whitespace-nowrap tabular-nums"
								>{row.value.toLocaleString($i18n.language)}
								<span class="text-gray-400">({usageShare(row.value, hovered.value)})</span></span
							>
						</div>
					{:else}<div class="text-gray-400">{$i18n.t('No activity in this period')}</div>{/each}
				</div>
			{/if}
		{/if}
	</div>
</div>
