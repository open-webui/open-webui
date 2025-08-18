<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';
	import { mcpServersApi, type MCPServerForm, type MCPServerModel } from '$lib/apis/mcp_servers';
	import Modal from '$lib/components/common/Modal.svelte';
	import DynamicOAuthConfig from './DynamicOAuthConfig.svelte';

	// Use shared AccessControl component for consistent ACL UI
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	export let editingServer: MCPServerModel | null = null;
	export let isAdmin: boolean = false;
	export let isGlobal: boolean = false;
	export let show: boolean = true;

	const dispatch = createEventDispatcher();

	let submitting = false;
	let oauthFinished = false;

	// Form state
	let form: MCPServerForm = {
		name: '',
		http_url: '',
		headers: {},
		oauth_config: null
	};

	// Admin-only access control state (shared component value)
	let access_control: any = {};

	// Initialize form only when editing server changes
	let lastEditingId: string | null = null;
	$: if (editingServer && editingServer.id !== lastEditingId) {
		form = {
			name: editingServer.name,
			http_url: editingServer.http_url,
			headers: editingServer.headers || {},
			oauth_config: editingServer.oauth_config || null
		};
		if (isAdmin) access_control = editingServer.access_control ?? null;
		lastEditingId = editingServer.id;
	} else if (!editingServer && lastEditingId !== null) {
		form = { name: '', http_url: '', headers: {}, oauth_config: null };
		// Default to private for all new servers; user can later edit to make public
		access_control = {};
		lastEditingId = null;
	}

	const handleSubmit = async () => {
		if (!form.name || !form.http_url) {
			toast.error('Please fill in all required fields');
			return;
		}

		try {
			submitting = true;

			const 				serverData: any = {
				name: form.name,
				http_url: form.http_url,
				headers: form.headers || {},
				oauth_config: form.oauth_config
			};

			if (isAdmin) {
				serverData.access_control = access_control;
			} else {
				// Explicitly default to private for non-admins
				serverData.access_control = {};
			}

			let result;
			if (editingServer) {
				await mcpServersApi
					.updateMCPServer(localStorage.token, editingServer.id, serverData)
					.catch(async (err) => {
						const msg = err instanceof Error ? err.message : String(err);
						// Detect 401 or auth-related failures and prompt reconnect
						if (/401|Unauthorized|requires\s*reauth|Authentication\s*required/i.test(msg)) {
							toast.error('Authentication expired. Please reconnect OAuth and try again.');
						} else {
							toast.error(`Failed to update: ${msg}`);
						}
						throw err;
					});
			} else {
				result = await mcpServersApi.createMCPServer(localStorage.token, serverData);
			}

			toast.success(
				editingServer ? 'Server updated successfully' : 'Server created successfully'
			);

			show = false;
			dispatch('close', { saved: true }); // Inform parent to refresh
		} catch (error) {
			console.error('Error saving server:', error);
			// Extract the actual error message from the Error object
			const errorMessage = error instanceof Error ? error.message : 'Failed to save server';
			toast.error(errorMessage);
		} finally {
			submitting = false;
		}
	};
</script>

<Modal bind:show>
	<div class="w-full max-w-2xl mx-auto" data-mcp-modal="true">
		<!-- Header -->
		<div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
				{editingServer ? 'Edit MCP Server' : 'Add MCP Server'}
			</h3>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					on:click={() => {
						show = false;
						dispatch('close', { saved: false });
					}}
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>

		<!-- Content -->
		<div class="px-5 pb-4 space-y-6">
			<!-- Server Name -->
			<div>
				<label for="name" class="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Name *</label>
				<input
					id="name"
					type="text"
					bind:value={form.name}
					placeholder="Enter server name"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
					required
				/>
			</div>

			<!-- HTTP Stream URL -->
			<div>
				<label for="http-url" class="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">MCP Server URL *</label>
				<input
					id="http-url"
					type="url"
					bind:value={form.http_url}
					placeholder="https://your-mcp-server.com/mcp"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
					required
				/>
			</div>

			<!-- Connection Testing -->
			<div class="space-y-4">
				<DynamicOAuthConfig
					bind:oauthConfig={form.oauth_config}
					bind:headers={form.headers}
					serverId={editingServer?.id || ''}
					serverName={form.name || 'New Server'}
					mcpServerUrl={form.http_url || ''}
					on:oauthCompleted={() => (oauthFinished = true)}
					on:serverDraft={(e) => dispatch('serverDraft', e.detail)}
				/>
			</div>

			{#if oauthFinished}
				<div class="mt-2 p-3 rounded bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-sm text-green-800 dark:text-green-200">
					OAuth completed and connection tested. Click "Create/Update" to finalize and save the server.
				</div>
			{/if}

		{#if isAdmin}
			<div class="space-y-3 border-t pt-4">
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Visibility & Permissions</label>
				<AccessControl
					bind:accessControl={access_control}
					accessRoles={["read"]}
					allowPublic={true}
					on:change={() => { /* bound via bind already */ }}
				/>
			</div>
		{/if}

			<!-- Footer/Actions -->
			<div class="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
				<div class="flex space-x-3">
					<button
						type="button"
						class="px-4 py-2 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
						on:click={() => {
							show = false;
							dispatch('close', { saved: false });
						}}
					>
						Cancel
					</button>
					<button
						type="button"
						class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
						on:click={handleSubmit}
						disabled={submitting || !form.name || !form.http_url}
					>
						{#if submitting}
							<span class="flex items-center space-x-2">
								<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
								<span>{editingServer ? 'Updating...' : 'Creating...'}</span>
							</span>
						{:else}
							{editingServer ? 'Update' : 'Create'}
						{/if}
					</button>
				</div>
			</div>
		</div>
	</div>
</Modal>
