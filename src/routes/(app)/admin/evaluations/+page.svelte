<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { WEBUI_BASE_PATH } from '$lib/constants';

	import Evaluations from '$lib/components/admin/Evaluations.svelte';

	onMount(() => {
		goto(WEBUI_BASE_PATH + '/admin/evaluations/leaderboard');
	});
</script>

<Evaluations />
