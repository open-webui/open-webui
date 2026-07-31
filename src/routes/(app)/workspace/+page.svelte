<script lang="ts">
	import { goto } from '$app/navigation';
	import { config, user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workspace?.models) {
				goto('/workspace/models', { replaceState: true });
			} else if ($user?.permissions?.workspace?.knowledge) {
				goto('/workspace/knowledge', { replaceState: true });
			} else if ($user?.permissions?.workspace?.prompts) {
				goto('/workspace/prompts', { replaceState: true });
			} else if ($config?.features?.enable_plugins && $user?.permissions?.workspace?.tools) {
				goto('/workspace/tools', { replaceState: true });
			} else if ($user?.permissions?.workspace?.skills) {
				goto('/workspace/skills', { replaceState: true });
			} else {
				goto('/', { replaceState: true });
			}
		} else {
			goto('/workspace/models', { replaceState: true });
		}
	});
</script>
