<script>
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Settings from '$lib/components/admin/Settings.svelte';

	onMount(() => {
		goto(`${base}/admin/settings/general`);
	});
</script>

<Settings />
