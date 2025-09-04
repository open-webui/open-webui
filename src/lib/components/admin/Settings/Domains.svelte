<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { createDomain, getDomains, deleteDomainById, updateDomainById } from '$lib/apis/domains';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let dbDomains = [];
	let newDomainInput = '';
	let newDepartmentInput = '';
	let showAddDomainForm = false;
	let loading = true;
	let showDeleteConfirm = null;
	let showEditForm = null;
	let editDomainInput = '';
	let editDepartmentInput = '';

	// Load available domains on component mount
	onMount(async () => {
		await loadDomains();
	});

	const loadDomains = async () => {
		loading = true;
		try {
			// Load database domains (already sorted by department name on backend)
			dbDomains = (await getDomains(localStorage.token)) || [];
		} catch (error) {
			console.error('Failed to load domains:', error);
			toast.error($i18n.t('Failed to load available domains'));
		}
		loading = false;
	};

	// Get domain info from database
	const getDomainInfo = (domain) => {
		return dbDomains.find((d) => d.domain === domain);
	};

	// Add a new domain
	const addDomain = async () => {
		const domainName = newDomainInput.trim();
		const departmentName = newDepartmentInput.trim();

		if (!domainName) {
			toast.error(i18n.t('Please enter a domain name'));
			return;
		}

		if (!departmentName) {
			toast.error(i18n.t('Please enter a department name'));
			return;
		}

		// Domain validation - Government of Canada domains (*.gc.ca + special cases)
		const domainRegex =
			/^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.gc\.ca|elections\.ca|canada\.ca|gc\.ca)$/;
		if (!domainRegex.test(domainName)) {
			toast.error(
				i18n.t(
					'Please enter a valid Government of Canada domain (*.gc.ca, canada.ca, elections.ca)'
				)
			);
			return;
		}

		try {
			// Add to database
			await createDomain(localStorage.token, {
				domain: domainName,
				description: departmentName
			});

			// Reload domains
			await loadDomains();

			// Reset form
			newDomainInput = '';
			newDepartmentInput = '';
			showAddDomainForm = false;

			toast.success(
				i18n.t('Domain "{domainName}" added for {departmentName}', { domainName, departmentName })
			);
		} catch (error) {
			console.error('Failed to add domain:', error);
			toast.error(error || i18n.t('Failed to add domain'));
		}
	};

	// Delete a domain from database
	const deleteDomain = async (domain) => {
		const domainInfo = getDomainInfo(domain);
		if (!domainInfo) return;

		try {
			await deleteDomainById(localStorage.token, domainInfo.id);

			// Reload domains
			await loadDomains();

			toast.success(i18n.t('Domain "{domain}" deleted successfully', { domain }));
		} catch (error) {
			console.error('Failed to delete domain:', error);
			toast.error(error || i18n.t('Failed to delete domain'));
		}
		showDeleteConfirm = null;
	};

	// Start editing a domain
	const startEditDomain = (domain) => {
		const domainInfo = getDomainInfo(domain);
		if (!domainInfo) return;

		showEditForm = domain;
		editDomainInput = domainInfo.domain;
		editDepartmentInput = domainInfo.description || '';
	};

	// Cancel editing
	const cancelEdit = () => {
		showEditForm = null;
		editDomainInput = '';
		editDepartmentInput = '';
	};

	// Save edited domain
	const saveEditDomain = async () => {
		const domainName = editDomainInput.trim();
		const departmentName = editDepartmentInput.trim();

		if (!domainName) {
			toast.error(i18n.t('Please enter a domain name'));
			return;
		}

		if (!departmentName) {
			toast.error(i18n.t('Please enter a department/organization name'));
			return;
		}

		// Domain validation - Government of Canada domains (*.gc.ca + special cases)
		const domainRegex =
			/^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.gc\.ca|elections\.ca|canada\.ca|gc\.ca)$/;
		if (!domainRegex.test(domainName)) {
			toast.error(
				i18n.t(
					'Please enter a valid Government of Canada domain (*.gc.ca, canada.ca, elections.ca)'
				)
			);
			return;
		}

		const domainInfo = getDomainInfo(showEditForm);
		if (!domainInfo) return;

		try {
			// Update domain in database
			await updateDomainById(localStorage.token, domainInfo.id, {
				domain: domainName,
				description: departmentName
			});

			// Reload domains
			await loadDomains();

			// Close edit form
			cancelEdit();

			toast.success(i18n.t('Domain updated successfully'));
		} catch (error) {
			console.error('Failed to update domain:', error);
			toast.error(error || i18n.t('Failed to update domain'));
		}
	};
</script>

<div class="flex flex-col space-y-4 max-w-full overflow-hidden px-2 sm:px-4">
	<div class="space-y-2">
		<div class="text-lg font-medium dark:text-gray-100">
			{$i18n.t('Government of Canada Domains')}
		</div>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'Manage the list of Government of Canada email domains that can be used for automatic group assignment. These domains will be available when configuring groups for domain-based access.'
			)}
		</div>
	</div>

	<!-- Add domain section -->
	<div class="space-y-3">
		<button
			type="button"
			class="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
			on:click={() => (showAddDomainForm = !showAddDomainForm)}
		>
			{showAddDomainForm ? $i18n.t('Cancel') : $i18n.t('+ Add Domain')}
		</button>

		{#if showAddDomainForm}
			<div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border max-w-full mr-4">
				<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
					{$i18n.t('Add Government of Canada Domain')}
				</div>
				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4 w-full">
					<div class="min-w-0">
						<label
							for="new-domain-input"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							{$i18n.t('Email Domain')}
						</label>
						<input
							id="new-domain-input"
							type="text"
							placeholder={$i18n.t('department.gc.ca')}
							bind:value={newDomainInput}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
							on:keydown={(e) => e.key === 'Enter' && e.shiftKey === false && addDomain()}
						/>
					</div>
					<div class="min-w-0">
						<label
							for="new-department-input"
							class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
						>
							{$i18n.t('Department/Organization Name')}
						</label>
						<input
							id="new-department-input"
							type="text"
							placeholder={$i18n.t('Department of Example Services')}
							bind:value={newDepartmentInput}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
							on:keydown={(e) => e.key === 'Enter' && e.shiftKey === false && addDomain()}
						/>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 pt-2">
					<button
						type="button"
						class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg"
						on:click={addDomain}
					>
						{$i18n.t('Add Domain')}
					</button>
					<button
						type="button"
						class="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 text-sm font-medium rounded-lg"
						on:click={() => (showAddDomainForm = false)}
					>
						{$i18n.t('Cancel')}
					</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- Domain list -->
	<div class="space-y-2">
		{#if loading}
			<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading domains...')}</div>
		{:else if dbDomains.length === 0}
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('No domains configured. Add your first Government of Canada domain above.')}
			</div>
		{:else}
			<div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
				<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
					<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">
						{$i18n.t('Configured Domains')} ({dbDomains.length})
					</h3>
				</div>
				<ul class="divide-y divide-gray-200 dark:divide-gray-700">
					{#each dbDomains as domainObj (domainObj.id)}
						<li class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700">
							{#if showEditForm === domainObj.domain}
								<!-- Edit form -->
								<div class="space-y-3">
									<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-full">
										<div>
											<label
												for="edit-domain-input"
												class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
											>
												{$i18n.t('Domain')}
											</label>
											<input
												id="edit-domain-input"
												type="text"
												bind:value={editDomainInput}
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
											/>
										</div>
										<div>
											<label
												for="edit-department-input"
												class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
											>
												{$i18n.t('Department/Organization')}
											</label>
											<input
												id="edit-department-input"
												type="text"
												bind:value={editDepartmentInput}
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
											/>
										</div>
									</div>
									<div class="flex space-x-2">
										<button
											type="button"
											class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg"
											on:click={saveEditDomain}
										>
											{$i18n.t('Save')}
										</button>
										<button
											type="button"
											class="px-3 py-1 bg-gray-300 hover:bg-gray-400 text-gray-700 text-sm rounded-lg"
											on:click={cancelEdit}
										>
											{$i18n.t('Cancel')}
										</button>
									</div>
								</div>
							{:else}
								<!-- Display mode -->
								<div class="flex items-center justify-between">
									<div>
										<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
											{domainObj.domain}
										</div>
										{#if domainObj.description}
											<div class="text-sm text-gray-500 dark:text-gray-400">
												{domainObj.description}
											</div>
										{/if}
									</div>
									<div class="flex space-x-2">
										<button
											type="button"
											class="px-3 py-1 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-sm font-medium rounded-lg border border-blue-200 dark:border-blue-800"
											on:click={() => startEditDomain(domainObj.domain)}
										>
											{$i18n.t('Edit')}
										</button>
										<button
											type="button"
											class="px-3 py-1 bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-300 text-sm font-medium rounded-lg border border-red-200 dark:border-red-800"
											on:click={() => (showDeleteConfirm = domainObj.domain)}
										>
											{$i18n.t('Delete')}
										</button>
									</div>
								</div>
							{/if}

							<!-- Delete confirmation -->
							{#if showDeleteConfirm === domainObj.domain}
								<div
									class="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
								>
									<div class="text-sm text-red-800 dark:text-red-200 mb-3">
										{$i18n.t(
											'Are you sure you want to delete the domain "{domain}"? This action cannot be undone.',
											{ domain: domainObj.domain }
										)}
									</div>
									<div class="flex space-x-2">
										<button
											type="button"
											class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg"
											on:click={() => deleteDomain(domainObj.domain)}
										>
											{$i18n.t('Delete')}
										</button>
										<button
											type="button"
											class="px-3 py-1 bg-gray-300 hover:bg-gray-400 text-gray-700 text-sm rounded-lg"
											on:click={() => (showDeleteConfirm = null)}
										>
											{$i18n.t('Cancel')}
										</button>
									</div>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
</div>
