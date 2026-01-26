<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';

	onMount(() => {
		// 重定向到新的设置路由
		if ($user?.role === 'admin') {
			goto('/settings/general', { replaceState: true });
		} else {
			goto('/settings/user-general', { replaceState: true });
		}
	});
</script>
