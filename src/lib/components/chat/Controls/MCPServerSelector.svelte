<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { user } from '$lib/stores';
	import { mcpServersApi, type MCPServerUserResponse } from '$lib/apis/mcp_servers';
	import { toast } from 'svelte-sonner';

	export let selectedServerId: string | null = null;
	export let disabled = false;

	const dispatch = createEventDispatcher();

	let servers: MCPServerUserResponse[] = [];
	let loading = true;
	let showDropdown = false;

	onMount(async () => {
		await loadServers();
	});

	const loadServers = async () => {
		try {
			loading = true;
			
			// Add timeout to prevent hanging
			const timeoutPromise = new Promise((_, reject) => 
				setTimeout(() => reject(new Error('Request timeout')), 8000)
			);
			
			const result = await Promise.race([
				mcpServersApi.getMCPServers(localStorage.token),
				timeoutPromise
			]);
			
			// Filter to only show active and connected servers
			servers = (result as MCPServerUserResponse[] | undefined)?.filter(
				(server: MCPServerUserResponse) => server.is_active && server.status === 'connected'
			) ?? [];
		} catch (error: any) {
			console.error('Failed to load MCP servers:', error);
			// Set default empty state instead of staying in loading forever
			servers = [];
			if (error.message === 'Request timeout') {
				toast.error('Request timeout loading servers - please try again');
			} else {
				toast.error('Failed to load MCP servers');
			}
		} finally {
			loading = false;
		}
	};

	const selectServer = (serverId: string | null) => {
		selectedServerId = serverId;
		showDropdown = false;
		dispatch('select', { serverId });
	};

	const getSelectedServer = () => {
		return servers.find((s) => s.id === selectedServerId);
	};

	let selectedServer: MCPServerUserResponse | undefined = undefined;
	$: selectedServer = getSelectedServer();

	const getStatusIcon = (status: string) => {
		switch (status) {
			case 'connected':
				return '🟢';
			case 'connecting':
				return '🟡';
			case 'error':
				return '🔴';
			default:
				return '⚪';
		}
	};
</script>

<div class="relative">
	<div class="flex flex-col space-y-2">
		<label class="text-sm font-medium text-gray-700 dark:text-gray-300"> MCP Servers </label>

		<button
			class="flex items-center justify-between w-full px-3 py-2 text-left bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent {disabled
				? 'opacity-50 cursor-not-allowed'
				: 'hover:bg-gray-50 dark:hover:bg-gray-700'}"
			on:click={() => !disabled && (showDropdown = !showDropdown)}
			{disabled}
		>
			<div class="flex items-center space-x-2">
				{#if loading}
					<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
					<span class="text-sm text-gray-600 dark:text-gray-400">Loading...</span>
				{:else if selectedServer}
					<span class="text-lg">{getStatusIcon(selectedServer.status)}</span>
					<span class="font-medium">{selectedServer.name}</span>
					<span
						class="text-xs text-gray-500 dark:text-gray-400 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded"
					>
						HTTP
					</span>
				{:else}
					<span class="text-gray-600 dark:text-gray-400">Select MCP Server</span>
				{/if}
			</div>

			<svg
				class="w-4 h-4 text-gray-400 transition-transform {showDropdown ? 'rotate-180' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>
	</div>

	{#if showDropdown && !disabled}
		<div
			class="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg"
		>
			<div class="max-h-60 overflow-y-auto">
				<!-- None option -->
				<button
					class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2"
					on:click={() => selectServer(null)}
				>
					<span class="text-gray-600 dark:text-gray-400">None</span>
				</button>

				{#if servers.length === 0}
					<div class="px-3 py-4 text-center text-gray-500 dark:text-gray-400">
						<p class="text-sm">No MCP servers available</p>
						<p class="text-xs mt-1">Configure servers in Settings → MCP</p>
					</div>
				{:else}
					{#each servers as server (server.id)}
						<button
							class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between {selectedServerId ===
							server.id
								? 'bg-blue-50 dark:bg-blue-900/20'
								: ''}"
							on:click={() => selectServer(server.id)}
						>
							<div class="flex items-center space-x-2">
								<span class="text-lg">{getStatusIcon(server.status)}</span>
								<div>
									<div class="font-medium">{server.name}</div>
								</div>
							</div>
							<span
								class="text-xs text-gray-500 dark:text-gray-400 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded"
							>
								HTTP
							</span>
						</button>
					{/each}
				{/if}
			</div>

			<div class="border-t border-gray-200 dark:border-gray-600 p-2">
				<a
					href="/admin/settings"
					class="block text-center text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
					on:click={() => (showDropdown = false)}
				>
					Manage MCP Servers
				</a>
			</div>
		</div>
	{/if}
</div>

<!-- Click outside to close -->
{#if showDropdown}
	<div
		class="fixed inset-0 z-40"
		on:click={() => (showDropdown = false)}
		role="button"
		tabindex="-1"
		on:keydown={(e) => e.key === 'Escape' && (showDropdown = false)}
	></div>
{/if}