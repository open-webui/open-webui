<script>
	import { onMount } from 'svelte';
	import { knowledge, knowledgeList } from '$lib/stores';

	import { getKnowledgeBases, getKnowledgeBaseList } from '$lib/apis/knowledge';
	import Knowledge from '$lib/components/workspace/Knowledge.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				knowledge.set(await getKnowledgeBases(localStorage.token));
				knowledgeList.set(await getKnowledgeBaseList(localStorage.token));
			})()
		]);
	});
</script>

{#if $knowledge !== null}
	<Knowledge />
{/if}
