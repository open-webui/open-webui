<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	export let serverId: string;
	export let serverName: string;
	export let oauthConfig: any = {};
	export let mcpServerUrl: string = '';
	export let headers: Record<string, string> = {}; // Get the MCP server URL from parent

	const dispatch = createEventDispatcher();

	// Connection state
	let connecting = false;
	let connectionResult: any = null;
	let showAdvanced = false;
	let oauthStateToken: string | null = null;

	// Advanced configuration fields (hidden by default)
	// Map old config method values to new simplified ones
	let configMethod = (() => {
		const method = oauthConfig?.config_method;
		if (method === 'manual') return 'manual';
		return 'auto'; // Default for mcp, dcr, discovery, or undefined
	})();
	let issuerUrl = oauthConfig?.issuer_url || '';
	let scopes = (oauthConfig?.scopes || []).join(' ');
	let authorizeUrl = oauthConfig?.authorize_url || '';
	let tokenUrl = oauthConfig?.token_url || '';
	let clientId = oauthConfig?.client_id || '';
	let clientSecret = oauthConfig?.client_secret || '';
	let usePkce = oauthConfig?.use_pkce ?? true;
	let audience = oauthConfig?.audience || '';
	let resource = oauthConfig?.resource || '';

	// OAuth completion polling using server ID (database-first)

	const handleConnect = async () => {
		if (!mcpServerUrl.trim()) {
			toast.error('Please enter an MCP server URL first');
			return;
		}

		try {
			connecting = true;
			connectionResult = null;

			// Step 1: Try OAuth discovery and connection
			// Skip OAuth discovery for new servers (serverId is empty)
			if (!serverId || serverId === '') {
				await testMCPConnection();
				return;
			}

			const oauthResponse = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/discover-from-mcp`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					mcp_server_url: mcpServerUrl.trim()
				})
			});

			const oauthResult = await oauthResponse.json();

			if (oauthResult.success) {
				// OAuth discovery successful - update config and start OAuth flow
				updateOAuthConfig(oauthResult);
				await startOAuthFlow();
			} else {
				// OAuth discovery failed - try direct connection and test tools
				await testMCPConnection();
			}
		} catch (error) {
			console.error('Connection error:', error);
			connectionResult = {
				success: false,
				error:
					'Connection failed. Please check your MCP server URL or use manual authentication headers.'
			};
		} finally {
			connecting = false;
		}
	};

	const testMCPConnection = async () => {
		try {
			// Test the MCP server connection and discover tools
			const testResponse = await fetch(`/api/v1/mcp-servers/test`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					http_url: mcpServerUrl.trim(),
					headers: {} // No headers for direct connection test
				})
			});

			const testResult = await testResponse.json();

			if (testResult.success) {
				let message = 'Connected successfully!';
				let toolsInfo = '';

				if (testResult.tools && testResult.tools.length > 0) {
					toolsInfo = ` Found ${testResult.tools.length} tool${testResult.tools.length > 1 ? 's' : ''}: ${testResult.tools
						.slice(0, 3)
						.map((t: any) => t.name)
						.join(', ')}${testResult.tools.length > 3 ? '...' : ''}`;
					message += toolsInfo;
				} else {
					message += ' No tools discovered.';
				}

				connectionResult = {
					success: true,
					message: message,
					tools: testResult.tools || []
				};

				toast.success('MCP server connection successful!');
			} else {
				// Connection failed - analyze the response to provide appropriate guidance
				if (testResult.message && testResult.message.includes('401')) {
					// 401 means OAuth is required
					connectionResult = {
						success: false,
						error: 'Authentication required. OAuth may be available for this server.',
						requiresAuth: true,
						authType: 'oauth',
						oauthAvailable: true,
						message:
							'This MCP server requires OAuth authentication. Click the button below to start the OAuth flow.'
					};
				} else if (testResult.message && testResult.message.includes('403')) {
					connectionResult = {
						success: false,
						error:
							'Access forbidden. Your credentials may not have permission to access this MCP server.',
						requiresAuth: true,
						authType: 'headers'
					};
				} else if (testResult.message && testResult.message.includes('404')) {
					connectionResult = {
						success: false,
						error: 'MCP server endpoint not found. Please verify the URL is correct.',
						requiresAuth: false
					};
				} else if (testResult.message && testResult.message.includes('500')) {
					connectionResult = {
						success: false,
						error: 'MCP server encountered an internal error. Please try again later.',
						requiresAuth: false
					};
				} else {
					connectionResult = {
						success: false,
						error: testResult.message || 'Connection failed. Please check your MCP server URL.',
						requiresAuth: false
					};
				}

				if (!connectionResult.success && !connectionResult.requiresAuth) {
					toast.error('MCP server connection failed');
				}
			}
		} catch (error) {
			console.error('MCP connection test error:', error);
			connectionResult = {
				success: false,
				error: 'Unable to connect to MCP server. Please verify the URL and network connectivity.',
				requiresAuth: false
			};
			toast.error('Connection test failed');
		}
	};

	const updateOAuthConfig = (discoveryResult: any) => {
		// Update OAuth configuration with discovered values
		configMethod = 'auto';
		issuerUrl = discoveryResult.authorization_servers?.[0] || '';

		// Update the oauthConfig object
		oauthConfig = {
			...oauthConfig,
			config_method: 'mcp',
			issuer_url: issuerUrl,
			mcp_server_url: mcpServerUrl.trim(),
			use_pkce: discoveryResult.pkce_supported,
			client_id: discoveryResult.client_id,
			authorize_url: discoveryResult.endpoints?.authorization_endpoint,
			token_url: discoveryResult.endpoints?.token_endpoint,
			registration_endpoint: discoveryResult.endpoints?.registration_endpoint,
			userinfo_endpoint: discoveryResult.endpoints?.userinfo_endpoint
		};

		// Dispatch the updated config
		dispatch('configUpdated', oauthConfig);
	};

	const startOAuthFlow = async () => {
		if (!mcpServerUrl.trim()) {
			connectionResult = {
				success: false,
				error: 'Please enter an MCP Server URL'
			};
			return;
		}

		connecting = true;
		connectionResult = null;

		try {
			const endpoint = serverId
				? `/api/v1/mcp-servers/${serverId}/oauth/start`
				: '/api/v1/mcp-servers/oauth/start-with-discovery';

			const payload = serverId
				? { serverId }
				: {
						serverName: serverName || 'MCP Server',
						mcpServerUrl: mcpServerUrl.trim(),
						headers: headers || {}
					};

			const response = await fetch(endpoint, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				const errorData = await response.json();
				// Handle improved backend error format
				if (errorData.detail && typeof errorData.detail === 'object') {
					const detail = errorData.detail;
					if (detail.needs_manual_config) {
						// Special handling for manual config required errors
						connectionResult = {
							success: false,
							error: detail.message || detail.error || 'OAuth configuration required',
							requiresManualConfig: true,
							serverType: detail.server_type
						};
						return;
					} else {
						throw new Error(
							detail.message || detail.error || `HTTP ${response.status}: ${response.statusText}`
						);
					}
				} else {
					throw new Error(
						errorData.detail?.message ||
							errorData.detail ||
							`HTTP ${response.status}: ${response.statusText}`
					);
				}
			}

			// Safely parse JSON; treat empty body (e.g., 204) as successful initiation
			let result: any = {};
			try {
				const text = await response.text();
				result = text ? JSON.parse(text) : {};
			} catch (_) {
				result = {};
			}

			// Capture oauth state token if provided by backend
			if (result.oauth_state_token) {
				oauthStateToken = result.oauth_state_token as string;
			}

			if (result.success && result.authorization_url) {
				// Store permanent server_id if it was created (for new servers)
				if (result.server_id) {
					// Update the serverId to the permanent server ID
					serverId = result.server_id;
					// Notify parent that a draft server exists so it can switch to edit/update mode
					dispatch('serverDraft', { serverId: result.server_id });
				}

				// Server ID stored for subsequent operations

				const popup = window.open(
					result.authorization_url,
					'oauth',
					'width=500,height=600,scrollbars=yes'
				);

				if (!popup) {
					connectionResult = {
						success: false,
						error: 'Popup blocked. Please allow popups for this site and try again.'
					};
					return;
				}

				// Begin polling backend status instead of checking popup.closed (avoids COOP issues)
				let attempts = 0;
				const maxAttempts = 120; // 2 minutes
				const poll = setInterval(async () => {
					attempts++;
					try {
						const resp = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/status`, {
							headers: { Authorization: `Bearer ${localStorage.token}` }
						});
						if (resp.ok) {
							const st = await resp.json();
							if (st.authenticated) {
								clearInterval(poll);
								connecting = false;
								await testMCPConnectionWithAuth();
								dispatch('oauthCompleted', { serverId });
							}
						}
					} catch (e) {
						/* ignore transient errors */
					}
					if (attempts >= maxAttempts) {
						clearInterval(poll);
						connecting = false;
					}
				}, 1000);
			} else if (response.ok && Object.keys(result).length === 0) {
				// No JSON body but request was OK; treat as successful initiation
				connectionResult = {
					success: true,
					message: 'OAuth initiated successfully.'
				};
				dispatch('oauthCompleted', { serverId });
			} else {
				throw new Error(result.error || 'Failed to start OAuth flow');
			}
		} catch (error) {
			console.error('OAuth flow error:', error);
			connectionResult = {
				success: false,
				error: `Failed to start OAuth: ${error instanceof Error ? error.message : String(error)}`
			};
		} finally {
			connecting = false;
		}
	};

	const checkOAuthStatus = async () => {
		try {
			// Check OAuth status for the current server

			if (!serverId) {
				console.log('No server ID available for OAuth status check');
				return;
			}

			const response = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/status`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!response.ok) {
				if (response.status === 404) {
					// Server not created yet
					return;
				}
				console.error('OAuth status request failed:', response.status, response.statusText);
				connectionResult = {
					success: false,
					error: `Failed to check OAuth status: ${response.status} ${response.statusText}`
				};
				return;
			}

			const result = await response.json();

			if (result.authenticated) {
				// Authenticated, now test connection
				await testMCPConnectionWithAuth();
			} else {
				// Not authenticated
				connectionResult = {
					success: false,
					error: result.message || 'OAuth authentication was not completed'
				};
			}
		} catch (error) {
			console.error('OAuth status check error:', error);
			connectionResult = {
				success: false,
				error: `Failed to verify OAuth status: ${error instanceof Error ? error.message : String(error)}`
			};
		}
	};

	const testMCPConnectionWithAuth = async () => {
		try {
			// Test the MCP server connection with OAuth authentication
			const testResponse = await fetch(`/api/v1/mcp-servers/${serverId}/oauth/test`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				}
			});

			const testResult = await testResponse.json();

			if (testResult.success) {
				let message = 'OAuth authentication and connection successful!';

				if (testResult.tools && testResult.tools.length > 0) {
					const toolsInfo = ` Found ${testResult.tools.length} tool${testResult.tools.length > 1 ? 's' : ''}: ${testResult.tools
						.slice(0, 3)
						.map((t: any) => t.name)
						.join(', ')}${testResult.tools.length > 3 ? '...' : ''}`;
					message += toolsInfo;
				} else {
					message += ' No tools discovered.';
				}

				connectionResult = {
					success: true,
					message: message,
					tools: testResult.tools || []
				};

				toast.success('MCP server connected with OAuth!');
			} else {
				connectionResult = {
					success: false,
					error: testResult.message || 'Failed to connect to MCP server after OAuth authentication'
				};
			}
		} catch (error) {
			console.error('MCP connection test with auth error:', error);
			connectionResult = {
				success: false,
				error: 'Failed to test MCP connection after OAuth authentication'
			};
		}
	};

	const saveAdvancedConfig = () => {
		// Update OAuth config with manual values
		oauthConfig = {
			...oauthConfig,
			config_method: configMethod,
			issuer_url: issuerUrl,
			scopes: scopes.split(' ').filter((s: string) => s.trim()),
			authorize_url: authorizeUrl,
			token_url: tokenUrl,
			client_id: clientId,
			client_secret: clientSecret,
			use_pkce: usePkce,
			audience: audience,
			resource: resource
		};

		dispatch('configUpdated', oauthConfig);
		toast.success('OAuth configuration saved');
	};

	// Header management functions
	const addHeader = () => {
		headers = { ...headers, '': '' };
	};

	const removeHeader = (key: string) => {
		const newHeaders = { ...headers };
		delete newHeaders[key];
		headers = newHeaders;
	};

	const updateHeaderKey = (oldKey: string, newKey: string) => {
		if (oldKey === newKey) return;

		const newHeaders = { ...headers };
		if (oldKey in newHeaders) {
			newHeaders[newKey] = newHeaders[oldKey];
			delete newHeaders[oldKey];
		}
		headers = newHeaders;
	};

	const updateHeaderValue = (key: string, value: string) => {
		headers = { ...headers, [key]: value };
	};

	// Check for OAuth completion by polling server status using the server ID
	const checkForOAuthCompletion = async () => {
		if (!serverId) {
			console.error('No server ID available for completion check');
			connectionResult = {
				success: false,
				error: 'No server ID available to check completion'
			};
			return;
		}

		try {
			// Poll for OAuth completion using server ID

			let attempts = 0;
			const maxAttempts = 10; // Poll for up to 10 seconds

			const pollForCompletion = async () => {
				attempts++;
				// Attempt count

				try {
					// Check OAuth completion using the server ID
					const response = await fetch(`/api/v1/mcp-servers/oauth/check-completion/${serverId}`, {
						headers: {
							Authorization: `Bearer ${localStorage.token}`
						}
					});

					if (response.ok) {
						const statusResult = await response.json();
						// OAuth completed

						// Update serverId to the final permanent one
						serverId = statusResult.server_id;

						// Cleanup OAuth state from Redis now that we have the final server ID
						if (oauthStateToken) {
							try {
								await fetch(`/api/v1/mcp-servers/oauth/cleanup/${oauthStateToken}`, {
									method: 'DELETE',
									headers: {
										Authorization: `Bearer ${localStorage.token}`
									}
								});
							} catch (cleanupError) {
								// Cleanup error is non-fatal
							}
						}

						// Dispatch event to parent with the final server ID (draft/edit mode)
						dispatch('serverDraft', { serverId: statusResult.server_id });

						// Test the connection with authentication
						await testMCPConnectionWithAuth();
						return; // Success!
					} else if (statusResult.error) {
						// Error during completion check
						// Continue polling unless it's a fatal error
						if (statusResult.error.includes('not found') || statusResult.error.includes('expired')) {
							connectionResult = {
								success: false,
								error: `OAuth state expired or invalid: ${statusResult.error}`
							};
							return;
						}
						// For other errors, continue polling
					} else {
						// Not yet completed
					}
				} catch (error) {
					console.error('Error during OAuth completion check:', error);
					if (attempts < maxAttempts) {
						setTimeout(pollForCompletion, 1000);
					} else {
						connectionResult = {
							success: false,
							error: `OAuth completion check failed: ${error instanceof Error ? error.message : String(error)}`
						};
					}
				}
			};

			// Start polling
			pollForCompletion();
		} catch (error) {
			console.error('Error in checkForOAuthCompletion:', error);
			connectionResult = {
				success: false,
				error: `Failed to check OAuth completion: ${error instanceof Error ? error.message : String(error)}`
			};
		}
	};
</script>

<div class="space-y-4">
	<div class="flex items-center justify-between">
		<h4 class="font-medium text-gray-900 dark:text-gray-100">Authentication</h4>
	</div>

	<!-- Simple Connect Button -->
	<div class="space-y-4">
		<div class="text-sm text-gray-600 dark:text-gray-400">
			Click Connect to test the MCP server connection and discover available tools. OAuth will be
			configured automatically if required.
		</div>

		<button
			on:click={handleConnect}
			disabled={connecting || !mcpServerUrl.trim()}
			class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors duration-200"
		>
			{#if connecting}
				<span class="loading loading-spinner loading-xs"></span>
				Connecting...
			{:else}
				🔗 Connect
			{/if}
		</button>

		<!-- Connection Results -->
		{#if connectionResult}
			<div
				class="mt-4 p-3 rounded-lg {connectionResult.success
					? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
					: connectionResult.requiresAuth
						? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
						: 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'}"
			>
				{#if connectionResult.success}
					<div class="text-sm text-green-800 dark:text-green-200">
						<div class="font-medium mb-2">✅ Connected Successfully!</div>
						<div class="text-xs text-green-700 dark:text-green-300">
							{connectionResult.message || 'You can now use this MCP server.'}
						</div>
						{#if connectionResult.tools && connectionResult.tools.length > 0}
							<div class="mt-2 text-xs text-green-600 dark:text-green-400">
								<div class="font-medium">Available Tools:</div>
								<div class="mt-1 space-y-1">
									{#each connectionResult.tools.slice(0, 5) as tool}
										<div class="flex items-center space-x-2">
											<span class="w-1 h-1 bg-green-500 rounded-full"></span>
											<span class="font-mono text-xs">{tool.name}</span>
											{#if tool.description}
												<span class="text-gray-500"
													>- {tool.description.slice(0, 50)}{tool.description.length > 50
														? '...'
														: ''}</span
												>
											{/if}
										</div>
									{/each}
									{#if connectionResult.tools.length > 5}
										<div class="text-gray-500 text-xs">
											...and {connectionResult.tools.length - 5} more
										</div>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				{:else if connectionResult.requiresAuth}
					<!-- Authentication Required -->
					{#if connectionResult.authType === 'oauth' && connectionResult.oauthAvailable}
						<div class="text-sm text-blue-800 dark:text-blue-200">
							<div class="font-medium mb-2">🔐 OAuth Authentication Available</div>
							<div class="text-xs text-blue-700 dark:text-blue-300 mb-3">
								{connectionResult.message || 'This MCP server supports OAuth authentication.'}
							</div>

							{#if connectionResult.oauthMetadata}
								<div class="text-xs text-blue-600 dark:text-blue-400 mb-3">
									<div class="font-medium">OAuth Configuration Discovered:</div>
									<div class="mt-1 space-y-1 font-mono">
										<div>• Issuer: {connectionResult.oauthMetadata.issuer}</div>
										<div>
											• PKCE: {connectionResult.oauthMetadata.code_challenge_methods_supported?.includes(
												'S256'
											)
												? 'Supported'
												: 'Not supported'}
										</div>
										<div>
											• DCR: {connectionResult.oauthMetadata.registration_endpoint
												? 'Available'
												: 'Not available'}
										</div>
									</div>
								</div>
							{/if}

							<div class="flex items-center space-x-2 mt-3">
								<button
									on:click={startOAuthFlow}
									class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
									disabled={connecting}
								>
									🚀 Start OAuth Authentication
								</button>
								<span class="text-xs text-blue-600 dark:text-blue-400">
									{!serverId
										? 'Will create server and start OAuth flow'
										: 'Click to authenticate with OAuth'}
								</span>
							</div>
						</div>
					{:else}
						<div class="text-sm text-blue-800 dark:text-blue-200">
							<div class="font-medium mb-2">🔑 Authentication Required</div>
							<div class="text-xs text-blue-700 dark:text-blue-300 mb-3">
								{connectionResult.message || 'This MCP server requires authentication headers.'}
							</div>

							<div class="text-xs text-blue-600 dark:text-blue-400 mb-3">
								<div class="font-medium">Next Steps:</div>
								<div class="mt-1 space-y-1">
									<div>• Add authentication headers in Advanced Configuration</div>
									<div>• Common headers: Authorization, X-API-Key, X-Auth-Token</div>
									<div>• Example: Authorization → Bearer your_token_here</div>
								</div>
							</div>

							<div class="text-xs text-blue-600 dark:text-blue-400">
								💡 Advanced Configuration is now expanded below
							</div>
						</div>
					{/if}
				{:else}
					<div
						class="text-sm {connectionResult.requiresManualConfig
							? 'text-orange-800 dark:text-orange-200'
							: 'text-red-800 dark:text-red-200'}"
					>
						<div class="font-medium mb-1">
							{connectionResult.requiresManualConfig
								? '⚙️ Manual Configuration Required'
								: '❌ Connection Failed'}
						</div>
						<div
							class="text-xs {connectionResult.requiresManualConfig
								? 'text-orange-700 dark:text-orange-300'
								: 'text-red-700 dark:text-red-300'} mb-2 whitespace-pre-line"
						>
							{connectionResult.error}
						</div>

						{#if connectionResult.requiresManualConfig}
							<div
								class="text-xs {connectionResult.requiresManualConfig
									? 'text-orange-600 dark:text-orange-400'
									: 'text-red-600 dark:text-red-400'}"
							>
								💡 You can configure OAuth manually in Advanced Configuration (now expanded), or use
								Custom Authentication Headers above
							</div>
						{:else if connectionResult.error && connectionResult.error.includes('404')}
							<div class="text-xs text-red-600 dark:text-red-400">
								💡 Please verify the MCP server URL is correct
							</div>
						{:else if connectionResult.error && connectionResult.error.includes('500')}
							<div class="text-xs text-red-600 dark:text-red-400">
								💡 Server error - please try again later or contact the server administrator
							</div>
						{:else}
							<div class="text-xs text-red-600 dark:text-red-400">
								💡 Check your network connection and server URL, or try adding authentication
								headers below
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Custom Headers Section (Always Visible) -->
	<div class="space-y-3 bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
		<div class="flex items-center justify-between">
			<div>
				<h5 class="font-medium text-sm text-gray-800 dark:text-gray-200">
					Custom Authentication Headers
				</h5>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Add custom headers for authentication (e.g., API keys, Bearer tokens)
				</div>
			</div>
			<button
				type="button"
				class="text-xs px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
				on:click={addHeader}
			>
				+ Add Header
			</button>
		</div>

		{#if Object.keys(headers || {}).length === 0}
			<div
				class="text-xs text-gray-400 dark:text-gray-500 italic p-3 border border-dashed border-gray-300 dark:border-gray-600 rounded"
			>
				No custom headers configured. Click "Add Header" to add authentication headers like
				Authorization, X-API-Key, etc.
			</div>
		{:else}
			<div class="space-y-2">
				{#each Object.entries(headers || {}) as [key, value], index}
					<div class="flex space-x-2 items-center">
						<input
							type="text"
							placeholder="Header name (e.g., Authorization)"
							value={key}
							on:change={(e) => updateHeaderKey(key, e.currentTarget.value)}
							class="flex-1 px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
						/>
						<input
							type="text"
							placeholder="Header value (e.g., Bearer token123)"
							{value}
							on:change={(e) => updateHeaderValue(key, e.currentTarget.value)}
							class="flex-1 px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
						/>
						<button
							type="button"
							class="text-red-500 hover:text-red-700 p-1"
							on:click={() => removeHeader(key)}
							title="Remove header"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
								/>
							</svg>
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Advanced Configuration (Collapsible) -->
	<div class="border-t pt-4">
		<button
			on:click={() => (showAdvanced = !showAdvanced)}
			class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
		>
			<span class="transform transition-transform {showAdvanced ? 'rotate-90' : ''}"
				>{showAdvanced ? '▼' : '▶'}</span
			>
			<span>⚙️ Advanced Configuration</span>
		</button>

		{#if showAdvanced}
			<div class="mt-4 space-y-4 pl-4 border-l-2 border-gray-200 dark:border-gray-700">
				<!-- Configuration Method Selection -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						OAuth Configuration
					</label>
					<div class="space-y-2">
						<label class="flex items-center space-x-2">
							<input type="radio" bind:group={configMethod} value="auto" class="radio radio-sm" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Automatic (Recommended)</span>
						</label>
						<label class="flex items-center space-x-2">
							<input type="radio" bind:group={configMethod} value="manual" class="radio radio-sm" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Manual Configuration</span>
						</label>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						{configMethod === 'auto'
							? 'OAuth will be discovered and configured automatically when you click Connect'
							: 'Manually configure OAuth endpoints and credentials'}
					</div>
				</div>

				<!-- Manual Configuration Fields -->
				{#if configMethod === 'manual'}
					<div class="space-y-3">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Issuer URL
							</label>
							<input
								type="url"
								bind:value={issuerUrl}
								placeholder="https://auth.example.com"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
							/>
						</div>

						{#if configMethod === 'manual'}
							<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
								<div>
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
										Authorize URL
									</label>
									<input
										type="url"
										bind:value={authorizeUrl}
										placeholder="https://auth.example.com/oauth/authorize"
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
									/>
								</div>

								<div>
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
										Token URL
									</label>
									<input
										type="url"
										bind:value={tokenUrl}
										placeholder="https://auth.example.com/oauth/token"
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
									/>
								</div>

								<div>
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
										Client ID
									</label>
									<input
										type="text"
										bind:value={clientId}
										placeholder="your-client-id"
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
									/>
								</div>

								<div>
									<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
										Client Secret
									</label>
									<input
										type="password"
										bind:value={clientSecret}
										placeholder="your-client-secret"
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
									/>
								</div>
							</div>
						{/if}
					</div>
				{/if}

				<!-- OAuth Scopes -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						OAuth Scopes
					</label>
					<input
						type="text"
						bind:value={scopes}
						placeholder="openid email profile groups"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
					/>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Space-separated list of OAuth scopes to request
					</div>
				</div>

				<!-- Advanced OAuth Options -->
				<div class="space-y-3">
					<h5 class="font-medium text-sm text-gray-800 dark:text-gray-200">
						Advanced OAuth Options
					</h5>

					<label class="flex items-center space-x-2">
						<input type="checkbox" bind:checked={usePkce} class="checkbox checkbox-sm" />
						<span class="text-sm text-gray-700 dark:text-gray-300"
							>Use PKCE (Proof Key for Code Exchange)</span
						>
					</label>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Audience
							</label>
							<input
								type="text"
								bind:value={audience}
								placeholder="https://api.example.com"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
							/>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Resource (Azure AD: use your application Client ID)
							</label>
							<input
								type="text"
								bind:value={resource}
								placeholder="your-application-client-id"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
							/>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								For Azure AD, use your application's Client ID to get tokens with group claims
							</div>
						</div>
					</div>
				</div>

				<div class="space-y-2">
					<div class="text-xs text-gray-500 dark:text-gray-400">
						Save these OAuth settings temporarily (you still need to click "Create" to create the
						server)
					</div>
					<button
						on:click={saveAdvancedConfig}
						class="px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors duration-200"
					>
						💾 Save OAuth Settings (Draft)
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
