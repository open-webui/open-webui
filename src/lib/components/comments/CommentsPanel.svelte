<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { socket, user, commentsView, commentCounts, type CommentsView } from '$lib/stores';
	import {
		commentsRequest,
		getComments,
		resourceQuery,
		CommentError,
		type CommentResource,
		type ResourceComment
	} from '$lib/apis/comments';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CommentItem from './CommentItem.svelte';
	import CommentReplies from './CommentReplies.svelte';
	import CommentComposer from './CommentComposer.svelte';
	import CommentReplyComposer from './CommentReplyComposer.svelte';
	export let view: CommentsView;
	export let embedded = false;
	export let onCountChange: (count: number) => void = () => {};
	let total: number | null = null;
	const i18n = getContext<any>('i18n');
	const resourceLabels = {
		model: 'Model',
		knowledge: 'Knowledge',
		prompt: 'Prompt',
		skill: 'Skill',
		tool: 'Tool',
		note: 'Note',
		chat: 'Chat'
	};
	let resource: CommentResource | null = null;
	let title = '';
	$: if (resource && total !== null && $user)
		commentCounts.update((counts) => ({
			...counts,
			[`${$user.id}:${resourceQuery(resource)}`]: total
		}));
	let composerVersion = 0;
	let loadedCount = 0;
	let items: ResourceComment[] = [];
	let cursor: string | null = null;
	let replyTo: ResourceComment | null = null;
	let postedComment: ResourceComment | null = null;
	let linkedRootId: string | null = null;
	let linkedCommentId: string | null = null;
	let error = '';
	let loading = true;
	let alive = true;
	let loadingMore = false;
	let refreshTimer: ReturnType<typeof setTimeout>;
	let connection: import('socket.io-client').Socket | null = null;
	let refreshVersion = 0;
	let revision = 0;
	let previousView = view;
	$: if (view !== previousView) {
		previousView = view;
		replyTo = null;
	}
	const clearContext = () => {
		replyTo = null;
		view = { ...view, target_id: undefined, target_type: undefined, anchor: undefined };
	};
	const reply = (comment: ResourceComment) => {
		replyTo = comment;
	};
	const postedReply = (comment: ResourceComment) => {
		if (!alive) return;
		postedComment = comment;
		linkedRootId = comment.parent_id;
		linkedCommentId = comment.id;
		void refresh();
	};
	const fail = (e: unknown) => {
		if (!alive) return;
		error = e instanceof Error ? e.message : String(e);
		if (e instanceof CommentError && [401, 403, 404].includes(e.status)) {
			items = [];
			replyTo = null;
			resource = null;
		}
	};
	const refresh = async () => {
		if (!resource || !alive) return;
		const version = ++refreshVersion;
		try {
			const result = await getComments(resource);
			while (alive && result.next_cursor && result.items.length < loadedCount) {
				const next = await getComments(resource, result.next_cursor);
				result.items.push(...next.items);
				result.next_cursor = next.next_cursor;
			}
			if (!alive || version !== refreshVersion) return;
			loadedCount = result.items.length;
			if (linkedRootId && !result.items.some((c) => c.id === linkedRootId))
				result.items.push(await commentsRequest<ResourceComment>(`/${linkedRootId}`));
			if (!alive || version !== refreshVersion) return;
			items = result.items.sort((a, b) => a.created_at - b.created_at || a.id.localeCompare(b.id));
			cursor = result.next_cursor;
			total = result.total;
			onCountChange(total);
			revision += 1;
			error = '';
		} catch (e) {
			if (version === refreshVersion) fail(e);
		}
	};
	const join = () => {
		if (resource)
			connection?.emit('comments:join', resource, (result: { error?: string }) => {
				if (result?.error) fail(new CommentError(403, result.error));
			});
	};
	const changed = (data: CommentResource) => {
		if (
			data.resource_type !== resource?.resource_type ||
			data.resource_id !== resource?.resource_id
		)
			return;
		clearTimeout(refreshTimer);
		refreshTimer = setTimeout(refresh, 150);
	};
	const reconnect = () => {
		join();
		refresh();
	};
	const unavailable = () =>
		fail(new CommentError(403, $i18n.t('Comments are no longer available.')));
	const setup = async () => {
		loading = true;
		try {
			const context = await commentsRequest<CommentResource & { title: string }>(
				`/context?${resourceQuery(view)}`
			);
			if (!alive) return;
			resource = { resource_type: context.resource_type, resource_id: context.resource_id };
			title = context.title;
			if (view.comment_id) {
				const comment = await commentsRequest<ResourceComment>(`/${view.comment_id}`);
				if (!alive) return;
				linkedRootId = comment.parent_id ?? comment.id;
				linkedCommentId = comment.id;
			}
			await refresh();
			join();
		} catch (e) {
			fail(e);
		} finally {
			if (alive) loading = false;
		}
		await tick();
		if (alive && linkedCommentId === linkedRootId)
			document.getElementById(`comment-${linkedRootId}`)?.scrollIntoView({ block: 'nearest' });
	};
	const more = async () => {
		if (!resource || loadingMore) return;
		loadingMore = true;
		const version = ++refreshVersion;
		try {
			const result = await getComments(resource, cursor ?? undefined);
			if (!alive || version !== refreshVersion) return;
			loadedCount += result.items.length;
			items = [...items, ...result.items.filter((c) => !items.some((old) => old.id === c.id))].sort(
				(a, b) => a.created_at - b.created_at || a.id.localeCompare(b.id)
			);
			cursor = result.next_cursor;
			total = result.total;
			onCountChange(total);
		} catch (e) {
			if (version === refreshVersion) fail(e);
		} finally {
			loadingMore = false;
		}
	};
	onMount(() => {
		setup();
	});
	$: if ($socket !== connection) {
		connection?.off('comments:changed', changed);
		connection?.off('connect', reconnect);
		connection?.off('comments:unavailable', unavailable);
		connection = $socket;
		connection?.on('comments:changed', changed);
		connection?.on('connect', reconnect);
		connection?.on('comments:unavailable', unavailable);
		join();
	}
	onDestroy(() => {
		alive = false;
		clearTimeout(refreshTimer);
		connection?.emit('comments:leave');
		connection?.off('comments:changed', changed);
		connection?.off('connect', reconnect);
		connection?.off('comments:unavailable', unavailable);
	});
</script>

<svelte:window on:focus={refresh} />
<div class="flex flex-col min-h-0 w-full h-full {embedded ? '' : 'bg-white dark:bg-gray-900'}">
	{#if !embedded}
		<header
			class="sticky top-0 flex min-h-10 shrink-0 items-center justify-between px-4 py-1.5"
		>
			<h2 class="flex items-center gap-1 font-normal text-sm" {title}>
				{$i18n.t('Comments')}{#if total !== null && total > 0}<span
						class="text-[0.8125rem] leading-none text-gray-400/70 dark:text-gray-500/70 font-normal"
						>{total}</span
					>{/if}
			</h2>
			<Tooltip content={$i18n.t('Close')}>
				<button
					type="button"
					aria-label={$i18n.t('Close')}
					class="flex h-7 items-center justify-center rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 px-0"
					on:click={() => commentsView.set(null)}><XMark className="size-4" /></button
				>
			</Tooltip>
		</header>
	{/if}
	{#if view.modal && resource && title}
		<div class="flex min-w-0 shrink-0 items-baseline gap-1.5 px-4 pb-1 leading-4">
			<span class="shrink-0 text-[0.6875rem] text-gray-500 dark:text-gray-400">
				{$i18n.t(resourceLabels[resource.resource_type])}
			</span>
			<span class="truncate text-xs font-normal" {title}>{title}</span>
		</div>
	{/if}
	<div
		class="flex-1 min-h-0 w-full overflow-y-auto will-change-transform"
		class:flex={!items.length}
		class:flex-col={!items.length}
	>
		{#if loading}<div class="flex justify-center py-5"><Spinner className="size-5" /></div>{/if}
		{#if error}<div class="px-4 py-2">
				<p role="alert" class="text-xs text-red-500">{error}</p>
				<button
					type="button"
					class="mt-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
					on:click={setup}>{$i18n.t('Retry')}</button
				>
			</div>{/if}
		{#if resource && !loading}
			{#if !items.length}<div
					class="flex flex-1 items-center justify-center px-4 py-6 text-center text-xs text-gray-500"
				>
					{$i18n.t('No comments yet')}
				</div>{/if}
			{#each items as comment (comment.id)}
				<div class="mx-1.5 my-0.5">
					<CommentItem {comment} onReply={reply} onChange={refresh} />

					{#if replyTo?.id === comment.id}
						<div class="ms-4">
							{#key replyTo.id}<CommentReplyComposer
									comment={replyTo}
									onCancel={() => (replyTo = null)}
									onSubmitted={(id) => {
										if (replyTo?.id === id) replyTo = null;
									}}
									onPosted={postedReply}
								/>{/key}
						</div>
					{/if}
					<CommentReplies
						parent={comment}
						{revision}
						{replyTo}
						{postedComment}
						onCancel={() => (replyTo = null)}
						onSubmitted={(id) => {
							if (replyTo?.id === id) replyTo = null;
						}}
						onPosted={postedReply}
						linkedCommentId={linkedRootId === comment.id && linkedCommentId !== comment.id
							? linkedCommentId
							: null}
						onReply={reply}
						onChange={refresh}
						onError={fail}
					/>
				</div>
			{/each}
			{#if cursor}<button
					type="button"
					class="mx-4 my-3 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
					disabled={loadingMore}
					on:click={more}>{$i18n.t('Load more')}</button
				>{/if}
		{/if}
	</div>
	{#if resource && !loading}
		<div class="shrink-0 px-3 pt-1 pb-3 mt-2">
			{#key `${resourceQuery(resource)}:${composerVersion}`}
				<CommentComposer
					onSubmitted={async () => {
						composerVersion++;
						await tick();
						if (alive && linkedCommentId)
							document
								.getElementById(`comment-${linkedCommentId}`)
								?.scrollIntoView({ block: 'nearest' });
					}}
					{resource}
					draftKey={`${$user?.id}:${resourceQuery(resource)}:root`}
					contextLabel={view.target_id
						? $i18n.t(
								view.target_type === 'note_page'
									? 'Comment on this page'
									: 'Comment on this message'
							)
						: ''}
					quote={view.anchor?.quote ?? ''}
					onClearContext={clearContext}
					onSubmit={async (content, temp_id) => {
						const created = await commentsRequest<ResourceComment>('/', 'POST', {
							...resource,
							content,
							temp_id,
							target_type: view.target_type,
							target_id: view.target_id,
							anchor: view.anchor
						});
						if (!alive) return;
						linkedRootId = created.id;
						linkedCommentId = created.id;
						clearContext();
						await refresh();
					}}
				/>
			{/key}
		</div>
	{/if}
</div>
