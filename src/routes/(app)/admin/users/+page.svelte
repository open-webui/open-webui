<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import Users from '$lib/components/admin/Users.svelte';

	onMount(() => {
		goto('/admin/users/overview');
	});
</script>

<Users />
