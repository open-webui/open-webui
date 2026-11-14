<script lang="ts">
	import { navigating, page } from '$app/state';

	import Chat from '$lib/components/chat/Chat.svelte';

	const params = $derived(
		(navigating.to?.route.id === page.route.id && navigating.to.params) || page.params
	);
</script>

<Chat chatIdProp={params.id} />
