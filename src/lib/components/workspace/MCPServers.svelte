<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { tools as _tools, WEBUI_NAME } from '$lib/stores';
	import { user } from '$lib/stores';
	import { mcpServersApi, type MCPServerUserResponse, type MCPServerModel } from '$lib/apis/mcp_servers';
	import { getTools } from '$lib/apis/tools';
	import MCPServerModal from '$lib/components/mcp/MCPServerModal.svelte';
	import MCPAuthChallengeModal from '$lib/components/mcp/MCPAuthChallengeModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');

	let loaded = false;
	let servers: MCPServerUserResponse[] = [];
	let loading = false;
	let showModal = false;
	let editingServer: MCPServerModel | null = null;
	let showDeleteConfirm = false;
	let serverToDelete: MCPServerUserResponse | null = null;
	let syncingServers = new Set<string>();
	let query = '';

	// Tools mapping for preview
	let mcpTools: Record<string, { id: string; name: string; description?: string; serverName: string }> = {};
	let serverTools: Record<string, Array<{ id: string; name: string }>> = {};

	// Auth modal state
	let showMCPAuthChallenge = false;
	let mcpAuthElicitationData: any = {};
	let lastAction: { type: 'test' | 'sync'; serverId: string; serverName: string } | null = null;

	// Derived filtered list for search
	let filteredServers: MCPServerUserResponse[] = [];
	$: filteredServers = (() => {
		const q = (query || '').toLowerCase().trim();
		if (!q) return servers;
		return servers.filter((s) => (s?.name || '').toLowerCase().includes(q));
	})();

	onMount(async () => {
		await loadServers();
		await loadTools();
		loaded = true;
	});

	async function loadServers() {
		try {
			loading = true;
			// Non-admin users should only see their own (private) servers in workspace
			if ($user?.role === 'admin') {
				servers = await mcpServersApi.getMCPServers(localStorage.token);
			} else {
				servers = await mcpServersApi.getUserMCPServers(localStorage.token);
			}
		} catch (e) {
			console.error(e);
			toast.error($i18n.t('mcp.workspace.failed_load'));
		} finally {
			loading = false;
		}
	}

	async function loadTools() {
		try {
			if ($_tools === null) {
				await _tools.set(await getTools(localStorage.token));
			}
			const allMcpTools = ($_tools || []).filter((tool: any) => tool.id?.startsWith('mcp:') && tool.user_id !== 'global');
			mcpTools = allMcpTools.reduce((acc: Record<string, any>, tool: any) => {
				let serverName = tool.meta?.manifest?.mcp_server_name || $i18n.t('mcp.workspace.unknown_server');
				let cleanToolName = tool.meta?.manifest?.mcp_original_name || tool.name;
				if (!tool.meta?.manifest?.mcp_server_name && tool.name?.startsWith('[MCP] ') && tool.name.includes(' - ')) {
					const nameWithoutPrefix = tool.name.substring(6);
					const parts = nameWithoutPrefix.split(' - ');
					if (parts.length >= 2) {
						serverName = parts[0];
						cleanToolName = parts.slice(1).join(' - ');
					}
				}
				acc[tool.id] = {
					id: tool.id,
					name: cleanToolName,
					description: tool.meta?.description || tool.meta?.manifest?.description,
					serverName
				};
				return acc;
			}, {});
			serverTools = Object.values(mcpTools).reduce((acc: Record<string, Array<{ id: string; name: string }>>, t) => {
				if (!acc[t.serverName]) acc[t.serverName] = [];
				acc[t.serverName].push({ id: t.id, name: t.name });
				return acc;
			}, {} as Record<string, Array<{ id: string; name: string }>>);
		} catch (e) {
			console.error('Failed to load tools', e);
		}
	}

	function filtered(list: MCPServerUserResponse[]) {
		if (!query.trim()) return list;
		const q = query.toLowerCase();
		return list.filter((s) => s.name.toLowerCase().includes(q));
	}

	function statusText(status: unknown): string {
		return String(status || '').toLowerCase();
	}

	async function openAddServer() {
		editingServer = null;
		showModal = true;
	}

	async function openEditServer(id: string) {
		try {
			editingServer = await mcpServersApi.getMCPServerById(localStorage.token, id);
			showModal = true;
		} catch (e) {
			console.error(e);
			toast.error($i18n.t('mcp.workspace.failed_load_server_details'));
		}
	}

	async function handleDelete() {
		if (!serverToDelete) return;
		try {
			await mcpServersApi.deleteMCPServer(localStorage.token, serverToDelete.id);
			toast.success($i18n.t('mcp.workspace.server_deleted'));
			await loadServers();
			await _tools.set(await getTools(localStorage.token));
			await loadTools();
		} catch (e) {
			console.error(e);
			toast.error($i18n.t('mcp.workspace.failed_delete_server'));
		}
	}

	function maybeShowAuthModal(result: any, serverId: string, serverName: string, action: 'test' | 'sync') {
		if (result && result.success === false && result.error_type === 'authentication') {
			// Map to elicitation data expected by MCPAuthChallengeModal
			mcpAuthElicitationData = {
				type: 'elicitation',
				name: 'mcp_authentication',
				data: {
					server_id: result.server_id || serverId,
					server_name: result.server_name || serverName,
					tool_name: '',
					error_message: result.message || $i18n.t('mcp.workspace.auth_required'),
					title: $i18n.t('mcp.auth.title_default'),
					message: $i18n.t('mcp.auth.message_default'),
					retry_context: {},
					challenge_type: result.challenge_type || 'oauth',
					can_auto_auth: Boolean(result.auth_url),
					auth_url: result.auth_url || null,
					instructions: result.instructions || null
				}
			};
			lastAction = { type: action, serverId, serverName };
			showMCPAuthChallenge = true;
			return true;
		}
		return false;
	}

	async function testServer(serverId: string, name: string) {
		try {
			const res = await mcpServersApi.testMCPServer(localStorage.token, serverId);
			if (res.success) {
				// verify server status is connected
				const server = await mcpServersApi.getMCPServerById(localStorage.token, serverId);
				if (String(server?.status || '') === 'connected') {
					toast.success($i18n.t('mcp.workspace.test_success', { name }));
				} else {
					toast.error($i18n.t('mcp.workspace.test_failed', { name }));
				}
			} else if (!maybeShowAuthModal(res, serverId, name, 'test')) {
				// Show detailed error message from the API response
				const errorMsg = res.message || $i18n.t('mcp.workspace.unknown_error');
				toast.error($i18n.t('mcp.workspace.test_failed_with_reason', { name, errorMsg }));
			}
		} catch (e: any) {
			console.error(e);
			if (e && e.error_type === 'authentication') {
				maybeShowAuthModal(e, serverId, name, 'test');
				return;
			}
			// Extract detailed error message from Error object (includes HTTP status)
			const errorMessage = e instanceof Error ? e.message : $i18n.t('mcp.workspace.unknown_error');
			toast.error($i18n.t('mcp.workspace.test_failed_with_reason', { name, errorMsg: errorMessage }));
		}
	}

	async function syncServer(serverId: string, name: string) {
		if (syncingServers.has(serverId)) return;
		syncingServers.add(serverId);
		syncingServers = new Set(syncingServers);
		try {
			const res = await mcpServersApi.syncServerTools(localStorage.token, serverId);
			if (res.success) {
				// Refresh tools and check server status to validate sync
				await _tools.set(await getTools(localStorage.token));
				await loadTools();
				const server = await mcpServersApi.getMCPServerById(localStorage.token, serverId);
				if (String(server?.status || '') === 'connected') {
					toast.success($i18n.t('mcp.workspace.sync_success', { name }));
				} else {
					toast.error($i18n.t('mcp.workspace.sync_failed', { name }));
				}
			} else if (!maybeShowAuthModal(res, serverId, name, 'sync')) {
				toast.error($i18n.t('mcp.workspace.sync_failed', { name }));
			}
		} catch (e: any) {
			console.error(e);
			if (e && e.error_type === 'authentication') {
				maybeShowAuthModal(e, serverId, name, 'sync');
			} else {
				toast.error($i18n.t('mcp.workspace.sync_failed', { name }));
			}
		} finally {
			syncingServers.delete(serverId);
			syncingServers = new Set(syncingServers);
		}
	}

	function pollForToolUpdates() {
		let attempts = 0;
		const maxAttempts = 10;
		const poll = async () => {
			attempts++;
			await _tools.set(await getTools(localStorage.token));
			await loadTools();
			if (attempts < maxAttempts) {
				setTimeout(poll, 500);
			}
		};
		poll();
	}

	async function onModalClose(e: CustomEvent<{ saved?: boolean }>) {
		showModal = false;
		editingServer = null;
		// Only refresh when changes were saved
		if (e?.detail?.saved) {
			await loadServers();
			// wait briefly to allow backend auto sync to start, then refresh tools and poll
			await new Promise((r) => setTimeout(r, 500));
			await _tools.set(await getTools(localStorage.token));
			await loadTools();
			pollForToolUpdates();
			toast.success($i18n.t('mcp.workspace.server_updated'));
		}
	}

	function handleAuthSuccess() {
		showMCPAuthChallenge = false;
		if (lastAction) {
			const { type, serverId, serverName } = lastAction;
			lastAction = null;
			// Retry the last action automatically
			if (type === 'test') {
				testServer(serverId, serverName);
			} else {
				syncServer(serverId, serverName);
			}
		}
	}

	function handleAuthCancelled() {
		showMCPAuthChallenge = false;
		lastAction = null;
	}
</script>

<svelte:head>
	<title>{$i18n.t('MCP Servers')} | {$WEBUI_NAME}</title>
</svelte:head>

{#if !loaded}
	<div class="w-full h-full flex justify-center items-center"><Spinner /></div>
{:else}
	<ConfirmDialog bind:show={showDeleteConfirm} on:confirm={handleDelete} />
	<MCPAuthChallengeModal bind:show={showMCPAuthChallenge} elicitationData={mcpAuthElicitationData} on:authenticated={handleAuthSuccess} on:cancelled={handleAuthCancelled} />

	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('MCP Servers')}
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{filteredServers.length}</span>
			</div>

			<button
				class="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center space-x-1"
				on:click={openAddServer}
			>
				<Plus className="size-3.5" />
				<span>{$i18n.t('Add')}</span>
			</button>
		</div>

		<!-- Search -->
		<div class="flex w-full space-x-2">
			<div class="flex flex-1 border border-gray-200/60 dark:border-gray-700 rounded-xl">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search MCP Servers')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => (query = '')}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
		</div>
	{:else if filteredServers.length === 0}
		<div class="text-center py-8 text-gray-500 dark:text-gray-400">
			<p>{$i18n.t('No personal MCP servers configured')}</p>
			<p class="text-sm">{$i18n.t('Click Add to create one.')}</p>
		</div>
	{:else}
		<div class="my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
			{#each filteredServers as server (server.id)}
				<div class="flex flex-col w-full px-4 py-3 border border-gray-50 dark:border-gray-850 rounded-2xl transition">
					<div class="flex gap-4 mt-1 mb-0.5">
						<div class="w-10">
							<div class="rounded-full object-cover {server.is_active ? '' : 'opacity-50'}">
								<div class="w-full h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5 text-white">
										<path stroke-linecap="round" stroke-linejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
									</svg>
								</div>
							</div>
						</div>

						<div class="flex-1 self-center {server.is_active ? '' : 'text-gray-500'}">
							<div class="font-semibold line-clamp-1 flex items-center gap-2">
								{server.name}
								<span class="px-1.5 py-0.5 text-xs font-medium rounded {server.is_public ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'bg-orange-100 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400'}">{server.is_public ? 'Public' : 'Private'}</span>
							</div>

							<div class="flex gap-1 text-xs overflow-hidden mt-1">
								<div class="line-clamp-1 text-gray-600 dark:text-gray-400">
									{#if statusText(server.status) === 'connected'}
										<span class="text-green-600 dark:text-green-400">● Connected</span>
									{:else if statusText(server.status) === 'connecting'}
										<span class="text-yellow-600 dark:text-yellow-400">● Connecting</span>
									{:else if statusText(server.status) === 'error'}
										<span class="text-red-600 dark:text-red-400">● Error</span>
									{:else}
										<span class="text-gray-500">● Disconnected</span>
									{/if}
									{#if serverTools[server.name]}
										• {serverTools[server.name].length} tool{serverTools[server.name].length !== 1 ? 's' : ''}
									{/if}
								</div>
							</div>
						</div>

						<!-- Action buttons -->
						<div class="flex items-center space-x-2">
							<Tooltip content={$i18n.t('Test Connection')}>
								<button class="p-2 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors {server.is_active ? '' : 'opacity-50 cursor-not-allowed'}" on:click={() => server.is_active && testServer(server.id, server.name)} disabled={!server.is_active}>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Sync Tools')}>
								<button class="p-2 text-gray-600 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-400 transition-colors {!server.is_active || syncingServers.has(server.id) ? 'opacity-50 cursor-not-allowed' : ''}" on:click={() => server.is_active && !syncingServers.has(server.id) && syncServer(server.id, server.name)} disabled={!server.is_active || syncingServers.has(server.id)}>
									{#if syncingServers.has(server.id)}
										<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
									{:else}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
									{/if}
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Edit Server')}>
								<button class="p-2 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" on:click={() => openEditServer(server.id)}>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Delete Server')}>
								<button class="p-2 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors" on:click={() => { serverToDelete = server; showDeleteConfirm = true; }}>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
								</button>
							</Tooltip>
						</div>
					</div>

					{#if serverTools[server.name] && serverTools[server.name].length > 0}
						<div class="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
							<div class="text-xs text-gray-500 mb-1">{$i18n.t('Available Tools')}:</div>
							<div class="flex flex-wrap gap-1">
								{#each serverTools[server.name].slice(0, 3) as tool}
									<span class="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded">{tool.name}</span>
								{/each}
								{#if serverTools[server.name].length > 3}
									<span class="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 rounded">+{$i18n.t('mcp.workspace.more_tools', { count: serverTools[server.name].length - 3 })}</span>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	{#if showModal}
		<MCPServerModal
			bind:show={showModal}
			{editingServer}
			isAdmin={$user?.role === 'admin'}
			isGlobal={false}
			on:serverDraft={async (e) => {
				try {
					const sid = e.detail?.serverId;
					if (sid) {
						editingServer = await mcpServersApi.getMCPServerById(localStorage.token, sid);
					}
				} catch (err) {
					console.error('Failed to load server draft', err);
				}
			}}
			on:close={onModalClose}
		/>
	{/if}
{/if}
