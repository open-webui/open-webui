<script>
	import { getContext } from 'svelte';
	
	export let activeTab = 'stats';
	export let onTabChange = () => {};
	export let isAdmin = false;
	
	const i18n = getContext('i18n');
	
	const tabs = [
		{ id: 'stats', label: 'Usage Stats', adminOnly: false },
		{ id: 'users', label: 'By User', adminOnly: true },
		{ id: 'models', label: 'By Model', adminOnly: true },
		{ id: 'subscription', label: 'Subscription', adminOnly: true },
		{ id: 'pricing', label: 'Model Pricing', adminOnly: false }
	];
	
	$: visibleTabs = tabs.filter(tab => !tab.adminOnly || isAdmin);
</script>

<div class="border-b border-gray-200 dark:border-gray-700 mb-6">
	<nav class="-mb-px flex space-x-8">
		{#each visibleTabs as tab}
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-150
					{activeTab === tab.id 
						? 'border-blue-500 text-blue-600 dark:text-blue-400' 
						: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'}"
				on:click={() => onTabChange(tab.id)}
			>
				{$i18n.t(tab.label)}
			</button>
		{/each}
	</nav>
</div>