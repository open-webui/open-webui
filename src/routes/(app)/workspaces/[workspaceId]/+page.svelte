<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { activeWorkspaceId, chatId } from '$lib/stores';

	let routeWorkspaceId = '';

	$: routeWorkspaceId = $page.params.workspaceId;
	$: if (routeWorkspaceId) {
		activeWorkspaceId.set(routeWorkspaceId);
		chatId.set('');
	}

	onDestroy(() => {
		activeWorkspaceId.update((current) => (current === routeWorkspaceId ? null : current));
	});
</script>

<Chat />
