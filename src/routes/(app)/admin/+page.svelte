<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';
	import { hasAdminAccess, hasAnalyticsAccess } from '$lib/utils/admin';

	onMount(() => {
		if (hasAdminAccess($user)) {
			goto('/admin/users');
		} else if (hasAnalyticsAccess($user)) {
			goto('/admin/analytics');
		} else {
			goto('/');
		}
	});
</script>
