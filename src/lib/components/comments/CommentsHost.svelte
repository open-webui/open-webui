<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { config, user, mobile, showControls, chatId } from '$lib/stores';
	import { commentsRequest, type ResourceComment } from '$lib/apis/comments';
	import ResizableSidePanel from '$lib/components/common/ResizableSidePanel.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import CommentsPanel, { type CommentsRequest } from './CommentsPanel.svelte';
	import CommentHighlights from './CommentHighlights.svelte';
	import { selectedComment, commentSelectionDraft } from './anchors';
	import { toast } from 'svelte-sonner';
	const i18n = getContext<any>('i18n');
	let comments: CommentsRequest | null = null;
	let selection: ReturnType<typeof selectedComment> = null;
	let account: string | null = null;
	let deepLink = '';
	let currentUrl = $page.url.href;
	let navigation = 0;
	$: if ($page.url.href !== currentUrl) {
		currentUrl = $page.url.href;
		navigation += 1;
		deepLink = '';
		comments = null;
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
		comments = null;
		commentSelectionDraft.set(null);
		selection = null;
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
				open({
					resource_type: comment.resource_type,
					resource_id: comment.resource_id,
					comment_id: id
				});
		} catch (e) {
			if (version === navigation && accountId === account)
				toast.error(e instanceof Error ? e.message : String(e));
		}
	};
	$: if (
		commentsAllowed &&
		$page.url.searchParams.get('comment') &&
		deepLink !== $page.url.href &&
		$page.route.id !== '/(app)/c/[id]' &&
		$page.route.id !== '/(app)/notes/[id]'
	) {
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
				document.dispatchEvent(
					new CustomEvent('open-comments', {
						detail: {
							resource_type: selected.options.resource_type,
							resource_id: selected.options.resource_id,
							target_type: selected.options.target_type,
							target_id: selected.options.target_id,
							anchor: selected.anchor
						}
					})
				);
			window.getSelection()?.removeAllRanges();
			selection = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : String(e));
		} finally {
			preparing = false;
		}
	};
	const open = (request: CommentsRequest) => {
		const note =
			request.resource_type === 'note' &&
			$page.route.id === '/(app)/notes/[id]' &&
			request.resource_id === $page.params.id;
		const modal =
			request.modal ?? (!note && !!document.querySelector('.modal, [aria-modal="true"]'));
		if (!modal && request.resource_type === 'chat' && request.resource_id === $chatId) {
			const { resource_type, resource_id, modal, ...target } = request;
			showControls.set({ ...target, tab: 'comments' });
		} else if (!note || modal) comments = { ...request, modal };
	};
	const openHandler = (event: Event) => open((event as CustomEvent<CommentsRequest>).detail);
	onMount(() => {
		document.addEventListener('open-comments', openHandler);
		document.addEventListener('mouseup', select);
		document.addEventListener('keyup', select);
		return () => {
			document.removeEventListener('open-comments', openHandler);
			document.removeEventListener('mouseup', select);
			document.removeEventListener('keyup', select);
		};
	});
</script>

<svelte:window
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			if (!comments?.modal) {
				comments = null;
				if ($showControls === 'comments' || typeof $showControls === 'object')
					showControls.set(false);
			}
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
	{#if comments}
		{#key `${account}:${comments.resource_type}:${comments.resource_id}:${comments.comment_id ?? ''}`}
			{#if comments.modal}
				<Modal
					show={true}
					size="md"
					ariaLabel={$i18n.t('Comments')}
					className="bg-white dark:bg-gray-900 rounded-4xl overflow-hidden"
					onRequestClose={() => (comments = null)}
				>
					<div class="h-[min(70dvh,40rem)]">
						<CommentsPanel bind:view={comments} onClose={() => (comments = null)} />
					</div>
				</Modal>
			{:else if $mobile}
				<Drawer show={true} onClose={() => (comments = null)}
					><div class="h-dvh">
						<CommentsPanel bind:view={comments} onClose={() => (comments = null)} />
					</div></Drawer
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
					onClose={() => (comments = null)}
				>
					<aside aria-label={$i18n.t('Comments')} class="h-full w-full">
						<CommentsPanel bind:view={comments} onClose={() => (comments = null)} />
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
