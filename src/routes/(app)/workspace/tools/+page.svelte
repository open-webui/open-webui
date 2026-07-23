<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';

	import Tools from '$lib/components/workspace/Tools.svelte';

	onMount(() => {
		if (!$config?.features?.enable_plugins) {
			goto('/workspace');
		}
	});
</script>

{#if $config?.features?.enable_plugins}
	<Tools />
{/if}
