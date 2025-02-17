<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto(WEBUI_BASE_URL + '/admin/functions/create');
	});
</script>
