<script>
	import { onMount } from 'svelte';
	import { knowledge } from '$lib/stores';

	import { getKnowledgeItems } from '$lib/apis/knowledge';
	import Knowledge from '$lib/components/workspace/Knowledge.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				knowledge.set(await getKnowledgeItems(localStorage.token));
			})()
		]);
	});
</script>

{#if $knowledge !== null}
	<Knowledge />
{/if}
