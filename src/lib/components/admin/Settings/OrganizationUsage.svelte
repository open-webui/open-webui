<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { config, user } from '$lib/stores';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext('i18n');

	// State management
	let loading = true;
	let syncing = false;
	let showSettings = false;
	let showUserMapping = false;
	let activeTab = 'overview';

	// Organization settings
	let orgSettings = {
		openrouter_org_id: '',
		openrouter_api_key: '',
		sync_enabled: true,
		sync_interval_hours: 1
	};

	// Usage data
	let usageStats = {
		total_tokens: 0,
		total_cost: 0.0,
		total_requests: 0,
		models_used: 0,
		date_range: 'All time'
	};

	let userUsage = [];
	let modelUsage = [];
	let dailyUsage = [];
	let syncStatus = {
		is_running: false,
		sync_enabled: false,
		last_sync_at: null,
		last_sync_human: null
	};

	// User mappings
	let userMappings = [];
	let newUserMapping = {
		owui_user_id: '',
		openrouter_user_id: ''
	};

	// Date range for filtering
	let dateRange = {
		start_date: '',
		end_date: ''
	};

	// API functions
	async function fetchOrganizationSettings() {
		try {
			const response = await fetch('/api/v1/organization/settings', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});
			
			if (response.ok) {
				const data = await response.json();
				orgSettings = { ...orgSettings, ...data };
			}
		} catch (error) {
			console.error('Failed to fetch organization settings:', error);
		}
	}

	async function updateOrganizationSettings() {
		try {
			const response = await fetch('/api/v1/organization/settings', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(orgSettings)
			});

			if (response.ok) {
				toast.success($i18n.t('Organization settings updated successfully'));
				showSettings = false;
				await fetchSyncStatus();
			} else {
				toast.error($i18n.t('Failed to update organization settings'));
			}
		} catch (error) {
			console.error('Failed to update organization settings:', error);
			toast.error($i18n.t('Failed to update organization settings'));
		}
	}

	async function fetchUsageStats() {
		try {
			const response = await fetch('/api/v1/organization/usage/stats', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(dateRange)
			});

			if (response.ok) {
				const data = await response.json();
				if (data.success) {
					usageStats = data.stats;
				}
			}
		} catch (error) {
			console.error('Failed to fetch usage stats:', error);
		}
	}

	async function fetchUserUsage() {
		try {
			const response = await fetch('/api/v1/organization/usage/by-user', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(dateRange)
			});

			if (response.ok) {
				const data = await response.json();
				userUsage = data.users || [];
			}
		} catch (error) {
			console.error('Failed to fetch user usage:', error);
		}
	}

	async function fetchModelUsage() {
		try {
			const response = await fetch('/api/v1/organization/usage/by-model', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(dateRange)
			});

			if (response.ok) {
				const data = await response.json();
				modelUsage = data.models || [];
			}
		} catch (error) {
			console.error('Failed to fetch model usage:', error);
		}
	}

	async function fetchSyncStatus() {
		try {
			const response = await fetch('/api/v1/organization/sync/status', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				syncStatus = await response.json();
			}
		} catch (error) {
			console.error('Failed to fetch sync status:', error);
		}
	}

	async function triggerManualSync() {
		syncing = true;
		try {
			const response = await fetch('/api/v1/organization/sync/manual', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const result = await response.json();
				if (result.success) {
					toast.success($i18n.t('Sync completed successfully'));
					await refreshData();
				} else {
					toast.error(result.message || $i18n.t('Sync failed'));
				}
			} else {
				toast.error($i18n.t('Failed to trigger sync'));
			}
		} catch (error) {
			console.error('Failed to trigger manual sync:', error);
			toast.error($i18n.t('Failed to trigger sync'));
		} finally {
			syncing = false;
		}
	}

	async function fetchUserMappings() {
		try {
			const response = await fetch('/api/v1/organization/user-mappings', {
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (response.ok) {
				const data = await response.json();
				userMappings = data.mappings || [];
			}
		} catch (error) {
			console.error('Failed to fetch user mappings:', error);
		}
	}

	async function createUserMapping() {
		try {
			const response = await fetch('/api/v1/organization/user-mappings', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(newUserMapping)
			});

			if (response.ok) {
				toast.success($i18n.t('User mapping created successfully'));
				newUserMapping = { owui_user_id: '', openrouter_user_id: '' };
				await fetchUserMappings();
				showUserMapping = false;
			} else {
				toast.error($i18n.t('Failed to create user mapping'));
			}
		} catch (error) {
			console.error('Failed to create user mapping:', error);
			toast.error($i18n.t('Failed to create user mapping'));
		}
	}

	async function refreshData() {
		await Promise.all([
			fetchUsageStats(),
			fetchUserUsage(),
			fetchModelUsage(),
			fetchSyncStatus()
		]);
	}

	// Set default date range to last 30 days
	onMount(async () => {
		const now = new Date();
		const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
		
		dateRange.end_date = now.toISOString().split('T')[0];
		dateRange.start_date = thirtyDaysAgo.toISOString().split('T')[0];

		await Promise.all([
			fetchOrganizationSettings(),
			fetchUserMappings(),
			refreshData()
		]);
		
		loading = false;
	});

	// Format numbers for display
	function formatNumber(num) {
		return new Intl.NumberFormat().format(num);
	}

	function formatCurrency(amount) {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD'
		}).format(amount);
	}
</script>

<div class="flex flex-col h-full text-sm">
	<!-- Header with tabs -->
	<div class="mb-6">
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-lg font-semibold">{$i18n.t('Organization Usage Tracking')}</h2>
			<div class="flex gap-2">
				<button
					class="px-3 py-1.5 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-lg transition"
					on:click={() => showSettings = true}
				>
					{$i18n.t('Settings')}
				</button>
				<button
					class="px-3 py-1.5 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-lg transition"
					on:click={() => showUserMapping = true}
				>
					{$i18n.t('User Mappings')}
				</button>
				<button
					class="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white border border-blue-600 rounded-lg transition flex items-center gap-2 {syncing ? 'cursor-not-allowed opacity-50' : ''}"
					on:click={triggerManualSync}
					disabled={syncing}
				>
					{syncing ? $i18n.t('Syncing...') : $i18n.t('Sync Now')}
					{#if syncing}
						<Spinner />
					{/if}
				</button>
			</div>
		</div>

		<!-- Tab navigation -->
		<div class="flex border-b border-gray-200 dark:border-gray-700">
			<button
				class="px-4 py-2 text-sm font-medium border-b-2 {activeTab === 'overview' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
				on:click={() => activeTab = 'overview'}
			>
				{$i18n.t('Overview')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium border-b-2 {activeTab === 'users' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
				on:click={() => activeTab = 'users'}
			>
				{$i18n.t('By User')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium border-b-2 {activeTab === 'models' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
				on:click={() => activeTab = 'models'}
			>
				{$i18n.t('By Model')}
			</button>
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center items-center h-64">
			<Spinner />
		</div>
	{:else}
		<!-- Date range selector -->
		<div class="mb-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
			<div class="flex items-center gap-4">
				<div class="flex-1">
					<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Start Date')}
					</label>
					<input
						type="date"
						bind:value={dateRange.start_date}
						on:change={refreshData}
						class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
					/>
				</div>
				<div class="flex-1">
					<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('End Date')}
					</label>
					<input
						type="date"
						bind:value={dateRange.end_date}
						on:change={refreshData}
						class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
					/>
				</div>
				<div class="flex-1">
					<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Last Sync')}
					</label>
					<div class="text-sm text-gray-600 dark:text-gray-400">
						{syncStatus.last_sync_human || $i18n.t('Never')}
					</div>
				</div>
			</div>
		</div>

		<!-- Overview tab -->
		{#if activeTab === 'overview'}
			<!-- Usage statistics cards -->
			<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
				<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
						{formatNumber(usageStats.total_tokens)}
					</div>
					<div class="text-xs text-blue-600 dark:text-blue-400">
						{$i18n.t('Total Tokens')}
					</div>
				</div>
				<div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
					<div class="text-2xl font-bold text-green-600 dark:text-green-400">
						{formatCurrency(usageStats.total_cost)}
					</div>
					<div class="text-xs text-green-600 dark:text-green-400">
						{$i18n.t('Total Cost')}
					</div>
				</div>
				<div class="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
					<div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
						{formatNumber(usageStats.total_requests)}
					</div>
					<div class="text-xs text-purple-600 dark:text-purple-400">
						{$i18n.t('Total Requests')}
					</div>
				</div>
				<div class="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
					<div class="text-2xl font-bold text-orange-600 dark:text-orange-400">
						{usageStats.models_used}
					</div>
					<div class="text-xs text-orange-600 dark:text-orange-400">
						{$i18n.t('Models Used')}
					</div>
				</div>
			</div>
		{/if}

		<!-- Users tab -->
		{#if activeTab === 'users'}
			<div class="space-y-4">
				{#each userUsage as user}
					<div class="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
						<div class="flex items-center justify-between mb-3">
							<div class="font-medium">{user.user_name}</div>
							<div class="text-sm text-gray-500">{user.user_id}</div>
						</div>
						<div class="grid grid-cols-3 gap-4 text-sm">
							<div>
								<div class="text-gray-500 text-xs">{$i18n.t('Tokens')}</div>
								<div class="font-medium">{formatNumber(user.total_tokens)}</div>
							</div>
							<div>
								<div class="text-gray-500 text-xs">{$i18n.t('Cost')}</div>
								<div class="font-medium">{formatCurrency(user.total_cost)}</div>
							</div>
							<div>
								<div class="text-gray-500 text-xs">{$i18n.t('Requests')}</div>
								<div class="font-medium">{formatNumber(user.total_requests)}</div>
							</div>
						</div>
						{#if user.models && user.models.length > 0}
							<div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
								<div class="text-xs text-gray-500 mb-2">{$i18n.t('Models Used')}</div>
								<div class="flex flex-wrap gap-2">
									{#each user.models as model}
										<span class="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 rounded">
											{model.model_name}
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		<!-- Models tab -->
		{#if activeTab === 'models'}
			<div class="space-y-4">
				{#each modelUsage as model}
					<div class="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
						<div class="flex items-center justify-between mb-3">
							<div class="font-medium">{model.model_name}</div>
						</div>
						<div class="grid grid-cols-3 gap-4 text-sm">
							<div>
								<div class="text-gray-500 text-xs">{$i18n.t('Tokens')}</div>
								<div class="font-medium">{formatNumber(model.total_tokens)}</div>
							</div>
							<div>
								<div class="text-gray-500 text-xs">{$i18n.t('Cost')}</div>
								<div class="font-medium">{formatCurrency(model.total_cost)}</div>
							</div>
							<div>
								<div class="text-gray-500 text-xs">{$i18n.t('Requests')}</div>
								<div class="font-medium">{formatNumber(model.total_requests)}</div>
							</div>
						</div>
						{#if model.users && model.users.length > 0}
							<div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
								<div class="text-xs text-gray-500 mb-2">{$i18n.t('Users')}</div>
								<div class="flex flex-wrap gap-2">
									{#each model.users as user}
										<span class="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 rounded">
											{user.user_name}
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<!-- Settings Modal -->
{#if showSettings}
	<Modal on:close={() => showSettings = false}>
		<div class="p-6">
			<h3 class="text-lg font-semibold mb-4">{$i18n.t('Organization Settings')}</h3>
			
			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium mb-2">
						{$i18n.t('OpenRouter Organization ID')}
					</label>
					<input
						type="text"
						bind:value={orgSettings.openrouter_org_id}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2">
						{$i18n.t('OpenRouter API Key')}
					</label>
					<input
						type="password"
						bind:value={orgSettings.openrouter_api_key}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
						placeholder={orgSettings.openrouter_api_key === '***configured***' ? '***configured***' : ''}
					/>
				</div>

				<div>
					<label class="flex items-center">
						<input
							type="checkbox"
							bind:checked={orgSettings.sync_enabled}
							class="mr-2"
						/>
						{$i18n.t('Enable automatic sync')}
					</label>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2">
						{$i18n.t('Sync interval (hours)')}
					</label>
					<input
						type="number"
						min="1"
						max="24"
						bind:value={orgSettings.sync_interval_hours}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
					/>
				</div>
			</div>

			<div class="flex justify-end gap-2 mt-6">
				<button
					class="px-3 py-1.5 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-lg transition"
					on:click={() => showSettings = false}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white border border-blue-600 rounded-lg transition"
					on:click={updateOrganizationSettings}
				>
					{$i18n.t('Save')}
				</button>
			</div>
		</div>
	</Modal>
{/if}

<!-- User Mapping Modal -->
{#if showUserMapping}
	<Modal on:close={() => showUserMapping = false}>
		<div class="p-6">
			<h3 class="text-lg font-semibold mb-4">{$i18n.t('User Mappings')}</h3>
			
			<!-- Add new mapping -->
			<div class="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<h4 class="font-medium mb-3">{$i18n.t('Add New Mapping')}</h4>
				<div class="space-y-3">
					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('Open WebUI User ID')}
						</label>
						<input
							type="text"
							bind:value={newUserMapping.owui_user_id}
							class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('OpenRouter User ID')}
						</label>
						<input
							type="text"
							bind:value={newUserMapping.openrouter_user_id}
							class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
						/>
					</div>
					<button
						class="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white border border-blue-600 rounded-lg transition"
						on:click={createUserMapping}
					>
						{$i18n.t('Add Mapping')}
					</button>
				</div>
			</div>

			<!-- Existing mappings -->
			<div class="space-y-2">
				<h4 class="font-medium">{$i18n.t('Existing Mappings')}</h4>
				{#each userMappings as mapping}
					<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
						<div>
							<div class="text-sm font-medium">{mapping.owui_user_id}</div>
							<div class="text-xs text-gray-500">→ {mapping.openrouter_user_id}</div>
						</div>
						<button
							class="px-2 py-1 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-md transition"
							on:click={() => {
								// TODO: Implement deactivate mapping
							}}
						>
							{$i18n.t('Remove')}
						</button>
					</div>
				{/each}
			</div>

			<div class="flex justify-end mt-6">
				<button
					class="px-3 py-1.5 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-lg transition"
					on:click={() => showUserMapping = false}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		</div>
	</Modal>
{/if}