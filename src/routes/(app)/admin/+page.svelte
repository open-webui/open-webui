<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	onMount(() => {
		goto(WEBUI_BASE_URL + '/admin/users');
	});
</script>
