<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { config, user, mobile } from '$lib/stores';
	import { commentsRequest, type CommentResource, type ResourceComment } from '$lib/apis/comments';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import ResizableSidePanel from '$lib/components/common/ResizableSidePanel.svelte';
	import CommentsPanel, { type CommentsRequest } from './CommentsPanel.svelte';

	export let children: import('svelte').Snippet | undefined = undefined;
	export let view: CommentsRequest | null = null;
	export let modal = false;
	export let resourceType: CommentResource['resource_type'] | null = null;
	const i18n = getContext<any>('i18n');
	let currentUrl = $page.url.href;
	let account = $user?.id;
	let deepLink = '';
	let alive = true;
	onDestroy(() => {
		alive = false;
	});
	$: enabled = !!($config?.features?.enable_comments && $user);
	$: if ($page.url.href !== currentUrl || $user?.id !== account) {
		currentUrl = $page.url.href;
		account = $user?.id;
		deepLink = '';
		view = null;
	}
	$: if (!enabled) view = null;
	const loadLink = async (id: string) => {
		const url = currentUrl;
		const accountId = account;
		try {
			const comment = await commentsRequest<ResourceComment>(`/${encodeURIComponent(id)}`);
			if (
				alive &&
				url === currentUrl &&
				accountId === account &&
				comment.resource_type === resourceType
			)
				view = {
					resource_type: comment.resource_type,
					resource_id: comment.resource_id,
					comment_id: id
				};
		} catch (e) {
			if (alive && url === currentUrl && accountId === account)
				toast.error(e instanceof Error ? e.message : String(e));
		}
	};
	$: if (
		enabled &&
		resourceType &&
		$page.url.searchParams.get('comment') &&
		deepLink !== currentUrl
	) {
		deepLink = currentUrl;
		loadLink($page.url.searchParams.get('comment')!);
	}
</script>

<svelte:window
	on:keydown={(event) => {
		if (event.key === 'Escape' && !modal) view = null;
	}}
/>

{#snippet panel()}
	{#if view && enabled}
		{#key `${$user.id}:${view.resource_type}:${view.resource_id}:${view.comment_id ?? ''}`}
			{#if modal}
				<Modal
					show={true}
					size="md"
					ariaLabel={$i18n.t('Comments')}
					className="bg-white dark:bg-gray-900 rounded-4xl overflow-hidden"
					onRequestClose={() => (view = null)}
				>
					<div class="h-[min(70dvh,40rem)]">
						<CommentsPanel bind:view {modal} onClose={() => (view = null)} />
					</div>
				</Modal>
			{:else if $mobile}
				<Drawer show={true} onClose={() => (view = null)}>
					<div class="h-dvh"><CommentsPanel bind:view onClose={() => (view = null)} /></div>
				</Drawer>
			{:else}
				<ResizableSidePanel
					open={true}
					width={350}
					minWidth={300}
					maxWidth={640}
					minSiblingWidth={400}
					resizerId="comments-resizer"
					portalTarget="workspace-layout"
					storageKey="comments-panel-width"
					className="h-full min-h-0"
					onClose={() => (view = null)}
				>
					<aside aria-label={$i18n.t('Comments')} class="h-full w-full">
						<CommentsPanel bind:view onClose={() => (view = null)} />
					</aside>
				</ResizableSidePanel>
			{/if}
		{/key}
	{/if}
{/snippet}

{#if modal}
	{@render children?.()}
	{@render panel()}
{:else}
	<div class="flex h-full min-h-0 w-full min-w-0">
		<div class="min-w-0 flex-1 h-full">{@render children?.()}</div>
		{@render panel()}
	</div>
{/if}
