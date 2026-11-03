<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { user } from '$lib/stores';
	import { commentsRequest, resourceQuery, type ResourceComment } from '$lib/apis/comments';
	import CommentComposer from './CommentComposer.svelte';
	export let comment: ResourceComment;
	export let autofocus = true;
	export let className = 'px-3 py-2';
	export let onCancel: (() => void) | null;
	export let onSubmitted: (id: string) => void;
	export let onPosted: (comment: ResourceComment) => void;
	let postedComment: ResourceComment | null = null;
	let composer: CommentComposer;
	let container: HTMLDivElement;
	onMount(() => {
		if (!autofocus) return;
		tick().then(() => {
			container?.scrollIntoView({ block: 'nearest' });
			composer?.focus();
		});
	});
</script>

<div class={className} bind:this={container}>
	<CommentComposer
		bind:this={composer}
		resource={comment}
		draftKey={`${$user?.id}:${resourceQuery(comment)}:${comment.id}`}
		submitLabel="Reply"
		onSubmitted={() => {
			onSubmitted(comment.id);
			if (postedComment) onPosted(postedComment);
		}}
		{onCancel}
		onSubmit={async (content, temp_id) => {
			postedComment = await commentsRequest<ResourceComment>(
				`/${comment.parent_id ?? comment.id}/replies`,
				'POST',
				{ content, temp_id, reply_to_id: comment.id }
			);
		}}
	/>
</div>
