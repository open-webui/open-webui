<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { commentsRequest, type ResourceComment } from '$lib/apis/comments';
	import CommentItem from './CommentItem.svelte';
	import CommentReplyComposer from './CommentReplyComposer.svelte';
	import { groupReplies } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	export let parent: ResourceComment;
	export let replyTo: ResourceComment | null;
	export let onCancel: () => void;
	export let onSubmitted: (id: string) => void;
	export let onPosted: (comment: ResourceComment) => void;
	export let postedComment: ResourceComment | null = null;
	export let revision: number;
	export let linkedCommentId: string | null = null;
	export let onReply: (comment: ResourceComment) => void;
	export let onChange: () => Promise<void>;
	export let onError: (error: unknown) => void;
	export let onLoaded: () => void = () => {};
	const i18n = getContext<any>('i18n');
	type CommentPage = { items: ResourceComment[]; next_cursor: string | null };
	let items: ResourceComment[] = [];
	$: children = groupReplies(items, parent.id);
	let cursor: string | null = null;
	let loading = false;
	let alive = true;
	let version = 0;
	let insertedId: string | null = null;
	$: if (postedComment?.parent_id === parent.id && postedComment.id !== insertedId) {
		// Show the saved reply in the same update that removes its composer.
		// Ignore older requests and avoid scrolling while the layout settles.
		++version;
		loading = false;
		items = [...items.filter((comment) => comment.id !== postedComment.id), postedComment];
		insertedId = postedComment.id;
	}
	const fetchPage = (cursor?: string) =>
		commentsRequest<CommentPage>(
			`/${parent.id}/replies${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`
		);
	const loadAncestors = async (comments: ResourceComment[], request: number) => {
		const ids = new Set(comments.map((comment) => comment.id));
		// A linked reply can be outside the loaded page, along with its ancestors.
		for (const comment of comments) {
			const target = comment.reply_to_id;
			if (!target || target === parent.id || ids.has(target)) continue;
			if (!alive || request !== version) return;
			const ancestor = await commentsRequest<ResourceComment>(`/${target}`);
			if (ancestor.parent_id !== parent.id) throw new Error('Reply belongs to another comment');
			ids.add(ancestor.id);
			comments.push(ancestor);
		}
	};
	const refresh = async () => {
		const request = ++version;
		loading = true;
		try {
			const result = await fetchPage();
			while (alive && result.next_cursor && result.items.length < items.length) {
				const next = await fetchPage(result.next_cursor);
				result.items.push(...next.items);
				result.next_cursor = next.next_cursor;
			}
			if (linkedCommentId && !result.items.some((c) => c.id === linkedCommentId))
				result.items.push(await commentsRequest<ResourceComment>(`/${linkedCommentId}`));
			await loadAncestors(result.items, request);
			if (!alive || request !== version) return;
			items = result.items;
			cursor = result.next_cursor;
		} catch (e) {
			if (alive && request === version) onError(e);
		} finally {
			if (alive && request === version) {
				loading = false;
				await tick();
				if (alive && request === version) onLoaded();
			}
		}
	};
	const more = async () => {
		if (!cursor || loading) return;
		const request = ++version;
		loading = true;
		try {
			const result = await fetchPage(cursor);
			const combined = [
				...items,
				...result.items.filter((c) => !items.some((old) => old.id === c.id))
			];
			await loadAncestors(combined, request);
			if (!alive || request !== version) return;
			items = combined;
			cursor = result.next_cursor;
		} catch (e) {
			if (alive && request === version) onError(e);
		} finally {
			if (alive && request === version) loading = false;
		}
	};
	$: if (revision >= 0 && (parent.reply_count > 0 || linkedCommentId)) refresh();
	onDestroy(() => {
		alive = false;
		++version;
	});
</script>

{#snippet branch(parentId: string)}
	{#each children.get(parentId) ?? [] as comment (comment.id)}
		<CommentItem {comment} {onReply} {onChange} />
		{#if replyTo?.id === comment.id}
			<div class="ms-4">
				<CommentReplyComposer {comment} {onCancel} {onSubmitted} {onPosted} />
			</div>
		{/if}
		{#if children.has(comment.id)}
			<div
				id={`comment-replies-${comment.id}`}
				class="ms-4 border-s border-gray-200/40 dark:border-gray-700/30"
			>
				{@render branch(comment.id)}
			</div>
		{/if}
	{/each}
{/snippet}

{#if items.length || loading}
	<div
		id={`comment-replies-${parent.id}`}
		aria-busy={loading}
		class="ms-4 border-s border-gray-200/40 dark:border-gray-700/30"
	>
		{@render branch(parent.id)}
		{#if loading && !items.length}<div class="flex justify-center py-2">
				<Spinner className="size-4" />
			</div>{/if}
		{#if cursor}<button
				type="button"
				class="mx-4 my-2 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
				disabled={loading}
				on:click={more}>{$i18n.t('Load more')}</button
			>{/if}
	</div>
{/if}
