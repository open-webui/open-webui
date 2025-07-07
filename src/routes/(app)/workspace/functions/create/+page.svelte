<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { WEBUI_BASE_PATH } from '$lib/constants';

	onMount(() => {
		goto(WEBUI_BASE_PATH + '/admin/functions/create');
	});
</script>
