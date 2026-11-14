<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto, url: pageUrl } = getPageContext();

	import { formatSchedule } from '$lib/utils/schedule';
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { copyToClipboard } from '$lib/utils';
	import type { AppLayoutContext } from '$lib/types';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import type i18nType from '$lib/i18n';

	import { WEBUI_NAME, baseModels, channels, folders, type AgentModel } from '$lib/stores';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal';
	import { getFolders } from '$lib/apis/folders';
	import { getChannels } from '$lib/apis/channels';

	import {
		getAutomationById,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		getAutomationRuns,
		getAutomationModels,
		updateAutomationById,
		type AutomationForm,
		type AutomationResponse,
		type AutomationRunModel
	} from '$lib/apis/automations';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationItemHeaderActions from '$lib/components/automations/AutomationItemHeaderActions.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import ScheduleDropdown from '$lib/components/automations/ScheduleDropdown.svelte';
	import ModelDropdown from '$lib/components/automations/ModelDropdown.svelte';
	import DestinationDropdown from '$lib/components/automations/DestinationDropdown.svelte';
	import TerminalDropdown from '$lib/components/automations/TerminalDropdown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	dayjs.extend(localizedFormat);

	const i18n: typeof i18nType = getContext('i18n');
	const automationsLayout: any = getContext('automationsLayout');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let automation: AutomationResponse;

	let is_active = automation.is_active;

	let loading = false;
	let showDeleteConfirm = false;
	let showCloneModal = false;

	// The page is the editor: fields start from the saved automation, Save appears once they differ.
	let name = '';
	let prompt = '';
	let model_id = '';
	let folder_id = '';
	let target_type: 'chat' | 'channel' = 'chat';
	let channel_id = '';
	let terminalServerId = '';
	let terminalCwd = '';
	let terminalServers: TerminalServer[] = [];
	let agentModels: AgentModel[] = [];
	let scheduleDropdown: ScheduleDropdown;
	let scheduleTick = 0;
	let saving = false;
	let fieldsReady = false;

	async function resetFields(source: AutomationResponse) {
		name = source.name;
		prompt = source.data.prompt;
		model_id = source.data.model_id;
		folder_id = source.folder_id ?? '';
		target_type = source.data.target?.type === 'channel' ? 'channel' : 'chat';
		channel_id = source.data.target?.channel_id ?? '';
		terminalServerId = source.data.terminal?.server_id ?? '';
		terminalCwd = source.data.terminal?.cwd ?? '';
		await tick();
		scheduleDropdown?.parseRrule(source.data.rrule);
		scheduleTick++;
		fieldsReady = true;
	}

	const rruleNow = (_tick: number) => scheduleDropdown?.buildRrule?.() ?? automation.data.rrule;
	$: dirty =
		fieldsReady &&
		(name.trim() !== automation.name ||
			prompt.trim() !== automation.data.prompt ||
			model_id !== automation.data.model_id ||
			(folder_id || '') !== (automation.folder_id ?? '') ||
			target_type !== (automation.data.target?.type === 'channel' ? 'channel' : 'chat') ||
			channel_id !== (automation.data.target?.channel_id ?? '') ||
			terminalServerId !== (automation.data.terminal?.server_id ?? '') ||
			terminalCwd.trim() !== (automation.data.terminal?.cwd ?? '') ||
			rruleNow(scheduleTick) !== automation.data.rrule);

	// Agent models depend on the chosen terminal, as in the automation modal.
	let modelRequest = 0;
	$: void loadAgentModels(terminalServerId, terminalCwd, target_type);
	async function loadAgentModels(terminalId: string, cwd: string, target: string) {
		const request = ++modelRequest;
		agentModels = [];
		if (!terminalId || target !== 'chat') return;
		try {
			const available = await getAutomationModels(
				localStorage.token,
				terminalId,
				cwd.trim(),
				automation.id
			);
			if (request === modelRequest) agentModels = available;
		} catch (error: any) {
			if (request === modelRequest) toast.error(error?.detail ?? String(error));
		}
	}

	const saveHandler = async () => {
		if (!name.trim() || !prompt.trim() || !model_id.trim()) {
			toast.error($i18n.t('Name, prompt, and model are required'));
			return;
		}
		if (target_type === 'channel' && !channel_id) {
			toast.error($i18n.t('Channel is required'));
			return;
		}
		saving = true;
		try {
			const form: AutomationForm = {
				name: name.trim(),
				folder_id: target_type === 'channel' ? null : folder_id || null,
				data: {
					prompt: prompt.trim(),
					model_id: model_id.trim(),
					rrule: scheduleDropdown.buildRrule(),
					terminal: terminalServerId
						? { server_id: terminalServerId, cwd: terminalCwd.trim() || undefined }
						: undefined,
					target: target_type === 'channel' ? { type: 'channel', channel_id } : { type: 'chat' }
				},
				meta: automation.meta ?? undefined,
				is_active
			};
			await updateAutomationById(localStorage.token, automation.id, form);
			await editSavedHandler();
			await resetFields(automation);
			toast.success($i18n.t('Automation updated'));
		} catch (error: any) {
			toast.error(error?.detail ?? String(error));
		} finally {
			saving = false;
		}
	};

	let runs: AutomationRunModel[] = [];
	let linkedRun: AutomationRunModel | null = null;
	$: visibleRuns =
		linkedRun && !runs.some((run) => run.id === linkedRun?.id)
			? [...runs, linkedRun].sort((a, b) => b.created_at - a.created_at)
			: runs;
	let linkedRunId = '';
	let alive = true;
	onDestroy(() => {
		alive = false;
	});
	$: if (($pageUrl.searchParams.get('run') ?? '') !== linkedRunId) {
		linkedRunId = $pageUrl.searchParams.get('run') ?? '';
		void revealRun(linkedRunId);
	}
	async function revealRun(id: string) {
		linkedRun = null;
		if (!id) return;
		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/automations/${encodeURIComponent(automation.id)}/runs/${encodeURIComponent(id)}`,
				{ headers: { Authorization: `Bearer ${localStorage.token}` } }
			);
			if (!response.ok) throw new Error($i18n.t('Run not found'));
			const run = await response.json();
			if (!alive || linkedRunId !== id) return;
			linkedRun = run;
			await tick();
			document.getElementById('inbox-automation-run')?.scrollIntoView({ block: 'center' });
		} catch (error) {
			if (alive && linkedRunId === id) toast.error(String(error));
		}
	}
	let runsLoading = false;
	let hasMoreRuns = true;
	let runsPage = 0;
	let foldersLoaded = false;
	let channelsLoaded = false;

	const ensureFolders = async () => {
		if (foldersLoaded || ($folders ?? []).length > 0) return;
		const res = await getFolders(localStorage.token).catch(() => null);
		if (res) folders.set(res);
		foldersLoaded = true;
	};

	const ensureChannels = async () => {
		if (channelsLoaded || ($channels ?? []).length > 0) return;
		const res = await getChannels(localStorage.token).catch(() => null);
		if (res) channels.set(res);
		channelsLoaded = true;
	};

	const formatTime = (ts: number | null): string => {
		if (!ts) return '-';
		return new Date(ts / 1_000_000).toLocaleString($i18n.language, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	const formatNextRun = (ts: number | null): string => {
		if (!ts) return $i18n.t('Not scheduled');
		const d = dayjs(ts / 1_000_000).locale($i18n.language);
		if (d.isSame(dayjs().locale($i18n.language), 'day'))
			return `${$i18n.t('Today at')} ${d.format('LT')}`;
		return d.format('L LT');
	};

	const formatDate = (ts: number): string =>
		dayjs(ts / 1_000_000)
			.locale($i18n.language)
			.format('ll');

	// A run's chat opens beside the page as a tab, like chats from a folder.
	const openRun = (run: AutomationRunModel) => {
		if (!run.chat_id) return;
		if (run.chat_id.startsWith('channel:')) {
			goto(`/channels/${run.chat_id.replace('channel:', '')}`);
			return;
		}
		const href = `/c/${run.chat_id}`;
		if (appLayout?.openPageTab) appLayout.openPageTab({ href, label: automation.name });
		else goto(href);
	};

	const copyLinkHandler = async () => {
		const copied = await copyToClipboard(`${window.location.origin}/automations/${automation.id}`);
		if (copied) toast.success($i18n.t('Copied link to clipboard'));
	};

	// The prompt grows with its text instead of scrolling inside a box.
	const autosize = (node: HTMLTextAreaElement, _value: string) => {
		const fit = () => {
			node.style.height = 'auto';
			node.style.height = `${node.scrollHeight}px`;
		};
		fit();
		return { update: fit };
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
		if (loading) return;
		loading = true;
		const res = await runAutomationById(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			automation = res;
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

		await resetFields(automation);
		await ensureFolders();
		await ensureChannels();
		terminalServers = await getTerminalServers(localStorage.token).catch(() => []);
		await loadRuns();
	});

	$: if (automation) {
		automationsLayout?.setHeader({
			itemName: automation.name,
			actions: AutomationItemHeaderActions,
			actionProps: {
				loading,
				dirty,
				saving,
				runNowHandler,
				copyLinkHandler,
				saveHandler,
				duplicateHandler: () => (showCloneModal = true),
				deleteHandler: () => (showDeleteConfirm = true)
			}
		});
	}
	import PageTitle from '$lib/components/common/PageTitle.svelte';

	const rowClass =
		'flex h-7 items-center gap-2 rounded-lg px-2 transition-colors hover:bg-gray-50 dark:hover:bg-gray-850/50';
	const labelClass =
		'flex w-[5.375rem] shrink-0 items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400';
	const valueClass = 'text-xs text-gray-700 dark:text-gray-300';
</script>

<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
<PageTitle title={(automation.name || $i18n.t('Automation')) + ' / ' + $WEBUI_NAME} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete automation?')}
	on:confirm={deleteHandler}
>
	<div class="text-sm text-gray-500 truncate">
		{$i18n.t('This will delete')} <span class="">{automation.name}</span>.
	</div>
</DeleteConfirmDialog>

<AutomationModal
	bind:show={showCloneModal}
	cloneFrom={{ ...automation, name: $i18n.t('{{name}} (Copy)', { name: automation.name }) }}
	on:save={(e) => e.detail?.id && goto(`/automations/${e.detail.id}`)}
/>

<div class="h-full overflow-y-auto scrollbar-hidden" on:scroll={onScroll}>
	<div class="w-full px-2.5 pb-12 md:px-3.5">
		<!-- One centered column, like an issue: name, prompt, properties, then activity. -->
		<div>
			<input
				class="w-full bg-transparent text-[0.9375rem] font-normal text-gray-800 outline-hidden placeholder:text-gray-400 dark:text-gray-200 dark:placeholder:text-gray-500"
				bind:value={name}
				aria-label={$i18n.t('Name')}
				placeholder={$i18n.t('Automation name')}
			/>
			<textarea
				class="mt-1 w-full resize-none overflow-hidden bg-transparent text-xs font-normal leading-relaxed text-gray-500 outline-hidden placeholder:text-gray-400 dark:text-gray-400 dark:placeholder:text-gray-500"
				bind:value={prompt}
				use:autosize={prompt}
				rows={1}
				aria-label={$i18n.t('Instructions')}
				placeholder={$i18n.t('Enter prompt here.')}
			></textarea>

			<div class="mt-6 mb-1 text-[0.6875rem] text-gray-400 dark:text-gray-500">
				{$i18n.t('Properties')}
			</div>
			<div class="-mx-2">
				<div class={rowClass}>
					<span class={labelClass}>
						<svg class="size-3 shrink-0" viewBox="0 0 16 16" fill="none" aria-hidden="true"
							><circle cx="8" cy="8" r="5.75" stroke="currentColor" stroke-width="1.5" /><path
								d="M8 2.25a5.75 5.75 0 0 1 0 11.5z"
								fill="currentColor"
							/></svg
						>{$i18n.t('Status')}
					</span>
					<span class="min-w-0 truncate {valueClass}"
						>{is_active ? $i18n.t('Active') : $i18n.t('Paused')}</span
					>
					<Switch
						state={is_active}
						on:change={toggleHandler}
						ariaLabel={is_active ? $i18n.t('Active') : $i18n.t('Paused')}
					/>
				</div>

				<div class={rowClass}>
					<span class={labelClass}
						><Calendar className="size-3 shrink-0" />{$i18n.t('Schedule')}</span
					>
					<div class="min-w-0 flex-1">
						<ScheduleDropdown
							bind:this={scheduleDropdown}
							plain
							side="bottom"
							align="start"
							onChange={() => scheduleTick++}
						/>
					</div>
				</div>

				<div class={rowClass}>
					<span class={labelClass}><Sparkles className="size-3 shrink-0" />{$i18n.t('Model')}</span>
					<div class="min-w-0 flex-1">
						<ModelDropdown
							bind:model_id
							items={[...$baseModels, ...agentModels]}
							plain
							side="bottom"
							align="start"
						/>
					</div>
				</div>

				<div class={rowClass}>
					<span class={labelClass}
						><Folder className="size-3 shrink-0" />{$i18n.t('Destination')}</span
					>
					<div class="min-w-0 flex-1">
						<DestinationDropdown
							bind:target_type
							bind:channel_id
							bind:folder_id
							folders={$folders}
							channels={$channels}
							plain
							side="bottom"
							align="start"
						/>
					</div>
				</div>

				<div class={rowClass}>
					<span class={labelClass}
						><Icon name="terminal" size={12} class="shrink-0" />{$i18n.t('Terminal')}</span
					>
					<div class="min-w-0 flex-1">
						<TerminalDropdown
							{terminalServers}
							bind:terminalServerId
							bind:terminalCwd
							plain
							side="bottom"
							align="start"
						/>
					</div>
				</div>

				<div class={rowClass}>
					<span class={labelClass}>
						<svg
							class="size-3 shrink-0"
							viewBox="0 0 16 16"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							aria-hidden="true"><circle cx="8" cy="8" r="5.75" /><path d="M8 5v3l2 1.5" /></svg
						>{$i18n.t('Next run')}
					</span>
					<span
						class="min-w-0 flex-1 truncate text-xs {is_active
							? 'text-gray-700 dark:text-gray-300'
							: 'text-gray-400 dark:text-gray-500'}"
						>{is_active
							? formatNextRun(automation.next_runs?.[0] ?? automation.next_run_at)
							: $i18n.t('Paused')}</span
					>
				</div>
			</div>

			<div class="mt-3 text-[0.6875rem] text-gray-400 dark:text-gray-500">
				{$i18n.t('Created {{date}}', { date: formatDate(automation.created_at) })} · {$i18n.t(
					'Updated {{date}}',
					{ date: formatDate(automation.updated_at) }
				)}
			</div>
		</div>

		<!-- What happened: each run, newest first. -->
		<section class="mt-6">
			<div class="mb-1 text-[0.6875rem] text-gray-400 dark:text-gray-500">
				{$i18n.t('Activity')}
			</div>
			<div class="-mx-2">
				{#if runsLoading && visibleRuns.length === 0}
					<div class="flex px-2 py-3"><Spinner className="size-3.5" /></div>
				{/if}
				{#each visibleRuns as run (run.id)}
					<button
						id={run.id === linkedRun?.id ? 'inbox-automation-run' : undefined}
						type="button"
						class="flex h-7 w-full items-center gap-2 rounded-lg px-2 text-left text-xs transition-colors enabled:hover:bg-gray-50 dark:enabled:hover:bg-gray-850/50 {run.id ===
						linkedRun?.id
							? 'bg-gray-50 dark:bg-gray-850/50'
							: ''}"
						disabled={!run.chat_id}
						on:click={() => openRun(run)}
					>
						<span
							class="flex shrink-0 text-gray-400 dark:text-gray-500"
							aria-label={run.status === 'success' ? $i18n.t('Succeeded') : $i18n.t('Failed')}
						>
							{#if run.status === 'success'}<Check className="size-3" />{:else}<XMark
									className="size-3"
								/>{/if}
						</span>
						<span class="min-w-0 truncate text-gray-700 dark:text-gray-300" title={run.error ?? ''}>
							{run.status === 'success'
								? $i18n.t('Ran')
								: run.error
									? `${$i18n.t('Failed')}: ${run.error}`
									: $i18n.t('Failed')}
						</span>
						<span class="shrink-0 tabular-nums text-gray-400 dark:text-gray-500"
							>· {formatTime(run.created_at)}</span
						>
					</button>
				{/each}
				{#if runsLoading && runs.length > 0}
					<div class="flex px-2 py-2"><Spinner className="size-3.5" /></div>
				{/if}
				{#if !hasMoreRuns || (!runsLoading && runs.length === 0)}
					<div class="flex h-7 items-center gap-2 px-2 text-xs">
						<Plus className="size-3 shrink-0 text-gray-400 dark:text-gray-500" strokeWidth="2" />
						<span class="text-gray-700 dark:text-gray-300">{$i18n.t('Automation created')}</span>
						<span class="shrink-0 tabular-nums text-gray-400 dark:text-gray-500"
							>· {formatTime(automation.created_at)}</span
						>
					</div>
				{/if}
			</div>
		</section>
	</div>
</div>
