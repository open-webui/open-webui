<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/admin/evaluations/leaderboard', { replaceState: true });
	});
</script>
