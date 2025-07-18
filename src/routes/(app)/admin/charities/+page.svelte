<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import Charities from '$lib/components/admin/Charities.svelte';

	onMount(() => {
		goto('/admin/charities/overview');
	});
</script>

<Charities />
