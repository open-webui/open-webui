<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, onDestroy, getContext } from 'svelte';

	const dispatch = createEventDispatcher();

	import { 
		getMCPConfig, 
		updateMCPConfig, 
		verifyMCPConnection, 
		getMCPURLs, 
		updateMCPURLs, 
		getMCPTools,
		getBuiltinServers,
		restartBuiltinServer
	} from '$lib/apis/mcp';
	import { getTools } from '$lib/apis/tools';

	import { user, tools } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n: any = getContext('i18n');

	// MCP Settings
	let MCP_BASE_URLS: string[] = [''];
	let MCP_API_CONFIGS: any = {};
	let ENABLE_MCP_API: boolean = false;

	let mcpToolsLoading = false;
	let mcpTools: any[] = [];
	
	// Built-in servers
	let builtinServers: any[] = [];
	let builtinServersLoading = false;
	
	// Server connection status tracking for external servers
	let serverStatuses: { [key: string]: string } = {};
	let autoVerifyInterval: NodeJS.Timeout | null = null;

	// Reactive statement to ensure we always have at least one input field
	$: {
		if (MCP_BASE_URLS.length === 0) {
			MCP_BASE_URLS = [''];
		}
	}

	// Enable/disable periodic verification based on MCP API status
	$: {
		if (ENABLE_MCP_API && MCP_BASE_URLS.some(url => url && url.trim() !== '')) {
			// Start periodic verification every 30 seconds
			if (!autoVerifyInterval) {
				autoVerifyInterval = setInterval(async () => {
					await autoVerifyAllConnections();
				}, 30000); // 30 seconds
			}
		} else {
			// Stop periodic verification when MCP is disabled
			if (autoVerifyInterval) {
				clearInterval(autoVerifyInterval);
				autoVerifyInterval = null;
			}
		}
	}

	const updateMCPHandler = async () => {
		if (ENABLE_MCP_API !== null) {
			// Remove trailing slashes
			MCP_BASE_URLS = MCP_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			const res = await updateMCPConfig(localStorage.token, {
				ENABLE_MCP_API: ENABLE_MCP_API,
				MCP_BASE_URLS: MCP_BASE_URLS,
				MCP_API_CONFIGS: MCP_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});
		if (res) {
			toast.success($i18n.t('MCP API settings updated'));
			await updateMCPURLsHandler();
			await getMCPToolsHandler();
			
			// Refresh tools list to reflect MCP tool availability
			try {
				const updatedTools = await getTools(localStorage.token);
				tools.set(updatedTools);
				console.log('Tools refreshed after MCP setting change');
			} catch (error) {
				console.error('Failed to refresh tools after MCP setting change:', error);
			}
		}
		}
	};

	const updateMCPURLsHandler = async () => {
		const res = await updateMCPURLs(localStorage.token, MCP_BASE_URLS).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			dispatch('save');
		}
	};

	const getMCPToolsHandler = async () => {
		mcpToolsLoading = true;
		const res = await getMCPTools(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		});

		mcpTools = res || [];
		mcpToolsLoading = false;
	};

	const getBuiltinServersHandler = async () => {
		builtinServersLoading = true;
		const res = await getBuiltinServers(localStorage.token).catch((error) => {
			console.error('Error fetching built-in servers:', error);
			return { servers: [] };
		});

		builtinServers = res.servers || [];
		builtinServersLoading = false;
	};

	const restartBuiltinServerHandler = async (serverName: string) => {
		const res = await restartBuiltinServer(localStorage.token, serverName).catch((error) => {
			toast.error(`Failed to restart ${serverName}: ${error}`);
			return null;
		});

		if (res && res.status === 'success') {
			toast.success(`${serverName} restarted successfully`);
			await getBuiltinServersHandler();
			await getMCPToolsHandler();
		}
	};

	const verifyMCPConnectionHandler = async (url: string, idx: number, showToasts: boolean = true) => {
		// Skip verification if URL is empty
		if (!url || url.trim() === '') {
			serverStatuses[url] = 'unknown';
			serverStatuses = { ...serverStatuses };
			return;
		}
		
		// Set loading status
		serverStatuses[url] = 'loading';
		serverStatuses = { ...serverStatuses };
		
		const res = await verifyMCPConnection(localStorage.token, url).catch((error) => {
			if (showToasts) {
				toast.error(`${error}`);
			}
			serverStatuses[url] = 'error';
			serverStatuses = { ...serverStatuses };
			return null;
		});

		if (res) {
			if (res.status === 'connected') {
				if (showToasts) {
					toast.success('MCP Server connected successfully');
				}
				serverStatuses[url] = 'connected';
			} else if (res.status === 'failed') {
				if (showToasts) {
					toast.error(`MCP Server connection failed: ${res.message || res.error || 'Unknown error'}`);
				}
				serverStatuses[url] = 'error';
			} else {
				if (showToasts) {
					toast.error('MCP Server connection failed');
				}
				serverStatuses[url] = 'error';
			}
		} else {
			serverStatuses[url] = 'error';
		}
		
		serverStatuses = { ...serverStatuses };
	};

	// Auto-verify connections for all URLs
	const autoVerifyAllConnections = async () => {
		if (!ENABLE_MCP_API) return;
		
		for (let idx = 0; idx < MCP_BASE_URLS.length; idx++) {
			const url = MCP_BASE_URLS[idx];
			if (url && url.trim() !== '') {
				// Don't show toasts for auto-verification to avoid spam
				await verifyMCPConnectionHandler(url, idx, false);
			}
		}
	};

	// Auto-verify a single connection when URL changes
	const autoVerifyConnection = async (url: string, idx: number) => {
		if (!ENABLE_MCP_API || !url || url.trim() === '') {
			serverStatuses[url] = 'unknown';
			serverStatuses = { ...serverStatuses };
			return;
		}
		
		// Add a small delay to avoid rapid API calls while typing
		setTimeout(async () => {
			// Check if URL is still the same (user might have continued typing)
			if (MCP_BASE_URLS[idx] === url) {
				await verifyMCPConnectionHandler(url, idx, false);
			}
		}, 1000);
	};

	onMount(async () => {
		const res = await getMCPConfig(localStorage.token);

		if (res) {
			ENABLE_MCP_API = res.ENABLE_MCP_API;
			MCP_BASE_URLS = res.MCP_BASE_URLS || [''];
			MCP_API_CONFIGS = res.MCP_API_CONFIGS || {};
			
			// Load built-in servers if available
			if (res.BUILTIN_SERVERS) {
				builtinServers = res.BUILTIN_SERVERS;
			} else {
				await getBuiltinServersHandler();
			}

			await getMCPToolsHandler();
			
			// Auto-verify all existing connections on initial load
			await autoVerifyAllConnections();
		}
	});

	onDestroy(() => {
		if (autoVerifyInterval) {
			clearInterval(autoVerifyInterval);
			autoVerifyInterval = null;
		}
	});

	// Watch for changes to MCP_BASE_URLS and auto-verify new/changed URLs
	let previousURLs = [...MCP_BASE_URLS];
	$: {
		if (ENABLE_MCP_API && MCP_BASE_URLS) {
			// Check for URL changes and auto-verify only changed ones
			MCP_BASE_URLS.forEach((url, idx) => {
				if (url !== previousURLs[idx] && url && url.trim() !== '') {
					autoVerifyConnection(url, idx);
				}
			});
			previousURLs = [...MCP_BASE_URLS];
		}
	}
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateMCPHandler();
	}}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div>
			<div class="mb-2 text-sm font-medium">{$i18n.t('MCP (Model Context Protocol)')}</div>
			<div class="text-xs text-gray-600 dark:text-gray-500">
				{$i18n.t('Configure connections to external MCP servers to extend model capabilities with additional tools and context.')}
			</div>
		</div>

		<hr class="dark:border-gray-700" />

		<div>
			<div class="flex justify-between items-center text-sm">
				<div class="font-medium">{$i18n.t('Enable MCP API')}</div>
				<Switch bind:state={ENABLE_MCP_API} ariaLabel="Enable MCP API" />
			</div>
		</div>

		{#if ENABLE_MCP_API}
			<hr class="dark:border-gray-700" />

			<!-- Built-in MCP Servers -->
			<div>
				<div class="mb-3 text-sm font-medium flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-green-500">
						<path d="M21.731 2.269a2.625 2.625 0 00-3.712 0l-1.157 1.157 3.712 3.712 1.157-1.157a2.625 2.625 0 000-3.712zM19.513 8.199l-3.712-3.712-12.15 12.15a5.25 5.25 0 00-1.32 2.214l-.8 2.685a.75.75 0 00.933.933l2.685-.8a5.25 5.25 0 002.214-1.32L19.513 8.2z" />
					</svg>
					{$i18n.t('Built-in MCP Servers')}
					{#if builtinServersLoading}
						<Spinner className="size-3" />
					{/if}
				</div>
				
				<div class="text-xs text-gray-600 dark:text-gray-500 mb-3">
					{$i18n.t('These servers are automatically managed and provide core functionality.')}
				</div>

				{#if builtinServers.length > 0}
					<div class="space-y-2">
						{#each builtinServers as server}
							<div class="border dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-gray-800">
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-3">
										<!-- Server Status Indicator -->
										<div class="flex items-center gap-2">
											{#if server.status === 'running'}
												<Tooltip content={$i18n.t('Server is running')}>
													<div class="w-2 h-2 rounded-full bg-green-500"></div>
												</Tooltip>
											{:else if server.status === 'stopped'}
												<Tooltip content={$i18n.t('Server is stopped')}>
													<div class="w-2 h-2 rounded-full bg-red-500"></div>
												</Tooltip>
											{:else}
												<Tooltip content={$i18n.t('Server status unknown')}>
													<div class="w-2 h-2 rounded-full bg-gray-500"></div>
												</Tooltip>
											{/if}
										</div>
										
										<div>
											<div class="font-medium text-sm">{server.display_name}</div>
											<div class="text-xs text-gray-700 dark:text-gray-400">{server.description}</div>
										</div>
									</div>
									
									<div class="flex items-center gap-2">
										<!-- Tools Count Badge -->
										<span class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
											{server.tools_count} {server.tools_count === 1 ? $i18n.t('tool') : $i18n.t('tools')}
										</span>
										
										<!-- Status Badge -->
										<span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium {server.status === 'running' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'}">
											{$i18n.t(server.status)}
										</span>								<!-- Restart Button -->
							<Tooltip content={$i18n.t('Restart Server')}>
								<button
									class="px-2 py-1 text-gray-700 dark:text-gray-200 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded text-xs transition"
									type="button"
									aria-label="Restart {server.display_name || server.name} server"
									on:click={() => restartBuiltinServerHandler(server.name)}
								>
												<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3">
													<path fill-rule="evenodd" d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.37l-.84-.841a4.5 4.5 0 0 0-7.08.932.75.75 0 0 1-1.3-.75 6 6 0 0 1 9.44-1.242l.842.84V3.227a.75.75 0 0 1 .75-.75zm-.911 7.5A.75.75 0 0 1 13.199 11a6 6 0 0 1-9.44 1.241l-.84-.84v1.371a.75.75 0 0 1-1.5 0V9.591a.75.75 0 0 1 .75-.75H5.35a.75.75 0 0 1 0 1.5H3.98l.841.841a4.5 4.5 0 0 0 7.08-.932.75.75 0 0 1 1.025-.273z" clip-rule="evenodd" />
												</svg>
											</button>
										</Tooltip>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-xs text-gray-700 dark:text-gray-400 p-3 border border-dashed dark:border-gray-700 rounded-lg text-center">
						{$i18n.t('No built-in servers available')}
					</div>
				{/if}
			</div>

			<hr class="dark:border-gray-700" />

			<!-- External MCP Servers -->
			{#if MCP_BASE_URLS.some(url => url && url.trim() !== '') || MCP_BASE_URLS.length === 1}
			<div>
				<div class="mb-2 text-sm font-medium flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-blue-500">
						<path d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
					</svg>
					{$i18n.t('External MCP Servers')}
				</div>
				
				<div class="text-xs text-gray-600 dark:text-gray-500 mb-3">
					{$i18n.t('Connect to external MCP servers to add additional tools and capabilities. These require manual configuration and URL management.')}
				</div>

				<div class="flex flex-col space-y-2">
					{#each MCP_BASE_URLS as url, idx}
						<div class="flex w-full">
							<div class="flex-1 mr-2 relative">
								<!-- Dynamic Server Status Indicator -->
								<div class="absolute left-3 top-1/2 transform -translate-y-1/2 flex items-center gap-2 pointer-events-none">
									{#if serverStatuses[url] === 'loading'}
										<Tooltip content="Checking connection...">
											<div class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
										</Tooltip>
									{:else if serverStatuses[url] === 'connected'}
										<Tooltip content="Connected and verified">
											<div class="w-2 h-2 rounded-full bg-green-500"></div>
										</Tooltip>
									{:else if serverStatuses[url] === 'error'}
										<Tooltip content="Connection failed - click verify to retry">
											<div class="w-2 h-2 rounded-full bg-red-500"></div>
										</Tooltip>
									{:else}
										<Tooltip content="Connection status unknown - will auto-verify when URL is entered">
											<div class="w-2 h-2 rounded-full bg-gray-500"></div>
										</Tooltip>
									{/if}
								</div>
								<input
									class="w-full rounded-lg py-2 pl-8 pr-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									placeholder={$i18n.t('Enter MCP server URL')}
									bind:value={url}
									autocomplete="off"
								/>
							</div>

							<div class="flex gap-1">
								<Tooltip content="Verify Connection">
									<button
										class="px-3 py-2 text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
										type="button"
										aria-label="Verify MCP server connection"
										disabled={serverStatuses[url] === 'loading'}
										on:click={() => {
											verifyMCPConnectionHandler(url, idx, true);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</Tooltip>

								{#if idx === 0}
									<Tooltip content="Add MCP Server">
										<button
											class="px-3 py-2 text-gray-700 dark:text-gray-200 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition"
											type="button"
											aria-label="Add new MCP server"
											on:click={() => {
												MCP_BASE_URLS = [...MCP_BASE_URLS, ''];
											}}
										>
											<Plus />
										</button>
									</Tooltip>
								{:else}
									<Tooltip content="Remove MCP Server">
										<button
											class="px-3 py-2 text-gray-700 dark:text-gray-200 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition"
											type="button"
											aria-label="Remove MCP server"
											on:click={() => {
												console.log('Removing server at index:', idx);
												console.log('Current MCP_BASE_URLS:', MCP_BASE_URLS);
												MCP_BASE_URLS = MCP_BASE_URLS.filter((_, i) => i !== idx);
												console.log('After filter:', MCP_BASE_URLS);
												// Ensure we always have at least one empty URL field for re-input
												if (MCP_BASE_URLS.length === 0) {
													MCP_BASE_URLS = [''];
													console.log('Added empty field:', MCP_BASE_URLS);
												}
												// Force reactivity update
												MCP_BASE_URLS = [...MCP_BASE_URLS];
												console.log('Final MCP_BASE_URLS:', MCP_BASE_URLS);
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													d="M3.75 7.25a.75.75 0 0 0 0 1.5h8.5a.75.75 0 0 0 0-1.5h-8.5Z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}
							</div>
						</div>
					{/each}
				</div>

				<div class="mt-3 flex gap-2">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition rounded-full"
						type="button"
						on:click={autoVerifyAllConnections}
						disabled={!ENABLE_MCP_API || MCP_BASE_URLS.every(url => !url || url.trim() === '')}
					>
						{$i18n.t('Refresh All Connections')}
					</button>
					
					<div class="text-xs text-gray-600 dark:text-gray-500 self-center">
						{$i18n.t('Connections are verified automatically when URLs change and every 30 seconds')}
					</div>
				</div>
			</div>
			{:else}
			<!-- Add External Server Button when no external servers are configured -->
			<div class="text-center py-4">
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition rounded-full flex items-center gap-2 mx-auto"
					type="button"
					on:click={() => {
						MCP_BASE_URLS = [''];
					}}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
						<path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
					</svg>
					{$i18n.t('Add External MCP Server')}
				</button>
				<div class="text-xs text-gray-600 dark:text-gray-500 mt-2">
					{$i18n.t('Connect to external MCP servers for additional tools and capabilities')}
				</div>
			</div>
			{/if}

			<hr class="dark:border-gray-700" />

			<div>
				<div class="mb-2 text-sm font-medium flex items-center gap-2">
					<!-- MCP Tools Icon -->
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-green-500">
						<path fill-rule="evenodd" d="M12 6.75a5.25 5.25 0 016.775-5.025.75.75 0 01.313 1.248l-3.32 3.319c.063.475.276.934.641 1.299.365.365.824.578 1.3.641l3.318-3.319a.75.75 0 011.248.313 5.25 5.25 0 01-5.472 6.756c-1.018-.086-1.87.1-2.309.634L7.344 21.3A3.298 3.298 0 112.7 16.657l8.684-7.151c.533-.44.72-1.291.634-2.309A5.25 5.25 0 0112 6.75zM4.117 19.125a.75.75 0 01.75-.75h.008a.75.75 0 01.75.75v.008a.75.75 0 01-.75.75h-.008a.75.75 0 01-.75-.75v-.008z" clip-rule="evenodd" />
					</svg>
					{$i18n.t('Available MCP Tools')}
					{#if mcpToolsLoading}
						<Spinner className="size-3" />
					{/if}
				</div>

				{#if mcpTools.length > 0}
					<div class="space-y-2">
						{#each mcpTools as tool}
							<div class="border dark:border-gray-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
								<div class="flex items-center gap-2 mb-2">
									<!-- Tool Icon -->
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-blue-400">
										<path fill-rule="evenodd" d="M8 1a.75.75 0 01.75.75V6h-1.5V2.5L3 7v11h14V7l-4.25-4.5V6h-1.5V1.75A.75.75 0 0112 1h-4z" clip-rule="evenodd" />
									</svg>
									<div class="font-medium text-sm">{tool.name}</div>
									<!-- Tool Source Badge -->
									{#if tool.mcp_server_url}
										<!-- External Server Tool -->
										<span class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
											External
										</span>
									{:else}
										<!-- Built-in Server Tool -->
										<span class="inline-flex items-center rounded-full bg-green-100 dark:bg-green-900 px-2 py-1 text-xs font-medium text-green-700 dark:text-green-300">
											{$i18n.t('Built-in')}
										</span>
									{/if}
								</div>
								{#if tool.description}
									<div class="text-xs text-gray-700 dark:text-gray-400 mt-1 ml-6">{tool.description}</div>
								{/if}
								<!-- Server Source Information -->
								{#if tool.mcp_server_url}
									<div class="flex items-center gap-1 mt-2 ml-6">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3 text-gray-600">
											<path d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
										</svg>
										<span class="text-xs text-gray-600">
											External Server: {tool.mcp_server_url.length > 25 ? 
												tool.mcp_server_url.substring(0, 25) + '...' : 
												tool.mcp_server_url}
										</span>
										{#if tool.mcp_server_idx !== undefined}
											<span class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300">
												#{tool.mcp_server_idx + 1}
											</span>
										{/if}
									</div>
								{:else}
									<!-- Built-in server indicator -->
									<div class="flex items-center gap-1 mt-2 ml-6">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3 text-gray-600">
											<path d="M21.731 2.269a2.625 2.625 0 00-3.712 0l-1.157 1.157 3.712 3.712 1.157-1.157a2.625 2.625 0 000-3.712zM19.513 8.199l-3.712-3.712-12.15 12.15a5.25 5.25 0 00-1.32 2.214l-.8 2.685a.75.75 0 00.933.933l2.685-.8a5.25 5.25 0 002.214-1.32L19.513 8.2z" />
										</svg>
										<span class="text-xs text-gray-600">{$i18n.t('Built-in Server Tool')}</span>
									</div>
								{/if}
								{#if tool.inputSchema}
									<details class="mt-2 ml-6">
										<summary class="text-xs cursor-pointer text-gray-600 hover:text-gray-500 flex items-center gap-1">
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
												<path d="M10.75 10.818v2.614A3.13 3.13 0 0011.888 13c.482-.315.612-.648.612-.875 0-.227-.13-.56-.612-.875a3.13 3.13 0 00-1.138-.432zM8.33 8.62c.053.055.115.11.184.164.208.16.46.284.736.363V6.603a2.45 2.45 0 00-.35.13c-.14.065-.27.143-.386.233-.377.292-.514.627-.514.909 0 .184.058.39.33.645zM4.867 19.125h10.266c.703 0 1.867-.422 1.867-1.384v-5.468c0-.509-.128-.77-.371-.99a2.06 2.06 0 00-.65-.382c-.59-.33-1.298-.59-2.052-.59s-1.462.26-2.052.59a2.06 2.06 0 00-.65.382c-.243.22-.371.481-.371.99v5.468c0 .962 1.164 1.384 1.867 1.384zM6 7.741V6.741c0-1.036.895-1.741 2-1.741s2 .705 2 1.741v1H6z" />
											</svg>
											{$i18n.t('Input Schema')}
										</summary>
										<pre class="text-xs mt-1 p-2 bg-gray-900 text-gray-300 rounded overflow-x-auto">
{JSON.stringify(tool.inputSchema, null, 2)}
										</pre>
									</details>
								{/if}
							</div>
						{/each}
					</div>
				{:else if !mcpToolsLoading}
					<div class="flex items-center gap-2 text-xs text-gray-600 p-4 border border-dashed dark:border-gray-600 rounded-lg">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zM10 15a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
						</svg>
						{$i18n.t('No MCP tools available. Configure and enable MCP servers to see available tools.')}
					</div>
				{/if}

				<button
					class="mt-2 px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition rounded-full"
					type="button"
					on:click={getMCPToolsHandler}
					disabled={mcpToolsLoading}
				>
					{$i18n.t('Refresh Tools')}
				</button>
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
