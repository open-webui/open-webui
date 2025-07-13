<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { copyToClipboard } from '$lib/utils';
	
	import {
		getSCIMConfig,
		updateSCIMConfig,
		generateSCIMToken,
		revokeSCIMToken,
		getSCIMStats,
		testSCIMConnection,
		type SCIMConfig,
		type SCIMStats
	} from '$lib/apis/scim';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	
	const i18n = getContext('i18n');

	export let saveHandler: () => void;
	
	let loading = false;
	let testingConnection = false;
	let generatingToken = false;
	
	let scimEnabled = false;
	let scimToken = '';
	let scimTokenCreatedAt = '';
	let scimTokenExpiresAt = '';
	let showToken = false;
	let tokenExpiry = 'never'; // 'never', '30days', '90days', '1year'
	
	let scimStats: SCIMStats | null = null;
	let scimBaseUrl = '';

	// Generate SCIM base URL
	// In production, the frontend and backend are served from the same origin
	// In development, we need to show the backend URL
	$: {
		if (import.meta.env.DEV) {
			// Development mode - backend is on port 8080
			scimBaseUrl = `http://localhost:8080/api/v1/scim/v2`;
		} else {
			// Production mode - same origin
			scimBaseUrl = `${window.location.origin}/api/v1/scim/v2`;
		}
	}

	const formatDate = (dateString: string) => {
		if (!dateString) return 'N/A';
		return new Date(dateString).toLocaleString();
	};

	const loadSCIMConfig = async () => {
		loading = true;
		try {
			const config = await getSCIMConfig(localStorage.token);
			console.log('Loaded SCIM config:', config);
			scimEnabled = config.enabled || false;
			scimToken = config.token || '';
			scimTokenCreatedAt = config.token_created_at || '';
			scimTokenExpiresAt = config.token_expires_at || '';
			
			if (scimEnabled && scimToken) {
				try {
					scimStats = await getSCIMStats(localStorage.token);
				} catch (statsError) {
					console.error('Error loading SCIM stats:', statsError);
					// Don't fail the whole load if stats fail
				}
			}
		} catch (error) {
			console.error('Error loading SCIM config:', error);
			toast.error($i18n.t('Failed to load SCIM configuration'));
		} finally {
			loading = false;
		}
	};

	const handleToggleSCIM = async () => {
		loading = true;
		try {
			console.log('Updating SCIM config, enabled:', scimEnabled);
			const config = await updateSCIMConfig(localStorage.token, { enabled: scimEnabled });
			console.log('SCIM config updated:', config);
			toast.success($i18n.t('SCIM configuration updated'));
			
			if (scimEnabled && !scimToken) {
				toast.info($i18n.t('Please generate a SCIM token to enable provisioning'));
			}
			
			// Reload config to ensure it's synced
			await loadSCIMConfig();
			
			saveHandler();
		} catch (error) {
			console.error('Error updating SCIM config:', error);
			toast.error($i18n.t('Failed to update SCIM configuration') + ': ' + (error.message || error));
			// Revert toggle
			scimEnabled = !scimEnabled;
		} finally {
			loading = false;
		}
	};

	const handleGenerateToken = async () => {
		generatingToken = true;
		try {
			let expiresIn = null;
			switch (tokenExpiry) {
				case '30days':
					expiresIn = 30 * 24 * 60 * 60; // 30 days in seconds
					break;
				case '90days':
					expiresIn = 90 * 24 * 60 * 60; // 90 days in seconds
					break;
				case '1year':
					expiresIn = 365 * 24 * 60 * 60; // 1 year in seconds
					break;
			}
			
			const tokenData = await generateSCIMToken(localStorage.token, expiresIn);
			scimToken = tokenData.token;
			scimTokenCreatedAt = tokenData.created_at;
			scimTokenExpiresAt = tokenData.expires_at || '';
			showToken = true;
			
			toast.success($i18n.t('SCIM token generated successfully'));
			toast.info($i18n.t('Make sure to copy this token now. You won\'t be able to see it again!'));
		} catch (error) {
			console.error('Error generating SCIM token:', error);
			toast.error($i18n.t('Failed to generate SCIM token'));
		} finally {
			generatingToken = false;
		}
	};

	const handleRevokeToken = async () => {
		if (!confirm($i18n.t('Are you sure you want to revoke the SCIM token? This will break any existing integrations.'))) {
			return;
		}
		
		loading = true;
		try {
			await revokeSCIMToken(localStorage.token);
			scimToken = '';
			scimTokenCreatedAt = '';
			scimTokenExpiresAt = '';
			showToken = false;
			
			toast.success($i18n.t('SCIM token revoked successfully'));
		} catch (error) {
			console.error('Error revoking SCIM token:', error);
			toast.error($i18n.t('Failed to revoke SCIM token'));
		} finally {
			loading = false;
		}
	};

	const handleTestConnection = async () => {
		testingConnection = true;
		try {
			const success = await testSCIMConnection(localStorage.token, scimToken);
			if (success) {
				toast.success($i18n.t('SCIM endpoint is accessible'));
			} else {
				toast.error($i18n.t('SCIM endpoint is not accessible'));
			}
		} catch (error) {
			console.error('Error testing SCIM connection:', error);
			toast.error($i18n.t('Failed to test SCIM connection'));
		} finally {
			testingConnection = false;
		}
	};

	const copyTokenToClipboard = () => {
		copyToClipboard(scimToken);
		toast.success($i18n.t('Token copied to clipboard'));
	};

	const copySCIMUrlToClipboard = () => {
		copyToClipboard(scimBaseUrl);
		toast.success($i18n.t('SCIM URL copied to clipboard'));
	};

	onMount(() => {
		loadSCIMConfig();
	});
</script>

<div class="flex flex-col gap-4 px-1 py-3 md:py-3">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<h3 class="text-lg font-semibold">{$i18n.t('SCIM 2.0 Integration')}</h3>
			<Badge type="info">Enterprise</Badge>
		</div>
		
		<Switch bind:state={scimEnabled} on:change={handleToggleSCIM} disabled={loading} />
	</div>

	<div class="text-sm text-gray-500 dark:text-gray-400">
		{$i18n.t('Enable SCIM 2.0 support for automated user and group provisioning from identity providers like Okta, Azure AD, and Google Workspace.')}
	</div>

	{#if scimEnabled}
		<div class="space-y-4 mt-4">
			<!-- Save Button -->
			<div class="flex justify-end">
				<button
					type="button"
					on:click={saveHandler}
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg"
				>
					{$i18n.t('Save')}
				</button>
			</div>
			
			<!-- SCIM Base URL -->
			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('SCIM Base URL')}</label>
				<div class="flex items-center gap-2">
					<input
						type="text"
						value={scimBaseUrl}
						readonly
						class="flex-1 px-3 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
					/>
					<button
						type="button"
						on:click={copySCIMUrlToClipboard}
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						title={$i18n.t('Copy URL')}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
						</svg>
					</button>
				</div>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{$i18n.t('Use this URL in your identity provider\'s SCIM configuration')}
				</p>
			</div>

			<!-- SCIM Token -->
			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('SCIM Bearer Token')}</label>
				
				{#if scimToken}
					<div class="space-y-2">
						<div class="flex items-center gap-2">
							<SensitiveInput
								bind:value={scimToken}
								bind:show={showToken}
								readonly
								placeholder={$i18n.t('Token hidden for security')}
							/>
							<button
								type="button"
								on:click={copyTokenToClipboard}
								class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								title={$i18n.t('Copy token')}
							>
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
								</svg>
							</button>
						</div>
						
						<div class="text-xs text-gray-500 dark:text-gray-400">
							<p>{$i18n.t('Created')}: {formatDate(scimTokenCreatedAt)}</p>
							{#if scimTokenExpiresAt}
								<p>{$i18n.t('Expires')}: {formatDate(scimTokenExpiresAt)}</p>
							{:else}
								<p>{$i18n.t('Expires')}: {$i18n.t('Never')}</p>
							{/if}
						</div>
						
						<div class="flex gap-2">
							<button
								type="button"
								on:click={handleTestConnection}
								disabled={testingConnection}
								class="px-3 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-lg"
							>
								{#if testingConnection}
									<Spinner size="sm" />
								{:else}
									{$i18n.t('Test Connection')}
								{/if}
							</button>
							
							<button
								type="button"
								on:click={handleRevokeToken}
								disabled={loading}
								class="px-3 py-1.5 text-sm font-medium bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition rounded-lg"
							>
								{$i18n.t('Revoke Token')}
							</button>
						</div>
					</div>
				{:else}
					<div class="space-y-3">
						<div>
							<label class="block text-sm font-medium mb-1">{$i18n.t('Token Expiration')}</label>
							<select
								bind:value={tokenExpiry}
								class="w-full px-3 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800"
							>
								<option value="never">{$i18n.t('Never expire')}</option>
								<option value="30days">{$i18n.t('30 days')}</option>
								<option value="90days">{$i18n.t('90 days')}</option>
								<option value="1year">{$i18n.t('1 year')}</option>
							</select>
						</div>
						
						<button
							type="button"
							on:click={handleGenerateToken}
							disabled={generatingToken}
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg"
						>
							{#if generatingToken}
								<Spinner size="sm" />
							{:else}
								{$i18n.t('Generate Token')}
							{/if}
						</button>
					</div>
				{/if}
			</div>

			<!-- SCIM Statistics -->
			{#if scimStats}
				<div class="border-t pt-4">
					<h4 class="text-sm font-medium mb-2">{$i18n.t('SCIM Statistics')}</h4>
					<div class="grid grid-cols-2 gap-4 text-sm">
						<div>
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Total Users')}:</span>
							<span class="ml-2 font-medium">{scimStats.total_users}</span>
						</div>
						<div>
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Total Groups')}:</span>
							<span class="ml-2 font-medium">{scimStats.total_groups}</span>
						</div>
						{#if scimStats.last_sync}
							<div class="col-span-2">
								<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Last Sync')}:</span>
								<span class="ml-2 font-medium">{formatDate(scimStats.last_sync)}</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}

		</div>
	{/if}
</div>