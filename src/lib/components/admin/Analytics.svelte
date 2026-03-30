<script>
	import { base } from '$app/paths';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import Dashboard from './Analytics/Dashboard.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto(`${base}/`);
		}
		loaded = true;
	});
</script>

{#if loaded}
	<div class="w-full h-full pb-2 px-[16px]">
		<Dashboard />
	</div>
{/if}
