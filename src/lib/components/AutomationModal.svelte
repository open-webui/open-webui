<script lang="ts">
	import { createEventDispatcher, getContext, tick, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import ScheduleDropdown from '$lib/components/automations/ScheduleDropdown.svelte';
	import ModelDropdown from '$lib/components/automations/ModelDropdown.svelte';
	import TerminalDropdown from '$lib/components/automations/TerminalDropdown.svelte';
	import WebhookDropdown from '$lib/components/automations/WebhookDropdown.svelte';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/machines';
	import DestinationDropdown from '$lib/components/automations/DestinationDropdown.svelte';
	import { getFolders } from '$lib/apis/folders';
	import { getChannels } from '$lib/apis/channels';
	import { baseModels, channels, config, folders, type AgentModel } from '$lib/stores';

	import {
		createAutomation,
		getAutomationModels,
		startsNew,
		repliesInThread,
		updateAutomationById,
		type AutomationForm,
		type AutomationResponse
	} from '$lib/apis/automations';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let automation: AutomationResponse | null = null;
	export let cloneFrom: AutomationResponse | null = null;
	/** Folder a new automation starts in. */
	export let folderId: string | null = null;

	let name = '';
	let prompt = '';
	let model_id = '';
	let terminalServerId = '';
	let terminalCwd = '';
	let terminalServers: TerminalServer[] = [];
	let agentModels: AgentModel[] = [];
	let modelsLoading = false;
	let initialized = false;
	let modelRequest = 0;
	let modelTimer: ReturnType<typeof setTimeout>;
	let folder_id = '';
	let target_type: 'chat' | 'channel' = 'chat';
	let channel_id = '';
	let start_new = true;
	let reply_in_thread = true;
	let is_active = true;
	let webhookEnabled = false;
	let webhookAllowGet = false;

	let loading = false;
	let foldersLoaded = false;
	let channelsLoaded = false;

	const loadAgentModels = (
		visible: boolean,
		terminalId: string,
		cwd: string,
		target: string,
		automationId?: string
	) => {
		const request = ++modelRequest;
		clearTimeout(modelTimer);
		agentModels = [];
		modelsLoading = visible && !!terminalId && target === 'chat';
		if (!visible) return;
		if (!modelsLoading) {
			if (model_id.startsWith('agent:')) model_id = '';
			return;
		}
		modelTimer = setTimeout(async () => {
			try {
				const available = await getAutomationModels(
					localStorage.token,
					terminalId,
					cwd.trim(),
					automationId
				);
				if (request !== modelRequest) return;
				agentModels = available;
				if (model_id.startsWith('agent:') && !available.some((model) => model.id === model_id)) {
					model_id = '';
				}
			} catch (error: any) {
				if (request === modelRequest) toast.error(error?.detail ?? String(error));
			} finally {
				if (request === modelRequest) modelsLoading = false;
			}
		}, 250);
	};
	$: loadAgentModels(
		show && initialized,
		terminalServerId,
		terminalCwd,
		target_type,
		automation?.id
	);
	onDestroy(() => {
		clearTimeout(modelTimer);
		modelRequest++;
	});

	// Schedule dropdown ref
	let scheduleDropdown: ScheduleDropdown;
	$: allowWebhook = !!$config?.features?.enable_automation_webhooks;

	const submitHandler = async () => {
		if (!name.trim() || !prompt.trim() || !model_id.trim()) {
			toast.error($i18n.t('Name, prompt, and model are required'));
			return;
		}
		if (target_type === 'channel' && !channel_id) {
			toast.error($i18n.t('Channel is required'));
			return;
		}
		if (!scheduleDropdown.buildRrule() && !webhookEnabled) {
			toast.error($i18n.t('Add a schedule or a webhook'));
			return;
		}
		if (scheduleDropdown?.frequency === 'ONCE') {
			const scheduled = new Date(`${scheduleDropdown.onceDate}T${scheduleDropdown.onceTime}`);
			if (scheduled <= new Date()) {
				toast.error($i18n.t('Scheduled time must be in the future'));
				return;
			}
		}
		loading = true;
		try {
			const form: AutomationForm = {
				name: name.trim(),
				folder_id: target_type === 'channel' ? null : folder_id || null,
				data: {
					prompt: prompt.trim(),
					model_id: model_id.trim(),
					rrule: scheduleDropdown.buildRrule(),
					webhook: webhookEnabled ? { allow_get: webhookAllowGet } : null,
					terminal: terminalServerId
						? { server_id: terminalServerId, cwd: terminalCwd.trim() || undefined }
						: undefined,
					target:
						target_type === 'channel'
							? { type: 'channel', channel_id, new_thread: start_new, reply_in_thread }
							: { type: 'chat', new_chat: start_new }
				},
				is_active
			};

			if (automation) {
				await updateAutomationById(localStorage.token, automation.id, form);
				toast.success($i18n.t('Automation updated'));
				show = false;
				dispatch('save', { id: automation.id });
			} else {
				const created = await createAutomation(localStorage.token, form);
				toast.success($i18n.t('Automation created'));
				show = false;
				dispatch('save', { id: created?.id });
			}
		} catch (e: any) {
			toast.error(e?.detail ?? `${e}` ?? 'Failed to save');
		} finally {
			loading = false;
		}
	};

	const init = async () => {
		initialized = false;
		await tick();
		terminalServers = await getTerminalServers(localStorage.token);
		if (!foldersLoaded && ($folders ?? []).length === 0) {
			const res = await getFolders(localStorage.token).catch(() => null);
			if (res) folders.set(res);
			foldersLoaded = true;
		}
		if (!channelsLoaded && ($channels ?? []).length === 0) {
			const res = await getChannels(localStorage.token).catch(() => null);
			if (res) channels.set(res);
			channelsLoaded = true;
		}

		terminalServerId = (automation ?? cloneFrom)?.data.terminal?.server_id ?? '';
		terminalCwd = (automation ?? cloneFrom)?.data.terminal?.cwd ?? '';
		if (automation) {
			name = automation.name;
			prompt = automation.data.prompt;
			model_id = automation.data.model_id;
			folder_id = automation.folder_id ?? '';
			target_type = automation.data.target?.type === 'channel' ? 'channel' : 'chat';
			channel_id = automation.data.target?.channel_id ?? '';
			start_new = startsNew(automation.data.target);
			reply_in_thread = repliesInThread(automation.data.target);
			is_active = automation.is_active;
			webhookEnabled = !!automation.data.webhook;
			webhookAllowGet = !!automation.data.webhook?.allow_get;
			scheduleDropdown?.parseRrule(automation.data.rrule);
		} else if (cloneFrom) {
			name = cloneFrom.name;
			prompt = cloneFrom.data.prompt;
			model_id = cloneFrom.data.model_id;
			folder_id = ($folders ?? []).some((folder) => folder.id === cloneFrom.folder_id)
				? (cloneFrom.folder_id ?? '')
				: '';
			target_type = cloneFrom.data.target?.type === 'channel' ? 'channel' : 'chat';
			channel_id = ($channels ?? []).some(
				(channel) => channel.id === cloneFrom.data.target?.channel_id
			)
				? (cloneFrom.data.target?.channel_id ?? '')
				: '';
			start_new = startsNew(cloneFrom.data.target);
			reply_in_thread = repliesInThread(cloneFrom.data.target);
			is_active = true;
			webhookEnabled = !!cloneFrom.data.webhook;
			webhookAllowGet = !!cloneFrom.data.webhook?.allow_get;
			scheduleDropdown?.parseRrule(cloneFrom.data.rrule);
		} else {
			name = '';
			prompt = '';
			model_id = '';
			folder_id = folderId ?? '';
			target_type = 'chat';
			channel_id = '';
			start_new = true;
			reply_in_thread = true;
			is_active = true;
			webhookEnabled = false;
			webhookAllowGet = false;
		}
		initialized = true;
	};

	$: if (show) {
		init();
	}
</script>

<Modal ariaLabel={name || $i18n.t('Automation')} size="lg" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between dark:text-base-100 px-4 pt-3 pb-1">
			<input
				class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
				type="text"
				bind:value={name}
				aria-label={$i18n.t('Automation title')}
				placeholder={$i18n.t('Automation title')}
			/>
			<button
				class="self-center shrink-0 ml-2"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<!-- Prompt -->
		<div class="px-4 pb-2">
			<label for="automation-instructions" class="block mb-1 text-xs text-base-500"
				>{$i18n.t('Instructions')}</label
			>
			<textarea
				id="automation-instructions"
				class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700 resize-none min-h-[min(28rem,55vh)]"
				bind:value={prompt}
				rows={8}
				placeholder={$i18n.t('Enter prompt here.')}
			/>
		</div>

		<!-- Bottom toolbar -->
		<div
			class="flex flex-col sm:flex-row sm:items-center sm:justify-between px-4 pb-3.5 pt-1 gap-2"
		>
			<div class="flex items-center gap-0.5 flex-wrap min-w-0 sm:flex-1">
				<ScheduleDropdown
					bind:this={scheduleDropdown}
					allowNone={webhookEnabled}
					side="top"
					align="start"
				/>

				{#if allowWebhook || webhookEnabled}
					<WebhookDropdown
						bind:enabled={webhookEnabled}
						bind:allowGet={webhookAllowGet}
						side="top"
						align="start"
					/>
				{/if}

				<ModelDropdown
					bind:model_id
					items={[...$baseModels, ...agentModels]}
					disabled={modelsLoading}
					side="top"
					align="start"
				/>

				<DestinationDropdown
					bind:target_type
					bind:channel_id
					bind:folder_id
					bind:start_new
					bind:reply_in_thread
					folders={$folders}
					channels={$channels}
					side="top"
					align="start"
				/>
				<TerminalDropdown
					{terminalServers}
					bind:terminalServerId
					bind:terminalCwd
					side="top"
					align="start"
				/>
			</div>

			<div class="flex items-center justify-end gap-2 shrink-0">
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal text-base-600 transition hover:bg-base-100 hover:text-base-900 disabled:opacity-60 dark:text-base-400 dark:hover:bg-base-850 dark:hover:text-base-0"
					type="button"
					on:click={() => (show = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0 disabled:cursor-not-allowed"
					on:click={submitHandler}
					type="button"
					disabled={loading || modelsLoading || !initialized}
				>
					{automation ? $i18n.t('Save') : $i18n.t('Create')}
					{#if loading}
						<span class="shrink-0"><Spinner className="size-3" /></span>
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>
