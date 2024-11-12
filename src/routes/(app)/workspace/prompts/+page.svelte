<script>
	import { onMount } from 'svelte';
	import { prompts } from '$lib/stores';

	import { getPrompts } from '$lib/apis/prompts';
	import Prompts from '$lib/components/workspace/Prompts.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				prompts.set(await getPrompts(localStorage.token));
			})()
		]);
	});
</script>

{#if $prompts !== null}
	<Prompts />
{/if}
