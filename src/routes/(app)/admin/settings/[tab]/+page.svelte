<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		const params = new URLSearchParams($page.url.searchParams);
		const tab =
			$page.params.tab === 'apps'
				? 'integrations'
				: $page.params.tab === 'videos'
					? 'images'
					: ($page.params.tab ?? 'general');
		params.set('settings', `admin:${tab}`);
		goto(`/?${params.toString()}`, { replaceState: true });
	});
</script>
