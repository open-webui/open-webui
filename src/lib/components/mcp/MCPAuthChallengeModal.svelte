<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { user } from '$lib/stores';

	import { mcpServersApi } from '$lib/apis/mcp_servers';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let show = false;
	export let elicitationData: any = {};

	const dispatch = createEventDispatcher();

	let authenticating = false;

	// Determine if current user can manage (admin or write access). For now, non-admins are read-only in MCP UI.
	$: isAdmin = ($user?.role === 'admin');
	let userHasManageRights = isAdmin;

	async function determineManageRights() {
		try {
			userHasManageRights = isAdmin;
			if (userHasManageRights) return;
			if (!serverId) return;
			// Fetch server details and allow owner to manage
			const server = await mcpServersApi.getMCPServerById(localStorage.token, serverId);
			userHasManageRights = Boolean(server && server.user_id === $user?.id);
		} catch (_) {
			userHasManageRights = isAdmin;
		}
	}

	$: if (show && serverId) {
		determineManageRights();
	}

	// Extract data from elicitation structure
	$: serverId = elicitationData?.data?.server_id || '';
	$: serverName = elicitationData?.data?.server_name || '';
	$: toolName = elicitationData?.data?.tool_name || '';
	$: errorMessage = elicitationData?.data?.error_message || '';
	$: title = elicitationData?.data?.title || $i18n.t('mcp.auth.title_default');
	$: message = elicitationData?.data?.message || $i18n.t('mcp.auth.message_default');
	$: retryContext = elicitationData?.data?.retry_context || {};
	$: challengeType = elicitationData?.data?.challenge_type || 'manual';
	$: canAutoAuth = elicitationData?.data?.can_auto_auth || false;
	$: authUrl = elicitationData?.data?.auth_url || null;
	$: instructions = elicitationData?.data?.instructions || null;

	const startAuthentication = async () => {
		if (authenticating || !serverId) return;

		try {
			authenticating = true;

			if (challengeType === 'oauth' && canAutoAuth) {
				// Handle OAuth authentication with popup
				if (authUrl) {
					// Use provided auth URL directly
					openOAuthPopup(authUrl);
				} else {
					// Start OAuth flow via backend
					const response = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/start`, {
						method: 'POST',
						headers: {
							Authorization: `Bearer ${localStorage.token}`,
							'Content-Type': 'application/json'
						}
					});

					if (!response.ok) {
						const errorData = await response.json().catch(() => ({}));
						throw new Error(errorData.detail || $i18n.t('mcp.auth.oauth_start_failed'));
					}

					const result = await response.json();
					openOAuthPopup(result.authorization_url);
				}
			} else {
				// Manual authentication - just close modal and show instructions
				toast.info(instructions || $i18n.t('mcp.auth.manual_instructions_default'));
				dispatch('cancelled');
				show = false;
				authenticating = false;
			}
		} catch (error: unknown) {
			console.error('Authentication error:', error);
			const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
			toast.error($i18n.t('mcp.auth.authentication_failed_with_error', { error: errorMessage }));
			authenticating = false;
		}
	};

	const openOAuthPopup = (url: string) => {
		// Open popup window
		const popup = window.open(
			url,
			'mcp_reauth_popup',
			'width=500,height=600,scrollbars=yes,resizable=yes,location=yes'
		);

		if (!popup) {
			toast.error($i18n.t('mcp.auth.popup_blocked'));
			authenticating = false;
			return;
		}

		// Monitor popup for completion
		const checkClosed = setInterval(async () => {
			if (popup.closed) {
				clearInterval(checkClosed);
				authenticating = false;

				// Check if authentication was successful
				setTimeout(async () => {
					try {
						const statusResponse = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/status`, {
							headers: { Authorization: `Bearer ${localStorage.token}` }
						});

						if (statusResponse.ok) {
							const status = await statusResponse.json();
							if (status.authenticated && !status.needs_reauth) {
								// Authentication successful - notify parent
								show = false;
								dispatch('authenticated', {
									retryContext,
									serverId,
									serverName,
									toolName
								});
								toast.success($i18n.t('mcp.auth.success'));
							} else {
								toast.error($i18n.t('mcp.auth.failed_incomplete'));
							}
						} else {
							toast.error($i18n.t('mcp.auth.verify_status_failed'));
						}
					} catch (error: unknown) {
						console.error('Status check error:', error);
						const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
						toast.error($i18n.t('mcp.auth.verify_failed_with_error', { error: errorMessage }));
					}
				}, 1000);
			}
		}, 1000);
	};

	const cancel = () => {
		show = false;
		dispatch('cancelled', { serverId, serverName, toolName });
	};
</script>

{#if show}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		role="dialog"
		aria-modal="true"
		aria-labelledby="auth-modal-title"
	>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4 shadow-xl">
			<h3 id="auth-modal-title" class="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
				{title}
			</h3>

			<div class="space-y-3 mb-6">
				<p class="text-sm text-gray-600 dark:text-gray-300">
					{message}
				</p>

				<div
					class="bg-red-50 dark:bg-red-900/20 p-3 rounded text-sm border border-red-200 dark:border-red-800"
				>
					<div class="space-y-1">
						<div>
							<strong class="text-red-800 dark:text-red-200">{$i18n.t('mcp.auth.tool_label')}</strong>
							<span class="text-red-700 dark:text-red-300">{toolName}</span>
						</div>
						<div>
							<strong class="text-red-800 dark:text-red-200">{$i18n.t('mcp.auth.server_label')}</strong>
							<span class="text-red-700 dark:text-red-300">{serverName}</span>
						</div>
						{#if errorMessage}
							<div>
								<strong class="text-red-800 dark:text-red-200">{$i18n.t('mcp.auth.error_label')}</strong>
								<span class="text-red-700 dark:text-red-300">{errorMessage}</span>
							</div>
						{/if}
					</div>
				</div>

				<div
					class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded text-sm border border-blue-200 dark:border-blue-800"
				>
					<p class="text-blue-800 dark:text-blue-200">
						<span class="font-medium">{$i18n.t('mcp.auth.what_happens_next')}</span><br />
						{#if (challengeType === 'oauth' && canAutoAuth && userHasManageRights)}
							1. {$i18n.t('mcp.auth.steps.oauth.1')}<br />
							2. {$i18n.t('mcp.auth.steps.oauth.2', { serverName })}<br />
							3. {$i18n.t('mcp.auth.steps.oauth.3')} 
						{:else}
							{#if !userHasManageRights}
								1. Ask your administrator to re-authenticate this MCP server<br />
								2. Once re-authenticated, click regenerate or try again
							{:else}
								1. {$i18n.t('mcp.auth.steps.manual.1')}<br />
								2. {instructions || $i18n.t('mcp.auth.steps.manual.2', { serverName })}<br />
								3. {$i18n.t('mcp.auth.steps.manual.3')}
							{/if}
						{/if}
					</p>
				</div>
			</div>

			<div class="flex space-x-3">
				<button
					on:click={(userHasManageRights && challengeType === 'oauth' && canAutoAuth) ? startAuthentication : cancel}
					disabled={(userHasManageRights && challengeType === 'oauth' && canAutoAuth) ? (authenticating || !serverId) : false}
					class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
				>
					{#if authenticating}
						<div class="flex items-center justify-center space-x-2">
							<div
								class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"
							></div>
							<span>{$i18n.t('mcp.auth.authenticating')}</span>
						</div>
					{:else if (challengeType === 'oauth' && canAutoAuth && userHasManageRights)}
						🔗 {$i18n.t('mcp.auth.authenticate_and_retry')}
					{:else}
						✅ {$i18n.t('mcp.auth.ok')}
					{/if}
				</button>

				<button
					on:click={cancel}
					disabled={authenticating}
					class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
				>
					{$i18n.t('mcp.auth.cancel')}
				</button>
			</div>
		</div>
	</div>
{/if}
