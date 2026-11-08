<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { resolveTerminalConnection, type TerminalConnection } from '$lib/apis/terminal';
	import TerminalSystemInfoModal from '../TerminalSystemInfoModal.svelte';
	import Activity from '$lib/components/icons/Activity.svelte';
	import WorkingDirectoryMenu from './WorkingDirectoryMenu.svelte';
	import type { TerminalContext } from '$lib/types';

	import {
		chatId as activeChatId,
		config,
		settings,
		showSettings,
		terminalServers,
		selectedTerminalId,
		temporaryChatEnabled,
		user
	} from '$lib/stores';
	import { getToolServersData } from '$lib/apis';
	import { isTemporaryChatId, isSavedChatId } from '$lib/utils/chatId';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Server from '$lib/components/icons/Server.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext<any>('i18n');

	export let show = false;
	export let inMenu = false;
	export let disabled = false;
	export let directoryLocked = false;
	export let chatId: string | null = null;
	export let terminalContext: TerminalContext | null = null;

	const chatContext = (terminal: any) => terminal?.contexts?.chat ?? {};

	$: systemTerminals = ($terminalServers ?? []).filter(
		(t) =>
			t.id &&
			chatContext(t) !== false &&
			!(
				($temporaryChatEnabled || isTemporaryChatId($activeChatId)) &&
				chatContext(t)?.context_id === 'chat_id'
			)
	);
	// Tether presences are the user's own paired devices, listed apart from servers.
	const isDevice = (terminal: any) => terminal.id.startsWith('tether:');
	$: systemSections = [
		{ devices: false, terminals: systemTerminals.filter((t) => !isDevice(t)) },
		{ devices: true, terminals: systemTerminals.filter(isDevice) }
	].filter((section) => section.terminals.length > 0);
	$: directTerminals = (
		$config?.features?.enable_direct_integrations &&
		($user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true))
			? ($settings?.terminalServers ?? [])
			: []
	).filter((s) => s.url);

	const refreshTerminalServersStore = async (servers: typeof directTerminals) => {
		// Preserve system terminals (those with an `id`) — only refresh direct ones
		const existingSystemTerminals = ($terminalServers ?? []).filter((t) => t.id);

		const activeTerminals = servers.filter((s) => s.enabled);
		if (activeTerminals.length > 0) {
			let data = await getToolServersData(
				activeTerminals.map((t) => ({
					url: t.url,
					auth_type: t.auth_type ?? 'bearer',
					key: t.key ?? '',
					path: t.path ?? '/openapi.json',
					config: { enable: true }
				}))
			);
			data = data.filter((d) => d && !d.error);
			terminalServers.set([
				...data.map((d, i) => ({
					...d,
					key: activeTerminals[i]?.key ?? '',
					config: activeTerminals[i]?.config ?? d?.config ?? {}
				})),
				...existingSystemTerminals
			]);
		} else {
			terminalServers.set(existingSystemTerminals);
		}
	};

	const selectDirect = async (terminal: (typeof directTerminals)[0]) => {
		const newId = $selectedTerminalId === terminal.url ? null : terminal.url;
		selectedTerminalId.set(newId);

		// Enable the selected direct terminal, disable all others
		const updatedServers = ($settings?.terminalServers ?? []).map((s) => ({
			...s,
			enabled: newId !== null && s.url === terminal.url
		}));

		settings.set({
			...$settings,
			terminalServers: updatedServers
		});

		show = false;

		// Refresh the store so Chat.svelte can inject it as a tool
		await refreshTerminalServersStore(updatedServers);
	};

	const selectSystem = async (terminal: (typeof systemTerminals)[0]) => {
		const newId = $selectedTerminalId === terminal.id ? null : terminal.id;
		selectedTerminalId.set(newId);

		// Disable all direct terminals when switching to a system terminal
		if ($settings?.terminalServers?.some((s) => s.enabled)) {
			const updatedServers = ($settings.terminalServers ?? []).map((s) => ({
				...s,
				enabled: false
			}));
			settings.set({
				...$settings,
				terminalServers: updatedServers
			});
			await refreshTerminalServersStore(updatedServers);
		}

		show = false;
	};

	$: selectedSystemTerminal = systemTerminals.find((t) => t.id === $selectedTerminalId);
	$: selectedDirectTerminal = directTerminals.find((t) => t.url === $selectedTerminalId);
	$: folderConnection = resolveTerminalConnection(
		$selectedTerminalId,
		systemTerminals,
		directTerminals,
		''
	);
	$: selectedDevice = !!selectedSystemTerminal && isDevice(selectedSystemTerminal);

	$: selectedLabel =
		selectedSystemTerminal?.name ||
		selectedSystemTerminal?.id ||
		selectedDirectTerminal?.name ||
		selectedDirectTerminal?.url?.replace(/^https?:\/\//, '') ||
		$i18n.t('Terminal');
	$: if (disabled && show) show = false;

	let info: { connection: TerminalConnection; chatId: string | null; label: string } | null = null;
	const openInfo = async (selector: string, label: string) => {
		if (
			chatContext(systemTerminals.find((t) => t.id === selector))?.context_id === 'chat_id' &&
			!isSavedChatId($activeChatId)
		)
			return;
		const connection = resolveTerminalConnection(
			selector,
			systemTerminals,
			directTerminals,
			localStorage.token ?? ''
		);
		if (!connection) return;
		const chatId = $activeChatId;
		show = false;
		await tick();
		info = { connection, chatId, label };
	};
	$: if (
		!$config?.features?.enable_tool_servers ||
		(info &&
			(info.chatId !== $activeChatId ||
				(info.connection.system
					? !systemTerminals.some((t) => t.id === info?.connection.selector)
					: !directTerminals.some((t) => t.url === info?.connection.selector))))
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
									class="p-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition"
									on:click|stopPropagation={() => {
										show = false;
										showSettings.set('tools');
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-3.5"
									>
										<path
											d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>

						{#each directTerminals as terminal}
							<div
								class="group/instance relative rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
							>
								<button
									type="button"
									role="menuitemradio"
									aria-checked={$selectedTerminalId === terminal.url}
									class="flex w-full min-w-0 gap-2 items-center h-[1.6875rem] pl-2 {$selectedTerminalId ===
									terminal.url
										? 'pr-14'
										: 'pr-8'} text-[0.8125rem] font-normal cursor-pointer rounded-xl {$selectedTerminalId ===
									terminal.url
										? 'bg-gray-50/40 dark:bg-gray-800/40'
										: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
									on:click={() => selectDirect(terminal)}
								>
									<div class="flex flex-1 gap-2 items-center truncate">
										<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
										<span class="truncate"
											>{terminal.name || terminal.url.replace(/^https?:\/\//, '')}</span
										>
									</div>
									{#if $selectedTerminalId === terminal.url}
										<div class="absolute right-2 text-emerald-600 dark:text-emerald-400">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-3.5"
											>
												<path
													fill-rule="evenodd"
													d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
									{/if}
								</button>
								<div
									class="absolute inset-y-0 {$selectedTerminalId === terminal.url
										? 'right-6'
										: 'right-1'} flex items-center opacity-0 pointer-events-none transition-opacity group-hover/instance:opacity-100 group-hover/instance:pointer-events-auto group-focus-within/instance:opacity-100 group-focus-within/instance:pointer-events-auto"
								>
									<Tooltip content={$i18n.t('System info')} placement="top">
										<button
											type="button"
											aria-label={$i18n.t('System info for {{name}}', {
												name: terminal.name || terminal.url.replace(/^https?:\/\//, '')
											})}
											class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus-visible:outline focus-visible:outline-2"
											on:click|stopPropagation={() =>
												openInfo(
													terminal.url,
													terminal.name || terminal.url.replace(/^https?:\/\//, '')
												)}><Activity className="size-3.5" /></button
										>
									</Tooltip>
								</div>
							</div>
						{/each}
					{/if}

					<!-- System terminals, then the user's own devices -->
					{#each systemSections as section}
						<div class="flex items-center justify-between pl-2 pr-1 py-1">
							<span
								class="text-[0.625rem] font-normal text-gray-400 dark:text-gray-500 uppercase tracking-wider"
							>
								{section.devices ? $i18n.t('Your devices') : $i18n.t('System')}
							</span>
							{#if !section.devices && $user?.role === 'admin'}
								<Tooltip content={$i18n.t('Add Terminal')} placement="top">
									<button
										type="button"
										aria-label={$i18n.t('Add Terminal')}
										class="p-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition"
										on:click|stopPropagation={() => {
											show = false;
											showSettings.set('admin:integrations');
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="size-3.5"
										>
											<path
												d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
											/>
										</svg>
									</button>
								</Tooltip>
							{/if}
						</div>

						{#each section.terminals as terminal}
							<div
								class="group/instance relative rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
							>
								<button
									type="button"
									role="menuitemradio"
									aria-checked={$selectedTerminalId === terminal.id}
									class="flex w-full min-w-0 gap-2 items-center h-[1.6875rem] pl-2 {$selectedTerminalId ===
									terminal.id
										? 'pr-14'
										: 'pr-8'} text-[0.8125rem] font-normal cursor-pointer rounded-xl {$selectedTerminalId ===
									terminal.id
										? 'bg-gray-50/40 dark:bg-gray-800/40'
										: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
									on:click={() => selectSystem(terminal)}
								>
									<div class="flex flex-1 gap-2 items-center truncate">
										{#if section.devices}
											<Server className="size-3.5 shrink-0" strokeWidth="2" />
										{:else}
											<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
										{/if}
										<span class="truncate">{terminal.name || $i18n.t('Terminal')}</span>
									</div>
									{#if $selectedTerminalId === terminal.id}
										<div class="absolute right-2 text-emerald-600 dark:text-emerald-400">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-3.5"
											>
												<path
													fill-rule="evenodd"
													d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
									{/if}
								</button>
								{#if chatContext(terminal)?.context_id !== 'chat_id' || isSavedChatId($activeChatId)}
									<div
										class="absolute inset-y-0 {$selectedTerminalId === terminal.id
											? 'right-6'
											: 'right-1'} flex items-center opacity-0 pointer-events-none transition-opacity group-hover/instance:opacity-100 group-hover/instance:pointer-events-auto group-focus-within/instance:opacity-100 group-focus-within/instance:pointer-events-auto"
									>
										<Tooltip content={$i18n.t('System info')} placement="top">
											<button
												type="button"
												aria-label={$i18n.t('System info for {{name}}', {
													name: terminal.name || terminal.id
												})}
												class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus-visible:outline focus-visible:outline-2"
												on:click|stopPropagation={() =>
													openInfo(terminal.id, terminal.name || terminal.id)}
												><Activity className="size-3.5" /></button
											>
										</Tooltip>
									</div>
								{/if}
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
			connection={info.connection}
			chatId={info.chatId}
			label={info.label}
			onClose={() => (info = null)}
		/>
	{/key}
{/if}

{#if folderConnection && (chatContext(selectedSystemTerminal)?.context_id !== 'chat_id' || isSavedChatId(chatId))}
	{#key `${$user?.id}:${folderConnection.selector}:${chatId ?? ''}`}
		<WorkingDirectoryMenu
			{inMenu}
			connection={folderConnection}
			{chatId}
			userId={$user?.id ?? ''}
			bind:terminalContext
			locked={directoryLocked || isSavedChatId(chatId)}
			disabled={disabled || directoryLocked || isSavedChatId(chatId)}
		/>
	{/key}
{/if}
