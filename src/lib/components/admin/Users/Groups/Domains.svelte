<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { createDomain, getDomains, deleteDomainById, updateDomainById } from '$lib/apis/domains';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let allowedDomains = [];

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
			toast.error('Failed to load available domains');
		}
		loading = false;
	};

	// Handle checkbox changes
	const handleDomainToggle = (domain, isChecked) => {
		if (isChecked) {
			if (!allowedDomains.includes(domain)) {
				allowedDomains = [...allowedDomains, domain];
			}
		} else {
			allowedDomains = allowedDomains.filter((d) => d !== domain);
		}
	};

	// Check if a domain is selected
	const isDomainSelected = (domain) => {
		return allowedDomains.includes(domain);
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
			toast.error('Please enter a domain name');
			return;
		}

		if (!departmentName) {
			toast.error('Please enter a department name');
			return;
		}

		// Domain validation - Government of Canada domains (*.gc.ca + special cases)
		const domainRegex =
			/^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.gc\.ca|elections\.ca|canada\.ca|gc\.ca)$/;
		if (!domainRegex.test(domainName)) {
			toast.error(
				'Please enter a valid Government of Canada domain (*.gc.ca, canada.ca, elections.ca)'
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

			// Automatically select the new domain
			if (!allowedDomains.includes(domainName)) {
				allowedDomains = [...allowedDomains, domainName];
			}

			// Reset form
			newDomainInput = '';
			newDepartmentInput = '';
			showAddDomainForm = false;

			toast.success(`Domain "${domainName}" added for ${departmentName}`);
		} catch (error) {
			console.error('Failed to add domain:', error);
			toast.error(error || 'Failed to add domain');
		}
	};

	// Delete a domain from database
	const deleteDomain = async (domain) => {
		const domainInfo = getDomainInfo(domain);
		if (!domainInfo) return;

		try {
			await deleteDomainById(localStorage.token, domainInfo.id);

			// Remove from selected domains if it was selected
			allowedDomains = allowedDomains.filter((d) => d !== domain);

			// Reload domains
			await loadDomains();

			toast.success(`Domain "${domain}" deleted successfully`);
		} catch (error) {
			console.error('Failed to delete domain:', error);
			toast.error(error || 'Failed to delete domain');
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
			toast.error('Please enter a domain name');
			return;
		}

		if (!departmentName) {
			toast.error('Please enter a department/organization name');
			return;
		}

		// Domain validation - Government of Canada domains (*.gc.ca + special cases)
		const domainRegex =
			/^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.gc\.ca|elections\.ca|canada\.ca|gc\.ca)$/;
		if (!domainRegex.test(domainName)) {
			toast.error(
				'Please enter a valid Government of Canada domain (*.gc.ca, canada.ca, elections.ca)'
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

			// Update allowed domains if the domain name changed
			if (showEditForm !== domainName && allowedDomains.includes(showEditForm)) {
				allowedDomains = allowedDomains.map((d) => (d === showEditForm ? domainName : d));
			}

			// Reload domains
			await loadDomains();

			// Close edit form
			cancelEdit();

			toast.success(`Domain updated successfully`);
		} catch (error) {
			console.error('Failed to update domain:', error);
			toast.error(error || 'Failed to update domain');
		}
	};
</script>

<div class="flex flex-col space-y-3">
	<div class="space-y-2">
		<div class="text-sm font-medium dark:text-gray-100">
			{$i18n.t('Email Domains')}
		</div>
		<div class="text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'Select Government of Canada email domains by department that will automatically grant access to this group. Users with email addresses from these domains will be automatically added to the group when they log in.'
			)}
		</div>
	</div>

	<!-- Add domain section -->
	<div class="space-y-2">
		<button
			type="button"
			class="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
			on:click={() => (showAddDomainForm = !showAddDomainForm)}
		>
			{showAddDomainForm ? 'Cancel' : '+ Add Domain'}
		</button>

		{#if showAddDomainForm}
			<div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
					Add Government of Canada Domain
				</div>
				<div class="space-y-2">
					<div>
						<label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
							Email Domain
						</label>
						<input
							type="text"
							placeholder="department.gc.ca"
							bind:value={newDomainInput}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
							on:keydown={(e) => e.key === 'Enter' && e.shiftKey === false && addDomain()}
						/>
					</div>
					<div>
						<label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
							Department/Organization Name
						</label>
						<input
							type="text"
							placeholder="Department of Example Services"
							bind:value={newDepartmentInput}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
							on:keydown={(e) => e.key === 'Enter' && e.shiftKey === false && addDomain()}
						/>
					</div>
				</div>
				<div class="flex justify-end">
					<button
						type="button"
						class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg"
						on:click={addDomain}
					>
						Add Domain
					</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- Available domains list -->
	<div class="space-y-1 max-h-72 overflow-y-auto">
		{#if loading}
			<div class="text-center py-4">
				<div class="text-sm text-gray-500 dark:text-gray-400">Loading domains...</div>
			</div>
		{:else if dbDomains.length === 0}
			<div class="text-center py-4">
				<div class="text-sm text-gray-500 dark:text-gray-400">
					No domains available. Add a domain above.
				</div>
			</div>
		{:else}
			{#each dbDomains as domainObj}
				<div
					class="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
				>
					<input
						type="checkbox"
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
						checked={isDomainSelected(domainObj.domain)}
						on:change={(e) => handleDomainToggle(domainObj.domain, e.target.checked)}
					/>
					<div class="flex-1">
						{#if showEditForm === domainObj.domain}
							<!-- Edit form for this domain -->
							<div
								class="space-y-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800"
							>
								<div class="text-xs text-blue-700 dark:text-blue-300 font-medium mb-2">
									Editing Domain
								</div>
								<div>
									<label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
										Email Domain
									</label>
									<input
										type="text"
										bind:value={editDomainInput}
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
										on:keydown={(e) =>
											e.key === 'Enter' && e.shiftKey === false && saveEditDomain()}
									/>
								</div>
								<div>
									<label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
										Department/Organization Name
									</label>
									<input
										type="text"
										bind:value={editDepartmentInput}
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
										on:keydown={(e) =>
											e.key === 'Enter' && e.shiftKey === false && saveEditDomain()}
									/>
								</div>
								<div class="flex justify-end space-x-2 pt-2">
									<button
										type="button"
										class="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg"
										on:click={cancelEdit}
									>
										Cancel
									</button>
									<button
										type="button"
										class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"
										on:click={saveEditDomain}
									>
										Save Changes
									</button>
								</div>
							</div>
						{:else}
							<!-- Normal display -->
							<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
								@{domainObj.domain}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{domainObj.description || 'No department specified'}
							</div>
						{/if}
					</div>

					{#if showEditForm !== domainObj.domain}
						<!-- Edit and Delete buttons (hidden when editing) -->
						<div class="flex space-x-1">
							<!-- Edit button -->
							<button
								type="button"
								class="text-blue-500 hover:text-blue-700 p-1 rounded"
								title="Edit domain"
								on:click={() => startEditDomain(domainObj.domain)}
							>
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
									<path
										d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
									></path>
								</svg>
							</button>

							<!-- Delete button -->
							<button
								type="button"
								class="text-red-500 hover:text-red-700 p-1 rounded"
								title="Delete domain"
								on:click={() => (showDeleteConfirm = domainObj.domain)}
							>
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9zM4 5a2 2 0 012-2h8a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 112 0v3a1 1 0 11-2 0V9zm4 0a1 1 0 112 0v3a1 1 0 11-2 0V9z"
										clip-rule="evenodd"
									></path>
								</svg>
							</button>
						</div>
					{/if}
				</div>
			{/each}
		{/if}
	</div>

	<!-- Delete confirmation modal -->
	{#if showDeleteConfirm}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
			<div class="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-md w-full mx-4">
				<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Delete Domain</h3>
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
					Are you sure you want to delete the domain "@{showDeleteConfirm}"? This action cannot be
					undone.
				</p>
				<div class="flex justify-end space-x-3">
					<button
						type="button"
						class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg"
						on:click={() => (showDeleteConfirm = null)}
					>
						Cancel
					</button>
					<button
						type="button"
						class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg"
						on:click={() => deleteDomain(showDeleteConfirm)}
					>
						Delete
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if allowedDomains.length > 0}
		<div class="space-y-2">
			<div class="text-sm font-medium dark:text-gray-100">
				{$i18n.t('Selected Domains')} ({allowedDomains.length})
			</div>
			<div class="flex flex-wrap gap-2">
				{#each allowedDomains as domain}
					<span
						class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
					>
						@{domain}
						<button
							type="button"
							class="ml-1 inline-flex items-center justify-center w-4 h-4 text-blue-400 hover:text-blue-600"
							on:click={() => handleDomainToggle(domain, false)}
						>
							<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
								<path
									fill-rule="evenodd"
									d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
									clip-rule="evenodd"
								></path>
							</svg>
						</button>
					</span>
				{/each}
			</div>
		</div>
	{:else}
		<div class="text-sm text-gray-500 dark:text-gray-400 italic">
			{$i18n.t('No domains selected. This group will not have automatic domain-based access.')}
		</div>
	{/if}
</div>
