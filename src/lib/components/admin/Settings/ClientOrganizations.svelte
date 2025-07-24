<script>
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getOpenRouterClientSettings, updateOpenRouterClientSettings, getClientOrganizations, createClientOrganization, updateClientOrganization, deactivateClientOrganization, getUserMappings, createUserMapping, deactivateUserMapping } from '$lib/apis/organizations';
	import Modal from '$lib/components/common/Modal.svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let loading = false;
	let globalSettings = {
		openrouter_provisioning_key: '',
		default_markup_rate: 1.3,
		billing_currency: 'USD'
	};

	let clients = [];
	let userMappings = [];
	let selectedClient = null;

	// Modal states
	let showGlobalSettings = false;
	let showCreateClient = false;
	let showEditClient = false;
	let showUserMapping = false;

	// Form data
	let newClient = {
		name: '',
		markup_rate: 1.3,
		monthly_limit: null,
		billing_email: ''
	};

	let editingClient = {
		id: '',
		name: '',
		markup_rate: 1.3,
		monthly_limit: null,
		billing_email: ''
	};

	let newUserMapping = {
		user_id: '',
		client_org_id: '',
		openrouter_user_id: ''
	};

	onMount(async () => {
		await loadGlobalSettings();
		await loadClients();
		await loadUserMappings();
	});

	const loadGlobalSettings = async () => {
		try {
			const settings = await getOpenRouterClientSettings($user.token);
			if (settings) {
				globalSettings = settings;
			}
		} catch (error) {
			console.error('Failed to load global settings:', error);
		}
	};

	const loadClients = async () => {
		try {
			loading = true;
			clients = await getClientOrganizations($user.token);
		} catch (error) {
			console.error('Failed to load clients:', error);
			toast.error($i18n.t('Failed to load client organizations'));
		} finally {
			loading = false;
		}
	};

	const loadUserMappings = async () => {
		try {
			userMappings = await getUserMappings($user.token);
		} catch (error) {
			console.error('Failed to load user mappings:', error);
		}
	};

	const handleSaveGlobalSettings = async () => {
		try {
			await updateOpenRouterClientSettings($user.token, globalSettings);
			toast.success($i18n.t('Global settings updated successfully'));
			showGlobalSettings = false;
		} catch (error) {
			console.error('Failed to update global settings:', error);
			toast.error($i18n.t('Failed to update global settings'));
		}
	};

	const handleCreateClient = async () => {
		try {
			const result = await createClientOrganization($user.token, newClient);
			if (result.success) {
				toast.success($i18n.t('Client organization created successfully'));
				await loadClients();
				showCreateClient = false;
				resetNewClient();
			} else {
				toast.error(result.message || $i18n.t('Failed to create client organization'));
			}
		} catch (error) {
			console.error('Failed to create client:', error);
			toast.error($i18n.t('Failed to create client organization'));
		}
	};

	const handleEditClient = (client) => {
		editingClient = {
			id: client.id,
			name: client.name,
			markup_rate: client.markup_rate,
			monthly_limit: client.monthly_limit,
			billing_email: client.billing_email
		};
		showEditClient = true;
	};

	const handleUpdateClient = async () => {
		try {
			const updates = {
				name: editingClient.name,
				markup_rate: editingClient.markup_rate,
				monthly_limit: editingClient.monthly_limit,
				billing_email: editingClient.billing_email
			};
			
			const result = await updateClientOrganization($user.token, editingClient.id, updates);
			if (result.success) {
				toast.success($i18n.t('Client organization updated successfully'));
				await loadClients();
				showEditClient = false;
			} else {
				toast.error(result.message || $i18n.t('Failed to update client organization'));
			}
		} catch (error) {
			console.error('Failed to update client:', error);
			toast.error($i18n.t('Failed to update client organization'));
		}
	};

	const handleDeactivateClient = async (clientId) => {
		if (!confirm($i18n.t('Are you sure you want to deactivate this client organization?'))) {
			return;
		}

		try {
			const result = await deactivateClientOrganization($user.token, clientId);
			if (result.success) {
				toast.success($i18n.t('Client organization deactivated successfully'));
				await loadClients();
			} else {
				toast.error(result.message || $i18n.t('Failed to deactivate client organization'));
			}
		} catch (error) {
			console.error('Failed to deactivate client:', error);
			toast.error($i18n.t('Failed to deactivate client organization'));
		}
	};

	const handleCreateUserMapping = async () => {
		try {
			const result = await createUserMapping($user.token, newUserMapping);
			if (result.success) {
				toast.success($i18n.t('User mapping created successfully'));
				await loadUserMappings();
				showUserMapping = false;
				resetNewUserMapping();
			} else {
				toast.error(result.message || $i18n.t('Failed to create user mapping'));
			}
		} catch (error) {
			console.error('Failed to create user mapping:', error);
			toast.error($i18n.t('Failed to create user mapping'));
		}
	};

	const handleDeactivateUserMapping = async (userId) => {
		if (!confirm($i18n.t('Are you sure you want to deactivate this user mapping?'))) {
			return;
		}

		try {
			const result = await deactivateUserMapping($user.token, userId);
			if (result.success) {
				toast.success($i18n.t('User mapping deactivated successfully'));
				await loadUserMappings();
			} else {
				toast.error(result.message || $i18n.t('Failed to deactivate user mapping'));
			}
		} catch (error) {
			console.error('Failed to deactivate user mapping:', error);
			toast.error($i18n.t('Failed to deactivate user mapping'));
		}
	};

	const resetNewClient = () => {
		newClient = {
			name: '',
			markup_rate: 1.3,
			monthly_limit: null,
			billing_email: ''
		};
	};

	const resetNewUserMapping = () => {
		newUserMapping = {
			user_id: '',
			client_org_id: '',
			openrouter_user_id: ''
		};
	};

	const getClientName = (clientId) => {
		const client = clients.find(c => c.id === clientId);
		return client ? client.name : clientId;
	};
</script>

<div class="mb-6">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">{$i18n.t('Client Organization Management')}</h2>
		<div class="flex gap-2">
			<button
				class="px-3 py-1.5 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-lg transition"
				on:click={() => showGlobalSettings = true}
			>
				{$i18n.t('Global Settings')}
			</button>
			<button
				class="px-3 py-1.5 text-sm font-medium bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 border border-gray-300 dark:border-gray-600 rounded-lg transition"
				on:click={() => showUserMapping = true}
			>
				{$i18n.t('User Mappings')}
			</button>
			<button
				class="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
				on:click={() => showCreateClient = true}
			>
				{$i18n.t('Create Client')}
			</button>
		</div>
	</div>

	{#if !globalSettings.openrouter_provisioning_key}
		<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
			<div class="flex">
				<div class="flex-shrink-0">
					<svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="ml-3">
					<h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
						{$i18n.t('OpenRouter Provisioning Key Required')}
					</h3>
					<div class="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
						<p>{$i18n.t('You need to configure your OpenRouter provisioning key to create and manage client-specific API keys.')}</p>
					</div>
					<div class="mt-3">
						<button
							type="button"
							class="bg-yellow-50 dark:bg-yellow-900/50 px-2 py-1.5 rounded-md text-sm font-medium text-yellow-800 dark:text-yellow-200 hover:bg-yellow-100 dark:hover:bg-yellow-900/70"
							on:click={() => showGlobalSettings = true}
						>
							{$i18n.t('Configure Now')}
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Client Organizations Table -->
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium">{$i18n.t('Client Organizations')}</h3>
		</div>
		
		{#if loading}
			<div class="p-6 text-center">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white mx-auto"></div>
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Loading clients...')}</p>
			</div>
		{:else if clients.length === 0}
			<div class="p-6 text-center">
				<p class="text-gray-600 dark:text-gray-400">{$i18n.t('No client organizations found.')}</p>
			</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
					<thead class="bg-gray-50 dark:bg-gray-800">
						<tr>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								{$i18n.t('Client Name')}
							</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								{$i18n.t('Markup Rate')}
							</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								{$i18n.t('Monthly Limit')}
							</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								{$i18n.t('Status')}
							</th>
							<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								{$i18n.t('Actions')}
							</th>
						</tr>
					</thead>
					<tbody class="bg-white dark:bg-gray-850 divide-y divide-gray-200 dark:divide-gray-700">
						{#each clients as client}
							<tr>
								<td class="px-6 py-4 whitespace-nowrap">
									<div class="text-sm font-medium text-gray-900 dark:text-white">{client.name}</div>
									<div class="text-sm text-gray-500 dark:text-gray-400">{client.billing_email || 'No email'}</div>
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
									{client.markup_rate}x
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
									{client.monthly_limit ? `$${client.monthly_limit}` : 'No limit'}
								</td>
								<td class="px-6 py-4 whitespace-nowrap">
									<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {client.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}">
										{client.is_active ? $i18n.t('Active') : $i18n.t('Inactive')}
									</span>
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
									<button
										class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 mr-3"
										on:click={() => handleEditClient(client)}
									>
										{$i18n.t('Edit')}
									</button>
									{#if client.is_active}
										<button
											class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
											on:click={() => handleDeactivateClient(client.id)}
										>
											{$i18n.t('Deactivate')}
										</button>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>

<!-- Global Settings Modal -->
<Modal bind:show={showGlobalSettings}>
	<div slot="title">{$i18n.t('OpenRouter Global Settings')}</div>
	<div slot="content">
		<div class="space-y-4">
			<div>
				<label for="provisioning-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('OpenRouter Provisioning Key')}
				</label>
				<input
					id="provisioning-key"
					type="password"
					bind:value={globalSettings.openrouter_provisioning_key}
					placeholder={$i18n.t('Enter your OpenRouter provisioning key')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('This key is used to create and manage client-specific API keys')}
				</p>
			</div>
			
			<div>
				<label for="default-markup" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Default Markup Rate')}
				</label>
				<input
					id="default-markup"
					type="number"
					step="0.1"
					min="1.0"
					bind:value={globalSettings.default_markup_rate}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Default multiplier for client pricing (e.g., 1.3 = 30% markup)')}
				</p>
			</div>

			<div>
				<label for="billing-currency" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Billing Currency')}
				</label>
				<select
					id="billing-currency"
					bind:value={globalSettings.billing_currency}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				>
					<option value="USD">USD</option>
					<option value="EUR">EUR</option>
					<option value="PLN">PLN</option>
				</select>
			</div>
		</div>
	</div>
	<div slot="footer">
		<div class="flex justify-end space-x-2">
			<button
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
				on:click={() => showGlobalSettings = false}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
				on:click={handleSaveGlobalSettings}
			>
				{$i18n.t('Save Settings')}
			</button>
		</div>
	</div>
</Modal>

<!-- Create Client Modal -->
<Modal bind:show={showCreateClient}>
	<div slot="title">{$i18n.t('Create Client Organization')}</div>
	<div slot="content">
		<div class="space-y-4">
			<div>
				<label for="client-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Client Name')} *
				</label>
				<input
					id="client-name"
					type="text"
					bind:value={newClient.name}
					placeholder={$i18n.t('Enter client organization name')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
					required
				/>
			</div>

			<div>
				<label for="client-markup" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Markup Rate')}
				</label>
				<input
					id="client-markup"
					type="number"
					step="0.1"
					min="1.0"
					bind:value={newClient.markup_rate}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Pricing multiplier (e.g., 1.3 = 30% markup)')}
				</p>
			</div>

			<div>
				<label for="client-limit" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Monthly Limit (USD)')}
				</label>
				<input
					id="client-limit"
					type="number"
					step="0.01"
					min="0"
					bind:value={newClient.monthly_limit}
					placeholder={$i18n.t('Optional spending limit')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
			</div>

			<div>
				<label for="client-email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Billing Email')}
				</label>
				<input
					id="client-email"
					type="email"
					bind:value={newClient.billing_email}
					placeholder={$i18n.t('Optional billing contact email')}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
			</div>
		</div>
	</div>
	<div slot="footer">
		<div class="flex justify-end space-x-2">
			<button
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
				on:click={() => { showCreateClient = false; resetNewClient(); }}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
				on:click={handleCreateClient}
				disabled={!newClient.name.trim()}
			>
				{$i18n.t('Create Client')}
			</button>
		</div>
	</div>
</Modal>

<!-- Edit Client Modal -->
<Modal bind:show={showEditClient}>
	<div slot="title">{$i18n.t('Edit Client Organization')}</div>
	<div slot="content">
		<div class="space-y-4">
			<div>
				<label for="edit-client-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Client Name')} *
				</label>
				<input
					id="edit-client-name"
					type="text"
					bind:value={editingClient.name}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
					required
				/>
			</div>

			<div>
				<label for="edit-client-markup" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Markup Rate')}
				</label>
				<input
					id="edit-client-markup"
					type="number"
					step="0.1"
					min="1.0"
					bind:value={editingClient.markup_rate}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
			</div>

			<div>
				<label for="edit-client-limit" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Monthly Limit (USD)')}
				</label>
				<input
					id="edit-client-limit"
					type="number"
					step="0.01"
					min="0"
					bind:value={editingClient.monthly_limit}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
			</div>

			<div>
				<label for="edit-client-email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Billing Email')}
				</label>
				<input
					id="edit-client-email"
					type="email"
					bind:value={editingClient.billing_email}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
				/>
			</div>
		</div>
	</div>
	<div slot="footer">
		<div class="flex justify-end space-x-2">
			<button
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
				on:click={() => showEditClient = false}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
				on:click={handleUpdateClient}
				disabled={!editingClient.name.trim()}
			>
				{$i18n.t('Update Client')}
			</button>
		</div>
	</div>
</Modal>

<!-- User Mapping Modal -->
<Modal bind:show={showUserMapping}>
	<div slot="title">{$i18n.t('User-Client Mappings')}</div>
	<div slot="content">
		<div class="space-y-6">
			<!-- Create new mapping form -->
			<div class="border-b border-gray-200 dark:border-gray-700 pb-4">
				<h4 class="text-md font-medium mb-3">{$i18n.t('Create New Mapping')}</h4>
				<div class="space-y-3">
					<div>
						<label for="mapping-user-id" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('User ID')}
						</label>
						<input
							id="mapping-user-id"
							type="text"
							bind:value={newUserMapping.user_id}
							placeholder={$i18n.t('Enter user ID')}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
						/>
					</div>

					<div>
						<label for="mapping-client" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('Client Organization')}
						</label>
						<select
							id="mapping-client"
							bind:value={newUserMapping.client_org_id}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
						>
							<option value="">{$i18n.t('Select client organization')}</option>
							{#each clients.filter(c => c.is_active) as client}
								<option value={client.id}>{client.name}</option>
							{/each}
						</select>
					</div>

					<div>
						<label for="mapping-openrouter-user" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							{$i18n.t('OpenRouter User ID')}
						</label>
						<input
							id="mapping-openrouter-user"
							type="text"
							bind:value={newUserMapping.openrouter_user_id}
							placeholder={$i18n.t('Enter OpenRouter user identifier')}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:text-white"
						/>
					</div>

					<button
						class="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
						on:click={handleCreateUserMapping}
						disabled={!newUserMapping.user_id || !newUserMapping.client_org_id || !newUserMapping.openrouter_user_id}
					>
						{$i18n.t('Create Mapping')}
					</button>
				</div>
			</div>

			<!-- Existing mappings list -->
			<div>
				<h4 class="text-md font-medium mb-3">{$i18n.t('Existing Mappings')}</h4>
				{#if userMappings.length === 0}
					<p class="text-gray-600 dark:text-gray-400 text-sm">{$i18n.t('No user mappings found.')}</p>
				{:else}
					<div class="space-y-2 max-h-60 overflow-y-auto">
						{#each userMappings as mapping}
							<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
								<div class="flex-1">
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{mapping.user_id}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										→ {getClientName(mapping.client_org_id)} ({mapping.openrouter_user_id})
									</div>
								</div>
								<button
									class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 text-sm"
									on:click={() => handleDeactivateUserMapping(mapping.user_id)}
								>
									{$i18n.t('Remove')}
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
	<div slot="footer">
		<div class="flex justify-end">
			<button
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
				on:click={() => { showUserMapping = false; resetNewUserMapping(); }}
			>
				{$i18n.t('Close')}
			</button>
		</div>
	</div>
</Modal>