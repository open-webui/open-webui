<script lang="ts">
	export let modelId: string | null = null;
	import { getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { templatesApi, resolveTerminalTarget, type TerminalTarget } from '$lib/apis/terminal';
	import UserTerminalsModal from '../UserTerminalsModal.svelte';
	import { updateChatById } from '$lib/apis/chats';
	import { toast } from 'svelte-sonner';
	import TerminalSystemInfoModal from '../TerminalSystemInfoModal.svelte';
	import TerminalFilesModal from '../TerminalFilesModal.svelte';
	import WorkingDirectoryMenu from './WorkingDirectoryMenu.svelte';
	import type { TerminalContext } from '$lib/types';

	import {
		chatId as activeChatId,
		config,
		settings,
		showSettings,
		terminalServers,
		temporaryChatEnabled,
		user
	} from '$lib/stores';
	import { selectTerminal } from '$lib/utils/terminal';
	import { isTemporaryChatId, isSavedChatId } from '$lib/utils/chatId';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Server from '$lib/components/icons/Server.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import TerminalItemMenu from './TerminalItemMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext<any>('i18n');
	export let selectedTerminalId: Pick<Writable<string | null>, 'subscribe' | 'set'>;

	const rowClass =
		'flex w-full min-w-0 gap-2 items-center h-[1.6875rem] pl-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40';
	const headerButtonClass =
		'p-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition';
	const moreClass =
		'flex items-center opacity-0 pointer-events-none transition-opacity group-hover/terminal:opacity-100 group-hover/terminal:pointer-events-auto group-focus-within/terminal:opacity-100 group-focus-within/terminal:pointer-events-auto';

	export let show = false;
	export let inMenu = false;
	export let disabled = false;
	export let chatId: string | null = null;
	export let terminalContext: TerminalContext | null = null;

	// Connections the user may create terminals on; a terminal on one of them is theirs to manage.
	let writable: { id: string; name: string }[] = [];
	$: if (show)
		templatesApi('/connections')
			.then((rows) => (writable = rows))
			.catch(() => (writable = []));
	$: manageable = new Set(writable.map((c) => c.id));
	const connectionOf = (id: string) =>
		id.startsWith('template:') ? id.slice('template:'.length, id.lastIndexOf(':')) : '';
	const canManage = (terminal: any, ids: Set<string>) =>
		!!terminal.template_id && ids.has(connectionOf(terminal.id));

	// Lifecycle actions act on this chat's machine of a terminal the user manages.
	const machineContext = () => ({
		chat_id: isSavedChatId($activeChatId) ? $activeChatId : null,
		model_id: modelId
	});
	const machineStatus = async (id: string) => {
		const query = new URLSearchParams();
		const context = machineContext();
		if (context.chat_id) query.set('chat_id', context.chat_id);
		if (context.model_id) query.set('model_id', context.model_id);
		return (await templatesApi(`/${encodeURIComponent(id)}/instance?${query}`))?.status ?? null;
	};
	const lifecycleCopy = {
		restart: {
			title: 'Restart {{name}}?',
			message: 'Running work stops and the machine starts again. Files are kept.',
			label: 'Restart',
			pending: 'Restarting {{name}}…',
			done: '{{name}} restarted'
		},
		stop: {
			title: 'Stop {{name}}?',
			message:
				'Running work stops. Files are kept, and the machine starts again when it is next used.',
			label: 'Stop',
			pending: 'Stopping {{name}}…',
			done: '{{name}} stopped'
		},
		start: { pending: 'Starting {{name}}…', done: '{{name}} started' }
	};
	let pending: { id: string; name: string; action: 'restart' | 'stop' } | null = null;
	let showConfirm = false;
	const runLifecycle = (id: string, name: string, action: 'restart' | 'stop' | 'start') => {
		const copy = lifecycleCopy[action];
		toast.promise(templatesApi(`/${encodeURIComponent(id)}/${action}`, 'POST', machineContext()), {
			loading: $i18n.t(copy.pending, { name }),
			success: () => $i18n.t(copy.done, { name }),
			error: (e) => (e instanceof Error ? e.message : String(e))
		});
	};
	const confirmLifecycle = (id: string, name: string, action: 'restart' | 'stop') => {
		pending = { id, name, action };
		show = false;
		showConfirm = true;
	};

	$: systemTerminals = ($terminalServers ?? []).filter(
		(t) =>
			t.id && !(($temporaryChatEnabled || isTemporaryChatId($activeChatId)) && t.scope === 'chat')
	);
	// Tether presences are the user's own paired devices, listed apart from servers.
	const isDevice = (terminal: any) => terminal.id.startsWith('tether:');
	$: systemSections = [
		{ devices: false, terminals: systemTerminals.filter((t) => !isDevice(t)) },
		{ devices: true, terminals: systemTerminals.filter(isDevice) }
	].filter((section) => !section.devices || section.terminals.length > 0);
	$: directTerminals = (
		$config?.features?.enable_direct_integrations &&
		($user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true))
			? ($settings?.terminalServers ?? [])
			: []
	).filter((s) => s.url);

	const toggleTerminal = (id: string) => {
		show = false;
		selectTerminal(selectedTerminalId, $selectedTerminalId === id ? null : id, chatId);
	};

	$: selectedSystemTerminal = systemTerminals.find(
		(t) => !!$selectedTerminalId && t.id === $selectedTerminalId
	);
	$: selectedDirectTerminal = directTerminals.find((t) => t.url === $selectedTerminalId);
	$: folderTarget = resolveTerminalTarget(
		$selectedTerminalId,
		systemTerminals,
		directTerminals,
		'',
		{ chatId: $activeChatId || null, modelId: modelId }
	);
	$: selectedDevice = !!selectedSystemTerminal && isDevice(selectedSystemTerminal);

	$: selectedLabel =
		selectedSystemTerminal?.name ||
		selectedSystemTerminal?.id ||
		selectedDirectTerminal?.name ||
		selectedDirectTerminal?.url?.replace(/^https?:\/\//, '') ||
		($selectedTerminalId ? $i18n.t('Unavailable terminal') : $i18n.t('Terminal'));
	$: if (disabled && show) show = false;

	let showTerminals = false;
	let managedTerminalId: string | null = null;
	const openTerminalDialog = (id: string | null) => {
		managedTerminalId = id;
		show = false;
		showTerminals = true;
	};
	let info: { target: TerminalTarget; label: string } | null = null;
	let files: { target: TerminalTarget; label: string } | null = null;
	const openFiles = async (selector: string, label: string) => {
		const target = resolveTerminalTarget(
			selector,
			systemTerminals,
			directTerminals,
			localStorage.token ?? '',
			{ chatId: $activeChatId || null, modelId: modelId }
		);
		if (!target) return;
		show = false;
		await tick();
		files = { target, label };
	};
	const openInfo = async (selector: string, label: string) => {
		if (
			systemTerminals.find((t) => !!selector && t.id === selector)?.scope === 'chat' &&
			!isSavedChatId($activeChatId)
		)
			return;
		const target = resolveTerminalTarget(
			selector,
			systemTerminals,
			directTerminals,
			localStorage.token ?? '',
			{ chatId: $activeChatId || null, modelId: modelId }
		);
		if (!target) return;
		show = false;
		await tick();
		info = { target, label };
	};
	$: if (
		!$config?.features?.enable_tool_servers ||
		(info &&
			// A new chat has no ID: the store holds '' and the target holds null.
			((info.target.context.chatId ?? '') !== ($activeChatId || '') ||
				(info.target.system
					? !systemTerminals.some((t) => t.id === info?.target.selector)
					: !directTerminals.some((t) => t.url === info?.target.selector))))
	)
		info = null;

	$: triggerClass = inMenu
		? `flex w-full min-w-0 items-center gap-2 h-[1.6875rem] px-2 text-[0.8125rem] rounded-xl text-left ${disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}`
		: `flex items-center gap-1.5 translate-y-[1px] text-[0.8125rem] transition rounded-lg ${
				disabled
					? 'p-1 cursor-not-allowed opacity-40 text-gray-400 dark:text-gray-600'
					: `text-gray-600 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200 cursor-pointer ${
							$selectedTerminalId && selectedLabel ? ' p-1 ' : ' p-1 opacity-50'
						}`
			}`;
</script>

<div class={inMenu ? 'w-full' : 'flex items-center translate-x-0.5'}>
	{#if disabled}
		<Tooltip content={selectedLabel} placement="top">
			<button
				type="button"
				disabled
				aria-disabled="true"
				aria-label={selectedLabel}
				class={triggerClass}
			>
				{#if selectedDevice}
					<Server className="size-3.5" strokeWidth="2" />
				{:else}
					<Cloud className="size-3.5" strokeWidth="2" />
				{/if}

				{#if inMenu || ($selectedTerminalId && selectedLabel)}
					<span class="truncate text-[0.8125rem] {inMenu ? 'flex-1' : 'max-w-[9.375rem]'}"
						>{selectedLabel}</span
					>
				{/if}
				{#if inMenu}<ChevronRight />{/if}
			</button>
		</Tooltip>
	{:else}
		<Dropdown bind:show align="start">
			<Tooltip content={selectedLabel} placement="top">
				<button type="button" aria-label={selectedLabel} class={triggerClass}>
					{#if selectedDevice}
						<Server className="size-3.5" strokeWidth="2" />
					{:else}
						<Cloud className="size-3.5" strokeWidth="2" />
					{/if}

					{#if inMenu || ($selectedTerminalId && selectedLabel)}
						<span class="truncate text-[0.8125rem] {inMenu ? 'flex-1' : 'max-w-[9.375rem]'}"
							>{selectedLabel}</span
						>
					{/if}
					{#if inMenu}<ChevronRight />{/if}
				</button>
			</Tooltip>

			<div slot="content">
				<DropdownMenu
					className="{inMenu
						? 'w-70'
						: 'w-60'} max-w-[calc(100vw-2rem)] max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
				>
					<!-- Direct terminals (gated by permission) -->
					{#if directTerminals.length > 0}
						<div class="flex items-center justify-between pl-2 pr-1 py-1">
							<span
								class="text-[0.625rem] font-normal text-gray-400 dark:text-gray-500 uppercase tracking-wider"
							>
								{$i18n.t('Direct')}
							</span>
							<Tooltip content={$i18n.t('Add Terminal')} placement="top">
								<button
									type="button"
									aria-label={$i18n.t('Add Terminal')}
									class={headerButtonClass}
									on:click|stopPropagation={() => {
										show = false;
										showSettings.set('tools');
									}}
								>
									<Plus className="size-3.5" />
								</button>
							</Tooltip>
						</div>

						{#each directTerminals as terminal}
							{@const label = terminal.name || terminal.url.replace(/^https?:\/\//, '')}
							<div class="group/terminal relative rounded-xl">
								<button
									type="button"
									role="menuitemradio"
									aria-checked={$selectedTerminalId === terminal.url}
									class="{rowClass} {$selectedTerminalId === terminal.url
										? 'pr-14 bg-gray-50/40 dark:bg-gray-800/40'
										: 'pr-8'}"
									on:click={() => toggleTerminal(terminal.url)}
								>
									<div class="flex flex-1 gap-2 items-center truncate">
										<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
										<span class="truncate">{label}</span>
									</div>
									{#if $selectedTerminalId === terminal.url}
										<div class="absolute right-2 text-emerald-600 dark:text-emerald-400">
											<Check className="size-3.5" />
										</div>
									{/if}
								</button>
								<div
									class="absolute inset-y-0 {$selectedTerminalId === terminal.url
										? 'right-6'
										: 'right-1'} {moreClass}"
								>
									<TerminalItemMenu
										{label}
										onInfo={() => openInfo(terminal.url, label)}
										onFiles={() => openFiles(terminal.url, label)}
									/>
								</div>
							</div>
						{/each}
					{/if}

					<!-- Terminals, then the user's own devices -->
					{#each systemSections as section}
						<div class="flex items-center justify-between pl-2 pr-1 py-1">
							<span
								class="text-[0.625rem] font-normal text-gray-400 dark:text-gray-500 uppercase tracking-wider"
							>
								{section.devices ? $i18n.t('Your devices') : $i18n.t('Terminals')}
							</span>
							{#if !section.devices}
								<div class="flex items-center gap-0.5">
									{#if writable.length}
										<Tooltip content={$i18n.t('New terminal')} placement="top">
											<button
												type="button"
												aria-label={$i18n.t('New terminal')}
												class={headerButtonClass}
												on:click|stopPropagation={() => openTerminalDialog(null)}
											>
												<Plus className="size-3.5" />
											</button>
										</Tooltip>
									{/if}
									{#if $user?.role === 'admin'}
										<Tooltip content={$i18n.t('Settings')} placement="top">
											<button
												type="button"
												aria-label={$i18n.t('Settings')}
												class={headerButtonClass}
												on:click|stopPropagation={() => {
													show = false;
													showSettings.set('admin:integrations');
												}}
											>
												<Cog6 className="size-3.5" />
											</button>
										</Tooltip>
									{/if}
								</div>
							{/if}
						</div>

						{#each section.terminals as terminal}
							{@const label = terminal.name || $i18n.t('Terminal')}
							{@const owned = canManage(terminal, manageable)}
							{@const reachable = terminal.scope !== 'chat' || isSavedChatId($activeChatId)}
							<div class="group/terminal relative rounded-xl">
								<button
									type="button"
									role="menuitemradio"
									aria-checked={$selectedTerminalId === terminal.id}
									class="{rowClass} {$selectedTerminalId === terminal.id
										? 'pr-14 bg-gray-50/40 dark:bg-gray-800/40'
										: 'pr-8'}"
									on:click={() => toggleTerminal(terminal.id)}
								>
									<div class="flex flex-1 gap-2 items-center truncate">
										{#if section.devices}
											<Server className="size-3.5 shrink-0" strokeWidth="2" />
										{:else}
											<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
										{/if}
										<span class="truncate">{label}</span>
									</div>
									{#if $selectedTerminalId === terminal.id}
										<div class="absolute right-2 text-emerald-600 dark:text-emerald-400">
											<Check className="size-3.5" />
										</div>
									{/if}
								</button>
								<div
									class="absolute inset-y-0 {$selectedTerminalId === terminal.id
										? 'right-6'
										: 'right-1'} {moreClass}"
								>
									<TerminalItemMenu
										{label}
										loadStatus={owned && reachable ? () => machineStatus(terminal.id) : null}
										onRestart={() => confirmLifecycle(terminal.id, label, 'restart')}
										onStop={() => confirmLifecycle(terminal.id, label, 'stop')}
										onStart={() => runLifecycle(terminal.id, label, 'start')}
										onInfo={reachable ? () => openInfo(terminal.id, label) : null}
										onFiles={reachable ? () => openFiles(terminal.id, label) : null}
										onSettings={owned ? () => openTerminalDialog(terminal.id) : null}
									/>
								</div>
							</div>
						{/each}
					{/each}
				</DropdownMenu>
			</div>
		</Dropdown>
	{/if}
</div>

{#if info}
	{#key info}
		<TerminalSystemInfoModal
			target={info.target}
			label={info.label}
			onClose={() => (info = null)}
		/>
	{/key}
{/if}

{#if folderTarget && (selectedSystemTerminal?.scope !== 'chat' || isSavedChatId(chatId))}
	{#key `${$user?.id}:${folderTarget.selector}:${chatId ?? ''}`}
		<WorkingDirectoryMenu
			{inMenu}
			target={folderTarget}
			{chatId}
			userId={$user?.id ?? ''}
			bind:terminalContext
			onSelect={async (path) => {
				if (isSavedChatId(chatId)) {
					await updateChatById(localStorage.token, chatId!, { working_directory: path });
				}
			}}
			{disabled}
		/>
	{/key}
{/if}

{#if showTerminals}
	<UserTerminalsModal
		bind:show={showTerminals}
		terminalId={managedTerminalId}
		connections={writable}
		onCreate={async (id) => selectTerminal(selectedTerminalId, id, chatId)}
	/>
{/if}

{#if files}
	{#key files}
		<TerminalFilesModal target={files.target} label={files.label} onClose={() => (files = null)} />
	{/key}
{/if}

<ConfirmDialog
	bind:show={showConfirm}
	title={pending ? $i18n.t(lifecycleCopy[pending.action].title, { name: pending.name }) : ''}
	message={pending ? $i18n.t(lifecycleCopy[pending.action].message) : ''}
	confirmLabel={pending ? $i18n.t(lifecycleCopy[pending.action].label) : undefined}
	onConfirm={() => pending && runLifecycle(pending.id, pending.name, pending.action)}
/>
