<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import MyOrganizationUsageContainer from '$lib/components/admin/Settings/MyOrganizationUsage/MyOrganizationUsageContainer.svelte';
	
	const i18n = getContext('i18n');
	
	// Client-side permission check since this app uses client-side auth
	$: if ($user && !$user.can_view_usage) {
		goto('/');
	}
</script>

{#if $user?.can_view_usage}
	<div class="w-full h-full flex flex-col">
		<div class="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 max-w-7xl mx-auto w-full">
			<div class="mb-6">
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Usage Dashboard')}
				</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					{$i18n.t('Track your organization\'s AI usage and costs')}
				</p>
			</div>
			
			<div class="bg-white dark:bg-gray-850 rounded-lg shadow-sm">
				<MyOrganizationUsageContainer />
			</div>
		</div>
	</div>
{:else if $user}
	<!-- User doesn't have permission - will redirect -->
{:else}
	<!-- Loading user data -->
	<div class="w-full h-full flex items-center justify-center">
		<div class="text-gray-500 dark:text-gray-400">
			{$i18n.t('Loading...')}
		</div>
	</div>
{/if}