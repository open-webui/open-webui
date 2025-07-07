<script>
	import { goto } from '$app/navigation';
	import { WEBUI_BASE_PATH } from '$lib/constants';
	import { onMount } from 'svelte';

	import Users from '$lib/components/admin/Users.svelte';

	onMount(() => {
		goto(WEBUI_BASE_PATH + '/admin/users/overview');
	});
</script>

<Users />
