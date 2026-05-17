<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import { getModels as _getModels } from '$lib/apis';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, settings, user, terminalServers } from '$lib/stores';
	import { getTerminalServers } from '$lib/apis/terminal';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Connection from '$lib/components/chat/Settings/Tools/Connection.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';
	import AddTerminalServerModal from '$lib/components/AddTerminalServerModal.svelte';

	import {
		getToolServerConnections,
		setToolServerConnections,
		getTerminalServerConnections,
		setTerminalServerConnections,
		getGitLabConnections,
		setGitLabConnections,
		triggerGitLabSync,
		getGitLabJobStatus,
		searchGitLabKnowledge
	} from '$lib/apis/configs';

	import AddGitLabModal from '$lib/components/AddGitLabModal.svelte';

	export let saveSettings: Function;

	let servers = null;
	let showConnectionModal = false;

	// Terminal server admin connections
	let terminalConnections = [];
	let showAddTerminalModal = false;
	let editTerminalIdx: number | null = null;

	// GitLab connections
	let gitlabConnections = [];
	let showAddGitLabModal = false;
	let editGitLabIdx: number | null = null;
	let syncingGitLabId = null;
	let gitlabSyncStatus = null;
	let gitlabSyncInterval = null;

	// GitLab search
	let gitlabSearchQuery = '';
	let gitlabSearchResults = null;
	let searchingGitLab = false;
	let showGitLabSearch = false;

	const addConnectionHandler = async (server) => {
		servers = [...servers, server];
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
			const existingDirectTerminals = ($terminalServers ?? []).filter((t) => !t.id);
			const systemTerminals = await getTerminalServers(localStorage.token);
			const systemEntries = systemTerminals.map((t) => ({
				id: t.id,
				url: `${WEBUI_API_BASE_URL}/terminals/${t.id}`,
				name: t.name,
				key: localStorage.token
			}));
			terminalServers.set([...existingDirectTerminals, ...systemEntries]);
		}
	};

	const addTerminalConnection = (server) => {
		terminalConnections = [...terminalConnections, { ...server, id: server.id ?? uuidv4() }];
		saveTerminalServers();
	};

	const updateTerminalConnection = (idx: number, updated) => {
		terminalConnections = terminalConnections.map((c, i) =>
			i === idx ? { ...c, ...updated, id: updated.id ?? c.id } : c
		);
		saveTerminalServers();
	};

	const removeTerminalConnection = (idx: number) => {
		terminalConnections = terminalConnections.filter((_, i) => i !== idx);
		saveTerminalServers();
	};

	// GitLab handlers
	const addGitLabConnection = (connection) => {
		const newConnection = { ...connection, id: connection.id ?? uuidv4() };
		gitlabConnections = [...gitlabConnections, newConnection];
		saveGitLabConnections();
	};

	const updateGitLabConnection = (idx: number, updated) => {
		gitlabConnections = gitlabConnections.map((c, i) =>
			i === idx ? { ...c, ...updated } : c
		);
		saveGitLabConnections();
	};

	const deleteGitLabConnection = (id: string) => {
		gitlabConnections = gitlabConnections.filter((c) => c.id !== id);
		saveGitLabConnections();
	};

	const saveGitLabConnections = async () => {
		const res = await setGitLabConnections(localStorage.token, gitlabConnections).catch((err) => {
			toast.error($i18n.t('Failed to save GitLab connections'));
			return null;
		});

		if (res) {
			toast.success($i18n.t('GitLab connections saved'));
		}
	};

	const syncGitLabConnection = async (id: string) => {
		syncingGitLabId = id;
		gitlabSyncStatus = { status: 'queued', progress: 0 };
		try {
			const res = await triggerGitLabSync(localStorage.token, id);
			if (res?.job_id) {
				toast.success($i18n.t('Sync job queued'));
				pollJobStatus(res.job_id);
			}
		} catch (error) {
			toast.error($i18n.t('Failed to trigger sync'));
			syncingGitLabId = null;
		}
	};

	const pollJobStatus = async (jobId: string) => {
		clearInterval(gitlabSyncInterval);
		gitlabSyncInterval = setInterval(async () => {
			try {
				const statusRes = await getGitLabJobStatus(localStorage.token, jobId);
				if (statusRes) {
					gitlabSyncStatus = statusRes;
					if (statusRes.status === 'completed' || statusRes.status === 'failed') {
						clearInterval(gitlabSyncInterval);
						syncingGitLabId = null;
					}
				}
			} catch {
				clearInterval(gitlabSyncInterval);
				syncingGitLabId = null;
			}
		}, 2000);
	};

	const searchGitLabKnowledgeHandler = async () => {
		if (!gitlabSearchQuery.trim()) return;
		searchingGitLab = true;
		try {
			const res = await searchGitLabKnowledge(localStorage.token, gitlabSearchQuery);
			gitlabSearchResults = res?.results || [];
		} catch (error) {
			toast.error($i18n.t('Search failed'));
		} finally {
			searchingGitLab = false;
		}
	};

	const clearGitLabSearch = () => {
		gitlabSearchQuery = '';
		gitlabSearchResults = null;
		showGitLabSearch = false;
	};

	onMount(async () => {
		const res = await getToolServerConnections(localStorage.token);
		servers = res.TOOL_SERVER_CONNECTIONS;

		// Load terminal server connections
		try {
			const terminalRes = await getTerminalServerConnections(localStorage.token);
			if (terminalRes?.TERMINAL_SERVER_CONNECTIONS) {
				terminalConnections = terminalRes.TERMINAL_SERVER_CONNECTIONS;
			}
		} catch {
			// Not configured yet
		}

		// Load GitLab connections
		try {
			const gitlabRes = await getGitLabConnections(localStorage.token);
			if (gitlabRes?.GITLAB_CONNECTIONS) {
				gitlabConnections = gitlabRes.GITLAB_CONNECTIONS;
			}
		} catch {
			// Not configured yet
		}
	});
</script>

<AddToolServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<AddTerminalServerModal
	bind:show={showAddTerminalModal}
	edit={editTerminalIdx !== null}
	connection={editTerminalIdx !== null ? terminalConnections[editTerminalIdx] : null}
	onSubmit={(c) => {
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

<AddGitLabModal
	bind:show={showAddGitLabModal}
	edit={editGitLabIdx !== null}
	connection={editGitLabIdx !== null ? gitlabConnections[editGitLabIdx] : null}
	onSubmit={(c) => {
		if (editGitLabIdx !== null) {
			updateGitLabConnection(editGitLabIdx, c);
			editGitLabIdx = null;
		} else {
			addGitLabConnection(c);
		}
	}}
	onDelete={(id) => {
		deleteGitLabConnection(id);
		editGitLabIdx = null;
	}}
/>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if servers !== null}
			<div class="">
				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5 flex flex-col w-full justify-between">
						<div class="flex justify-between items-center mb-0.5">
							<div class="font-medium">{$i18n.t('Manage Tool Servers')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
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
							{#each servers as server, idx}
								<Connection
									bind:connection={server}
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										servers = servers.filter((_, i) => i !== idx);
										updateHandler();
									}}
								/>
							{/each}
						</div>

						{#if servers.length === 0}
							<div class="text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('No tool server connections configured.')}
							</div>
						{/if}

						<div class="my-1.5">
							<div class="text-xs text-gray-500">
								{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
							</div>
						</div>
					</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-4" />

					<div class="mb-2.5 flex flex-col w-full">
						<div class="flex justify-between items-center mb-1">
							<div class="flex items-center gap-2">
								<div class="font-medium">{$i18n.t('Open Terminal')}</div>
								<span
									class="text-[0.65rem] font-medium uppercase px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
									>{$i18n.t('Experimental')}</span
								>
							</div>

							<Tooltip content={$i18n.t('Add Connection')}>
								<button
									class="px-1"
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

												<div class="outline-hidden w-full bg-transparent text-sm">
													{connection.name || connection.url || $i18n.t('New Terminal')}
												</div>
											</div>
										</div>
									</Tooltip>

									<div class="flex gap-1 items-center">
										<Tooltip content={$i18n.t('Configure')}>
											<button
												class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
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
							<div class="text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('No terminal connections configured.')}
							</div>
						{/if}

						<div class="mt-1.5">
							<div class="text-xs text-gray-500">
								{$i18n.t(
									'Connect to Open Terminal instances. All users will have access to file browsing and terminal tools through these servers.'
								)}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-300 mt-1">
								<a
									class="underline"
									href="https://github.com/open-webui/open-terminal"
									target="_blank">{$i18n.t('Learn more about Open Terminal')} ↗</a
								>
							</div>
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('GitLab')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5 flex flex-col w-full">
						<div class="flex justify-between items-center mb-1">
							<div class="flex items-center gap-2">
								<div class="font-medium">{$i18n.t('Manage GitLab Connections')}</div>
								<span
									class="text-[0.65rem] font-medium uppercase px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
								>
									{$i18n.t('Beta')}
								</span>
							</div>

							<Tooltip content={$i18n.t('Add Connection')}>
								<button
									class="px-1"
									on:click={() => {
										editGitLabIdx = null;
										showAddGitLabModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1.5">
							{#each gitlabConnections as connection, idx}
								<div class="flex w-full gap-2 items-center">
									<div
										class="flex-1 relative flex gap-1.5 items-center {connection?.enabled === false
											? 'opacity-50'
											: ''}"
									>
										<Tooltip content={$i18n.t('GitLab')}>
											<svg class="size-4" viewBox="0 0 24 24" fill="currentColor">
												<path
													d="M22.65 10.785l-1.423-4.39L17.257 2.5 8.928 8.068 3.743 6.395l-1.423 4.39L0 12.227l8.928 6.868 4.035 1.424 1.424-4.39 8.283-5.344z"
												/>
											</svg>
										</Tooltip>

										<div class="outline-hidden w-full bg-transparent text-sm">
											{connection.name || connection.url || $i18n.t('New GitLab')}
										</div>
									</div>

									<div class="flex gap-1 items-center">
										<button
											class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
											on:click={() => {
												showGitLabSearch = !showGitLabSearch;
											}}
											type="button"
										>
											<Search />
										</button>

										<Tooltip content={$i18n.t('Sync')}>
											<button
												class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
												on:click={() => syncGitLabConnection(connection.id)}
												type="button"
												disabled={syncingGitLabId === connection.id}
											>
												{#if syncingGitLabId === connection.id}
													<Spinner className="size-4" />
												{:else}
													<svg class="size-4" viewBox="0 0 20 20" fill="currentColor">
														<path
															fill-rule="evenodd"
															d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
															clip-rule="evenodd"
														/>
													</svg>
												{/if}
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Configure')}>
											<button
												class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
												on:click={() => {
													editGitLabIdx = idx;
													showAddGitLabModal = true;
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
													gitlabConnections = gitlabConnections.map((c, i) =>
														i === idx ? { ...c, enabled: !(c?.enabled !== false) } : c
													);
													saveGitLabConnections();
												}}
											/>
										</Tooltip>
									</div>
								</div>
							{/each}
						</div>

						{#if gitlabConnections.length === 0}
							<div class="text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('No GitLab connections configured.')}
							</div>
						{/if}

						{#if syncingGitLabId && gitlabSyncStatus}
							<div class="mt-2 flex flex-col gap-1.5">
								<div class="flex items-center gap-2">
									<div class="w-32 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
										<div
											class="h-full bg-blue-500 transition-all duration-300"
											style="width: {gitlabSyncStatus.progress || 0}%"
										></div>
									</div>
									<span class="text-xs text-gray-500">{gitlabSyncStatus.progress || 0}%</span>
								</div>
								<div class="flex items-center gap-2 text-xs">
									{#if gitlabSyncStatus.status === 'connecting'}
										<Spinner className="size-3" />
									{:else if gitlabSyncStatus.status === 'completed'}
										<Check className="size-3 text-green-500" />
									{:else if gitlabSyncStatus.status === 'failed'}
										<XMark className="size-3 text-red-500" />
									{:else}
										<div class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
									{/if}
									<span class="text-gray-600 dark:text-gray-400">
										{gitlabSyncStatus.message || gitlabSyncStatus.status}
									</span>
								</div>
								{#if gitlabSyncStatus.details}
									<div class="text-xs text-gray-400 dark:text-gray-500 pl-4">
										{#if gitlabSyncStatus.details.stage}
											Stage: {gitlabSyncStatus.details.stage}
										{/if}
										{#if gitlabSyncStatus.details.total_files}
											• Files: {gitlabSyncStatus.details.file_index || 0}/{gitlabSyncStatus.details.total_files}
										{/if}
										{#if gitlabSyncStatus.details.processed !== undefined}
											• Processed: {gitlabSyncStatus.details.processed}
										{/if}
										{#if gitlabSyncStatus.details.errors}
											• Errors: {gitlabSyncStatus.details.errors}
										{/if}
									</div>
								{/if}
							</div>
						{/if}

						{#if showGitLabSearch}
							<div class="mt-3 flex flex-col gap-2">
								<div class="flex gap-2">
									<input
										type="text"
										placeholder={$i18n.t('Search GitLab knowledge...')}
										bind:value={gitlabSearchQuery}
										class="flex-1 px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-transparent outline-none"
										on:keydown={(e) => {
											if (e.key === 'Enter') {
												searchGitLabKnowledgeHandler();
											}
										}}
									/>
									<button
										class="px-3 py-1.5 text-xs bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg"
										on:click={() => searchGitLabKnowledgeHandler()}
										disabled={searchingGitLab}
									>
										{searchingGitLab ? $i18n.t('Searching...') : $i18n.t('Search')}
									</button>
									<button
										class="px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
										on:click={() => clearGitLabSearch()}
									>
										{$i18n.t('Clear')}
									</button>
								</div>

								{#if gitlabSearchResults !== null && gitlabSearchResults.length > 0}
									<div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
										<div class="max-h-64 overflow-y-auto">
											{#each gitlabSearchResults as result}
												<div class="p-3 border-b border-gray-100 dark:border-gray-800 last:border-b-0">
													<div class="text-xs text-gray-500 mb-1">
														{result.metadata?.project_name || result.collection} / {result.metadata?.file_path ||
															'unknown'}
													</div>
													<div class="text-xs text-gray-700 dark:text-gray-300 line-clamp-3">
														{result.text}
													</div>
												</div>
											{/each}
										</div>
									</div>
								{:else if gitlabSearchResults !== null}
									<div class="text-xs text-gray-400 text-center py-2">
										{$i18n.t('No results found')}
									</div>
								{/if}
							</div>
						{/if}

						<div class="mt-1.5">
							<div class="text-xs text-gray-500">
								{$i18n.t('Connect to GitLab repositories and sync content as knowledge.')}
							</div>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
