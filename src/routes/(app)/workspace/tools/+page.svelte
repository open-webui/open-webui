<script>
	import { onMount } from 'svelte';
	import { tools } from '$lib/stores';

	import { getTools } from '$lib/apis/tools';
	import Tools from '$lib/components/workspace/Tools.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				tools.set(await getTools(localStorage.token));
			})()
		]);
	});
</script>

{#if $tools !== null}
	<Tools />
{/if}
