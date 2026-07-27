<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/?settings=admin%3Ageneral', { replaceState: true });
	});
</script>
