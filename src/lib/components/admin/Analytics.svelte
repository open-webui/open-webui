<script>
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { hasAnalyticsAccess } from '$lib/utils/admin';

	import Dashboard from './Analytics/Dashboard.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (!hasAnalyticsAccess($user)) {
			await goto('/');
			return;
		}
		loaded = true;
	});
</script>

{#if loaded}
	<div class="w-full h-full pb-2 px-[16px]">
		<Dashboard />
	</div>
{/if}
