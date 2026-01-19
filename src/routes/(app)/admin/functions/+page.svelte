<script>
	import { onMount } from 'svelte';
	import { functions } from '$lib/stores';

	import { getFunctions } from '$lib/apis/functions';
	import Functions from '$lib/components/admin/Functions.svelte';

	onMount(async () => {
		// Only fetch if not already cached
		if (!$functions) {
			functions.set(await getFunctions(localStorage.token));
		}
	});
</script>

{#if $functions !== null}
	<Functions />
{/if}
