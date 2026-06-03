<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { activeWorkspaceId } from '$lib/stores';

	let routeWorkspaceId: string | null = null;

	$: routeWorkspaceId = $page.params.workspaceId ?? null;
	$: if (routeWorkspaceId) {
		activeWorkspaceId.set(routeWorkspaceId);
	}

	onDestroy(() => {
		activeWorkspaceId.update((current) => (current === routeWorkspaceId ? null : current));
	});
</script>

<Chat chatIdProp={$page.params.id} workspaceIdProp={routeWorkspaceId} />
