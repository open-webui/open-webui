<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import {
		config,
		user,
		mobile,
		commentsView,
		chatCommentsId,
		noteCommentsId,
		commentDrafts,
		openComments
	} from '$lib/stores';
	import { commentsRequest, type ResourceComment } from '$lib/apis/comments';
	import ResizableSidePanel from '$lib/components/common/ResizableSidePanel.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import CommentsPanel from './CommentsPanel.svelte';
	import CommentHighlights from './CommentHighlights.svelte';
	import { selectedComment, commentSelectionDraft } from './anchors';
	import { toast } from 'svelte-sonner';
	const i18n = getContext<any>('i18n');
	let selection: ReturnType<typeof selectedComment> = null;
	let account: string | null = null;
	let deepLink = '';
	let currentUrl = $page.url.href;
	let navigation = 0;
	$: if ($page.url.href !== currentUrl) {
		currentUrl = $page.url.href;
		navigation += 1;
		deepLink = '';
		commentsView.set(null);
		commentSelectionDraft.set(null);
		selection = null;
	}
	$: commentsAllowed = !!(
		$config?.features?.enable_comments &&
		$user &&
		!$page.url.pathname.startsWith('/s/')
	);
	let preparing = false;
	$: if (($user?.id ?? null) !== account) {
		account = $user?.id ?? null;
		commentsView.set(null);
		commentSelectionDraft.set(null);
		selection = null;
		tick().then(() => commentDrafts.clear());
	}
	const loadLink = async (id: string) => {
		const version = navigation;
		const accountId = account;
		try {
			const comment = await commentsRequest<ResourceComment>(`/${encodeURIComponent(id)}`);
			if (
				version === navigation &&
				accountId === account &&
				$page.url.searchParams.get('comment') === id
			)
				openComments(
					{ resource_type: comment.resource_type, resource_id: comment.resource_id },
					{ comment_id: id }
				);
		} catch (e) {
			if (version === navigation && accountId === account)
				toast.error(e instanceof Error ? e.message : String(e));
		}
	};
	$: if (commentsAllowed && $page.url.searchParams.get('comment') && deepLink !== $page.url.href) {
		deepLink = $page.url.href;
		loadLink($page.url.searchParams.get('comment')!);
	}
	const select = () => {
		if (!preparing) selection = commentsAllowed ? selectedComment() : null;
	};
	const commentSelection = async () => {
		const selected = selection;
		if (!selected || preparing) return;
		preparing = true;
		const version = navigation;
		const accountId = account;
		try {
			await selected.options.prepare?.();
			if (version !== navigation || accountId !== account) return;
			if (selected.options.resource_type === 'chat') commentSelectionDraft.set(selected);
			else
				openComments(
					{
						resource_type: selected.options.resource_type,
						resource_id: selected.options.resource_id
					},
					{
						target_type: selected.options.target_type,
						target_id: selected.options.target_id,
						anchor: selected.anchor
					}
				);
			window.getSelection()?.removeAllRanges();
			selection = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : String(e));
		} finally {
			preparing = false;
		}
	};
	onMount(() => {
		document.addEventListener('mouseup', select);
		document.addEventListener('keyup', select);
		return () => {
			document.removeEventListener('mouseup', select);
			document.removeEventListener('keyup', select);
		};
	});
</script>

<svelte:window
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			if (!$commentsView?.modal) commentsView.set(null);
			selection = null;
		}
	}}
	on:scroll|capture={() => (selection = null)}
/>
{#if commentsAllowed}
	{#key account}<CommentHighlights />{/key}
	{#if selection && !selection.options.toolbar_id}
		<button
			type="button"
			class="fixed z-9999 flex items-center gap-1 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 px-2 py-1 text-xs shadow-xl"
			style={`left:${Math.max(8, Math.min(selection.rect.left, window.innerWidth - 130))}px;top:${Math.min(window.innerHeight - 48, selection.rect.bottom + 12)}px`}
			on:mousedown|preventDefault
			disabled={preparing}
			on:click={commentSelection}><Annotation className="size-3" />{$i18n.t('Comment')}</button
		>
	{/if}
	{#if $commentsView && ($commentsView.modal || !(($commentsView.resource_type === 'chat' && $commentsView.resource_id === $chatCommentsId) || ($commentsView.resource_type === 'note' && $commentsView.resource_id === $noteCommentsId)))}
		{#key `${account}:${$commentsView.resource_type}:${$commentsView.resource_id}:${$commentsView.comment_id ?? ''}`}
			{#if $commentsView.modal}
				<Modal
					show={true}
					size="md"
					ariaLabel={$i18n.t('Comments')}
					className="bg-white dark:bg-gray-900 rounded-4xl overflow-hidden"
					onRequestClose={() => commentsView.set(null)}
				>
					<div class="h-[min(70dvh,40rem)]">
						<CommentsPanel bind:view={$commentsView} />
					</div>
				</Modal>
			{:else if $mobile}
				<Drawer show={true} onClose={() => commentsView.set(null)}
					><div class="h-dvh"><CommentsPanel bind:view={$commentsView} /></div></Drawer
				>
			{:else}
				<ResizableSidePanel
					open={true}
					width={350}
					minWidth={300}
					maxWidth={640}
					minSiblingWidth={400}
					resizerId="comments-resizer"
					storageKey="comments-panel-width"
					className="h-full min-h-0"
					onClose={() => commentsView.set(null)}
				>
					<aside aria-label={$i18n.t('Comments')} class="h-full w-full">
						<CommentsPanel bind:view={$commentsView} />
					</aside>
				</ResizableSidePanel>
			{/if}
		{/key}
	{/if}
{/if}

<style>
	:global(::highlight(resource-comment)) {
		background: #fde68a;
		color: #111827;
	}
</style>
