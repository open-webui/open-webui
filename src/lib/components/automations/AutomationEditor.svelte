<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	import { WEBUI_NAME, showSidebar } from '$lib/stores';

	import {
		updateAutomationById,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		getAutomationRuns,
		type AutomationForm,
		type AutomationResponse,
		type AutomationRunModel
	} from '$lib/apis/automations';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	import ScheduleDropdown from '$lib/components/automations/ScheduleDropdown.svelte';
	import ModelDropdown from '$lib/components/automations/ModelDropdown.svelte';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	const i18n = getContext('i18n');

	export let automation: AutomationResponse;

	let name = '';
	let prompt = '';
	let model_id = '';
	let is_active = true;

	let loading = false;
	let saving = false;
	let showDeleteConfirm = false;

	let runs: AutomationRunModel[] = [];
	let runsLoading = false;
	let hasMoreRuns = true;
	let runsPage = 0;
	let isDirty = false;

	let scheduleDropdown: ScheduleDropdown;

	const formatRunTime = (ts: number): string => {
		const now = Date.now();
		const diff = now - ts / 1_000_000;

		const seconds = Math.floor(diff / 1000);
		const minutes = Math.floor(seconds / 60);
		const hours = Math.floor(minutes / 60);
		const days = Math.floor(hours / 24);
		const weeks = Math.floor(days / 7);
		const years = Math.floor(days / 365);

		if (years > 0) return $i18n.t('{{COUNT}}y', { COUNT: years, context: 'time_ago' });
		if (weeks > 0) return $i18n.t('{{COUNT}}w', { COUNT: weeks, context: 'time_ago' });
		if (days > 0) return $i18n.t('{{COUNT}}d', { COUNT: days, context: 'time_ago' });
		if (hours > 0) return $i18n.t('{{COUNT}}h', { COUNT: hours, context: 'time_ago' });
		if (minutes > 0) return $i18n.t('{{COUNT}}m', { COUNT: minutes, context: 'time_ago' });
		return $i18n.t('1m', { context: 'time_ago' });
	};

	const formatNextRun = (ts: number | null): string => {
		if (!ts) return $i18n.t('Not scheduled');
		const d = dayjs(ts / 1_000_000);
		if (d.isSame(dayjs(), 'day')) return `${$i18n.t('Today at')} ${d.format('LT')}`;
		return d.format('L LT');
	};

	const saveHandler = async () => {
		if (!name.trim() || !prompt.trim() || !model_id.trim()) {
			toast.error($i18n.t('Name, prompt, and model are required'));
			return;
		}
		saving = true;
		try {
			const form: AutomationForm = {
				name: name.trim(),
				data: {
					prompt: prompt.trim(),
					model_id: model_id.trim(),
					rrule: scheduleDropdown.buildRrule()
				},
				is_active
			};
			const updated = await updateAutomationById(localStorage.token, automation.id, form);
			if (updated) {
				automation = updated;
				isDirty = false;
				toast.success($i18n.t('Automation updated'));
			}
		} catch (e: any) {
			toast.error(e?.detail ?? `${e}` ?? 'Failed to save');
		} finally {
			saving = false;
		}
	};

	const toggleHandler = async () => {
		const res = await toggleAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			is_active = res.is_active;
			automation = res;
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

	const markDirty = () => {
		isDirty = true;
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
		name = automation.name;
		prompt = automation.data.prompt;
		model_id = automation.data.model_id;
		is_active = automation.is_active;

		if (scheduleDropdown) {
			scheduleDropdown.parseRrule(automation.data.rrule);
		}

		await loadRuns();
	});
</script>

<svelte:head>
	<title>{name || $i18n.t('Automation')} • {$WEBUI_NAME}</title>
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

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="flex-1 max-h-full flex flex-col pt-3 pb-1 px-3 md:px-[18px]">
		<!-- Header Segment (Shrink-0 so it doesn't compress) -->
		<div class="flex items-start justify-between gap-4 shrink-0 mb-0.5">
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-1.5 mb-1.5">
					<Tooltip content={$i18n.t('Back')}>
						<button
							class="text-sm p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition"
							aria-label={$i18n.t('Back')}
							on:click={() => goto('/automations')}
							type="button"
						>
							<ChevronLeft strokeWidth="2.5" />
						</button>
					</Tooltip>
					<input
						class="text-2xl w-full bg-transparent outline-hidden"
						placeholder={$i18n.t('Automation Name')}
						bind:value={name}
						on:input={markDirty}
					/>
				</div>
			</div>

			<div class="flex items-center gap-2 shrink-0">
				<Tooltip content={$i18n.t('Delete')}>
					<button
						class="p-2 rounded-full bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 text-gray-500 hover:text-black dark:hover:text-white transition"
						on:click={() => (showDeleteConfirm = true)}
						type="button"
					>
						<GarbageBin />
					</button>
				</Tooltip>

				{#if isDirty}
					<button
						class="px-3 py-1 text-sm bg-black text-white dark:bg-white dark:text-black rounded-full hover:opacity-90 transition flex items-center gap-1.5"
						on:click={saveHandler}
						disabled={saving}
						type="button"
					>
						{$i18n.t('Save')}
						{#if saving}
							<Spinner className="size-3" />
						{/if}
					</button>
				{/if}

				<button
					class="px-2.5 py-1 text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-full flex items-center gap-1.5"
					on:click={runNowHandler}
					type="button"
					disabled={loading}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							d="M6.3 2.84A1.5 1.5 0 0 0 4 4.11v11.78a1.5 1.5 0 0 0 2.3 1.27l9.344-5.891a1.5 1.5 0 0 0 0-2.538L6.3 2.841Z"
						/>
					</svg>
					<div class="hidden md:block">{$i18n.t('Run now')}</div>
					{#if loading}
						<Spinner className="size-3" />
					{/if}
				</button>
			</div>
		</div>

		<!-- Content Segment: Independent Scrolling Columns based on PromptEditor -->
		<div class="flex flex-col md:flex-row gap-4 flex-1 overflow-hidden pb-2 px-1">
			<!-- Main Input Column -->
			<div class="flex-1 flex flex-col min-h-0 overflow-hidden">
				<div class="flex items-center justify-between mb-2 shrink-0 px-1">
					<div class="text-gray-500 text-xs">{$i18n.t('Instructions')}</div>
				</div>
				<div class="relative flex-1 min-h-0">
					<div
						class="bg-gray-50 dark:bg-gray-900 rounded-2xl p-4 border border-gray-100/50 dark:border-gray-850/50 h-full"
					>
						<textarea
							class="w-full h-full text-sm bg-transparent outline-hidden resize-none placeholder:text-gray-300 dark:placeholder:text-gray-700"
							bind:value={prompt}
							on:input={markDirty}
							placeholder={$i18n.t('Enter the prompt instructions for this automation...')}
						/>
					</div>
				</div>
			</div>

			<!-- Sidebar Configuration Column -->
			<div class="hidden md:flex w-full md:w-66 shrink-0 overflow-y-auto px-1 flex-col gap-5">
				<div>
					<div class="text-gray-500 text-xs mb-3">{$i18n.t('Configuration')}</div>
					<div class="space-y-1">
						<!-- Schedule -->
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Repeats')}</span>
							<ScheduleDropdown
								bind:this={scheduleDropdown}
								side="bottom"
								align="end"
								onChange={markDirty}
							/>
						</div>

						<!-- Model -->
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Model')}</span>
							<ModelDropdown bind:model_id side="bottom" align="end" onChange={markDirty} />
						</div>
					</div>
				</div>

				<!-- Status section -->
				<div>
					<div class="text-gray-500 text-xs mb-3">{$i18n.t('Status')}</div>
					<div class="space-y-2.5">
						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('State')}</span>
							<span
								class="flex items-center gap-1.5 text-xs {is_active
									? 'text-emerald-700 dark:text-emerald-400'
									: 'text-gray-600 dark:text-gray-400'}"
							>
								<span
									class="inline-block size-1.5 rounded-full {is_active
										? 'bg-emerald-500'
										: 'bg-gray-400'}"
								></span>
								{is_active ? $i18n.t('Active') : $i18n.t('Paused')}
							</span>
						</div>

						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Next run')}</span>
							<span class=" text-gray-700 dark:text-gray-300"
								>{formatNextRun(automation.next_runs?.[0] ?? automation.next_run_at)}</span
							>
						</div>

						<div class="flex items-center justify-between text-xs">
							<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Last ran')}</span>
							<span class=" text-gray-700 dark:text-gray-300"
								>{automation.last_run_at
									? formatNextRun(automation.last_run_at)
									: $i18n.t('Never')}</span
							>
						</div>
					</div>
				</div>

				<div class="flex-1 flex flex-col min-h-0 -mx-1">
					<div class="text-gray-500 text-xs mb-2 mx-1 shrink-0">
						{$i18n.t('Execution Logs')}
					</div>
					<div class="flex-1 overflow-y-auto scrollbar-hidden w-full" on:scroll={onScroll}>
						{#if runsLoading && runs.length === 0}
							<div class="flex justify-center py-4">
								<Spinner className="size-4" />
							</div>
						{:else if runs.length === 0}
							<div class="text-xs text-gray-400 py-4 tabular-nums">
								{$i18n.t('No execution logs available yet')}
							</div>
						{:else}
							<div class="space-y-0.5 w-full">
								{#each runs as run (run.id)}
									<button
										class="w-full text-left flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-gray-100/80 dark:hover:bg-gray-850/80 transition-colors {run.chat_id
											? 'cursor-pointer'
											: 'cursor-default'}"
										on:click={() => {
											if (run.chat_id) goto(`/c/${run.chat_id}`);
										}}
										type="button"
									>
										<div class="shrink-0 flex items-center justify-center">
											{#if run.status === 'success'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3 text-emerald-500"
													><path
														fill-rule="evenodd"
														d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
														clip-rule="evenodd"
													/></svg
												>
											{:else if run.status === 'error'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3 text-red-500"
													><path
														fill-rule="evenodd"
														d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
														clip-rule="evenodd"
													/></svg
												>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3 text-blue-500"
													><path
														d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
													/></svg
												>
											{/if}
										</div>
										<div class="flex-1 min-w-0">
											<div class="text-xs text-gray-800 dark:text-gray-200 truncate">
												{automation.name}
											</div>
										</div>
										<span class="shrink-0 text-[10px] text-gray-500 font-mono"
											>{formatRunTime(run.created_at)}</span
										>
									</button>
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
		</div>
	</div>
</div>
