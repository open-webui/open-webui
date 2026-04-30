<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, mobile, showSidebar, user } from '$lib/stores';
	import {
		getCalendars,
		getCalendarEvents,
		deleteCalendar,
		type CalendarModel,
		type CalendarEventModel
	} from '$lib/apis/calendar';
	import CalendarView from '$lib/components/calendar/CalendarView.svelte';
	import CalendarSidebar from '$lib/components/calendar/CalendarSidebar.svelte';
	import CalendarEventModal from '$lib/components/calendar/CalendarEventModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Select from '$lib/components/common/Select.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let calendars: CalendarModel[] = [];
	let events: CalendarEventModel[] = [];
	let visibleCalendarIds: Set<string> = new Set();

	let view: 'month' | 'week' | 'day' = 'month';
	let currentDate = new Date();

	let showEventModal = false;
	let editEvent: CalendarEventModel | null = null;
	let defaultStartAt: number | null = null;

	const MONTH_NAMES = [
		'January',
		'February',
		'March',
		'April',
		'May',
		'June',
		'July',
		'August',
		'September',
		'October',
		'November',
		'December'
	];
	const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

	function getVisibleRange(): { start: string; end: string } {
		const d = new Date(currentDate);
		let start: Date;
		let end: Date;

		if (view === 'month') {
			start = new Date(d.getFullYear(), d.getMonth(), 1);
			start.setDate(start.getDate() - start.getDay());
			end = new Date(start);
			end.setDate(end.getDate() + 42);
		} else if (view === 'week') {
			start = new Date(d);
			start.setDate(start.getDate() - start.getDay());
			start.setHours(0, 0, 0, 0);
			end = new Date(start);
			end.setDate(end.getDate() + 7);
		} else {
			start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
			end = new Date(start);
			end.setDate(end.getDate() + 1);
		}

		return {
			start: start.toISOString(),
			end: end.toISOString()
		};
	}

	async function loadCalendars() {
		try {
			calendars = (await getCalendars(localStorage.token)) ?? [];
			visibleCalendarIds = new Set(calendars.map((c) => c.id));
		} catch (err) {
			console.error('loadCalendars', err);
			calendars = [];
		}
	}

	async function loadEvents() {
		try {
			const { start, end } = getVisibleRange();
			events = await getCalendarEvents(localStorage.token, start, end);
		} catch (err) {
			toast.error(`${err}`);
		}
	}

	async function refresh() {
		await loadEvents();
	}

	function toggleCalendar(id: string) {
		const next = new Set(visibleCalendarIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		visibleCalendarIds = next;
	}

	async function handleDeleteCalendar(id: string) {
		try {
			const result = await deleteCalendar(localStorage.token, id);
			if (result) {
				toast.success($i18n.t('Calendar deleted'));
				await loadCalendars();
				await refresh();
			} else {
				toast.error($i18n.t('Failed to delete calendar'));
			}
		} catch (err) {
			toast.error(`${err}`);
		}
	}

	function handleCreateEvent(e: CustomEvent<{ start_at: number }>) {
		editEvent = null;
		defaultStartAt = e.detail.start_at;
		showEventModal = true;
	}

	function handleEventClick(e: CustomEvent<CalendarEventModel>) {
		const evt = e.detail;
		if (evt.meta?.automation_id) {
			if (evt.meta?.chat_id) {
				goto(`/c/${evt.meta.chat_id}`);
			} else {
				goto(`/automations/${evt.meta.automation_id}`);
			}
			return;
		}
		editEvent = evt;
		defaultStartAt = null;
		showEventModal = true;
	}

	async function handleNavigate() {
		await tick();
		refresh();
	}

	async function handleDateSelect(date: Date) {
		currentDate = date;
		await tick();
		refresh();
	}

	function handleNewEvent() {
		editEvent = null;
		defaultStartAt = null;
		showEventModal = true;
	}

	function navigateCalendar(delta: number) {
		const d = new Date(currentDate);
		if (view === 'month') {
			d.setDate(1);
			d.setMonth(d.getMonth() + delta);
		} else if (view === 'week') d.setDate(d.getDate() + delta * 7);
		else d.setDate(d.getDate() + delta);
		currentDate = d;
		handleNavigate();
	}

	function goToToday() {
		currentDate = new Date();
		handleNavigate();
	}

	$: defaultCalendarId = calendars.find((c) => c.is_default)?.id || calendars[0]?.id || '';

	$: headerText =
		view === 'day'
			? `${DAY_NAMES[currentDate.getDay()]}, ${MONTH_NAMES[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`
			: `${MONTH_NAMES[currentDate.getMonth()]} ${currentDate.getFullYear()}`;

	onMount(async () => {
		await loadCalendars();
		await refresh();
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Calendar')} • {$WEBUI_NAME}</title>
</svelte:head>

<CalendarEventModal
	bind:show={showEventModal}
	event={editEvent}
	{calendars}
	{defaultCalendarId}
	{defaultStartAt}
	on:save={() => refresh()}
	on:delete={() => refresh()}
/>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	{#if loaded}
		<!-- Top Navbar — spans above sidebar and calendar -->
		<nav class="px-3 pt-2 pb-2 backdrop-blur-xl drag-region select-none shrink-0">
			<div class="flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => showSidebar.set(!$showSidebar)}
							>
								<div class="self-center p-1.5">
									<SidebarIcon />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="flex w-full items-center">
					<div class="flex items-center gap-0.5 py-1">
						<span class="min-w-fit px-1 text-sm select-none">{headerText}</span>
						<button
							class="p-1 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={() => navigateCalendar(-1)}
							aria-label="Previous"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3.5 text-gray-400"
								><path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15.75 19.5 8.25 12l7.5-7.5"
								/></svg
							>
						</button>
						<button
							class="p-1 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={() => navigateCalendar(1)}
							aria-label="Next"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3.5 text-gray-400"
								><path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m8.25 4.5 7.5 7.5-7.5 7.5"
								/></svg
							>
						</button>
					</div>

					<div class="ml-auto flex items-center gap-1">
						<button
							class="hidden sm:inline text-xs px-2 py-1 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-500 hover:text-gray-700 dark:hover:text-white"
							on:click={goToToday}
						>
							{$i18n.t('Today')}
						</button>

						<Select
							bind:value={view}
							items={[
								{ value: 'day', label: $i18n.t('Day') },
								{ value: 'week', label: $i18n.t('Week') },
								{ value: 'month', label: $i18n.t('Month') }
							]}
							onChange={() => handleNavigate()}
							triggerClass="relative flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl text-xs"
							contentClass="rounded-2xl w-40 p-1 border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
							align="end"
						>
							<svelte:fragment slot="trigger" let:selectedLabel>
								<span
									class="inline-flex h-input px-0.5 outline-hidden bg-transparent truncate line-clamp-1"
								>
									{selectedLabel}
								</span>
								<ChevronDown className="size-3.5" strokeWidth="2.5" />
							</svelte:fragment>

							<svelte:fragment slot="item" let:item let:selected>
								{item.label}
								<div class="ml-auto {selected ? '' : 'invisible'}">
									<Check />
								</div>
							</svelte:fragment>
						</Select>

						<button
							class="ml-1 px-2 py-1.5 text-xs gap-1 rounded-xl bg-black text-white dark:bg-white dark:text-black transition text-sm flex items-center"
							on:click={handleNewEvent}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2.5"
								stroke="currentColor"
								class="size-3"
								><path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 4.5v15m7.5-7.5h-15"
								/></svg
							>

							<span class="hidden sm:inline">{$i18n.t('New Event')}</span>
						</button>
					</div>
				</div>
			</div>
		</nav>

		<div class="flex flex-1 min-h-0">
			<!-- Sidebar -->
			<div class="hidden md:flex flex-col w-56 shrink-0 pr-1.5 pl-3 overflow-y-auto">
				<CalendarSidebar
					{calendars}
					{visibleCalendarIds}
					{currentDate}
					onToggle={toggleCalendar}
					onDeleteCalendar={handleDeleteCalendar}
					onDateSelect={handleDateSelect}
				/>
			</div>

			<!-- Calendar -->
			<div class="flex-1 flex flex-col min-h-0">
				<CalendarView
					{events}
					{calendars}
					{visibleCalendarIds}
					bind:view
					bind:currentDate
					on:createEvent={handleCreateEvent}
					on:eventClick={handleEventClick}
					on:navigate={handleNavigate}
					on:viewChange={handleNavigate}
				/>
			</div>
		</div>
	{:else}
		<div class="w-full h-full flex justify-center items-center">
			<Spinner className="size-5" />
		</div>
	{/if}
</div>
