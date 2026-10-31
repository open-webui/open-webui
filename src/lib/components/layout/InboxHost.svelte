<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/stores';
	import { mobile, showSidebar, socket, user } from '$lib/stores';
	import { refreshInboxCount, setInboxCount } from '$lib/stores/inbox';
	import { inboxRequest, type InboxItem } from '$lib/apis/notifications/inbox';
	import InboxPanel from './InboxPanel.svelte';
	import Comments from '$lib/components/comments/Comments.svelte';
	import type { CommentsRequest } from '$lib/components/comments/CommentsPanel.svelte';
	export let panel: InboxPanel | undefined = undefined;
	let comments: CommentsRequest | null = null;
	let alive = true;
	let timer: ReturnType<typeof setTimeout>;
	let connection: import('socket.io-client').Socket | null = null;
	const refresh = async () => {
		if (!alive) return;
		await refreshInboxCount();
		if (alive) panel?.refresh();
	};
	const changed = () => {
		clearTimeout(timer);
		timer = setTimeout(refresh, 150);
	};
	$: if ($socket !== connection) {
		connection?.off('notifications:changed', changed);
		connection?.off('connect', changed);
		connection = $socket;
		connection?.on('notifications:changed', changed);
		connection?.on('connect', changed);
	}
	export const close = () => {
		if (!$page.state.inbox) return;
		replaceState('', { ...$page.state, inbox: false, inboxUserId: undefined });
	};
	export const select = async (item: InboxItem) => {
		const current = await inboxRequest<InboxItem>(`/${encodeURIComponent(item.id)}`, 'PATCH');
		if (!alive) return;
		if (!current.resource_type) {
			panel?.refresh();
			return;
		}
		const state = { inbox: $page.state.inbox, inboxUserId: $page.state.inboxUserId };
		if ($mobile) showSidebar.set(false);
		if (current.object_type === 'comment') {
			comments = {
				resource_type: current.resource_type as CommentsRequest['resource_type'],
				resource_id: current.resource_id!,
				comment_id: current.object_id!
			};
		} else if (current.resource_type === 'channel') {
			const query = new URLSearchParams({
				message: current.object_id!,
				thread: current.data.parent_id ?? current.object_id!
			});
			await goto(`/channels/${encodeURIComponent(current.resource_id!)}?${query}`, { state });
		} else if (current.resource_type === 'automation')
			await goto(
				`/automations/${encodeURIComponent(current.resource_id!)}?run=${encodeURIComponent(current.object_id!)}`,
				{ state }
			);
		else if (current.resource_type === 'calendar')
			await goto(`/calendar?event=${encodeURIComponent(current.object_id!)}`, { state });
		void refresh();
	};
	onMount(() => {
		if ($page.state.inbox && $page.state.inboxUserId !== $user?.id)
			replaceState('', { ...$page.state, inbox: false, inboxUserId: undefined });
		void refresh();
	});
	onDestroy(() => {
		alive = false;
		clearTimeout(timer);
		connection?.off('notifications:changed', changed);
		connection?.off('connect', changed);
		setInboxCount(0);
	});
</script>

<svelte:window on:focus={changed} />
<Comments modal bind:view={comments} />
