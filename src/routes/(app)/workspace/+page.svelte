<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workspace?.models) {
				goto(WEBUI_BASE_URL + '/workspace/models');
			} else if ($user?.permissions?.workspace?.knowledge) {
				goto(WEBUI_BASE_URL + '/workspace/knowledge');
			} else if ($user?.permissions?.workspace?.prompts) {
				goto(WEBUI_BASE_URL + '/workspace/prompts');
			} else if ($user?.permissions?.workspace?.tools) {
				goto(WEBUI_BASE_URL + '/workspace/tools');
			} else {
				goto(WEBUI_BASE_URL + '/');
			}
		} else {
			goto(WEBUI_BASE_URL + '/workspace/models');
		}
	});
</script>
