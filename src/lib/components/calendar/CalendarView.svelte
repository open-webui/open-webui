<script lang="ts">
	import { focusIfLost } from '$lib/utils/listFocus';
	import { createEventDispatcher, getContext, tick } from 'svelte';
	import { settings } from '$lib/stores';
	import type { CalendarEventModel, CalendarModel } from '$lib/apis/calendar';
	import CalendarEventChip from './CalendarEventChip.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const dispatch = createEventDispatcher();

	export let events: CalendarEventModel[] = [];
	export let calendars: CalendarModel[] = [];
	export let visibleCalendarIds: Set<string> = new Set();
	export let view: 'month' | 'week' | 'day' = 'month';
	export let currentDate: Date = new Date();
	export let onNavigate: () => void = () => {};

	let grid: HTMLElement;
	const NS = 1_000_000;
	$: DAY_NAMES = [
		$i18n.t('Sun'),
		$i18n.t('Mon'),
		$i18n.t('Tue'),
		$i18n.t('Wed'),
		$i18n.t('Thu'),
		$i18n.t('Fri'),
		$i18n.t('Sat')
	];

	$: calColorMap = calendars.reduce(
		(acc, c) => ({ ...acc, [c.id]: c.color }),
		{} as Record<string, string | null>
	);
	$: filteredEvents = events.filter((e) => visibleCalendarIds.has(e.calendar_id));

	// Pre-group events by day key so the template reactively updates when events change
	$: eventsByDay = (() => {
		const map: Record<string, CalendarEventModel[]> = {};
		for (const e of filteredEvents) {
			const startMs = e.start_at / NS;
			const endMs = Math.max(startMs, (e.end_at || e.start_at) / NS - 1);
			// Get local midnight for event start/end
			const startDate = new Date(startMs);
			const endDate = new Date(endMs);
			const d = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
			const last = Math.max(
				d.getTime(),
				new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate()).getTime()
			);
			while (d.getTime() <= last) {
				const key = d.getTime().toString();
				(map[key] ??= []).push(e);
				d.setDate(d.getDate() + 1);
			}
		}
		return map;
	})();

	$: monthStart = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
	$: calendarStart = (() => {
		const d = new Date(monthStart);
		d.setDate(d.getDate() - d.getDay());
		return d;
	})();

	$: monthDays = (() => {
		const days: Date[] = [];
		const d = new Date(calendarStart);
		for (let i = 0; i < 42; i++) {
			days.push(new Date(d));
			d.setDate(d.getDate() + 1);
		}
		return days;
	})();

	$: weekStart = (() => {
		const d = new Date(currentDate);
		d.setDate(d.getDate() - d.getDay());
		d.setHours(0, 0, 0, 0);
		return d;
	})();

	$: weekDays = (() => {
		const days: Date[] = [];
		const d = new Date(weekStart);
		for (let i = 0; i < 7; i++) {
			days.push(new Date(d));
			d.setDate(d.getDate() + 1);
		}
		return days;
	})();

	$: hours = Array.from({ length: 24 }, (_, i) => i);

	function isToday(d: Date): boolean {
		return d.toDateString() === new Date().toDateString();
	}

	function isCurrentMonth(d: Date): boolean {
		return d.getMonth() === currentDate.getMonth();
	}

	function getEventsForDay(day: Date): CalendarEventModel[] {
		const dayStartMs = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
		const dayEndMs = dayStartMs + 86_400_000;
		return filteredEvents.filter((e) => {
			const startMs = e.start_at / NS;
			const endMs = Math.max(startMs, (e.end_at || e.start_at) / NS);
			return startMs < dayEndMs && endMs >= dayStartMs;
		});
	}

	// Week and day views draw events on a time grid, one hour per HOUR_REM.
	const HOUR_REM = 3.25;
	// Shortest drawn event: one line of text plus padding.
	const MIN_EVENT_REM = 1.25;

	$: timeColumns = view === 'week' ? weekDays : [currentDate];
	$: tzLabel =
		new Intl.DateTimeFormat($i18n.language, { timeZoneName: 'shortOffset' })
			.formatToParts(new Date())
			.find((p) => p.type === 'timeZoneName')?.value ?? '';

	function dayKey(d: Date): string {
		return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime().toString();
	}

	type PlacedEvent = {
		event: CalendarEventModel;
		start: number;
		end: number;
		col: number;
		cols: number;
	};

	// Timed events for one day, clipped to the day, with overlapping events placed side by side.
	function layoutDay(day: Date, list: CalendarEventModel[]) {
		const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
		const dayEnd = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1).getTime();
		const minMs = (MIN_EVENT_REM / HOUR_REM) * 3_600_000;

		const items: PlacedEvent[] = list
			.filter((e) => {
				if (e.all_day) return false;
				const s = e.start_at / NS;
				const en = (e.end_at ?? e.start_at) / NS;
				return s < dayEnd && (en > dayStart || s >= dayStart);
			})
			.map((e) => {
				const start = Math.max(e.start_at / NS, dayStart);
				const end = Math.min(Math.max((e.end_at ?? e.start_at) / NS, start + minMs), dayEnd);
				return { event: e, start, end, col: 0, cols: 1 };
			})
			.sort((a, b) => a.start - b.start || b.end - a.end);

		let cluster: PlacedEvent[] = [];
		let colEnds: number[] = [];
		let clusterEnd = -Infinity;
		const flush = () => {
			for (const item of cluster) item.cols = colEnds.length;
			cluster = [];
			colEnds = [];
		};
		for (const item of items) {
			if (item.start >= clusterEnd) flush();
			let col = colEnds.findIndex((end) => end <= item.start);
			if (col === -1) col = colEnds.push(item.end) - 1;
			colEnds[col] = item.end;
			item.col = col;
			cluster.push(item);
			clusterEnd = Math.max(clusterEnd, item.end);
		}
		flush();

		return items.map((item) => ({
			...item,
			top: ((item.start - dayStart) / 3_600_000) * HOUR_REM,
			height: ((item.end - item.start) / 3_600_000) * HOUR_REM
		}));
	}

	function formatTime(ms: number): string {
		return new Date(ms).toLocaleTimeString($i18n.language, { hour: 'numeric', minute: '2-digit' });
	}

	function formatMinutes(minutes: number): string {
		return new Intl.NumberFormat($i18n.language, {
			style: 'unit',
			unit: 'minute',
			unitDisplay: 'narrow'
		}).format(Math.round(minutes));
	}

	// Open week and day views scrolled to the current hour.
	let scroller: HTMLElement;
	$: if (scroller) {
		const remPx = parseFloat(getComputedStyle(document.documentElement).fontSize);
		scroller.scrollTop = Math.max(0, new Date().getHours() - 1) * HOUR_REM * remPx;
	}

	// Drag an event to another day (month, all-day row) or day and time (time grid).
	const SNAP_MINUTES = 15;
	let dragged: CalendarEventModel | null = null;
	let dropTarget: string | null = null;
	let dropMinute: number | null = null;
	// How far below the event's top it was grabbed, so it lands where it is drawn.
	let grabOffsetPx = 0;

	function canMove(e: CalendarEventModel): boolean {
		return !e.rrule && !e.instance_id && !e.meta?.automation_id;
	}

	function startDrag(e: DragEvent, event: CalendarEventModel) {
		if (!canMove(event)) {
			e.preventDefault();
			return;
		}
		dragged = event;
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		grabOffsetPx = event.all_day ? 0 : e.clientY - rect.top;
		e.dataTransfer?.setData('text/plain', event.id);
		if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
	}

	function endDrag() {
		dragged = null;
		dropTarget = null;
		dropMinute = null;
	}

	function allowDrop(e: DragEvent, target: string) {
		if (!dragged) return;
		e.preventDefault();
		dropTarget = target;
	}

	function minuteAt(e: DragEvent): number {
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		const minutes = ((e.clientY - grabOffsetPx - rect.top) / rect.height) * 24 * 60;
		const snapped = Math.round(minutes / SNAP_MINUTES) * SNAP_MINUTES;
		return Math.min(24 * 60 - SNAP_MINUTES, Math.max(0, snapped));
	}

	function allowTimeDrop(e: DragEvent, key: string) {
		allowDrop(e, `time-${key}`);
		if (dragged) dropMinute = minuteAt(e);
	}

	function dropOn(day: Date, minute?: number) {
		const event = dragged;
		endDrag();
		if (!event) return;
		const start = new Date(event.start_at / NS);
		start.setFullYear(day.getFullYear(), day.getMonth(), day.getDate());
		if (minute !== undefined && !event.all_day) start.setHours(0, minute, 0, 0);
		const start_at = start.getTime() * NS;
		if (start_at === event.start_at) return;
		const end_at = event.end_at === null ? null : event.end_at + (start_at - event.start_at);
		dispatch('moveEvent', { event, start_at, end_at });
	}

	function formatHour(h: number): string {
		return new Date(2000, 0, 1, h).toLocaleTimeString($i18n.language, {
			hour: 'numeric',
			minute: '2-digit'
		});
	}

	function formatDay(d: Date): string {
		return d.toLocaleDateString($i18n.language, {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	function formatDayHour(d: Date, h: number): string {
		return new Date(d.getFullYear(), d.getMonth(), d.getDate(), h).toLocaleString($i18n.language, {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			hour: 'numeric'
		});
	}

	function handleDayClick(day: Date) {
		currentDate = day;
		view = 'day';
		onNavigate();
	}

	export async function focusSlot(date: Date) {
		await tick();
		const slot = new Date(date).setHours(view === 'month' ? 0 : date.getHours(), 0, 0, 0);
		focusIfLost(grid?.querySelector<HTMLButtonElement>(`[data-slot="${slot}"]`));
	}

	function goToDayView(day: Date, event: CalendarEventModel) {
		currentDate = day;
		view = 'day';
		onNavigate();
		focusSlot(new Date(Math.max(day.getTime(), event.start_at / NS)));
	}

	function handleHourClick(day: Date, hour: number) {
		currentDate = day;
		const ms = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour).getTime();
		dispatch('createEvent', { start_at: ms * NS });
	}

	function handleEventClick(event: CalendarEventModel) {
		dispatch('eventClick', event);
	}
</script>

<div bind:this={grid} class="flex flex-col h-full w-full min-h-0 min-w-0">
	<!-- Month View -->
	{#if view === 'month'}
		<div class="flex-1 flex flex-col min-h-0 px-3 pb-3">
			<div class="grid grid-cols-7">
				{#each DAY_NAMES as day}
					<div class="px-2 py-1.5 text-xs text-base-400 dark:text-base-500 text-left truncate">
						{day}
					</div>
				{/each}
			</div>

			<div
				class="flex-1 grid grid-cols-7 auto-rows-fr min-h-0 rounded-2xl overflow-hidden border border-base-100/30 dark:border-base-850/30"
			>
				{#each monthDays as day, i}
					{@const key = dayKey(day)}
					{@const dayEvents = eventsByDay[key] || []}
					{@const col = i % 7}
					{@const row = Math.floor(i / 7)}
					<div
						class="relative p-1 min-h-0 text-left overflow-hidden transition cursor-pointer flex flex-col
							{isCurrentMonth(day) ? '' : ($settings?.highContrastMode ?? false) ? 'opacity-80' : 'opacity-40'}
							{dropTarget === key
							? 'bg-base-100/60 dark:bg-base-800/40'
							: 'hover:bg-base-50/80 dark:hover:bg-base-850/30'}
							{col > 0 ? 'border-l border-base-100/20 dark:border-base-850/20' : ''}
							{row > 0 ? 'border-t border-base-100/20 dark:border-base-850/20' : ''}"
						role="list"
						on:dragover={(e) => allowDrop(e, key)}
						on:drop|preventDefault={() => dropOn(day)}
					>
						<button
							type="button"
							class="absolute inset-0"
							data-slot={key}
							aria-label={formatDay(day)}
							on:click={() => handleDayClick(day)}
						></button>
						<div class="relative pointer-events-none flex justify-start px-0.5 mb-0.5">
							<span
								class="text-xs w-6 h-6 flex items-center justify-center rounded-full
								{isToday(day)
									? ($settings?.highContrastMode ?? false)
										? 'bg-blue-600 text-white'
										: 'bg-blue-500 text-white'
									: 'text-base-500 dark:text-base-400'}"
							>
								{day.getDate()}
							</span>
						</div>
						<div class="relative pointer-events-none flex flex-col gap-0 flex-1 overflow-hidden">
							{#each dayEvents.slice(0, 3) as evt (evt.instance_id || evt.id)}
								<CalendarEventChip
									event={evt}
									calendarColor={calColorMap[evt.calendar_id]}
									draggable={canMove(evt)}
									on:dragstart={(e) => startDrag(e, evt)}
									on:dragend={endDrag}
									on:click={() => handleEventClick(evt)}
								/>
							{/each}
							{#if dayEvents.length > 3}
								<button
									type="button"
									class="pointer-events-auto text-[0.625rem] text-base-400 dark:text-base-500 px-1 mt-auto hover:text-base-700 dark:hover:text-base-200 text-left w-full truncate z-10"
									on:click={() => goToDayView(day, dayEvents[3])}
								>
									{$i18n.t('and {{COUNT}} more', { COUNT: dayEvents.length - 3 })}
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Week and Day View -->
	{:else}
		{@const gridCols = `4rem repeat(${timeColumns.length}, minmax(0, 1fr))`}
		<div class="flex-1 flex flex-col min-h-0 px-3 pb-3">
			<div
				bind:this={scroller}
				class="flex-1 overflow-auto rounded-2xl border border-base-100/30 dark:border-base-850/30"
			>
				<div class={view === 'week' ? 'min-w-[43.75rem]' : ''}>
					<div
						class="sticky top-0 z-20 bg-base-0 dark:bg-base-900 border-b border-base-100/30 dark:border-base-850/30"
					>
						<div class="grid" style="grid-template-columns: {gridCols};">
							<div
								class="self-center pr-2 text-right text-[0.625rem] text-base-400 dark:text-base-500 truncate"
							>
								{tzLabel}
							</div>
							{#each timeColumns as day}
								<button
									type="button"
									class="flex items-center justify-center gap-1.5 py-2 text-xs border-l border-base-100/20 dark:border-base-850/20 hover:bg-base-50/50 dark:hover:bg-base-850/20 transition"
									aria-label={formatDay(day)}
									on:click={() => handleDayClick(day)}
								>
									<span class="font-medium text-base-800 dark:text-base-100"
										>{DAY_NAMES[day.getDay()]}</span
									>
									<span
										class={isToday(day)
											? 'font-medium text-base-800 dark:text-base-100'
											: 'text-base-400 dark:text-base-500'}
									>
										{day.getDate()}
									</span>
								</button>
							{/each}
						</div>

						{#if timeColumns.some((d) => (eventsByDay[dayKey(d)] ?? []).some((e) => e.all_day))}
							<div class="grid" style="grid-template-columns: {gridCols};">
								<div></div>
								{#each timeColumns as day}
									{@const key = dayKey(day)}
									<div
										class="min-w-0 px-0.5 pb-1 border-l border-base-100/20 dark:border-base-850/20 {dropTarget ===
										key
											? 'bg-base-100/60 dark:bg-base-800/40'
											: ''}"
										role="list"
										on:dragover={(e) => allowDrop(e, key)}
										on:drop|preventDefault={() => dropOn(day)}
									>
										{#each (eventsByDay[key] ?? []).filter((e) => e.all_day) as evt (evt.instance_id || evt.id)}
											<CalendarEventChip
												event={evt}
												calendarColor={calColorMap[evt.calendar_id]}
												draggable={canMove(evt)}
												on:dragstart={(e) => startDrag(e, evt)}
												on:dragend={endDrag}
												on:click={() => handleEventClick(evt)}
											/>
										{/each}
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<div class="grid" style="grid-template-columns: {gridCols}; height: {24 * HOUR_REM}rem;">
						<div class="relative select-none">
							{#each hours.slice(1) as hour}
								<div
									class="absolute right-2 -translate-y-1/2 text-[0.625rem] text-base-400 dark:text-base-500"
									style="top: {hour * HOUR_REM}rem;"
								>
									{formatHour(hour)}
								</div>
							{/each}
						</div>

						{#each timeColumns as day}
							{@const key = dayKey(day)}
							<div
								class="relative border-l border-base-100/20 dark:border-base-850/20"
								role="list"
								on:dragover={(e) => allowTimeDrop(e, key)}
								on:drop|preventDefault={(e) => dropOn(day, minuteAt(e))}
							>
								{#each hours as hour}
									<button
										type="button"
										class="absolute inset-x-0 transition hover:bg-base-50/50 dark:hover:bg-base-850/20 {hour >
										0
											? 'border-t border-base-100/15 dark:border-base-850/15'
											: ''}"
										style="top: {hour * HOUR_REM}rem; height: {HOUR_REM}rem;"
										data-slot={new Date(day).setHours(hour, 0, 0, 0)}
										aria-label={formatDayHour(day, hour)}
										on:click={() => handleHourClick(day, hour)}
									></button>
								{/each}

								{#if dragged && !dragged.all_day && dropTarget === `time-${key}` && dropMinute !== null}
									<div
										class="absolute inset-x-0.5 rounded-md bg-base-100/60 dark:bg-base-800/40 pointer-events-none"
										style="top: {(dropMinute / 60) * HOUR_REM}rem; height: {Math.max(
											MIN_EVENT_REM,
											(((dragged.end_at ?? dragged.start_at) - dragged.start_at) / NS / 3_600_000) *
												HOUR_REM
										)}rem;"
									></div>
								{/if}

								{#each layoutDay(day, filteredEvents) as p (p.event.instance_id || p.event.id)}
									{@const color = p.event.color || calColorMap[p.event.calendar_id] || '#3b82f6'}
									{@const tint = `color-mix(in srgb, ${color} 20%, transparent)`}
									{@const oneLine = p.height < 2 * MIN_EVENT_REM}
									<button
										type="button"
										class="absolute flex overflow-hidden rounded-md pl-3 pr-1.5 text-left {oneLine
											? 'items-center gap-1.5'
											: 'flex-col justify-start gap-0.5 py-1'} text-[0.6875rem] leading-tight text-base-800 dark:text-base-100 bg-base-0 dark:bg-base-900 hover:brightness-95 dark:hover:brightness-125 transition {dragged ===
										p.event
											? 'opacity-50'
											: ''}"
										style="top: {p.top}rem; height: {p.height}rem; left: calc({(p.col / p.cols) *
											100}% + 2px); width: calc({100 /
											p.cols}% - 4px); background-image: linear-gradient({tint}, {tint});"
										draggable={canMove(p.event)}
										on:dragstart={(e) => startDrag(e, p.event)}
										on:dragend={endDrag}
										on:click={() => handleEventClick(p.event)}
									>
										<span
											class="absolute left-1 top-1 bottom-1 w-[3px] rounded-full"
											style="background-color: {color};"
										></span>
										<div class="{oneLine ? 'truncate' : 'line-clamp-3 break-words'} font-medium">
											{p.event.title}
										</div>
										<div class="shrink-0 truncate text-[0.625rem] text-base-500 dark:text-base-400">
											{formatTime(p.event.start_at / NS)}{!oneLine &&
											p.event.end_at &&
											p.event.end_at > p.event.start_at
												? ` · ${formatMinutes((p.event.end_at - p.event.start_at) / NS / 60_000)}`
												: ''}
										</div>
									</button>
								{/each}
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
