<script>
	import { page } from '$app/stores';
	import KnowledgeBase from '$lib/components/workspace/Knowledge/KnowledgeBase.svelte';
</script>

<KnowledgeBase id={$page.params.id} />
