<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import type { CalendarModel, CalendarEventModel, CalendarEventForm } from '$lib/apis/calendar';
	import {
		createCalendarEvent,
		updateCalendarEvent,
		deleteCalendarEvent
	} from '$lib/apis/calendar';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let event: CalendarEventModel | null = null;
	export let calendars: CalendarModel[] = [];
	export let defaultCalendarId: string = '';
	export let defaultStartAt: number | null = null;

	let title = '';
	let description = '';
	let calendarId = '';
	let startDate = '';
	let startTime = '';
	let endDate = '';
	let endTime = '';
	let allDay = false;
	let location = '';
	let alertMinutes: number = 10;
	let loading = false;
	let showDeleteConfirmDialog = false;

	const NS = 1_000_000;

	function nsToDateStr(ns: number): string {
		return new Date(ns / NS).toISOString().slice(0, 10);
	}

	function nsToTimeStr(ns: number): string {
		return new Date(ns / NS).toTimeString().slice(0, 5);
	}

	function dateTimeToNs(dateStr: string, timeStr: string): number {
		return new Date(`${dateStr}T${timeStr || '00:00'}`).getTime() * NS;
	}

	function reset() {
		if (event) {
			title = event.title;
			description = event.description || '';
			calendarId = event.calendar_id;
			startDate = nsToDateStr(event.start_at);
			startTime = nsToTimeStr(event.start_at);
			endDate = event.end_at ? nsToDateStr(event.end_at) : '';
			endTime = event.end_at ? nsToTimeStr(event.end_at) : '';
			allDay = event.all_day;
			location = event.location || '';
			alertMinutes = event.meta?.alert_minutes ?? 10;
		} else {
			title = '';
			description = '';
			calendarId = defaultCalendarId || (calendars.length > 0 ? calendars[0].id : '');
			if (defaultStartAt) {
				startDate = nsToDateStr(defaultStartAt);
				startTime = nsToTimeStr(defaultStartAt);
				const endNs = defaultStartAt + 60 * 60 * 1000 * NS;
				endDate = nsToDateStr(endNs);
				endTime = nsToTimeStr(endNs);
			} else {
				const now = new Date();
				startDate = now.toISOString().slice(0, 10);
				startTime = now.toTimeString().slice(0, 5);
				const later = new Date(now.getTime() + 60 * 60 * 1000);
				endDate = later.toISOString().slice(0, 10);
				endTime = later.toTimeString().slice(0, 5);
			}
			allDay = false;
			location = '';
			alertMinutes = 10;
		}
	}

	$: if (show) reset();

	const submitHandler = async () => {
		if (!title.trim()) {
			toast.error($i18n.t('Title is required'));
			return;
		}

		loading = true;
		try {
			const startNs = dateTimeToNs(startDate, allDay ? '00:00' : startTime);
			const endNs = endDate ? dateTimeToNs(endDate, allDay ? '23:59' : endTime) : undefined;

			if (event && !event.meta?.automation_id) {
				const result = await updateCalendarEvent(localStorage.token, event.id, {
					calendar_id: calendarId,
					title: title.trim(),
					description: description.trim() || undefined,
					start_at: startNs,
					end_at: endNs,
					all_day: allDay,
					location: location.trim() || undefined,
					meta: { alert_minutes: alertMinutes }
				});
				if (result) {
					toast.success($i18n.t('Event updated'));
					dispatch('save', result);
					show = false;
				}
			} else {
				const form: CalendarEventForm = {
					calendar_id: calendarId,
					title: title.trim(),
					description: description.trim() || undefined,
					start_at: startNs,
					end_at: endNs,
					all_day: allDay,
					location: location.trim() || undefined,
					meta: { alert_minutes: alertMinutes }
				};
				const result = await createCalendarEvent(localStorage.token, form);
				if (result) {
					toast.success($i18n.t('Event created'));
					dispatch('save', result);
					show = false;
				}
			}
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			loading = false;
		}
	};

	const deleteHandler = async () => {
		if (!event || event.meta?.automation_id) return;
		loading = true;
		try {
			await deleteCalendarEvent(localStorage.token, event.id);
			toast.success($i18n.t('Event deleted'));
			dispatch('delete', event);
			show = false;
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			loading = false;
		}
	};
</script>

<Modal size="md" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<input
				class="w-full text-lg bg-transparent outline-hidden font-primary placeholder:text-gray-300 dark:placeholder:text-gray-700"
				type="text"
				bind:value={title}
				placeholder={$i18n.t('Event title')}
			/>
			<button
				class="self-center shrink-0 ml-2"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Details -->
		<div class="px-5 pb-2 flex flex-col gap-3">
			<!-- Calendar -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Calendar')}</div>
				<select
					class="w-full text-sm bg-transparent outline-hidden cursor-pointer"
					bind:value={calendarId}
				>
					{#each calendars.filter((c) => c.id !== '__scheduled_tasks__') as cal (cal.id)}
						<option value={cal.id}>{cal.name}</option>
					{/each}
				</select>
			</div>

			<!-- Date / Time -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('When')}</div>
				<div class="flex items-center gap-2 text-sm flex-wrap">
					<input type="date" class="bg-transparent outline-hidden" bind:value={startDate} />
					{#if !allDay}
						<input type="time" class="bg-transparent outline-hidden" bind:value={startTime} />
						<span class="text-gray-300 dark:text-gray-600">–</span>
						<input type="time" class="bg-transparent outline-hidden" bind:value={endTime} />
					{/if}
					<label class="flex items-center gap-1.5 cursor-pointer text-xs text-gray-400 ml-auto">
						<input type="checkbox" class="accent-blue-500" bind:checked={allDay} />
						{$i18n.t('All day')}
					</label>
				</div>
			</div>

			<!-- Location -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Location')}</div>
				<input
					class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
					placeholder={$i18n.t('Add location')}
					bind:value={location}
				/>
			</div>

			<!-- Reminder -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Reminder')}</div>
				<select
					class="w-full text-sm bg-transparent outline-hidden cursor-pointer"
					bind:value={alertMinutes}
				>
					<option value={-1}>{$i18n.t('None')}</option>
					<option value={0}>{$i18n.t('At time of event')}</option>
					<option value={5}>{$i18n.t('5 minutes before')}</option>
					<option value={10}>{$i18n.t('10 minutes before')}</option>
					<option value={15}>{$i18n.t('15 minutes before')}</option>
					<option value={30}>{$i18n.t('30 minutes before')}</option>
					<option value={60}>{$i18n.t('1 hour before')}</option>
				</select>
			</div>

			<!-- Description -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Description')}</div>
				<textarea
					class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 resize-none min-h-[4rem]"
					placeholder={$i18n.t('Add description')}
					bind:value={description}
					rows="3"
				></textarea>
			</div>
		</div>

		<!-- Bottom toolbar -->
		<div class="flex items-center justify-between px-4 pb-3.5 pt-1 gap-2">
			<div class="flex items-center gap-0.5 flex-1 min-w-0">
				{#if event && !event.meta?.automation_id}
					<button
						class="px-3 py-1 text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
						type="button"
						on:click={() => (showDeleteConfirmDialog = true)}
						disabled={loading}
					>
						{$i18n.t('Delete')}
					</button>
				{/if}
			</div>

			<div class="flex items-center gap-2 shrink-0">
				<button
					class="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition"
					type="button"
					on:click={() => (show = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-3.5 py-1.5 text-sm bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 {loading
						? 'cursor-not-allowed'
						: ''}"
					on:click={submitHandler}
					type="button"
					disabled={loading}
				>
					{event && !event.meta?.automation_id ? $i18n.t('Save') : $i18n.t('Create')}
					{#if loading}
						<span class="shrink-0"><Spinner /></span>
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>

<DeleteConfirmDialog
	bind:show={showDeleteConfirmDialog}
	title={$i18n.t('Delete Event')}
	message={$i18n.t('This action cannot be undone. Do you wish to continue?')}
	on:confirm={deleteHandler}
/>
