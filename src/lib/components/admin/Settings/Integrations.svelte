<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, onDestroy, getContext, tick } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const dispatch = createEventDispatcher();
	const i18n = getContext<Writable<i18nType>>('i18n');

	import { models, settings, user, terminalServers } from '$lib/stores';
	import { getTerminalServers } from '$lib/apis/terminal';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Connection from '$lib/components/chat/Settings/Tools/Connection.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';
	import AddTerminalServerModal from '$lib/components/AddTerminalServerModal.svelte';
	import AddLangfuseConnectionModal from '$lib/components/AddLangfuseConnectionModal.svelte';
	import ExternalKnowledge from './ExternalKnowledge.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	import ChartBar from '$lib/components/icons/ChartBar.svelte';

	import {
		getToolServerConnections,
		setToolServerConnections,
		getTerminalServerConnections,
		setTerminalServerConnections,
		getLangfuseConfig,
		setLangfuseConfig
	} from '$lib/apis/configs';
	import { formatLangfuseConfigSaveError } from '$lib/apis/langfuse';

	export let saveSettings: Function;

	type ToolServerConnection = any;
	type TerminalConnection = {
		id?: string;
		url?: string;
		name?: string;
		key?: string;
		enabled?: boolean;
		[key: string]: any;
	};

	type LangfuseConnection = {
		id?: string;
		url?: string;
		name?: string;
		public_key?: string;
		secret_key?: string;
		secret_key_set?: boolean;
		enabled?: boolean;
	};

	let servers: ToolServerConnection[] | null = null;
	let showConnectionModal = false;

	// Terminal server admin connections
	let terminalConnections: TerminalConnection[] = [];
	let showAddTerminalModal = false;
	let editTerminalIdx: number | null = null;

	// Langfuse admin connections
	let langfuseConnections: LangfuseConnection[] = [];
	let langfusePromptCacheTtl = 300;
	let showAddLangfuseModal = false;
	let editLangfuseIdx: number | null = null;
	let langfuseSaveTimer: ReturnType<typeof setTimeout> | null = null;

	const debouncedSaveLangfuseConfig = () => {
		if (langfuseSaveTimer) {
			clearTimeout(langfuseSaveTimer);
		}
		langfuseSaveTimer = setTimeout(() => {
			saveLangfuseConfig();
		}, 500);
	};

	const addConnectionHandler = async (server: ToolServerConnection) => {
		servers = [...(servers ?? []), server];
		await updateHandler();
	};

	const updateHandler = async () => {
		const res = await setToolServerConnections(localStorage.token, {
			TOOL_SERVER_CONNECTIONS: servers
		}).catch((err) => {
			toast.error($i18n.t('Failed to save connections'));
			return null;
		});

		if (res) {
			toast.success($i18n.t('Connections saved successfully'));
		}
	};

	const saveTerminalServers = async () => {
		const res = await setTerminalServerConnections(localStorage.token, {
			TERMINAL_SERVER_CONNECTIONS: terminalConnections
		}).catch((err) => {
			toast.error($i18n.t('Failed to save terminal servers'));
			return null;
		});

		if (res) {
			toast.success($i18n.t('Terminal servers saved'));

			// Refresh the terminalServers store so changes are reflected immediately
			// Preserve user direct terminals, refresh system terminals from backend
			const existingDirectTerminals = (($terminalServers ?? []) as TerminalConnection[]).filter(
				(t) => !t.id
			);
			const systemTerminals = await getTerminalServers(localStorage.token);
			const systemEntries = systemTerminals.map((t) => ({
				id: t.id,
				url: `${WEBUI_API_BASE_URL}/terminals/${t.id}`,
				name: t.name,
				key: localStorage.token
			}));
			terminalServers.set([...existingDirectTerminals, ...systemEntries] as any);
		}
	};

	const addTerminalConnection = (server: TerminalConnection) => {
		terminalConnections = [
			...terminalConnections,
			{ ...server, id: server.id ?? crypto.randomUUID() }
		];
		saveTerminalServers();
	};

	const updateTerminalConnection = (idx: number, updated: TerminalConnection) => {
		terminalConnections = terminalConnections.map((c, i) =>
			i === idx ? { ...c, ...updated, id: updated.id ?? c.id } : c
		);
		saveTerminalServers();
	};

	const removeTerminalConnection = (idx: number) => {
		terminalConnections = terminalConnections.filter((_, i) => i !== idx);
		saveTerminalServers();
	};

	const buildLangfuseConnectionLabels = (connections: LangfuseConnection[]) =>
		Object.fromEntries(
			connections
				.filter((connection): connection is LangfuseConnection & { id: string } =>
					Boolean(connection.id)
				)
				.map((connection) => [connection.id, connection.name || connection.url])
		);

	const saveLangfuseConfig = async (connections: LangfuseConnection[] = langfuseConnections) => {
		const connectionLabels = buildLangfuseConnectionLabels(langfuseConnections);

		const payloadConnections = connections.map((connection) => ({
			id: connection.id,
			name: connection.name,
			url: connection.url,
			public_key: connection.public_key,
			secret_key: connection.secret_key ?? '',
			enabled: connection.enabled
		}));

		const res = await setLangfuseConfig(localStorage.token, {
			LANGFUSE_CONNECTIONS: payloadConnections,
			LANGFUSE_PROMPT_CACHE_TTL: langfusePromptCacheTtl
		}).catch((err) => {
			const { title, description } = formatLangfuseConfigSaveError(
				err,
				(key, options) => $i18n.t(key, options),
				{
					connectionLabel: (connectionId) => connectionLabels[connectionId]
				}
			);

			if (description) {
				toast.error(title, {
					description,
					classes: { description: 'whitespace-pre-line' }
				});
			} else {
				toast.error(title);
			}
			return null;
		});

		if (res) {
			toast.success($i18n.t('Langfuse configuration saved'));
			if (res?.LANGFUSE_CONNECTIONS) {
				langfuseConnections = res.LANGFUSE_CONNECTIONS as LangfuseConnection[];
			} else {
				langfuseConnections = connections;
			}
			if (typeof res?.LANGFUSE_PROMPT_CACHE_TTL === 'number') {
				langfusePromptCacheTtl = res.LANGFUSE_PROMPT_CACHE_TTL;
			}
		}
	};

	const addLangfuseConnection = (connection: LangfuseConnection) => {
		langfuseConnections = [
			...langfuseConnections,
			{ ...connection, id: connection.id ?? crypto.randomUUID() }
		];
		saveLangfuseConfig();
	};

	const updateLangfuseConnection = (idx: number, updated: LangfuseConnection) => {
		langfuseConnections = langfuseConnections.map((c, i) =>
			i === idx ? { ...c, ...updated, id: updated.id ?? c.id } : c
		);
		saveLangfuseConfig();
	};

	const removeLangfuseConnection = (idx: number) => {
		saveLangfuseConfig(langfuseConnections.filter((_, i) => i !== idx));
	};

	onMount(async () => {
		const res = await getToolServerConnections(localStorage.token);
		servers = res.TOOL_SERVER_CONNECTIONS as ToolServerConnection[];

		try {
			const terminalRes = await getTerminalServerConnections(localStorage.token);
			if (terminalRes?.TERMINAL_SERVER_CONNECTIONS) {
				terminalConnections = terminalRes.TERMINAL_SERVER_CONNECTIONS as TerminalConnection[];
			}
		} catch {
			// Not configured yet
		}

		try {
			const langfuseRes = await getLangfuseConfig(localStorage.token);
			if (langfuseRes?.LANGFUSE_CONNECTIONS) {
				langfuseConnections = langfuseRes.LANGFUSE_CONNECTIONS as LangfuseConnection[];
			}
			if (typeof langfuseRes?.LANGFUSE_PROMPT_CACHE_TTL === 'number') {
				langfusePromptCacheTtl = langfuseRes.LANGFUSE_PROMPT_CACHE_TTL;
			}
		} catch {
			// Not configured yet
		}
	});

	onDestroy(() => {
		if (langfuseSaveTimer) {
			clearTimeout(langfuseSaveTimer);
		}
	});
</script>

<AddToolServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<AddTerminalServerModal
	bind:show={showAddTerminalModal}
	edit={editTerminalIdx !== null}
	connection={editTerminalIdx !== null ? terminalConnections[editTerminalIdx] : null}
	onSubmit={(c: TerminalConnection) => {
		if (editTerminalIdx !== null) {
			updateTerminalConnection(editTerminalIdx, c);
			editTerminalIdx = null;
		} else {
			addTerminalConnection(c);
		}
	}}
	onDelete={() => {
		if (editTerminalIdx !== null) {
			removeTerminalConnection(editTerminalIdx);
			editTerminalIdx = null;
		}
	}}
/>

<AddLangfuseConnectionModal
	bind:show={showAddLangfuseModal}
	edit={editLangfuseIdx !== null}
	connection={editLangfuseIdx !== null ? langfuseConnections[editLangfuseIdx] : null}
	onSubmit={(c: LangfuseConnection) => {
		if (editLangfuseIdx !== null) {
			updateLangfuseConnection(editLangfuseIdx, c);
			editLangfuseIdx = null;
		} else {
			addLangfuseConnection(c);
		}
	}}
	onDelete={() => {
		if (editLangfuseIdx !== null) {
			removeLangfuseConnection(editLangfuseIdx);
			editLangfuseIdx = null;
		}
	}}
/>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Integrations')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if servers !== null}
			<AdminSettingSection title={$i18n.t('Tools')} first>
				<div>
					<div class="mb-2 flex items-center justify-between">
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('External Tool Servers')}
						</div>

						<Tooltip content={$i18n.t(`Add Connection`)}>
							<button
								class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
								on:click={() => {
									showConnectionModal = true;
								}}
								type="button"
							>
								<Plus />
							</button>
						</Tooltip>
					</div>

					<div class="flex flex-col gap-1">
						{#each servers ?? [] as server, idx}
							<Connection
								bind:connection={server}
								onSubmit={() => {
									updateHandler();
								}}
								onDelete={() => {
									servers = (servers ?? []).filter((_, i) => i !== idx);
									updateHandler();
								}}
							/>
						{/each}
					</div>

					{#if (servers ?? []).length === 0}
						<div class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('No tool server connections configured.')}
						</div>
					{/if}

					<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
					</div>
				</div>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Terminal')}>
				<div>
					<div class="mb-2 flex items-center justify-between">
						<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Open Terminal')}</div>

						<Tooltip content={$i18n.t('Add Connection')}>
							<button
								class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
								on:click={() => {
									editTerminalIdx = null;
									showAddTerminalModal = true;
								}}
								type="button"
							>
								<Plus />
							</button>
						</Tooltip>
					</div>

					<div class="flex flex-col gap-1.5">
						{#each terminalConnections as connection, idx}
							<div class="flex w-full gap-2 items-center">
								<Tooltip className="w-full relative" content={''} placement="top-start">
									<div class="flex w-full">
										<div
											class="flex-1 relative flex gap-1.5 items-center {connection?.enabled ===
											false
												? 'opacity-50'
												: ''}"
										>
											<Tooltip content={$i18n.t('Terminal')}>
												<Cloud className="size-4" strokeWidth="1.5" />
											</Tooltip>

											<div
												class="outline-hidden w-full bg-transparent text-xs text-gray-700 dark:text-gray-300"
											>
												{connection.name || connection.url || $i18n.t('New Terminal')}
											</div>
										</div>
									</div>
								</Tooltip>

								<div class="flex gap-1 items-center">
									<Tooltip content={$i18n.t('Configure')}>
										<button
											class="self-center p-1 bg-transparent hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition"
											on:click={() => {
												editTerminalIdx = idx;
												showAddTerminalModal = true;
											}}
											type="button"
										>
											<Cog6 />
										</button>
									</Tooltip>

									<Tooltip
										content={connection?.enabled !== false
											? $i18n.t('Enabled')
											: $i18n.t('Disabled')}
									>
										<Switch
											state={connection?.enabled !== false}
											on:change={() => {
												terminalConnections = terminalConnections.map((c, i) =>
													i === idx ? { ...c, enabled: !(c?.enabled !== false) } : c
												);
												saveTerminalServers();
											}}
										/>
									</Tooltip>
								</div>
							</div>
						{/each}
					</div>

					{#if terminalConnections.length === 0}
						<div class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('No terminal connections configured.')}
						</div>
					{/if}

					<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t(
							'Connect to Open Terminal instances. All users will have access to file browsing and terminal tools through these servers.'
						)}
					</div>
					<a
						class="mt-0.5 block text-[0.6875rem] text-gray-500 underline hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
						href="https://github.com/open-webui/open-terminal"
						target="_blank">{$i18n.t('Learn more about Open Terminal')} ↗</a
					>
				</div>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Langfuse')}>
				<div>
					<div class="mb-2 flex items-center justify-between">
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Langfuse Connections')}
						</div>

						<Tooltip content={$i18n.t('Add Connection')}>
							<button
								class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
								on:click={() => {
									editLangfuseIdx = null;
									showAddLangfuseModal = true;
								}}
								type="button"
							>
								<Plus />
							</button>
						</Tooltip>
					</div>

					<div class="flex flex-col gap-1.5">
						{#each langfuseConnections as connection, idx}
							<div class="flex w-full items-center gap-2">
								<Tooltip className="w-full relative" content={''} placement="top-start">
									<div class="flex w-full">
										<div
											class="relative flex flex-1 items-center gap-1.5 {connection?.enabled ===
											false
												? 'opacity-50'
												: ''}"
										>
											<Tooltip content={$i18n.t('Langfuse')}>
												<ChartBar className="size-4" strokeWidth="1.5" />
											</Tooltip>

											<div
												class="w-full bg-transparent text-xs text-gray-700 outline-hidden dark:text-gray-300"
											>
												{connection.name || connection.url || $i18n.t('New Langfuse Connection')}
											</div>
										</div>
									</div>
								</Tooltip>

								<div class="flex items-center gap-1">
									<Tooltip content={$i18n.t('Configure')}>
										<button
											class="self-center rounded-lg bg-transparent p-1 transition hover:bg-black/5 dark:hover:bg-white/5"
											on:click={() => {
												editLangfuseIdx = idx;
												showAddLangfuseModal = true;
											}}
											type="button"
										>
											<Cog6 />
										</button>
									</Tooltip>

									<Tooltip
										content={connection?.enabled !== false
											? $i18n.t('Enabled')
											: $i18n.t('Disabled')}
									>
										<Switch
											state={connection?.enabled !== false}
											on:change={() => {
												langfuseConnections = langfuseConnections.map((c, i) =>
													i === idx ? { ...c, enabled: !(c?.enabled !== false) } : c
												);
												debouncedSaveLangfuseConfig();
											}}
										/>
									</Tooltip>
								</div>
							</div>
						{/each}
					</div>

					{#if langfuseConnections.length === 0}
						<div class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('No Langfuse connections configured.')}
						</div>
					{/if}

					<div class="mt-3 flex flex-col gap-1">
						<label for="langfuse-prompt-cache-ttl" class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Prompt cache TTL (seconds)')}
						</label>
						<input
							id="langfuse-prompt-cache-ttl"
							class="w-full max-w-[12rem] rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
							type="number"
							min="0"
							bind:value={langfusePromptCacheTtl}
							on:change={debouncedSaveLangfuseConfig}
						/>
					</div>

					<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t(
							'Configure Langfuse instances for optional model system prompt sync and observability.'
						)}
					</div>
					<a
						class="mt-0.5 block text-[0.6875rem] text-gray-500 underline hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
						href="https://langfuse.com/docs"
						target="_blank">{$i18n.t('Learn more about Langfuse')} ↗</a
					>
				</div>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Knowledge')}>
				<ExternalKnowledge />
			</AdminSettingSection>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
