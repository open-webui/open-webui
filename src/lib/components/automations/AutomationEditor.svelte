<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto, url: pageUrl, tab: pageTab } = getPageContext();

	import { formatSchedule } from '$lib/utils/schedule';
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import { copyToClipboard } from '$lib/utils';
	import type { AppLayoutContext } from '$lib/types';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import type i18nType from '$lib/i18n';

	import {
		WEBUI_NAME,
		baseModels,
		channels,
		config,
		folders,
		mobile,
		showSidebar,
		user,
		type AgentModel
	} from '$lib/stores';
	import { getMachines, type MachineServer } from '$lib/apis/machines';
	import { getFolders } from '$lib/apis/folders';
	import { getChannels } from '$lib/apis/channels';

	import {
		getAutomationById,
		updateAutomationAccessGrants,
		toggleAutomationById,
		runAutomationById,
		deleteAutomationById,
		getAutomationRuns,
		getAutomationModels,
		startsNew,
		repliesInThread,
		updateAutomationById,
		regenerateAutomationToken,
		getAutomationHookUrl,
		getRunVariables,
		type AutomationForm,
		type AutomationResponse,
		type AutomationRunModel
	} from '$lib/apis/automations';

	import AutomationModal from '$lib/components/AutomationModal.svelte';
	import AutomationItemHeaderActions from '$lib/components/automations/AutomationItemHeaderActions.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import ScheduleDropdown from '$lib/components/automations/ScheduleDropdown.svelte';
	import ModelDropdown from '$lib/components/automations/ModelDropdown.svelte';
	import DestinationDropdown from '$lib/components/automations/DestinationDropdown.svelte';
	import MachineDropdown from '$lib/components/automations/MachineDropdown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import LinkIcon from '$lib/components/icons/Link.svelte';
	import WebhookDropdown from '$lib/components/automations/WebhookDropdown.svelte';
	import InputVariablesModal from '$lib/components/chat/MessageInput/InputVariablesModal.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';

	dayjs.extend(localizedFormat);

	const i18n: typeof i18nType = getContext('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let automation: AutomationResponse;

	let is_active = automation.is_active;

	// Every run uses the owner's account, so only the owner changes what it does. Anyone it's
	// shared with for editing renames, reschedules, pauses and runs it; viewers only look.
	$: canEdit = automation.user_id === $user?.id;
	$: canManage = canEdit || !!automation.write_access;
	$: canShare = canEdit || $user?.role === 'admin';
	let showAccessControlModal = false;
	let accessGrants: any[] = [];
	$: accessGrants = automation.access_grants ?? [];

	let loading = false;
	let showDeleteConfirm = false;
	let showCloneModal = false;

	// The page is the editor: fields start from the saved automation, Save appears once they differ.
	let name = '';
	let prompt = '';
	// Like the model editor's system prompt: a saved prompt starts collapsed.
	let showPrompt = true;
	// Collapsing (and its Show more / Show less toggle) only applies when the prompt is longer
	// than the five-line preview; a hidden copy of the preview tells us whether it gets cut off.
	let promptMeasureEl: HTMLDivElement | null = null;
	let promptClamped = false;
	const measurePrompt = () => {
		if (!promptMeasureEl) return;
		promptClamped = promptMeasureEl.scrollHeight > promptMeasureEl.clientHeight + 1;
	};
	$: if (promptMeasureEl) {
		void prompt;
		tick().then(measurePrompt);
	}
	onMount(() => {
		const observer = new ResizeObserver(measurePrompt);
		if (promptMeasureEl) observer.observe(promptMeasureEl);
		return () => observer.disconnect();
	});
	let model_id = '';
	let folder_id = '';
	let target_type: 'chat' | 'channel' = 'chat';
	let channel_id = '';
	let start_new = true;
	let reply_in_thread = true;
	let machineServerId = '';
	let machineCwd = '';
	let machines: MachineServer[] = [];
	let agentModels: AgentModel[] = [];
	let scheduleDropdown: ScheduleDropdown;
	let scheduleTick = 0;
	// The stored rule as the schedule fields rebuild it, so an untouched schedule is not a change.
	let savedRrule = '';
	let webhookEnabled = false;
	let webhookAllowGet = false;
	$: allowWebhook = !!$config?.features?.enable_automation_webhooks;
	$: hookUrl = getAutomationHookUrl(automation);
	let saving = false;
	let fieldsReady = false;

	async function resetFields(source: AutomationResponse) {
		name = source.name;
		prompt = source.data.prompt;
		model_id = source.data.model_id;
		folder_id = source.folder_id ?? '';
		target_type = source.data.target?.type === 'channel' ? 'channel' : 'chat';
		channel_id = source.data.target?.channel_id ?? '';
		start_new = startsNew(source.data.target);
		reply_in_thread = repliesInThread(source.data.target);
		machineServerId = automationMachineOf(source.data)?.server_id ?? '';
		machineCwd = automationMachineOf(source.data)?.cwd ?? '';
		webhookEnabled = !!source.data.webhook;
		webhookAllowGet = !!source.data.webhook?.allow_get;
		await tick();
		scheduleDropdown?.parseRrule(source.data.rrule);
		savedRrule = scheduleDropdown?.buildRrule?.() ?? source.data.rrule;
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
			start_new !== startsNew(automation.data.target) ||
			reply_in_thread !== repliesInThread(automation.data.target) ||
			machineServerId !== (automationMachineOf(automation.data)?.server_id ?? '') ||
			machineCwd.trim() !== (automationMachineOf(automation.data)?.cwd ?? '') ||
			rruleNow(scheduleTick) !== savedRrule ||
			webhookEnabled !== !!automation.data.webhook ||
			(webhookEnabled && webhookAllowGet !== !!automation.data.webhook?.allow_get));

	// Agent models depend on the chosen machine, as in the automation modal.
	let modelRequest = 0;
	$: void loadAgentModels(machineServerId, machineCwd, target_type);
	async function loadAgentModels(machineId: string, cwd: string, target: string) {
		const request = ++modelRequest;
		agentModels = [];
		// Only the owner picks the model, through the owner's machine.
		if (!machineId || target !== 'chat' || automation.user_id !== $user?.id) return;
		try {
			const available = await getAutomationModels(
				localStorage.token,
				machineId,
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
		const rrule = scheduleDropdown.buildRrule();
		if (!rrule && !webhookEnabled) {
			toast.error($i18n.t('Add a schedule or a webhook'));
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
					// An untouched schedule keeps its stored start date.
					rrule: rrule === savedRrule ? automation.data.rrule : rrule,
					webhook: webhookEnabled ? { allow_get: webhookAllowGet } : null,
					machine: machineServerId
						? { server_id: machineServerId, cwd: machineCwd.trim() || undefined }
						: undefined,
					target:
						target_type === 'channel'
							? { type: 'channel', channel_id, new_thread: start_new, reply_in_thread }
							: { type: 'chat', new_chat: start_new }
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

	const RUNS_PAGE_SIZE = 20;
	let runs: AutomationRunModel[] = [];
	let runsDirection: 'desc' | 'asc' = 'desc';
	let linkedRun: AutomationRunModel | null = null;
	$: visibleRuns =
		linkedRun && !runs.some((run) => run.id === linkedRun?.id)
			? [...runs, linkedRun].sort((a, b) =>
					runsDirection === 'asc' ? a.created_at - b.created_at : b.created_at - a.created_at
				)
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
	// Bumped on every fresh load so a slower, older response can't overwrite a newer one.
	let runsRequest = 0;
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

	let showVariablesModal = false;
	let runVariables: Record<string, any> = {};

	const runNowHandler = async () => {
		if (loading) return;
		runVariables = getRunVariables(automation.data.prompt);
		// Variables are written into the owner's prompt; others run it with the defaults.
		if (Object.keys(runVariables).length > 0 && canEdit) {
			showVariablesModal = true;
			return;
		}
		await run();
	};

	const regenerateHookUrlHandler = async () => {
		const res = await regenerateAutomationToken(localStorage.token, automation.id).catch((err) => {
			toast.error(`${err}`);
			return null;
		});
		if (res) {
			automation = res;
			toast.success($i18n.t('New URL created. The old one no longer works.'));
		}
	};

	const run = async (variables?: Record<string, any>) => {
		loading = true;
		const res = await runAutomationById(localStorage.token, automation.id, variables).catch(
			(err) => {
				toast.error(`${err}`);
				return null;
			}
		);
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
		if (loadMore && (runsLoading || !hasMoreRuns)) return;

		const request = loadMore ? runsRequest : ++runsRequest;
		runsLoading = true;

		// hasMoreRuns keeps its value until the response arrives, so the "Automation created"
		// row doesn't blink out on every reload.
		if (!loadMore) runsPage = 0;

		try {
			const fetchedRuns =
				(await getAutomationRuns(
					localStorage.token,
					automation.id,
					runsPage * RUNS_PAGE_SIZE,
					// One extra row tells us whether another page exists without an empty "Show more".
					RUNS_PAGE_SIZE + 1,
					runsDirection
				)) ?? [];
			if (request !== runsRequest) return;
			const pageRuns = fetchedRuns.slice(0, RUNS_PAGE_SIZE);
			runs = loadMore ? [...runs, ...pageRuns] : pageRuns;
			hasMoreRuns = fetchedRuns.length > RUNS_PAGE_SIZE;
			runsPage++;
		} catch {
			if (request !== runsRequest) return;
			if (!loadMore) {
				runs = [];
				hasMoreRuns = false;
			}
		}
		runsLoading = false;
	};

	let runsSortMenuOpen = false;
	$: runsSortOptions = [
		{ value: 'desc' as const, label: $i18n.t('Newest first') },
		{ value: 'asc' as const, label: $i18n.t('Oldest first') }
	];
	const setRunsDirection = (direction: 'desc' | 'asc') => {
		runsSortMenuOpen = false;
		if (runsDirection === direction) return;
		runsDirection = direction;
		void loadRuns();
	};

	onMount(async () => {
		is_active = automation.is_active;

		await resetFields(automation);
		showPrompt = !prompt.trim();
		await ensureFolders();
		await ensureChannels();
		machines = await getMachines(localStorage.token).catch(() => []);
		await loadRuns();
	});

	import PageTitle from '$lib/components/common/PageTitle.svelte';
	import { automationMachineOf } from '$lib/utils/machines';

	const rowClass =
		'flex h-7 items-center gap-2 rounded-lg px-2 transition-colors hover:bg-base-50 dark:hover:bg-base-850/50';
	const labelClass =
		'flex w-[5.375rem] shrink-0 items-center gap-1.5 text-xs text-base-500 dark:text-base-400';
	const valueClass = 'text-xs text-base-700 dark:text-base-300';
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
	<div class="text-sm text-base-500 truncate">
		{$i18n.t('This will delete')} <span class="">{automation.name}</span>.
	</div>
</DeleteConfirmDialog>

<InputVariablesModal
	bind:show={showVariablesModal}
	variables={runVariables}
	title={$i18n.t('Run {{name}}', { name: automation.name })}
	onSave={(values) => run(values)}
/>

{#if canShare}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessGrants
		accessRoles={['read', 'write']}
		share={$user?.permissions?.sharing?.automations || $user?.role === 'admin'}
		sharePublic={false}
		shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
		allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) ||
			$user?.role === 'admin'}
		onChange={async () => {
			try {
				automation = await updateAutomationAccessGrants(
					localStorage.token,
					automation.id,
					accessGrants
				);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				accessGrants = automation.access_grants ?? [];
				toast.error(`${error}`);
			}
		}}
	/>
{/if}

<AutomationModal
	bind:show={showCloneModal}
	cloneFrom={{ ...automation, name: $i18n.t('{{name}} (Copy)', { name: automation.name }) }}
	on:save={(e) => e.detail?.id && goto(`/automations/${e.detail.id}`)}
/>

<div class="h-full overflow-y-auto scrollbar-hidden">
	<div class="w-full px-2.5 pb-12 md:px-3.5">
		<!-- One centered column, like an issue: name, prompt, properties, then activity. -->
		<div>
			<div class="flex h-8 items-center gap-1">
				{#if $mobile && !pageTab}
					<div class="{$showSidebar ? 'md:hidden' : ''} -ml-1 flex flex-none items-center">
						<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
							<button
								id="sidebar-toggle-button"
								class="flex size-7 items-center justify-center text-base-400 transition"
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
								type="button"
							>
								<SidebarIcon className="size-4" />
							</button>
						</Tooltip>
					</div>
				{/if}
				<input
					class="min-w-0 flex-1 bg-transparent text-[0.9375rem] font-normal text-base-800 outline-hidden placeholder:text-base-400 dark:text-base-200 dark:placeholder:text-base-500"
					bind:value={name}
					readonly={!canManage}
					aria-label={$i18n.t('Name')}
					placeholder={$i18n.t('Automation name')}
				/>
				<AutomationItemHeaderActions
					{loading}
					{dirty}
					{saving}
					runNowHandler={canManage ? runNowHandler : null}
					{copyLinkHandler}
					{saveHandler}
					duplicateHandler={() => (showCloneModal = true)}
					shareHandler={canShare ? () => (showAccessControlModal = true) : null}
					deleteHandler={canShare ? () => (showDeleteConfirm = true) : null}
				/>
			</div>
			{#if !canEdit}
				<div class="mt-0.5 text-[0.6875rem] text-base-400 dark:text-base-500">
					{$i18n.t('Shared by {{name}}', {
						name: automation.user?.name ?? $i18n.t('Deleted User')
					})}
					· {canManage ? $i18n.t('Write') : $i18n.t('Read')}
				</div>
			{/if}
			<div class="relative">
				<div
					bind:this={promptMeasureEl}
					aria-hidden="true"
					class="pointer-events-none invisible absolute inset-x-0 top-0 line-clamp-5 whitespace-pre-wrap break-words text-xs font-normal leading-relaxed"
				>
					{prompt}
				</div>
			</div>
			{#if showPrompt || !promptClamped}
				<Textarea
					className="mt-1 w-full resize-none overflow-hidden bg-transparent text-xs font-normal leading-relaxed text-base-500 outline-hidden placeholder:text-base-400 dark:text-base-400 dark:placeholder:text-base-500"
					bind:value={prompt}
					readonly={!canEdit}
					rows={1}
					ariaLabel={$i18n.t('Instructions')}
					placeholder={$i18n.t('Enter prompt here.')}
				/>
			{:else}
				<button
					type="button"
					aria-label={$i18n.t('Instructions')}
					aria-expanded={false}
					on:click={() => {
						showPrompt = true;
					}}
					class="mt-1 w-full cursor-text text-start line-clamp-5 whitespace-pre-wrap break-words text-xs font-normal leading-relaxed text-base-500 dark:text-base-400"
				>
					{prompt}
				</button>
			{/if}
			{#if promptClamped}
				<button
					class="mt-1 block text-xs text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
					type="button"
					aria-expanded={showPrompt}
					on:click={() => {
						showPrompt = !showPrompt;
					}}
				>
					{showPrompt ? $i18n.t('Show less') : $i18n.t('Show more')}
				</button>
			{/if}

			<div class="mt-6 mb-1 text-[0.6875rem] text-base-400 dark:text-base-500">
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
						disabled={!canManage}
						on:change={toggleHandler}
						ariaLabel={is_active ? $i18n.t('Active') : $i18n.t('Paused')}
					/>
				</div>

				<div class={rowClass}>
					<span class={labelClass}
						><Calendar className="size-3 shrink-0" />{$i18n.t('Schedule')}</span
					>
					<div class="min-w-0 flex-1" inert={!canManage || undefined}>
						<ScheduleDropdown
							bind:this={scheduleDropdown}
							allowNone={webhookEnabled}
							plain
							side="bottom"
							align="start"
							onChange={() => scheduleTick++}
						/>
					</div>
				</div>

				{#if allowWebhook || automation.data.webhook}
					<div class={rowClass}>
						<span class={labelClass}
							><LinkIcon className="size-3 shrink-0" />{$i18n.t('Webhook')}</span
						>
						<div class="min-w-0 flex-1" inert={!canEdit || undefined}>
							<WebhookDropdown
								bind:enabled={webhookEnabled}
								bind:allowGet={webhookAllowGet}
								url={webhookEnabled && automation.data.webhook ? hookUrl : ''}
								onRegenerate={regenerateHookUrlHandler}
								plain
								side="bottom"
								align="start"
							/>
						</div>
					</div>
				{/if}

				<div class={rowClass}>
					<span class={labelClass}><Sparkles className="size-3 shrink-0" />{$i18n.t('Model')}</span>
					<div class="min-w-0 flex-1" inert={!canEdit || undefined}>
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
					<div class="min-w-0 flex-1" inert={!canEdit || undefined}>
						<DestinationDropdown
							bind:target_type
							bind:channel_id
							bind:folder_id
							bind:start_new
							bind:reply_in_thread
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
						><Icon name="terminal" size={12} class="shrink-0" />{$i18n.t('Machine')}</span
					>
					<div class="min-w-0 flex-1" inert={!canEdit || undefined}>
						<MachineDropdown
							{machines}
							bind:machineServerId
							bind:machineCwd
							plain
							side="bottom"
							align="start"
						/>
					</div>
				</div>

				<div class={rowClass} class:hidden={!automation.data.rrule}>
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
					<!-- localisation keys kept from the previous runs list (so they don't get automatically removed):
						{$i18n.t('Runs')}
						{$i18n.t('Last run')}
						{$i18n.t('No runs yet')}
						{$i18n.t('View chat')}
						{$i18n.t('View channel')}
					-->
					<span
						class="min-w-0 flex-1 truncate text-xs {is_active
							? 'text-base-700 dark:text-base-300'
							: 'text-base-400 dark:text-base-500'}"
						>{is_active
							? formatNextRun(automation.next_runs?.[0] ?? automation.next_run_at)
							: $i18n.t('Paused')}</span
					>
				</div>
			</div>

			<div class="mt-3 text-[0.6875rem] text-base-400 dark:text-base-500">
				{$i18n.t('Created {{date}}', { date: formatDate(automation.created_at) })} · {$i18n.t(
					'Updated {{date}}',
					{ date: formatDate(automation.updated_at) }
				)}
			</div>
		</div>

		<!-- What happened: the latest runs (newest first by default), a page at a time. -->
		<section class="mt-6">
			<div class="mb-1 flex items-center justify-between gap-2">
				<div class="text-[0.6875rem] text-base-400 dark:text-base-500">
					{$i18n.t('Activity')}
				</div>
				<Dropdown bind:show={runsSortMenuOpen} align="end" sideOffset={4}>
					<Tooltip content={$i18n.t('Sort')}>
						<button
							type="button"
							class="flex size-5 shrink-0 items-center justify-center rounded text-base-500 transition-colors duration-100 hover:text-base-800 dark:text-base-400 dark:hover:text-base-200"
							aria-label={$i18n.t('Sort')}
						>
							<Icon name="sort" size={11} strokeWidth={1.4} />
						</button>
					</Tooltip>

					<div slot="content">
						<DropdownMenu className="min-w-[9.375rem]">
							{#each runsSortOptions as option (option.value)}
								<button
									type="button"
									class="flex h-7 w-full select-none items-center gap-2 rounded-lg px-2 text-xs transition hover:bg-base-50/40 dark:hover:bg-base-0/4"
									on:click={() => setRunsDirection(option.value)}
								>
									<span class="flex-1 text-left">{option.label}</span>
									{#if runsDirection === option.value}
										<Check className="size-3 text-base-500 dark:text-base-400" />
									{/if}
								</button>
							{/each}
						</DropdownMenu>
					</div>
				</Dropdown>
			</div>
			<div class="-mx-2">
				{#if runsDirection === 'asc'}
					<div class="flex h-7 items-center gap-2 px-2 text-xs">
						<Plus className="size-3 shrink-0 text-base-400 dark:text-base-500" strokeWidth="2" />
						<span class="text-base-700 dark:text-base-300">{$i18n.t('Automation created')}</span>
						<span class="shrink-0 tabular-nums text-base-400 dark:text-base-500"
							>· {formatTime(automation.created_at)}</span
						>
					</div>
				{/if}
				{#if runsLoading && visibleRuns.length === 0}
					<div class="flex px-2 py-3"><Spinner className="size-3.5" /></div>
				{/if}
				{#each visibleRuns as run (run.id)}
					<button
						id={run.id === linkedRun?.id ? 'inbox-automation-run' : undefined}
						type="button"
						class="flex h-7 w-full items-center gap-2 rounded-lg px-2 text-left text-xs transition-colors enabled:hover:bg-base-50 dark:enabled:hover:bg-base-850/50 {run.id ===
						linkedRun?.id
							? 'bg-base-50 dark:bg-base-850/50'
							: ''}"
						disabled={!run.chat_id}
						on:click={() => openRun(run)}
					>
						<span
							class="flex shrink-0 text-base-400 dark:text-base-500"
							aria-label={run.status === 'success' ? $i18n.t('Succeeded') : $i18n.t('Failed')}
						>
							{#if run.status === 'success'}<Check className="size-3" />{:else}<XMark
									className="size-3"
								/>{/if}
						</span>
						<span class="min-w-0 truncate text-base-700 dark:text-base-300" title={run.error ?? ''}>
							{run.status === 'success'
								? $i18n.t('Ran')
								: run.error
									? `${$i18n.t('Failed')}: ${run.error}`
									: $i18n.t('Failed')}
						</span>
						<span class="shrink-0 tabular-nums text-base-400 dark:text-base-500"
							>· {formatTime(run.created_at)}</span
						>
					</button>
				{/each}
				{#if runsLoading && runs.length > 0}
					<div class="flex px-2 py-2"><Spinner className="size-3.5" /></div>
				{:else if hasMoreRuns && runs.length > 0}
					<button
						type="button"
						class="flex h-7 w-full items-center rounded-lg px-2 text-left text-xs text-base-500 transition-colors hover:bg-base-50 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-850/50 dark:hover:text-base-300"
						on:click={() => loadRuns(true)}
					>
						{$i18n.t('Show more')}
					</button>
				{/if}
				{#if runsDirection === 'desc' && (!hasMoreRuns || (!runsLoading && runs.length === 0))}
					<div class="flex h-7 items-center gap-2 px-2 text-xs">
						<Plus className="size-3 shrink-0 text-base-400 dark:text-base-500" strokeWidth="2" />
						<span class="text-base-700 dark:text-base-300">{$i18n.t('Automation created')}</span>
						<span class="shrink-0 tabular-nums text-base-400 dark:text-base-500"
							>· {formatTime(automation.created_at)}</span
						>
					</div>
				{/if}
			</div>
		</section>
	</div>
</div>
