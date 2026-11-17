<script lang="ts">
	import EditPrompt from '$lib/components/workspace/Prompts/EditPrompt.svelte';
	import { page } from '$app/stores';
</script>

<EditPrompt id={$page.params.id} />
