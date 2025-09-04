<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getDomains } from '$lib/apis/domains';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let allowedDomains = [];

	let dbDomains = [];
	let loading = true;

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
			toast.error(i18n.t('Failed to load available domains'));
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
			// Filter creates a new array, ensuring reactivity
			allowedDomains = allowedDomains.filter((d) => d !== domain);
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
				'Select Government of Canada email domains that will automatically grant access to this group. Users with email addresses from these domains will be automatically added to the group when they log in.'
			)}
		</div>
	</div>

	<!-- Selected Domains section - moved to top for constant visibility -->
	{#if allowedDomains.length > 0}
		<div
			class="space-y-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
		>
			<div class="text-sm font-medium text-blue-900 dark:text-blue-100">
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
		<div
			class="text-sm text-gray-500 dark:text-gray-400 italic p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
		>
			{$i18n.t('No domains selected. This group will not have automatic domain-based access.')}
		</div>
	{/if}

	<!-- Note about managing domains -->
	{#if dbDomains.length === 0}
		<div
			class="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg"
		>
			<div class="text-sm text-yellow-800 dark:text-yellow-200">
				<strong>{$i18n.t('No domains available.')}</strong>
				{$i18n.t(
					'Go to Admin Settings → Domains to add Government of Canada email domains that can be used for group assignment.'
				)}
			</div>
		</div>
	{/if}

	<!-- Available domains list for selection -->
	<div class="space-y-1 max-h-72 overflow-y-auto">
		{#if loading}
			<div class="text-center py-4">
				<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading domains...')}</div>
			</div>
		{:else if dbDomains.length === 0}
			<div class="text-center py-4">
				<div class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('No domains configured. Please configure domains in Admin Settings first.')}
				</div>
			</div>
		{:else}
			{#each dbDomains as domainObj (domainObj.id)}
				{@const isSelected = allowedDomains.includes(domainObj.domain)}
				<label
					class="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
				>
					<input
						type="checkbox"
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
						checked={isSelected}
						on:change={(e) => handleDomainToggle(domainObj.domain, e.target.checked)}
					/>
					<div class="flex-1">
						<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
							@{domainObj.domain}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{domainObj.description || $i18n.t('No department specified')}
						</div>
					</div>
				</label>
			{/each}
		{/if}
	</div>
</div>
