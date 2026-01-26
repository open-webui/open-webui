<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		// 重定向到新的设置路由，保留 tab 参数
		const pathParts = $page.url.pathname.split('/');
		const tab = pathParts[pathParts.length - 1];
		goto(`/settings/${tab}`, { replaceState: true });
	});
</script>
