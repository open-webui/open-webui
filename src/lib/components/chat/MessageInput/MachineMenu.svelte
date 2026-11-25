<script lang="ts">
	export let modelId: string | null = null;
	import { getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { templatesApi, resolveMachineTarget, type MachineTarget } from '$lib/apis/machines';
	import UserMachinesModal from '../UserMachinesModal.svelte';
	import { updateChatById } from '$lib/apis/chats';
	import { toast } from 'svelte-sonner';
	import MachineSystemInfoModal from '../MachineSystemInfoModal.svelte';
	import MachineFilesModal from '../MachineFilesModal.svelte';
	import WorkingDirectoryMenu from './WorkingDirectoryMenu.svelte';
	import type { MachineContext } from '$lib/types';

	import { config, settings, showSettings, machines, user } from '$lib/stores';
	import { selectMachine } from '$lib/utils/machines';
	import { isTemporaryChatId, isSavedChatId } from '$lib/utils/chatId';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Server from '$lib/components/icons/Server.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import { fly } from 'svelte/transition';
	import MachineItemMenu from './MachineItemMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import { getChatContext } from '$lib/components/chat/context';

	const { chatId: activeChatId, temporary } = getChatContext();

	const i18n = getContext<any>('i18n');
	export let selectedMachineId: Pick<Writable<string | null>, 'subscribe' | 'set'>;

	const rowClass =
		'flex w-full min-w-0 gap-2 items-center h-[1.6875rem] pl-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-base-50/40 dark:hover:bg-base-800/40';
	const headerButtonClass =
		'p-0.5 rounded-md text-base-400 hover:text-base-600 dark:text-base-500 dark:hover:text-base-300 transition';
	const moreClass =
		'flex items-center opacity-0 pointer-events-none transition-opacity group-hover/terminal:opacity-100 group-hover/terminal:pointer-events-auto group-focus-within/terminal:opacity-100 group-focus-within/terminal:pointer-events-auto';

	export let show = false;
	export let inMenu = false;
	export let tab = '';
	const closeMenu = () => {
		show = false;
		if (inMenu) tab = '';
	};
	export let disabled = false;
	export let chatId: string | null = null;
	export let machineContext: MachineContext | null = null;
	/** Also offers the working directory of the selected machine. */
	export let showDirectory = true;
	/** Replaces the icon button that opens the menu; receives the selected ID and its label. */
	export let trigger: import('svelte').Snippet<[string | null, string]> | undefined = undefined;

	// Connections the user may create machines on; a machine on one of them is theirs to manage.
	let writable: { id: string; name: string }[] = [];
	$: if (inMenu ? tab === 'terminal' : show)
		templatesApi('/connections')
			.then((rows) => (writable = rows))
			.catch(() => (writable = []));
	$: manageable = new Set(writable.map((c) => c.id));
	const connectionOf = (id: string) =>
		id.startsWith('template:') ? id.slice('template:'.length, id.lastIndexOf(':')) : '';
	const canManage = (machine: any, ids: Set<string>) =>
		!!machine.template_id && ids.has(connectionOf(machine.id));

	// Lifecycle actions act on this chat's instance of a machine the user manages.
	const instanceContext = () => ({
		chat_id: isSavedChatId($activeChatId) ? $activeChatId : null,
		model_id: modelId
	});
	const instanceStatus = async (id: string) => {
		const query = new URLSearchParams();
		const context = instanceContext();
		if (context.chat_id) query.set('chat_id', context.chat_id);
		if (context.model_id) query.set('model_id', context.model_id);
		return (await templatesApi(`/${encodeURIComponent(id)}/instance?${query}`))?.status ?? null;
	};
	const lifecycleCopy = {
		restart: {
			title: 'Restart {{name}}?',
			message: 'Running work stops and the instance starts again. Files are kept.',
			label: 'Restart',
			pending: 'Restarting {{name}}…',
			done: '{{name}} restarted'
		},
		stop: {
			title: 'Stop {{name}}?',
			message:
				'Running work stops. Files are kept, and the instance starts again when it is next used.',
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
		toast.promise(templatesApi(`/${encodeURIComponent(id)}/${action}`, 'POST', instanceContext()), {
			loading: $i18n.t(copy.pending, { name }),
			success: () => $i18n.t(copy.done, { name }),
			error: (e) => (e instanceof Error ? e.message : String(e))
		});
	};
	const confirmLifecycle = (id: string, name: string, action: 'restart' | 'stop') => {
		pending = { id, name, action };
		closeMenu();
		showConfirm = true;
	};

	$: systemMachines = ($machines ?? []).filter(
		(t) => t.id && !(($temporary || isTemporaryChatId($activeChatId)) && t.scope === 'chat')
	);
	// Tether presences are the user's own paired devices, listed apart from servers.
	const isDevice = (machine: any) => machine.id.startsWith('tether:');
	$: systemSections = [
		{ devices: false, machines: systemMachines.filter((t) => !isDevice(t)) },
		{ devices: true, machines: systemMachines.filter(isDevice) }
	].filter((section) => !section.devices || section.machines.length > 0);

	const toggleMachine = (id: string) => {
		closeMenu();
		selectMachine(selectedMachineId, $selectedMachineId === id ? null : id, chatId);
	};

	$: selectedSystemMachine = systemMachines.find(
		(t) => !!$selectedMachineId && t.id === $selectedMachineId
	);
	$: folderTarget = resolveMachineTarget($selectedMachineId, systemMachines, '', {
		chatId: $activeChatId || null,
		modelId: modelId
	});
	$: selectedDevice = !!selectedSystemMachine && isDevice(selectedSystemMachine);

	$: selectedLabel =
		selectedSystemMachine?.name ||
		selectedSystemMachine?.id ||
		($selectedMachineId ? $i18n.t('Unavailable machine') : $i18n.t('Machine'));
	$: if (disabled && (show || (inMenu && tab === 'terminal'))) closeMenu();

	let showMachines = false;
	let managedMachineId: string | null = null;
	const openMachineDialog = (id: string | null) => {
		managedMachineId = id;
		closeMenu();
		showMachines = true;
	};
	let info: { target: MachineTarget; label: string } | null = null;
	let files: { target: MachineTarget; label: string } | null = null;
	const openFiles = async (selector: string, label: string) => {
		const target = resolveMachineTarget(selector, systemMachines, localStorage.token ?? '', {
			chatId: $activeChatId || null,
			modelId: modelId
		});
		if (!target) return;
		closeMenu();
		await tick();
		files = { target, label };
	};
	const openInfo = async (selector: string, label: string) => {
		if (
			systemMachines.find((t) => !!selector && t.id === selector)?.scope === 'chat' &&
			!isSavedChatId($activeChatId)
		)
			return;
		const target = resolveMachineTarget(selector, systemMachines, localStorage.token ?? '', {
			chatId: $activeChatId || null,
			modelId: modelId
		});
		if (!target) return;
		closeMenu();
		await tick();
		info = { target, label };
	};
	$: if (
		!$config?.features?.enable_tool_servers ||
		(info &&
			// A new chat has no ID: the store holds '' and the target holds null.
			((info.target.context.chatId ?? '') !== ($activeChatId || '') ||
				!systemMachines.some((t) => t.id === info?.target.selector)))
	)
		info = null;

	$: triggerClass = `flex items-center gap-1.5 translate-y-[1px] text-[0.8125rem] transition rounded-lg ${
		disabled
			? 'p-1 cursor-not-allowed opacity-40 text-base-400 dark:text-base-600'
			: `text-base-600 hover:text-base-700 dark:text-base-300 dark:hover:text-base-200 cursor-pointer ${
					$selectedMachineId && selectedLabel ? ' p-1 ' : ' p-1 opacity-50'
				}`
	}`;
</script>

{#snippet menuItems()}
	{#if $selectedMachineId && !selectedSystemMachine}
		<button
			type="button"
			role="menuitemradio"
			aria-checked="true"
			class="{rowClass} pr-2 bg-base-50/40 dark:bg-base-800/40"
			on:click={() => toggleMachine($selectedMachineId)}
		>
			<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
			<span class="flex-1 truncate text-left">{selectedLabel}</span>
			<Check className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
		</button>
	{/if}
	<!-- Machines, then the user's own devices -->
	{#each systemSections as section}
		<div class="flex items-center justify-between pl-2 pr-1 py-1">
			<span
				class="text-[0.625rem] font-normal text-base-400 dark:text-base-500 uppercase tracking-wider"
			>
				{section.devices ? $i18n.t('Your devices') : $i18n.t('Machines')}
			</span>
			{#if !section.devices}
				<div class="flex items-center gap-0.5">
					{#if writable.length}
						<Tooltip content={$i18n.t('New machine')} placement="top">
							<button
								type="button"
								aria-label={$i18n.t('New machine')}
								class={headerButtonClass}
								on:click|stopPropagation={() => openMachineDialog(null)}
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
									closeMenu();
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

		{#each section.machines as machine}
			{@const label = machine.name || $i18n.t('Machine')}
			{@const owned = canManage(machine, manageable)}
			{@const reachable = machine.scope !== 'chat' || isSavedChatId($activeChatId)}
			<div class="group/terminal relative rounded-xl">
				<button
					type="button"
					role="menuitemradio"
					aria-checked={$selectedMachineId === machine.id}
					class="{rowClass} {$selectedMachineId === machine.id
						? 'pr-14 bg-base-50/40 dark:bg-base-800/40'
						: 'pr-8'}"
					on:click={() => toggleMachine(machine.id)}
				>
					<div class="flex flex-1 gap-2 items-center truncate">
						{#if section.devices}
							<Server className="size-3.5 shrink-0" strokeWidth="2" />
						{:else}
							<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
						{/if}
						<span class="truncate">{label}</span>
					</div>
					{#if $selectedMachineId === machine.id}
						<div class="absolute right-2 text-emerald-600 dark:text-emerald-400">
							<Check className="size-3.5" />
						</div>
					{/if}
				</button>
				<div
					class="absolute inset-y-0 {$selectedMachineId === machine.id
						? 'right-6'
						: 'right-1'} {moreClass}"
				>
					<MachineItemMenu
						{label}
						loadStatus={owned && reachable ? () => instanceStatus(machine.id) : null}
						onRestart={() => confirmLifecycle(machine.id, label, 'restart')}
						onStop={() => confirmLifecycle(machine.id, label, 'stop')}
						onStart={() => runLifecycle(machine.id, label, 'start')}
						onInfo={reachable ? () => openInfo(machine.id, label) : null}
						onFiles={reachable ? () => openFiles(machine.id, label) : null}
						onSettings={owned ? () => openMachineDialog(machine.id) : null}
					/>
				</div>
			</div>
		{/each}
	{/each}
{/snippet}

{#if inMenu}
	{#if tab === ''}
		<div in:fly={{ x: -20, duration: 150 }}>
			<button
				type="button"
				role="menuitem"
				{disabled}
				class="flex w-full min-w-0 gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl text-left hover:bg-base-50/40 dark:hover:bg-base-800/40 disabled:cursor-not-allowed disabled:opacity-40"
				on:click={() => {
					tab = 'terminal';
				}}
			>
				{#if selectedDevice}<Server className="size-3.5 shrink-0" strokeWidth="2" />{:else}<Cloud
						className="size-3.5 shrink-0"
						strokeWidth="2"
					/>{/if}
				<span class="flex-1 truncate">{selectedLabel}</span>
				<div class="text-base-500"><ChevronRight /></div>
			</button>
		</div>
	{:else if tab === 'terminal'}
		<div class="flex min-h-0 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
			<button
				role="menuitem"
				class="flex w-full shrink-0 justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal select-none cursor-pointer rounded-xl hover:bg-base-50/40 dark:hover:bg-base-800/40"
				on:click={() => {
					tab = '';
				}}
			>
				<ChevronLeft />
				<div class="flex items-center w-full justify-between">
					<div>{$i18n.t('Machines')}</div>
				</div>
			</button>
			<div class="min-h-0 overflow-y-auto overflow-x-hidden scrollbar-thin">
				{@render menuItems()}
			</div>
		</div>
	{/if}
{:else}
	<div class="flex items-center translate-x-0.5">
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

					{#if $selectedMachineId && selectedLabel}
						<span data-input-label class="truncate text-[0.8125rem] max-w-[9.375rem]"
							>{selectedLabel}</span
						>
					{/if}
				</button>
			</Tooltip>
		{:else}
			<Dropdown bind:show align="start">
				{#if trigger}
					{@render trigger($selectedMachineId, selectedLabel)}
				{:else}
					<Tooltip content={selectedLabel} placement="top">
						<button type="button" aria-label={selectedLabel} class={triggerClass}>
							{#if selectedDevice}
								<Server className="size-3.5" strokeWidth="2" />
							{:else}
								<Cloud className="size-3.5" strokeWidth="2" />
							{/if}

							{#if $selectedMachineId && selectedLabel}
								<span data-input-label class="truncate text-[0.8125rem] max-w-[9.375rem]"
									>{selectedLabel}</span
								>
							{/if}
						</button>
					</Tooltip>
				{/if}

				<div slot="content">
					<DropdownMenu
						className="w-60 max-w-[calc(100vw-2rem)] max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
					>
						{@render menuItems()}
					</DropdownMenu>
				</div>
			</Dropdown>
		{/if}
	</div>
{/if}

{#if info}
	{#key info}
		<MachineSystemInfoModal target={info.target} label={info.label} onClose={() => (info = null)} />
	{/key}
{/if}

{#if showDirectory && folderTarget && (selectedSystemMachine?.scope !== 'chat' || isSavedChatId(chatId))}
	{#key `${$user?.id}:${folderTarget.selector}:${chatId ?? ''}`}
		<WorkingDirectoryMenu
			{inMenu}
			bind:tab
			target={folderTarget}
			{chatId}
			userId={$user?.id ?? ''}
			bind:machineContext
			onSelect={async (path) => {
				if (isSavedChatId(chatId)) {
					await updateChatById(localStorage.token, chatId!, { working_directory: path });
				}
			}}
			{disabled}
		/>
	{/key}
{/if}

{#if showMachines}
	<UserMachinesModal
		bind:show={showMachines}
		machineId={managedMachineId}
		connections={writable}
		onCreate={async (id) => selectMachine(selectedMachineId, id, chatId)}
	/>
{/if}

{#if files}
	{#key files}
		<MachineFilesModal target={files.target} label={files.label} onClose={() => (files = null)} />
	{/key}
{/if}

<ConfirmDialog
	bind:show={showConfirm}
	title={pending ? $i18n.t(lifecycleCopy[pending.action].title, { name: pending.name }) : ''}
	message={pending ? $i18n.t(lifecycleCopy[pending.action].message) : ''}
	confirmLabel={pending ? $i18n.t(lifecycleCopy[pending.action].label) : undefined}
	onConfirm={() => pending && runLifecycle(pending.id, pending.name, pending.action)}
/>
