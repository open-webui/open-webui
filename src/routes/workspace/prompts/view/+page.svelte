<script lang="ts">
	import { page } from '$app/stores';
	import PromptViewer from '$lib/components/workspace/Prompts/PromptViewer.svelte';

	const command = $page.url.searchParams.get('command');
</script>

<PromptViewer {command} />
