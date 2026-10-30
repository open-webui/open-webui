<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Message from '$lib/components/channel/Messages/Message.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import FaceSmile from '$lib/components/icons/FaceSmile.svelte';
	import dayjs from 'dayjs';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import CommentComposer from './CommentComposer.svelte';
	import { commentsRequest, type ResourceComment } from '$lib/apis/comments';
	import { highlightAnchor } from './anchors';
	import { commentLink } from '$lib/utils';
	export let comment: ResourceComment;
	export let onReply: (comment: ResourceComment) => void;
	export let onChange: () => Promise<void>;
	const i18n = getContext<any>('i18n');
	let editing = false;
	let confirmDelete = false;
	let unavailable = false;
	let busy = false;
	let editingEtag = comment.etag;
	$: message = {
		...comment,
		user_id: comment.user?.id,
		latest_reply_at: comment.latest_reply_at ?? comment.updated_at,
		reactions: comment.reactions.map((r) => ({ ...r, users: [] }))
	};
	const action = async (fn: () => Promise<unknown>) => {
		if (busy) return;
		busy = true;
		try {
			await fn();
			await onChange();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : String(e));
		} finally {
			busy = false;
		}
	};
	const react = (name: string) => {
		const remove = comment.reactions.some((r) => r.name === name && r.reacted);
		return action(() =>
			commentsRequest(
				`/${comment.id}/reactions${remove ? `?name=${encodeURIComponent(name)}` : ''}`,
				remove ? 'DELETE' : 'PUT',
				remove ? undefined : { name }
			)
		);
	};
	const actionClass =
		'flex size-6 items-center justify-center rounded-md text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200 transition';
</script>

<ConfirmDialog
	bind:show={confirmDelete}
	title={$i18n.t('Delete comment?')}
	message={$i18n.t('This cannot be undone. Replies will remain visible.')}
	onConfirm={() => {
		action(() => commentsRequest(`/${comment.id}?etag=${comment.etag}`, 'DELETE'));
	}}
/>
<div id={`comment-${comment.id}`} class="comment-item group/comment">
	<Message
		className="px-3 py-1.5! rounded-lg bg-transparent hover:bg-transparent!"
		{message}
		channel={null}
		id="comments"
		thread={true}
		showUserProfile={!!comment.user}
		disabled={!!comment.deleted_at || busy}
		onReply={() => onReply(comment)}
		onReaction={react}
	>
		<svelte:fragment slot="header">
			<div class="mb-1.5 flex min-w-0 items-center gap-2">
				<div class="-ml-1 size-6 shrink-0">
					<ProfilePreview user={comment.user}>
						<ProfileImage
							src={comment.user?.id
								? `${WEBUI_API_BASE_URL}/users/${comment.user.id}/profile/image`
								: undefined}
							className="size-6 shrink-0 rounded-full!"
						/>
					</ProfilePreview>
				</div>
				<span class="min-w-0 truncate text-[0.8125rem] font-medium text-gray-900 dark:text-gray-100"
					>{comment.user?.name ?? $i18n.t('Unknown User')}</span
				>
				<Tooltip
					className="ms-auto flex shrink-0"
					content={dayjs(comment.created_at / 1000000)
						.locale($i18n.language)
						.format('LLLL')}
				>
					<span class="shrink-0 text-xs text-gray-400 dark:text-gray-500"
						>{dayjs(comment.created_at / 1000000)
							.locale($i18n.language)
							.fromNow()}</span
					>
				</Tooltip>
				<div class="shrink-0">
					{#if !comment.deleted_at && !busy}
						<Dropdown align="end" closeOnSelect>
							<Tooltip content={$i18n.t('More')}>
								<button type="button" aria-label={$i18n.t('More')} class={actionClass}>
									<EllipsisHorizontal className="size-4" />
								</button>
							</Tooltip>
							<div slot="content">
								<DropdownMenu className="min-w-36">
									{#if !comment.reactions.length}
										<EmojiPicker align="end" onSubmit={react}>
											<button
												type="button"
												class="flex w-full h-[1.6875rem] items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/60 dark:hover:bg-gray-800/60"
											>
												<FaceSmile className="size-3.5" /><span>{$i18n.t('Add Reaction')}</span>
											</button>
										</EmojiPicker>
									{/if}
									{#if comment.can_edit}
										<button
											type="button"
											on:click={() => {
												editingEtag = comment.etag;
												editing = true;
											}}><Pencil /><span>{$i18n.t('Edit')}</span></button
										>
									{/if}
									<button
										type="button"
										on:click={() => {
											navigator.clipboard
												.writeText(new URL(commentLink(comment), location.origin).href)
												.catch((e) => toast.error(String(e)));
										}}><Link /><span>{$i18n.t('Copy link')}</span></button
									>
									{#if comment.can_delete}
										<hr class="border-gray-100 dark:border-gray-800" />
										<button type="button" on:click={() => (confirmDelete = true)}>
											<GarbageBin /><span>{$i18n.t('Delete')}</span>
										</button>
									{/if}
								</DropdownMenu>
							</div>
						</Dropdown>
					{/if}
				</div>
			</div>
		</svelte:fragment>
		<svelte:fragment slot="content">
			{#if comment.deleted_at}<p class="text-xs text-gray-500">{$i18n.t('Comment deleted')}</p>
			{:else if editing}
				<div class="py-2">
					<CommentComposer
						resource={comment}
						draftKey={`edit:${comment.id}`}
						initialContent={comment.content}
						submitLabel="Save"
						onCancel={() => (editing = false)}
						onSubmit={async (content) => {
							await commentsRequest(`/${comment.id}`, 'PATCH', { content, etag: editingEtag });
							editing = false;
							await onChange();
						}}
					/>
				</div>
			{:else}
				{#if comment.meta?.anchor}
					<button
						type="button"
						class="my-1 max-h-24 w-full overflow-auto border-l-2 border-gray-200 dark:border-gray-700 ps-2 text-left text-xs text-gray-500 dark:text-gray-400 whitespace-pre-wrap break-words"
						on:click={() =>
							(unavailable = !highlightAnchor(
								comment,
								comment.target_id ?? '',
								comment.meta!.anchor!
							))}>{comment.meta.anchor.quote}</button
					>
					{#if unavailable}<p class="mb-1 text-[0.6875rem] text-gray-500">
							{$i18n.t('Original passage changed or is unavailable.')}
							<a class="underline" href={commentLink(comment)}>{$i18n.t('Open source')}</a>
						</p>{/if}
				{:else if comment.target_id}<a
						class="text-[0.6875rem] text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
						href={commentLink(comment)}
						>{$i18n.t(comment.target_type === 'note_page' ? 'Page comment' : 'Message comment')}</a
					>{/if}
				<div class="markdown-prose comment-body text-gray-600 dark:text-gray-300">
					<Markdown
						id={`comment-body-${comment.id}`}
						content={comment.content}
						allowEmbeds={false}
						allowHtml={false}
						editCodeBlock={false}
					/>
				</div>
			{/if}
		</svelte:fragment>
		<svelte:fragment slot="footer">
			{#if !comment.deleted_at && !editing}
				<div class="mt-1 flex h-5 items-center gap-3">
					<button
						type="button"
						disabled={busy}
						class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-200 transition"
						on:click={() => onReply(comment)}>{$i18n.t('Reply')}</button
					>
				</div>
			{/if}
		</svelte:fragment>
	</Message>
</div>
