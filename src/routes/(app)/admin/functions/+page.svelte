<script>
	import { onMount } from 'svelte';
	import { config, functions } from '$lib/stores';
	import { goto } from '$app/navigation';

	import { getFunctions } from '$lib/apis/functions';
	import Functions from '$lib/components/admin/Functions.svelte';

	onMount(async () => {
		if (!$config?.features?.enable_plugins) {
			await goto('/admin');
			return;
		}

		await Promise.all([
			(async () => {
				functions.set(await getFunctions(localStorage.token));
			})()
		]);
	});
</script>

{#if $functions !== null}
	<Functions />
{/if}
