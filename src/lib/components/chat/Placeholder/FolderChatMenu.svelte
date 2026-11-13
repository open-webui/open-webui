<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { chatId, user, tags } from '$lib/stores';
	import {
		archiveChatById,
		cloneChatById,
		deleteChatById,
		getAllTags,
		markChatUnreadById,
		updateChatFolderIdById
	} from '$lib/apis/chats';
	import { refreshSidebar } from '$lib/stores/chatList';
	import { updateFolderChatLists } from '$lib/stores/folderStates';
	import type { WorkspaceChat } from '$lib/utils/folders';
	import ChatMenu from '$lib/components/layout/Sidebar/ChatMenu.svelte';
	import MoreHorizontalIcon from '$lib/components/layout/Sidebar/icons/MoreHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ShareChatModal from '$lib/components/chat/ShareChatModal.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let chat: WorkspaceChat;
	/** Start renaming the chat inline in its row. */
	export let onRename: () => void = () => {};
	/** Reload the folder view after a change. */
	export let onChange: () => Promise<void> = async () => {};
	export let open = false;

	let showShare = false;
	let showDelete = false;
	let busy = false;

	// Same actions as the sidebar chat item, refreshing this view and the sidebar after each.
	async function run(action: () => Promise<unknown>, removed = false) {
		if (busy) return;
		busy = true;
		try {
			const result = await action();
			if (result === null) return;
			if (removed) {
				updateFolderChatLists({ id: chat.id }, undefined, true);
				if ($chatId === chat.id) {
					await goto('/');
					chatId.set('');
					await tick();
				}
			}
			await Promise.all([
				refreshSidebar(localStorage.token),
				getAllTags(localStorage.token).then((value) => tags.set(value)),
				onChange()
			]);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			busy = false;
		}
	}

	const clone = () =>
		run(async () => {
			if (!($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true))) {
				toast.error($i18n.t('Access prohibited'));
				return null;
			}
			const res = await cloneChatById(
				localStorage.token,
				chat.id,
				$i18n.t('Clone of {{TITLE}}', { TITLE: chat.title })
			);
			if (res) void goto(`/c/${res.id}`);
			return res;
		});

	const archive = () =>
		run(async () => {
			await archiveChatById(localStorage.token, chat.id);
			toast.success($i18n.t('Chat archived.'));
		}, true);

	const remove = () => run(() => deleteChatById(localStorage.token, chat.id), true);

	const move = (id: string, folderId: string) =>
		run(async () => {
			const res = await updateChatFolderIdById(localStorage.token, id, folderId);
			if (res) {
				updateFolderChatLists(res, folderId);
				toast.success($i18n.t('Chat moved successfully'));
			}
			return res;
		});

	const markUnread = () =>
		run(async () => {
			const res = await markChatUnreadById(localStorage.token, chat.id);
			if (res) updateFolderChatLists({ id: chat.id, last_read_at: res.last_read_at ?? 0 });
			return res;
		});
</script>

<ShareChatModal bind:show={showShare} chatId={chat.id} />

<DeleteConfirmDialog bind:show={showDelete} title={$i18n.t('Delete chat?')} on:confirm={remove}>
	<div class="flex-1 line-clamp-3 text-sm text-gray-500">
		{$i18n.t('This will delete')} <span class="font-normal">{chat.title}</span>.
	</div>
</DeleteConfirmDialog>

<ChatMenu
	readonly={!chat.can_edit_tags}
	chatId={chat.id}
	cloneChatHandler={clone}
	shareHandler={() => (showShare = true)}
	moveChatHandler={move}
	archiveChatHandler={archive}
	renameHandler={onRename}
	deleteHandler={() => (showDelete = true)}
	markUnreadHandler={markUnread}
	onOpen={() => (open = true)}
	onClose={() => (open = false)}
	onPinChange={() => onChange()}
>
	<button
		type="button"
		aria-label={$i18n.t('Chat Menu')}
		class="flex size-5 items-center justify-center rounded-md text-gray-400 transition hover:text-gray-700 dark:text-gray-500 dark:hover:text-white"
		disabled={busy}
	>
		<MoreHorizontalIcon className="size-3.5" strokeWidth="2" />
	</button>
</ChatMenu>
