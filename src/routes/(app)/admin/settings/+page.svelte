<script>
	import { goto } from '$app/navigation';
	import { WEBUI_BASE_PATH } from '$lib/constants';
	import { onMount } from 'svelte';
	import Settings from '$lib/components/admin/Settings.svelte';

	onMount(() => {
		goto(WEBUI_BASE_PATH + '/admin/settings/general');
	});
</script>

<Settings />
