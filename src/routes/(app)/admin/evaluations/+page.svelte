<script>
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import Evaluations from '$lib/components/admin/Evaluations.svelte';

	onMount(() => {
		goto(`${base}/admin/evaluations/leaderboard`);
	});
</script>

<Evaluations />
