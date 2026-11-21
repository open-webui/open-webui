<script lang="ts">
	import { onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getPageContext } from '$lib/utils/page';
	import { config, user } from '$lib/stores';
	import { commentsRequest, type CommentResource, type ResourceComment } from '$lib/apis/comments';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import CommentButton from './CommentButton.svelte';
	import CommentsPanel, { type CommentsRequest } from './CommentsPanel.svelte';

	const { url: pageUrl } = getPageContext();

	export let resource: CommentResource;
	/** Shared across a page so a menu item can open the popover anchored to its row's button. */
	export let view: CommentsRequest | null = null;
	/** Open the popover when the page URL carries ?comment=<id> for this resource. */
	export let deepLink = false;
	/** Show the resource name above the thread, for lists where the anchor alone is ambiguous. */
	export let showResource = false;
	export let className = '';
	export let wrapperClassName = '';

	$: enabled = !!($config?.features?.enable_comments && $user && resource.resource_id);
	$: open =
		enabled &&
		view?.resource_type === resource.resource_type &&
		view?.resource_id === resource.resource_id;

	let alive = true;
	onDestroy(() => {
		alive = false;
	});
	let linked = '';
	const loadLink = async (id: string, url: string) => {
		try {
			const comment = await commentsRequest<ResourceComment>(`/${encodeURIComponent(id)}`);
			if (
				alive &&
				url === $pageUrl.href &&
				comment.resource_type === resource.resource_type &&
				comment.resource_id === resource.resource_id
			)
				view = { ...resource, comment_id: id };
		} catch (e) {
			if (alive && url === $pageUrl.href) toast.error(e instanceof Error ? e.message : String(e));
		}
	};
	$: if (deepLink && enabled && $pageUrl.href !== linked) {
		linked = $pageUrl.href;
		const id = $pageUrl.searchParams.get('comment');
		if (id) loadLink(id, linked);
	}
</script>

{#if enabled}
	<Dropdown
		show={open}
		align="end"
		maxHeight="min(36rem, calc(100dvh - 6rem))"
		contentClass="w-[min(24rem,calc(100vw-2rem))] h-[min(36rem,calc(100dvh-6rem))] rounded-3xl border border-base-100/50 dark:border-base-800/50 bg-base-0 dark:bg-base-900 shadow-lg overflow-hidden! z-50"
		onOpenChange={(state) => {
			if (!state) {
				if (open) view = null;
			} else if (!open) view = { ...resource };
		}}
	>
		<CommentButton
			{className}
			{wrapperClassName}
			{resource}
			onComment={(request) => (view = open ? null : request)}
		/>
		<div slot="content" class="h-full">
			{#if open && view}
				{#key `${$user?.id}:${resource.resource_type}:${resource.resource_id}:${view.comment_id ?? ''}`}
					<CommentsPanel bind:view modal={showResource} onClose={() => (view = null)} />
				{/key}
			{/if}
		</div>
	</Dropdown>
{/if}
