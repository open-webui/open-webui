<script lang="ts">
	import { onMount, createEventDispatcher, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user, tools as _tools } from '$lib/stores';
	import { mcpServersApi, type MCPServerUserResponse, type MCPServerModel } from '$lib/apis/mcp_servers';
	import { getTools } from '$lib/apis/tools';
	import MCPServerModal from './MCPServerModal.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let isAdmin = false;

	const dispatch = createEventDispatcher();

	// MCP Allowlist configuration
	let allowlistText = '';
	let saving = false;
	let originalAllowlist: string[] = [];

	onMount(async () => {
		await loadAllowlist();
	});

	// MCP Allowlist management functions
	const loadAllowlist = async () => {
		try {
			const response = await fetch(`${WEBUI_API_BASE_URL}/configs/mcp_allowlist`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (response.ok) {
				const config = await response.json();
				const allowlist = config?.MCP_SERVER_ALLOWLIST || [];
				originalAllowlist = [...allowlist];
				allowlistText = allowlist.join('\n');
				// ensure reset reflects current baseline
				await tick();
			}
		} catch (error) {
			console.error('Failed to load allowlist:', error);
			toast.error('Failed to load MCP allowlist configuration');
		}
	};

	const saveAllowlist = async () => {
		try {
			saving = true;
			const domains = allowlistText
				.split('\n')
				.map((domain) => domain.trim())
				.filter((domain) => domain.length > 0);

			const response = await fetch(`${WEBUI_API_BASE_URL}/configs/mcp_allowlist`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					MCP_SERVER_ALLOWLIST: domains
				})
			});

			if (response.ok) {
				const result = await response.json();
				originalAllowlist = [...(result.MCP_SERVER_ALLOWLIST || [])];
				toast.success('MCP allowlist updated successfully');
			} else {
				throw new Error('Failed to save configuration');
			}
		} catch (error) {
			console.error('Failed to save allowlist:', error);
			toast.error('Failed to save MCP allowlist configuration');
		} finally {
			saving = false;
		}
	};

	const resetAllowlist = () => {
		allowlistText = originalAllowlist.join('\n');
	};
</script>

<div class="space-y-6">
	<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
		<h3 class="text-lg font-semibold mb-4">MCP Server Domain Allowlist</h3>
		<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
			Configure which domains users can add MCP servers from. Leave empty to allow all domains.
		</p>

		<div class="space-y-4">
			<div>
				<label class="block text-sm font-medium mb-2">Allowed Domains</label>
				<textarea
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-transparent resize-none"
					rows="6"
					placeholder="Enter allowed domains, one per line:\nexample.com\napi.company.com\nlocalhost"
					bind:value={allowlistText}
				></textarea>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
					Enter one domain per line. Subdomains are automatically allowed (e.g., "example.com" allows "api.example.com").
				</p>
			</div>

			<div class="flex justify-end space-x-3">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors"
					on:click={resetAllowlist}
				>
					Reset
				</button>
				<button
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
					on:click={saveAllowlist}
					disabled={saving}
				>
					{saving ? 'Saving...' : 'Save Allowlist'}
				</button>
			</div>
		</div>
	</div>
</div>
