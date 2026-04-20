<script lang="ts">
	import { getContext } from 'svelte';
	import type { CalendarModel } from '$lib/apis/calendar';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	export let calendars: CalendarModel[] = [];
	export let visibleCalendarIds: Set<string> = new Set();
	export let currentDate: Date = new Date();
	export let onToggle: (id: string) => void = () => {};
	export let onCreateCalendar: () => void = () => {};
	export let onDeleteCalendar: (id: string) => void = () => {};
	export let onDateSelect: (date: Date) => void = () => {};

	// Delete confirmation state
	let showDeleteConfirm = false;
	let deleteTargetCalendar: CalendarModel | null = null;

	function isDeletable(cal: CalendarModel): boolean {
		return !cal.is_default && !cal.is_system;
	}

	function handleDeleteClick(e: MouseEvent, cal: CalendarModel) {
		e.stopPropagation();
		deleteTargetCalendar = cal;
		showDeleteConfirm = true;
	}

	function confirmDelete() {
		if (deleteTargetCalendar) {
			onDeleteCalendar(deleteTargetCalendar.id);
		}
		deleteTargetCalendar = null;
	}

	// Mini calendar state
	$: miniMonth = currentDate.getMonth();
	$: miniYear = currentDate.getFullYear();

	$: miniMonthStart = new Date(miniYear, miniMonth, 1);
	$: miniCalStart = (() => {
		const d = new Date(miniMonthStart);
		d.setDate(d.getDate() - d.getDay());
		return d;
	})();

	$: miniDays = (() => {
		const days: Date[] = [];
		const d = new Date(miniCalStart);
		for (let i = 0; i < 42; i++) {
			days.push(new Date(d));
			d.setDate(d.getDate() + 1);
		}
		return days;
	})();

	$: miniMonthNames = [
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

	function isToday(d: Date): boolean {
		return d.toDateString() === new Date().toDateString();
	}

	function isSelected(d: Date): boolean {
		return d.toDateString() === currentDate.toDateString();
	}

	function navigateMini(delta: number) {
		if (miniMonth + delta > 11) {
			miniMonth = 0;
			miniYear++;
		} else if (miniMonth + delta < 0) {
			miniMonth = 11;
			miniYear--;
		} else {
			miniMonth += delta;
		}
	}
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Calendar')}
	message={$i18n.t('This will permanently delete the calendar "{{name}}" and all its events. This action cannot be undone.', { name: deleteTargetCalendar?.name ?? '' })}
	confirmLabel={$i18n.t('Delete')}
	onConfirm={confirmDelete}
/>

<div class="flex flex-col gap-4">
	<!-- Mini Month Calendar -->
	<div>
		<div class="flex items-center justify-between px-1 mb-1.5 mt-1.5">
			<div class="text-[11px] font-medium">{miniMonthNames[miniMonth]} {miniYear}</div>
			<div class="flex items-center gap-0.5">
				<button
					class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => navigateMini(-1)}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="size-3"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15.75 19.5 8.25 12l7.5-7.5"
						/></svg
					>
				</button>
				<button
					class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => navigateMini(1)}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="size-3"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="m8.25 4.5 7.5 7.5-7.5 7.5"
						/></svg
					>
				</button>
			</div>
		</div>

		<div class="grid grid-cols-7 text-center text-[9px] text-gray-400 dark:text-gray-500 mb-0.5">
			{#each ['S', 'M', 'T', 'W', 'T', 'F', 'S'] as d}
				<div class="py-0.5">{d}</div>
			{/each}
		</div>

		<div class="grid grid-cols-7 text-center text-[10px]">
			{#each miniDays as day}
				<button
					class="w-6 h-6 flex items-center justify-center rounded-full transition
						{day.getMonth() !== miniMonth ? 'text-gray-300 dark:text-gray-600' : ''}
						{isToday(day) ? 'bg-blue-500 text-white' : ''}
						{day.toDateString() === currentDate.toDateString() && !isToday(day)
						? 'bg-gray-200 dark:bg-gray-700'
						: ''}
						{!isToday(day) && day.toDateString() !== currentDate.toDateString()
						? 'hover:bg-gray-100 dark:hover:bg-gray-800'
						: ''}"
					on:click={() => onDateSelect(day)}
				>
					{day.getDate()}
				</button>
			{/each}
		</div>
	</div>

	<!-- Calendar List -->
	<div>
		<div class="flex items-center justify-between mb-1 px-1">
			<div class="text-[11px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">
				{$i18n.t('Calendars')}
			</div>
		</div>

		{#each calendars as cal (cal.id)}
			<div class="group flex items-center w-full">
				<button
					class="flex items-center gap-2 px-2 py-1 rounded-lg text-xs transition
						hover:bg-gray-50 dark:hover:bg-gray-800/50 flex-1 text-left min-w-0"
					on:click={() => onToggle(cal.id)}
				>
					<span
						class="shrink-0 size-2.5 rounded-full transition-opacity"
						style="background-color: {cal.color || '#3b82f6'}; opacity: {visibleCalendarIds.has(
							cal.id
						)
							? '1'
							: '0.25'};"
					></span>
					<span
						class="truncate flex-1 {visibleCalendarIds.has(cal.id)
							? ''
							: 'text-gray-400 dark:text-gray-500'}"
					>
						{cal.name}
					</span>
				</button>

				{#if isDeletable(cal)}
					<button
						class="shrink-0 p-1 rounded-lg opacity-0 group-hover:opacity-100
							hover:bg-red-50 dark:hover:bg-red-900/20
							text-gray-400 hover:text-red-500 dark:hover:text-red-400
							transition-all duration-150"
						title={$i18n.t('Delete calendar')}
						on:click={(e) => handleDeleteClick(e, cal)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
							/>
						</svg>
					</button>
				{/if}
			</div>
		{/each}
	</div>
</div>
