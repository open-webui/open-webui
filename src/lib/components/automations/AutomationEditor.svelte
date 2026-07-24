<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import type i18nType from '$lib/i18n';

	import { WEBUI_NAME } from '$lib/stores';

	import {
		getAutomationById,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		getAutomationRuns,
		type AutomationResponse,
		type AutomationRunModel
	} from '$lib/apis/automations';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationItemHeaderActions from '$lib/components/automations/AutomationItemHeaderActions.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ArrowRight from '$lib/components/icons/ArrowRight.svelte';

	dayjs.extend(localizedFormat);

	const i18n: typeof i18nType = getContext('i18n');
	const automationsLayout: any = getContext('automationsLayout');

	export let automation: AutomationResponse;

	let is_active = automation.is_active;

	let loading = false;
	let showDeleteConfirm = false;
	let showEditModal = false;

	let runs: AutomationRunModel[] = [];
	let runsLoading = false;
	let hasMoreRuns = true;
	let runsPage = 0;

	const formatTime = (ts: number | null): string => {
		if (!ts) return '-';
		return new Date(ts / 1_000_000).toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	const formatNextRun = (ts: number | null): string => {
		if (!ts) return $i18n.t('Not scheduled');
		const d = dayjs(ts / 1_000_000);
		if (d.isSame(dayjs(), 'day')) return `${$i18n.t('Today at')} ${d.format('LT')}`;
		return d.format('L LT');
	};

	const formatSchedule = (rrule: string): string => {
		if (rrule.includes('COUNT=1')) {
			const match = rrule.match(/DTSTART:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
			if (match) {
				const d = new Date(`${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}`);
				return `${$i18n.t('Once')} · ${d.toLocaleDateString(undefined, {
					month: 'short',
					day: 'numeric'
				})} ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`;
			}
			return $i18n.t('Once');
		}

		const parts: Record<string, string> = {};
		rrule
			.replace('RRULE:', '')
			.split(';')
			.forEach((part) => {
				const [key, value] = part.split('=');
				if (key && value) parts[key] = value;
			});

		const freq = parts.FREQ || '';
		const hour = parseInt(parts.BYHOUR || '0');
		const minute = (parts.BYMINUTE || '0').padStart(2, '0');
		const interval = parseInt(parts.INTERVAL || '1');
		const ampm = hour >= 12 ? 'PM' : 'AM';
		const hour12 = hour % 12 || 12;
		const time = `${hour12}:${minute} ${ampm}`;

		if (freq === 'MINUTELY')
			return interval === 1
				? $i18n.t('Every minute')
				: $i18n.t('Every {{count}} minutes', { count: interval });
		if (freq === 'HOURLY')
			return interval === 1
				? $i18n.t('Hourly')
				: $i18n.t('Every {{count}} hours', { count: interval });
		if (freq === 'DAILY') return `${$i18n.t('Daily at')} ${time}`;
		if (freq === 'WEEKLY')
			return parts.BYDAY
				? `${parts.BYDAY} ${$i18n.t('at')} ${time}`
				: `${$i18n.t('Weekly at')} ${time}`;
		if (freq === 'MONTHLY')
			return `${$i18n.t('Monthly')} ${parts.BYMONTHDAY ?? '1'} ${$i18n.t('at')} ${time}`;

		return rrule;
	};

	const toggleHandler = async () => {
		const previousState = automation.is_active;
		const res = await toggleAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			is_active = res.is_active;
			automation = res;
		} else {
			is_active = previousState;
		}
	};

	const runNowHandler = async () => {
		loading = true;
		const res = await runAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Automation triggered'));
			setTimeout(() => loadRuns(false), 2000);
		}
		loading = false;
	};

	const editSavedHandler = async () => {
		const updated = await getAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});

		if (updated) {
			automation = updated;
			is_active = updated.is_active;
			await loadRuns();
		}
	};

	const deleteHandler = async () => {
		const res = await deleteAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: automation.name }));
			goto('/automations');
		}
	};

	const loadRuns = async (loadMore = false) => {
		if (runsLoading || (!hasMoreRuns && loadMore)) return;

		runsLoading = true;

		if (!loadMore) {
			runsPage = 0;
			hasMoreRuns = true;
		}

		try {
			const fetchedRuns =
				(await getAutomationRuns(localStorage.token, automation.id, runsPage * 50, 50)) ?? [];
			if (loadMore) {
				runs = [...runs, ...fetchedRuns];
			} else {
				runs = fetchedRuns;
			}

			if (fetchedRuns.length < 50) {
				hasMoreRuns = false;
			}
			runsPage++;
		} catch {
			if (!loadMore) runs = [];
		}
		runsLoading = false;
	};

	const onScroll = (e: Event) => {
		const target = e.target as HTMLElement;
		if (target.scrollTop + target.clientHeight >= target.scrollHeight - 50) {
			if (!runsLoading && hasMoreRuns) {
				loadRuns(true);
			}
		}
	};

	onMount(async () => {
		is_active = automation.is_active;

		await loadRuns();
	});

	$: if (automation) {
		automationsLayout?.setHeader({
			itemName: automation.name,
			actions: AutomationItemHeaderActions,
			actionProps: {
				isActive: is_active,
				loading,
				toggleHandler,
				runNowHandler,
				editHandler: () => (showEditModal = true),
				deleteHandler: () => (showDeleteConfirm = true)
			}
		});
	}
</script>

<svelte:head>
	<title>{automation.name || $i18n.t('Automation')} / {$WEBUI_NAME}</title>
</svelte:head>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete automation?')}
	on:confirm={deleteHandler}
>
	<div class="text-sm text-gray-500 truncate">
		{$i18n.t('This will delete')} <span class="">{automation.name}</span>.
	</div>
</DeleteConfirmDialog>

<AutomationModal bind:show={showEditModal} {automation} on:save={editSavedHandler} />

<div class="h-full overflow-y-auto scrollbar-hidden">
	<div class="pb-1 px-1">
		<div class="flex h-7 items-center px-3">
			<span class="w-24 shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Status')}
			</span>
			<span
				class="flex min-w-0 items-center gap-1.5 text-xs {is_active
					? 'text-emerald-700 dark:text-emerald-400'
					: 'text-gray-600 dark:text-gray-400'}"
			>
				<svg class="size-1.5 shrink-0" viewBox="0 0 6 6" fill="currentColor" aria-hidden="true">
					<circle cx="3" cy="3" r="3" />
				</svg>
				{is_active ? $i18n.t('Active') : $i18n.t('Paused')}
			</span>
		</div>

		<div class="flex h-7 items-center px-3">
			<span class="w-24 shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Schedule')}
			</span>
			<span class="min-w-0 truncate text-xs text-gray-700 dark:text-gray-300">
				{formatSchedule(automation.data.rrule)}
			</span>
		</div>

		<div class="flex h-7 items-center px-3">
			<span class="w-24 shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Model')}
			</span>
			<span class="min-w-0 truncate text-xs text-gray-700 dark:text-gray-300">
				{automation.data.model_id}
			</span>
		</div>

		<div class="flex h-7 items-center px-3">
			<span class="w-24 shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Next run')}
			</span>
			<span class="min-w-0 truncate text-xs text-gray-700 dark:text-gray-300">
				{formatNextRun(automation.next_runs?.[0] ?? automation.next_run_at)}
			</span>
		</div>

		<div class="flex h-7 items-center px-3">
			<span class="w-24 shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Last run')}
			</span>
			<span class="min-w-0 truncate text-xs text-gray-700 dark:text-gray-300">
				{automation.last_run_at ? formatNextRun(automation.last_run_at) : $i18n.t('Never')}
			</span>
		</div>
	</div>

	<hr class="my-1.5 border-gray-50/60 dark:border-gray-850/25" />

	<div class="px-4 py-2">
		<div class="mb-2 text-[11px] text-gray-400 dark:text-gray-500">{$i18n.t('Prompt')}</div>
		<div
			class="whitespace-pre-wrap font-mono text-xs leading-relaxed text-gray-700 dark:text-gray-300"
		>
			{automation.data.prompt}
		</div>
	</div>

	<hr class="my-1.5 border-gray-50/60 dark:border-gray-850/25" />

	<div class="px-4 py-2">
		<div class="mb-1 text-[11px] text-gray-400 dark:text-gray-500">{$i18n.t('Runs')}</div>
		<div class="overflow-y-auto scrollbar-hidden" on:scroll={onScroll}>
			{#if runsLoading && runs.length === 0}
				<div class="flex justify-center py-8">
					<Spinner className="size-4" />
				</div>
			{:else if runs.length === 0}
				<div class="py-2 text-[11px] text-gray-400 dark:text-gray-600">
					{$i18n.t('No runs yet')}
				</div>
			{:else}
				<div>
					{#each runs as run}
						<div class="flex h-7 items-center gap-2 text-xs">
							<span
								class="h-1.5 w-1.5 shrink-0 rounded-full {run.status === 'success'
									? 'bg-emerald-500'
									: 'bg-red-400'}"
							></span>
							<span class="text-gray-500 dark:text-gray-400">{formatTime(run.created_at)}</span>
							{#if run.chat_id}
								<button
									class="group flex items-center gap-1 text-[0.6875rem] text-gray-400"
									on:click={() => {
										goto(`/c/${run.chat_id}`);
									}}
									type="button"
								>
									<span class="group-hover:underline">{$i18n.t('View chat')}</span>
									<ArrowRight className="size-2.5" strokeWidth="2" />
								</button>
							{/if}
							{#if run.error}
								<span class="truncate text-[0.6875rem] text-red-400" title={run.error}>
									{run.error}
								</span>
							{/if}
						</div>
					{/each}

					{#if runsLoading && runs.length > 0}
						<div class="flex justify-center py-4">
							<Spinner className="size-4" />
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
