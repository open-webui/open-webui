<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	const dispatch = createEventDispatcher();

	import { 
		getMCPConfig, 
		updateMCPConfig, 
		verifyMCPConnection, 
		getMCPURLs, 
		updateMCPURLs, 
		getMCPTools,
		getBuiltinServers,
		restartBuiltinServer,
		getExternalServers,
		createExternalServer,
		updateExternalServer,
		deleteExternalServer,
		startExternalServer,
		stopExternalServer,
		restartExternalServer
	} from '$lib/apis/mcp';
	import { getTools } from '$lib/apis/tools';

	import { user, tools } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Modal from '$lib/components/common/Modal.svelte';

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
	
	// External servers
	let externalServers: any[] = [];
	let externalServersLoading = false;
	
	// Server creation/editing modal
	let showServerModal = false;
	let editingServer: any = null;
	let serverForm = {
		name: '',
		description: '',
		command: '',
		args: [],
		env: {},
		transport: 'stdio',
		url: '',
		port: null,
		is_active: true
	};
	
	// Form state
	let serverFormArgsText = '';
	let serverFormEnvText = '';
	
	// Server connection status tracking for external servers

	// Reactive statement to ensure we always have at least one input field
	$: {
		if (MCP_BASE_URLS.length === 0) {
			MCP_BASE_URLS = [''];
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

	const getExternalServersHandler = async () => {
		externalServersLoading = true;
		const res = await getExternalServers(localStorage.token).catch((error) => {
			console.error('Error fetching external servers:', error);
			return { servers: [] };
		});

		externalServers = res.servers || [];
		externalServersLoading = false;
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

	// External Server Management Functions
	const openServerModal = (server: any = null) => {
		editingServer = server;
		if (server) {
			// Editing existing server
			serverForm = {
				name: server.name || '',
				description: server.description || '',
				command: server.command || '',
				args: server.args || [],
				env: server.env || {},
				transport: server.transport || 'stdio',
				url: server.url || '',
				port: server.port || null,
				is_active: server.is_active !== undefined ? server.is_active : true
			};
		} else {
			// Creating new server
			serverForm = {
				name: '',
				description: '',
				command: '',
				args: [],
				env: {},
				transport: 'stdio',
				url: '',
				port: null,
				is_active: true
			};
		}
		
		// Convert arrays and objects to text for editing
		serverFormArgsText = Array.isArray(serverForm.args) ? serverForm.args.join('\n') : '';
		serverFormEnvText = JSON.stringify(serverForm.env, null, 2);
		
		showServerModal = true;
	};

	const closeServerModal = () => {
		showServerModal = false;
		editingServer = null;
		serverForm = {
			name: '',
			description: '',
			command: '',
			args: [],
			env: {},
			transport: 'stdio',
			url: '',
			port: null,
			is_active: true
		};
		serverFormArgsText = '';
		serverFormEnvText = '';
	};

	const saveServerHandler = async () => {
		try {
			// Parse args from text
			const args = serverFormArgsText.trim() ? serverFormArgsText.split('\n').map(arg => arg.trim()).filter(arg => arg) : [];
			
			// Parse env from JSON text
			let env = {};
			if (serverFormEnvText.trim()) {
				try {
					env = JSON.parse(serverFormEnvText);
				} catch (e) {
					toast.error('Invalid JSON in environment variables');
					return;
				}
			}

			const serverData = {
				name: serverForm.name,
				description: serverForm.description,
				command: serverForm.command,
				args: args,
				env: env,
				transport: serverForm.transport,
				url: serverForm.url || null,
				port: serverForm.port || null,
				is_active: serverForm.is_active
			};

			let res;
			if (editingServer) {
				// Update existing server
				res = await updateExternalServer(localStorage.token, editingServer.id, serverData);
			} else {
				// Create new server
				res = await createExternalServer(localStorage.token, serverData);
			}

			if (res) {
				toast.success(editingServer ? 'Server updated successfully' : 'Server created successfully');
				closeServerModal();
				await getExternalServersHandler();
				await getMCPToolsHandler();
				
				// Refresh tools list
				try {
					const updatedTools = await getTools(localStorage.token);
					tools.set(updatedTools);
				} catch (error) {
					console.error('Failed to refresh tools:', error);
				}
			}
		} catch (error) {
			toast.error(`Failed to save server: ${error}`);
		}
	};

	const deleteServerHandler = async (serverId: string, serverName: string) => {
		if (!confirm(`Are you sure you want to delete server "${serverName}"? This action cannot be undone.`)) {
			return;
		}

		try {
			const res = await deleteExternalServer(localStorage.token, serverId);
			if (res) {
				toast.success('Server deleted successfully');
				await getExternalServersHandler();
				await getMCPToolsHandler();
				
				// Refresh tools list
				try {
					const updatedTools = await getTools(localStorage.token);
					tools.set(updatedTools);
				} catch (error) {
					console.error('Failed to refresh tools:', error);
				}
			}
		} catch (error) {
			toast.error(`Failed to delete server: ${error}`);
		}
	};

	const startServerHandler = async (serverId: string, serverName: string) => {
		try {
			const res = await startExternalServer(localStorage.token, serverId);
			if (res) {
				toast.success(`Server "${serverName}" started successfully`);
				await getExternalServersHandler();
				await getMCPToolsHandler();
			}
		} catch (error) {
			toast.error(`Failed to start server: ${error}`);
		}
	};

	const stopServerHandler = async (serverId: string, serverName: string) => {
		try {
			const res = await stopExternalServer(localStorage.token, serverId);
			if (res) {
				toast.success(`Server "${serverName}" stopped successfully`);
				await getExternalServersHandler();
				await getMCPToolsHandler();
			}
		} catch (error) {
			toast.error(`Failed to stop server: ${error}`);
		}
	};

	const restartExternalServerHandler = async (serverId: string, serverName: string) => {
		try {
			const res = await restartExternalServer(localStorage.token, serverId);
			if (res) {
				toast.success(`Server "${serverName}" restarted successfully`);
				await getExternalServersHandler();
				await getMCPToolsHandler();
			}
		} catch (error) {
			toast.error(`Failed to restart server: ${error}`);
		}
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

			// Load external servers
			await getExternalServersHandler();

			await getMCPToolsHandler();
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateMCPHandler();
	}}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="flex flex-col gap-1 mt-1.5 mb-2">
			<div class="flex justify-between items-center">
				<div class="flex items-center md:self-center text-xl font-medium px-0.5">
					{$i18n.t('MCP Servers')}
					<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
					<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
						>{(builtinServers?.length || 0) + (externalServers?.length || 0)}</span
					>
				</div>

				<div class="flex items-center gap-1.5">
					<Tooltip content={$i18n.t('Enable MCP API')}>
						<Switch bind:state={ENABLE_MCP_API} ariaLabel="Enable MCP API" />
					</Tooltip>
				</div>
			</div>

			<div class="text-xs text-gray-600 dark:text-gray-500">
				{$i18n.t('Configure connections to external MCP servers to extend model capabilities with additional tools and context.')}
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
										</span>
										
										<!-- Restart Button -->
										<Tooltip content={$i18n.t('Restart Server')}>
											<button
												class="px-2 py-1 text-gray-700 dark:text-gray-200 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded text-xs transition"
												type="button"
												aria-label="Restart {server.display_name || server.name} server"
												on:click={() => restartBuiltinServerHandler(server.name)}
											>
												<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3" aria-hidden="true">
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
			<div>
				<div class="mb-3 text-sm font-medium flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-purple-500">
						<path d="M6.75 6a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 .75.75v6a.75.75 0 0 1-.75.75h-9A.75.75 0 0 1 6.75 12V6Z" />
						<path d="M6.75 17.25a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-.75.75h-9a.75.75 0 0 1-.75-.75v-1.5Z" />
					</svg>
					{$i18n.t('External MCP Servers')}
					{#if externalServersLoading}
						<Spinner className="size-3" />
					{/if}
					<button
						class="ml-auto px-2 py-1 text-purple-700 dark:text-purple-300 bg-purple-100 hover:bg-purple-200 dark:bg-purple-900 dark:hover:bg-purple-800 rounded text-xs transition"
						type="button"
						aria-label="{$i18n.t('Add Server')}"
						on:click={() => openServerModal()}
					>
						<Plus className="w-3 h-3 inline mr-1" />
						{$i18n.t('Add Server')}
					</button>
				</div>
				
				<div class="text-xs text-gray-600 dark:text-gray-500 mb-3">
					{$i18n.t('Create and manage custom MCP servers with full configuration control.')}
				</div>

				{#if externalServers.length > 0}
					<div class="space-y-2">
						{#each externalServers as server}
							<div class="border dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-gray-800">
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-3">
										<!-- Server Status Indicator -->
										<div class="flex items-center gap-2">
											{#if server.runtime_status === 'running'}
												<Tooltip content={$i18n.t('Server is running')}>
													<div class="w-2 h-2 rounded-full bg-green-500"></div>
												</Tooltip>
											{:else if server.runtime_status === 'stopped'}
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
											<div class="font-medium text-sm">{server.name}</div>
											<div class="text-xs text-gray-700 dark:text-gray-400">{server.description || 'External MCP Server'}</div>
											<div class="text-xs text-gray-600 dark:text-gray-500 mt-1">
												{server.transport} • {server.command}
											</div>
										</div>
									</div>
									
									<div class="flex items-center gap-2">
										<!-- Tools Count Badge -->
										<span class="inline-flex items-center rounded-full bg-purple-100 dark:bg-purple-900 px-2 py-1 text-xs font-medium text-purple-700 dark:text-purple-300">
											{server.tools_count || 0} {(server.tools_count || 0) === 1 ? $i18n.t('tool') : $i18n.t('tools')}
										</span>
										
										<!-- Status Badge -->
										<span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium {server.runtime_status === 'running' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'}">
											{$i18n.t(server.runtime_status || 'unknown')}
										</span>
										
										<!-- Action Buttons -->
										<div class="flex gap-1">
											{#if server.runtime_status === 'running'}
												<Tooltip content={$i18n.t('Stop Server')}>
													<button
														class="px-2 py-1 text-red-700 dark:text-red-300 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 rounded text-xs transition"
														type="button"
														aria-label="Stop {server.name} server"
														on:click={() => stopServerHandler(server.id, server.name)}
													>
														<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3" aria-hidden="true">
															<path d="M5.5 3.5A1.5 1.5 0 0 1 7 2h2a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 9 14H7a1.5 1.5 0 0 1-1.5-1.5v-9Z" />
														</svg>
													</button>
												</Tooltip>
												<Tooltip content={$i18n.t('Restart Server')}>
													<button
														class="px-2 py-1 text-gray-700 dark:text-gray-200 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded text-xs transition"
														type="button"
														aria-label="Restart {server.name} server"
														on:click={() => restartExternalServerHandler(server.id, server.name)}
													>
														<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3" aria-hidden="true">
															<path fill-rule="evenodd" d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.37l-.84-.841a4.5 4.5 0 0 0-7.08.932.75.75 0 0 1-1.3-.75 6 6 0 0 1 9.44-1.242l.842.84V3.227a.75.75 0 0 1 .75-.75zm-.911 7.5A.75.75 0 0 1 13.199 11a6 6 0 0 1-9.44 1.241l-.84-.84v1.371a.75.75 0 0 1-1.5 0V9.591a.75.75 0 0 1 .75-.75H5.35a.75.75 0 0 1 0 1.5H3.98l.841.841a4.5 4.5 0 0 0 7.08-.932.75.75 0 0 1 1.025-.273z" clip-rule="evenodd" />
														</svg>
													</button>
												</Tooltip>
											{:else}
												<Tooltip content={$i18n.t('Start Server')}>
													<button
														class="px-2 py-1 text-green-700 dark:text-green-300 bg-green-100 hover:bg-green-200 dark:bg-green-900 dark:hover:bg-green-800 rounded text-xs transition"
														type="button"
														aria-label="Start {server.name} server"
														on:click={() => startServerHandler(server.id, server.name)}
													>
														<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3" aria-hidden="true">
															<path d="m11.596 8.697-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393Z" />
														</svg>
													</button>
												</Tooltip>
											{/if}
											<Tooltip content={$i18n.t('Edit Server')}>
												<button
													class="px-2 py-1 text-blue-700 dark:text-blue-300 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:hover:bg-blue-800 rounded text-xs transition"
													type="button"
													aria-label="Edit {server.name} server"
													on:click={() => openServerModal(server)}
												>
													<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3" aria-hidden="true">
														<path d="M13.488 2.513a1.75 1.75 0 0 0-2.475 0L6.75 6.774a2.75 2.75 0 0 0-.596.892l-.848 2.047a.75.75 0 0 0 .98.98l2.047-.848a2.75 2.75 0 0 0 .892-.596l4.261-4.262a1.75 1.75 0 0 0 0-2.474Z" />
														<path d="M4.75 3.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h6.5c.69 0 1.25-.56 1.25-1.25V9A.75.75 0 0 1 14 9v2.25A2.75 2.75 0 0 1 11.25 14h-6.5A2.75 2.75 0 0 1 2 11.25v-6.5A2.75 2.75 0 0 1 4.75 2H7a.75.75 0 0 1 0 1.5H4.75Z" />
													</svg>
												</button>
											</Tooltip>
											<Tooltip content={$i18n.t('Delete Server')}>
												<button
													class="px-2 py-1 text-red-700 dark:text-red-300 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 rounded text-xs transition"
													type="button"
													aria-label="Delete {server.name} server"
													on:click={() => deleteServerHandler(server.id, server.name)}
												>
													<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3" aria-hidden="true">
														<path fill-rule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.712Z" clip-rule="evenodd" />
													</svg>
												</button>
											</Tooltip>
										</div>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-xs text-gray-700 dark:text-gray-400 p-3 border border-dashed dark:border-gray-700 rounded-lg text-center">
						{$i18n.t('No external servers configured. Click "Add Server" to create your first external MCP server.')}
					</div>
				{/if}
			</div>

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
										<!-- Legacy URL-based Server Tool -->
										<span class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
											URL-based
										</span>
									{:else if tool.is_builtin === true}
										<!-- Built-in Server Tool -->
										<span class="inline-flex items-center rounded-full bg-green-100 dark:bg-green-900 px-2 py-1 text-xs font-medium text-green-700 dark:text-green-300">
											{$i18n.t('Built-in')}
										</span>
									{:else}
										<!-- External MCP Server Tool -->
										<span class="inline-flex items-center rounded-full bg-purple-100 dark:bg-purple-900 px-2 py-1 text-xs font-medium text-purple-700 dark:text-purple-300">
											External
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
											URL Server: {tool.mcp_server_url.length > 25 ? 
												tool.mcp_server_url.substring(0, 25) + '...' : 
												tool.mcp_server_url}
										</span>
									</div>
								{:else if tool.is_builtin === true}
									<!-- Built-in server indicator -->
									<div class="flex items-center gap-1 mt-2 ml-6">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3 text-gray-600">
											<path d="M21.731 2.269a2.625 2.625 0 00-3.712 0l-1.157 1.157 3.712 3.712 1.157-1.157a2.625 2.625 0 000-3.712zM19.513 8.199l-3.712-3.712-12.15 12.15a5.25 5.25 0 00-1.32 2.214l-.8 2.685a.75.75 0 00.933.933l2.685-.8a5.25 5.25 0 002.214-1.32L19.513 8.2z" />
										</svg>
										<span class="text-xs text-gray-600">{$i18n.t('Built-in Server Tool')}</span>
									</div>
								{:else if tool.mcp_server_name}
									<!-- External server indicator -->
									<div class="flex items-center gap-1 mt-2 ml-6">
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3 text-gray-600">
											<path d="M6.75 6a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 .75.75v6a.75.75 0 0 1-.75.75h-9A.75.75 0 0 1 6.75 12V6Z" />
										</svg>
										<span class="text-xs text-gray-600">External Server: {tool.mcp_server_name}</span>
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

<!-- External Server Modal -->
{#if showServerModal}
	<Modal size="lg" bind:show={showServerModal}>
		<div class="px-6 py-4">
			<!-- Modal Header -->
			<div class="flex items-center gap-2 mb-4 pb-4 border-b dark:border-gray-700">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-purple-500">
					<path d="M6.75 6a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 .75.75v6a.75.75 0 0 1-.75.75h-9A.75.75 0 0 1 6.75 12V6Z" />
					<path d="M6.75 17.25a.75.75 0 0 1 .75-.75h9a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-.75.75h-9a.75.75 0 0 1-.75-.75v-1.5Z" />
				</svg>
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					{editingServer ? $i18n.t('Edit External MCP Server') : $i18n.t('Add External MCP Server')}
				</h2>
			</div>
			
			<!-- Modal Content -->
			<div class="space-y-4 max-h-96 overflow-y-auto">
				<form on:submit|preventDefault={saveServerHandler} class="space-y-4">
					<!-- Basic Information -->
					<div class="space-y-3">
						<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Basic Information')}</h3>
						
						<div>
							<label for="server-name" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
								{$i18n.t('Server Name')} *
							</label>
							<input
								id="server-name"
								type="text"
								class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
								placeholder={$i18n.t('Enter a name for this server')}
								bind:value={serverForm.name}
								required
							/>
						</div>
						
						<div>
							<label for="server-description" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
								{$i18n.t('Description')}
							</label>
							<textarea
								id="server-description"
								class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
								placeholder={$i18n.t('Optional description for this server')}
								bind:value={serverForm.description}
								rows="2"
							></textarea>
						</div>
					</div>

					<!-- Transport Configuration -->
					<div class="space-y-3">
						<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Transport Configuration')}</h3>
						
						<div>
							<label for="server-transport" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
								{$i18n.t('Transport Type')} *
							</label>
							<select
								id="server-transport"
								class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
								bind:value={serverForm.transport}
								required
							>
								<option value="stdio">{$i18n.t('Standard I/O (stdio)')}</option>
								<option value="sse">{$i18n.t('Server-Sent Events (SSE)')}</option>
							</select>
						</div>

						{#if serverForm.transport === 'stdio'}
							<div>
								<label for="server-command" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n.t('Command')} *
								</label>
								<input
									id="server-command"
									type="text"
									class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
									placeholder={$i18n.t('e.g., python, node, /path/to/executable')}
									bind:value={serverForm.command}
									required
								/>
							</div>
							
							<div>
								<label for="server-args" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n.t('Arguments')}
								</label>
								<textarea
									id="server-args"
									class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
									placeholder={$i18n.t('One argument per line, e.g.:\nscript.py\n--verbose')}
									bind:value={serverFormArgsText}
									rows="3"
								></textarea>
								<div class="text-xs text-gray-500 mt-1">{$i18n.t('One argument per line')}</div>
							</div>
						{:else if serverForm.transport === 'sse'}
							<div class="grid grid-cols-2 gap-3">
								<div>
									<label for="server-url" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
										{$i18n.t('URL')} *
									</label>
									<input
										id="server-url"
										type="url"
										class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
										placeholder={$i18n.t('http://localhost:3000')}
										bind:value={serverForm.url}
										required
									/>
								</div>
								
								<div>
									<label for="server-port" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
										{$i18n.t('Port')}
									</label>
									<input
										id="server-port"
										type="number"
										min="1"
										max="65535"
										class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
										placeholder={$i18n.t('3000')}
										bind:value={serverForm.port}
									/>
								</div>
							</div>
						{/if}
					</div>

					<!-- Environment Variables -->
					<div class="space-y-3">
						<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Environment Variables')}</h3>
						
						<div>
							<label for="server-env" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
								{$i18n.t('Environment Variables (JSON)')}
							</label>
							<textarea
								id="server-env"
								class="w-full rounded-lg py-2 px-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none border border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400"
								placeholder={`{\n  "API_KEY": "your-api-key",\n  "DEBUG": "true"\n}`}
								bind:value={serverFormEnvText}
								rows="4"
							></textarea>
							<div class="text-xs text-gray-500 mt-1">{$i18n.t('Valid JSON object with environment variables')}</div>
						</div>
					</div>

					<!-- Server Options -->
					<div class="space-y-3">
						<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Server Options')}</h3>
						
						<div class="flex items-center justify-between">
							<div>
								<div class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Start server automatically')}</div>
								<div class="text-xs text-gray-500">{$i18n.t('Start this server when the application starts')}</div>
							</div>
							<Switch bind:state={serverForm.is_active} ariaLabel="Auto-start server" />
						</div>
					</div>
				</form>
			</div>
			
			<!-- Modal Footer -->
			<div class="flex justify-end gap-2 mt-6 pt-4 border-t dark:border-gray-700">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition"
					type="button"
					on:click={closeServerModal}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 dark:bg-purple-700 dark:hover:bg-purple-600 rounded-lg transition"
					type="button"
					on:click={saveServerHandler}
				>
					{editingServer ? $i18n.t('Update Server') : $i18n.t('Create Server')}
				</button>
			</div>
		</div>
	</Modal>
{/if}
