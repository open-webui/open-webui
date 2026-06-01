<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { CalendarEventModel, CalendarModel } from '$lib/apis/calendar';
	import CalendarEventChip from './CalendarEventChip.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let events: CalendarEventModel[] = [];
	export let calendars: CalendarModel[] = [];
	export let visibleCalendarIds: Set<string> = new Set();
	export let view: 'month' | 'week' | 'day' = 'month';
	export let currentDate: Date = new Date();

	const NS = 1_000_000;
	const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

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
			const endMs = (e.end_at || e.start_at) / NS;
			// Get local midnight for event start/end
			const startDate = new Date(startMs);
			const endDate = new Date(endMs);
			const d = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
			const last = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate()).getTime();
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
			const endMs = (e.end_at || e.start_at) / NS;
			return startMs < dayEndMs && endMs >= dayStartMs;
		});
	}

	function getEventsForHour(
		day: Date,
		hour: number,
		eventsList: CalendarEventModel[] = filteredEvents
	): CalendarEventModel[] {
		const hourStartMs = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour).getTime();
		const hourEndMs = hourStartMs + 3_600_000;
		return eventsList.filter((e) => {
			const startMs = e.start_at / NS;
			return startMs >= hourStartMs && startMs < hourEndMs;
		});
	}

	function formatHour(h: number): string {
		if (h === 0) return '12 AM';
		if (h < 12) return `${h} AM`;
		if (h === 12) return '12 PM';
		return `${h - 12} PM`;
	}

	function handleDayClick(day: Date) {
		currentDate = day;
		const ms = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 9).getTime();
		dispatch('createEvent', { start_at: ms * NS });
	}

	function goToDayView(day: Date) {
		currentDate = day;
		view = 'day';
		dispatch('viewChange', view);
		dispatch('navigate', { date: currentDate });
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

<div class="flex flex-col h-full w-full min-h-0 min-w-0">
	<!-- Month View -->
	{#if view === 'month'}
		<div class="flex-1 flex flex-col min-h-0 px-3 pb-3">
			<div class="grid grid-cols-7">
				{#each DAY_NAMES as day}
					<div class="px-2 py-1.5 text-xs text-gray-400 dark:text-gray-500 text-left truncate">
						{$i18n.t(day)}
					</div>
				{/each}
			</div>

			<div
				class="flex-1 grid grid-cols-7 auto-rows-fr min-h-0 rounded-2xl overflow-hidden bg-white dark:bg-gray-900 border border-gray-100/30 dark:border-gray-850/30"
			>
				{#each monthDays as day, i}
					{@const dayKey = new Date(day.getFullYear(), day.getMonth(), day.getDate())
						.getTime()
						.toString()}
					{@const dayEvents = eventsByDay[dayKey] || []}
					{@const col = i % 7}
					{@const row = Math.floor(i / 7)}
					<button
						class="p-1 min-h-0 text-left overflow-hidden transition cursor-pointer flex flex-col
							{isCurrentMonth(day) ? '' : 'opacity-40'}
							hover:bg-gray-50/80 dark:hover:bg-gray-850/30
							{col > 0 ? 'border-l border-gray-100/20 dark:border-gray-850/20' : ''}
							{row > 0 ? 'border-t border-gray-100/20 dark:border-gray-850/20' : ''}"
						on:click={() => handleDayClick(day)}
					>
						<div class="flex justify-start px-0.5 mb-0.5">
							<span
								class="text-xs w-6 h-6 flex items-center justify-center rounded-full
								{isToday(day) ? 'bg-blue-500 text-white' : 'text-gray-500 dark:text-gray-400'}"
							>
								{day.getDate()}
							</span>
						</div>
						<div class="flex flex-col gap-0 flex-1 overflow-hidden">
							{#each dayEvents.slice(0, 3) as evt (evt.instance_id || evt.id)}
								<CalendarEventChip
									event={evt}
									calendarColor={calColorMap[evt.calendar_id]}
									on:click={() => handleEventClick(evt)}
								/>
							{/each}
							{#if dayEvents.length > 3}
								<!-- svelte-ignore a11y-click-events-have-key-events --><!-- svelte-ignore a11y-no-static-element-interactions -->
								<div
									class="text-[10px] text-gray-400 dark:text-gray-500 px-1 mt-auto hover:text-gray-700 dark:hover:text-gray-200 text-left w-full truncate z-10"
									on:click|stopPropagation={() => goToDayView(day)}
								>
									+{dayEvents.length - 3} more
								</div>
							{/if}
						</div>
					</button>
				{/each}
			</div>
		</div>

		<!-- Week View -->
	{:else if view === 'week'}
		<div class="flex-1 flex flex-col min-h-0 px-3 pb-3">
			<div
				class="flex-1 rounded-2xl bg-white dark:bg-gray-900 border border-gray-100/30 dark:border-gray-850/30 overflow-hidden relative"
			>
				<div class="absolute inset-0 overflow-x-auto flex flex-col">
					<div class="min-w-[700px] flex flex-col flex-1">
						<div
							class="grid grid-cols-[52px_repeat(7,1fr)] shrink-0 border-b border-gray-100/30 dark:border-gray-850/30"
						>
							<div></div>
							{#each weekDays as day}
								<div
									class="text-center py-2.5 {day.getDay() > 0
										? 'border-l border-gray-100/20 dark:border-gray-850/20'
										: ''}"
								>
									<div class="text-[11px] text-gray-400 dark:text-gray-500">
										{DAY_NAMES[day.getDay()]}
									</div>
									<div
										class="text-sm mt-0.5 w-7 h-7 flex items-center justify-center mx-auto rounded-full {isToday(
											day
										)
											? 'bg-blue-500 text-white'
											: ''}"
									>
										{day.getDate()}
									</div>
								</div>
							{/each}
						</div>

						<div class="flex-1 overflow-y-auto">
							{#each hours as hour}
								<div
									class="grid grid-cols-[52px_repeat(7,1fr)] min-h-[52px] {hour > 0
										? 'border-t border-gray-100/15 dark:border-gray-850/15'
										: ''}"
								>
									<div
										class="text-[10px] text-gray-400 dark:text-gray-500 text-right pr-2 select-none -mt-1.5 z-10"
									>
										{hour > 0 ? formatHour(hour) : ''}
									</div>
									{#each weekDays as day}
										{@const hourEvents = getEventsForHour(day, hour, filteredEvents)}
										<button
											class="px-0.5 py-0.5 {day.getDay() > 0
												? 'border-l border-gray-100/15 dark:border-gray-850/15'
												: ''} hover:bg-gray-50/50 dark:hover:bg-gray-850/20 transition cursor-pointer min-w-0 flex flex-col"
											on:click={() => handleHourClick(day, hour)}
										>
											<div class="flex flex-col gap-0.5 w-full min-h-0">
												{#each hourEvents.slice(0, 3) as evt (evt.instance_id || evt.id)}
													<CalendarEventChip
														event={evt}
														calendarColor={calColorMap[evt.calendar_id]}
														on:click={() => handleEventClick(evt)}
													/>
												{/each}
												{#if hourEvents.length > 3}
													<!-- svelte-ignore a11y-click-events-have-key-events --><!-- svelte-ignore a11y-no-static-element-interactions -->
													<div
														class="text-[10px] text-gray-400 dark:text-gray-500 px-1 mt-auto hover:text-gray-700 dark:hover:text-gray-200 text-left w-full truncate z-10"
														on:click|stopPropagation={() => goToDayView(day)}
													>
														+{hourEvents.length - 3} more
													</div>
												{/if}
											</div>
										</button>
									{/each}
								</div>
							{/each}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Day View -->
	{:else}
		<div class="flex-1 flex flex-col min-h-0 px-3 pb-3">
			<div
				class="flex-1 rounded-2xl overflow-hidden bg-white dark:bg-gray-900 border border-gray-100/30 dark:border-gray-850/30 overflow-y-auto"
			>
				{#each hours as hour}
					{@const hourEvents = getEventsForHour(currentDate, hour, filteredEvents)}
					<div
						class="flex min-h-[52px] {hour > 0
							? 'border-t border-gray-100/15 dark:border-gray-850/15'
							: ''}"
					>
						<div
							class="w-14 shrink-0 text-[10px] text-gray-400 dark:text-gray-500 text-right pr-3 mt-1 select-none"
						>
							{formatHour(hour)}
						</div>
						<button
							class="flex-1 border-l border-gray-100/15 dark:border-gray-850/15 px-1.5 py-0.5
								hover:bg-gray-50/50 dark:hover:bg-gray-850/20 transition cursor-pointer flex flex-col text-left justify-start"
							on:click={() => handleHourClick(currentDate, hour)}
						>
							<div class="flex flex-col gap-0.5 w-full">
								{#each hourEvents as evt (evt.instance_id || evt.id)}
									<CalendarEventChip
										event={evt}
										calendarColor={calColorMap[evt.calendar_id]}
										on:click={() => handleEventClick(evt)}
									/>
								{/each}
							</div>
						</button>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
