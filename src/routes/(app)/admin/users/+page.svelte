<script>
	import Users from '$lib/components/admin/Users.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/admin/users/overview');
	});
</script>

<Users />
