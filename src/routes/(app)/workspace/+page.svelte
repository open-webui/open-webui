<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workspace?.models) {
				goto(`${base}/workspace/models`);
			} else if ($user?.permissions?.workspace?.knowledge) {
				goto(`${base}/workspace/knowledge`);
			} else if ($user?.permissions?.workspace?.prompts) {
				goto(`${base}/workspace/prompts`);
			} else if ($user?.permissions?.workspace?.tools) {
				goto(`${base}/workspace/tools`);
			} else {
				goto(`${base}/`);
			}
		} else {
			goto(`${base}/workspace/models`);
		}
	});
</script>
