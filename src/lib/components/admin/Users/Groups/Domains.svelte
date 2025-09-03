<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	export let allowedDomains = [];

	// Government of Canada email domains
	const GOC_DOMAINS = [
		{ value: 'gc.ca', label: 'Government of Canada (gc.ca)' },
		{ value: 'canada.ca', label: 'Canada.ca (canada.ca)' },
		{ value: 'parl.gc.ca', label: 'Parliament of Canada (parl.gc.ca)' },
		{ value: 'agr.gc.ca', label: 'Agriculture and Agri-Food Canada (agr.gc.ca)' },
		{ value: 'dfait-maeci.gc.ca', label: 'Global Affairs Canada (dfait-maeci.gc.ca)' },
		{ value: 'fin.gc.ca', label: 'Department of Finance (fin.gc.ca)' },
		{ value: 'hc-sc.gc.ca', label: 'Health Canada (hc-sc.gc.ca)' },
		{ value: 'ic.gc.ca', label: 'Innovation, Science and Economic Development (ic.gc.ca)' },
		{ value: 'ircc.gc.ca', label: 'Immigration, Refugees and Citizenship (ircc.gc.ca)' },
		{ value: 'justice.gc.ca', label: 'Department of Justice (justice.gc.ca)' },
		{ value: 'nrc-cnrc.gc.ca', label: 'National Research Council (nrc-cnrc.gc.ca)' },
		{ value: 'nrcan-rncan.gc.ca', label: 'Natural Resources Canada (nrcan-rncan.gc.ca)' },
		{ value: 'phac-aspc.gc.ca', label: 'Public Health Agency of Canada (phac-aspc.gc.ca)' },
		{ value: 'pwgsc.gc.ca', label: 'Public Works and Government Services (pwgsc.gc.ca)' },
		{ value: 'rcmp-grc.gc.ca', label: 'Royal Canadian Mounted Police (rcmp-grc.gc.ca)' },
		{ value: 'ssc-spc.gc.ca', label: 'Shared Services Canada (ssc-spc.gc.ca)' },
		{ value: 'statcan.gc.ca', label: 'Statistics Canada (statcan.gc.ca)' },
		{ value: 'tbs-sct.gc.ca', label: 'Treasury Board of Canada Secretariat (tbs-sct.gc.ca)' },
		{ value: 'tc.gc.ca', label: 'Transport Canada (tc.gc.ca)' },
		{ value: 'veterans.gc.ca', label: 'Veterans Affairs Canada (veterans.gc.ca)' }
	];

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
</script>

<div class="flex flex-col space-y-3">
	<div class="space-y-2">
		<div class="text-sm font-medium dark:text-gray-100">
			{$i18n.t('Email Domains')}
		</div>
		<div class="text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'Select email domains that will automatically grant access to this group. Users with email addresses from these domains will be automatically added to the group when they log in.'
			)}
		</div>
	</div>

	<div class="space-y-1 max-h-72 overflow-y-auto">
		{#each GOC_DOMAINS as domain}
			<label
				class="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
			>
				<input
					type="checkbox"
					class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					checked={isDomainSelected(domain.value)}
					on:change={(e) => handleDomainToggle(domain.value, e.target.checked)}
				/>
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
						{domain.label}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						@{domain.value}
					</div>
				</div>
			</label>
		{/each}
	</div>

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
