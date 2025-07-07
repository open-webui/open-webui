<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';
	import { WEBUI_BASE_PATH } from '$lib/constants';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workspace?.models) {
				goto(WEBUI_BASE_PATH + '/workspace/models');
			} else if ($user?.permissions?.workspace?.knowledge) {
				goto(WEBUI_BASE_PATH + '/workspace/knowledge');
			} else if ($user?.permissions?.workspace?.prompts) {
				goto(WEBUI_BASE_PATH + '/workspace/prompts');
			} else if ($user?.permissions?.workspace?.tools) {
				goto(WEBUI_BASE_PATH + '/workspace/tools');
			} else {
				goto(WEBUI_BASE_PATH + '/');
			}
		} else {
			goto(WEBUI_BASE_PATH + '/workspace/models');
		}
	});
</script>
