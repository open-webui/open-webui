<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	export let serverId: string;
	export let serverName: string;

	const dispatch = createEventDispatcher();

	let oauthStatus = {
		has_oauth_config: false,
		oauth_enabled: false,
		has_tokens: false,
		is_expired: false,
		expires_in: null,
		status: 'disconnected',
		needs_reauth: false,
		error_message: null
	};

	let connecting = false;
	let testing = false;

	onMount(async () => {
		await checkStatus();

		// Handle OAuth callback results
		const urlParams = new URLSearchParams(window.location.search);
		const success = urlParams.get('oauth_success');
		const error = urlParams.get('oauth_error');

		if (success === serverId) {
			toast.success('OAuth connected successfully!');
			await checkStatus();
			dispatch('connected');
			// Clean URL
			window.history.replaceState({}, '', window.location.pathname + window.location.hash);
		} else if (error) {
			toast.error(`OAuth failed: ${decodeURIComponent(error)}`);
			// Clean URL
			window.history.replaceState({}, '', window.location.pathname + window.location.hash);
		}
	});

	const checkStatus = async () => {
		try {
			const response = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/status`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (response.ok) {
				oauthStatus = await response.json();
			} else {
				console.error('Failed to check OAuth status:', response.statusText);
			}
		} catch (error) {
			console.error('Error checking OAuth status:', error);
		}
	};

	const startOAuth = async () => {
		if (connecting) return;

		try {
			connecting = true;

			// Get authorization URL
			const response = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/start`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Failed to start OAuth flow');
			}

			const result = await response.json();

			// Open popup window
			const popup = window.open(
				result.authorization_url,
				'oauth_popup',
				'width=500,height=600,scrollbars=yes,resizable=yes,location=yes'
			);

			if (!popup) {
				toast.error('Popup blocked. Please allow popups and try again.');
				return;
			}

			// Monitor popup
			const checkClosed = setInterval(async () => {
				if (popup.closed) {
					clearInterval(checkClosed);
					connecting = false;

					// Check if authentication was successful
					setTimeout(async () => {
						await checkStatus();
						if (oauthStatus.has_tokens && !oauthStatus.needs_reauth) {
							dispatch('connected');
						}
					}, 1000);
				}
			}, 1000);
		} catch (error) {
			console.error('OAuth error:', error);
			const errorMessage = error instanceof Error ? error.message : 'Unknown error';
			toast.error(`Failed to start OAuth authentication: ${errorMessage}`);
			connecting = false;
		}
	};

	const testConnection = async () => {
		if (testing) return;

		try {
			testing = true;

			const response = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/test`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				}
			});

			const result = await response.json();

			if (result.success) {
				toast.success('OAuth connection is valid!');
			} else {
				toast.warning(result.message || 'OAuth connection test failed');
				if (result.needs_reauth) {
					await checkStatus();
				}
			}
		} catch (error) {
			console.error('OAuth test error:', error);
			toast.error('Failed to test OAuth connection');
		} finally {
			testing = false;
		}
	};

	const disconnect = async () => {
		if (!confirm('Disconnect OAuth? You will need to re-authenticate to use this server.')) {
			return;
		}

		try {
			const response = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/disconnect`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				}
			});

			if (response.ok) {
				toast.success('OAuth disconnected');
				await checkStatus();
				dispatch('disconnected');
			} else {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Failed to disconnect');
			}
		} catch (error) {
			console.error('Disconnect error:', error);
			const errorMessage = error instanceof Error ? error.message : 'Unknown error';
			toast.error(`Failed to disconnect OAuth: ${errorMessage}`);
		}
	};

	const formatExpiry = (seconds: number): string => {
		if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
		if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
		return `${Math.floor(seconds / 86400)}d`;
	};

	const getStatusColor = (status: string) => {
		switch (status) {
			case 'connected':
				return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300';
			case 'oauth_required':
			case 'token_expired':
				return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300';
			case 'connecting':
				return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300';
			default:
				return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
		}
	};

	const getStatusText = (
		status: string,
		hasTokens: boolean,
		isExpired: boolean,
		needsReauth: boolean
	) => {
		if (hasTokens && !isExpired && !needsReauth) {
			return 'Connected';
		} else if (needsReauth || isExpired) {
			return 'Re-authentication Required';
		} else if (status === 'connecting') {
			return 'Connecting';
		} else {
			return 'Not Connected';
		}
	};
</script>

<div class="space-y-3 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800/50">
	<div class="flex items-center justify-between">
		<h4 class="font-medium text-gray-900 dark:text-gray-100">OAuth Authentication</h4>

		<span class="px-2 py-1 text-xs rounded-full {getStatusColor(oauthStatus.status)}">
			{getStatusText(
				oauthStatus.status,
				oauthStatus.has_tokens,
				oauthStatus.is_expired,
				oauthStatus.needs_reauth
			)}
			{#if oauthStatus.has_tokens && !oauthStatus.needs_reauth && oauthStatus.expires_in}
				(expires in {formatExpiry(oauthStatus.expires_in)})
			{/if}
		</span>
	</div>

	{#if !oauthStatus.has_oauth_config}
		<div class="text-sm text-gray-600 dark:text-gray-400">
			Configure OAuth settings above to enable authentication.
		</div>
	{:else if !oauthStatus.oauth_enabled}
		<div class="text-sm text-gray-600 dark:text-gray-400">
			OAuth is configured but disabled. Enable it in the configuration above.
		</div>
	{:else if !oauthStatus.has_tokens || oauthStatus.needs_reauth}
		<div class="space-y-3">
			{#if oauthStatus.error_message}
				<div
					class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded"
				>
					⚠️ {oauthStatus.error_message}
				</div>
			{:else if oauthStatus.is_expired}
				<div
					class="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-2 rounded"
				>
					⚠️ Your OAuth token has expired. Click "Connect" to re-authenticate.
				</div>
			{:else if oauthStatus.needs_reauth}
				<div
					class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded"
				>
					🔒 Authentication required. Click "Connect" to authenticate with the OAuth provider.
				</div>
			{:else}
				<div class="text-sm text-gray-600 dark:text-gray-400">
					Click "Connect" to authenticate with the OAuth provider.
				</div>
			{/if}

			<button on:click={startOAuth} disabled={connecting} class="btn btn-primary btn-sm">
				{#if connecting}
					<span class="loading loading-spinner loading-xs"></span>
					Connecting...
				{:else}
					🔗 Connect
				{/if}
			</button>
		</div>
	{:else}
		<div class="space-y-3">
			<div class="text-sm text-green-600 dark:text-green-400">✅ OAuth authentication active</div>

			<div class="flex space-x-2">
				<button on:click={testConnection} disabled={testing} class="btn btn-outline btn-sm">
					{#if testing}
						<span class="loading loading-spinner loading-xs"></span>
						Testing...
					{:else}
						🔍 Test Connection
					{/if}
				</button>

				<button on:click={disconnect} class="btn btn-outline btn-error btn-sm">
					🔌 Disconnect
				</button>
			</div>
		</div>
	{/if}
</div>
