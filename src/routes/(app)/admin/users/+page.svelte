<script>
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(async () => {
		await goto(`${base}/admin/users/overview`);
	});
</script>
