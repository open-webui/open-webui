<script lang="ts">
	import { getI18n } from '$lib/utils/context';

	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, tick } from 'svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Bookmark from '$lib/components/icons/Bookmark.svelte';
	import BookmarkSlash from '$lib/components/icons/BookmarkSlash.svelte';
	import {
		getChatById,
		getChatPinnedStatusById,
		toggleChatPinnedStatusById
	} from '$lib/apis/chats';
	import { createMessagesList } from '$lib/utils';
	import { downloadChatAsPDF } from '$lib/apis/utils';
	import Download from '$lib/components/icons/Download.svelte';
	import { toast } from 'svelte-sonner';
	import { getRequestToken } from '$lib/services/auth';
	import MoveChatModal from './MoveChatModal.svelte';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getI18n();

	export let cloneChatHandler: Function;
	export let archiveChatHandler: Function;
	export let renameHandler: Function;
	export let deleteHandler: Function;
	export let onClose: Function;
	export let buttonClass = '';
	export let ariaLabel = '';
	export let chatId = '';
	export let buttonID = '';

	let show = false;
	let pinned = false;
	let showMove = false;
	let showTags = false;

	const handleEscape = async (event: CustomEvent<{ originalEvent: KeyboardEvent }>) => {
		if (event.detail.originalEvent.key === 'Escape') {
			event.preventDefault();
			event.detail.originalEvent.stopPropagation();
			show = false;
			await tick();
			document.getElementById(buttonID)?.focus();
		}
	};

	const openDialog = async (dialog: 'move' | 'tags') => {
		show = false;
		await tick();
		if (dialog === 'move') showMove = true;
		else showTags = true;
	};

	const pinHandler = async () => {
		await toggleChatPinnedStatusById(getRequestToken(), chatId);
		dispatch('change', { buttonID });
		if (pinned) {
			toast.success($i18n.t('Chat unpinned. It will now appear in the regular list.'));
		} else {
			toast.success($i18n.t('Chat pinned. You can find it at the top section of your chat list.'));
		}
	};

	const checkPinned = async () => {
		pinned = await getChatPinnedStatusById(getRequestToken(), chatId);
	};

	const getChatAsText = async (chat: any) => {
		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const chatText = messages.reduce((a: any, message: any, i: any, arr: any) => {
			return `${a}### ${message.role.toUpperCase()}\n${message.content}\n\n`;
		}, '');

		return chatText.trim();
	};

	const downloadTxt = async () => {
		const chat: any = await getChatById(getRequestToken(), chatId);
		if (!chat) {
			return;
		}

		const chatText = await getChatAsText(chat);
		let blob = new Blob([chatText], {
			type: 'text/plain'
		});

		saveAs(blob, `chat-${chat.chat.title}.txt`);
	};

	const downloadPdf = async () => {
		const chat: any = await getChatById(getRequestToken(), chatId);
		if (!chat) {
			return;
		}

		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const blob = await downloadChatAsPDF(chat.chat.title, messages);

		// Create a URL for the blob
		const url = window.URL.createObjectURL(blob);

		// Create a link element to trigger the download
		const a = document.createElement('a');
		a.href = url;
		a.download = `chat-${chat.chat.title}.pdf`;

		// Append the link to the body and click it programmatically
		document.body.appendChild(a);
		a.click();

		// Remove the link from the body
		document.body.removeChild(a);

		// Revoke the URL to release memory
		window.URL.revokeObjectURL(url);
	};

	$: if (show) {
		checkPinned();
	}
</script>

<MoveChatModal
	bind:show={showMove}
	{chatId}
	returnFocusSelector={buttonID ? `#${buttonID}` : ''}
	on:change={(e) => dispatch('change', { buttonID: e.detail.focusId })}
/>

<Modal
	bind:show={showTags}
	size="sm"
	title={$i18n.t('Tags')}
	labelledBy={`chat-tags-title-${chatId}`}
	returnFocusSelector={buttonID ? `#${buttonID}` : ''}
>
	<div class="p-5 space-y-4">
		<h2 id={`chat-tags-title-${chatId}`} class="text-lg font-semibold">{$i18n.t('Tags')}</h2>
		<Tags
			{chatId}
			on:add={(e) => dispatch('tag', { type: 'add', name: e.detail.name })}
			on:delete={(e) => dispatch('tag', { type: 'delete', name: e.detail.name })}
		/>
		<button type="button" class="rounded-lg px-3 py-2" on:click={() => (showTags = false)}
			>{$i18n.t('Close')}</button
		>
	</div>
</Modal>

<Dropdown
	bind:show
	on:keydown={handleEscape}
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
	{buttonClass}
	{ariaLabel}
	{buttonID}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			on:keydown={handleEscape}
			class="w-full max-w-[200px] rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => openDialog('move')}
			>
				<div>{$i18n.t('Move to folder')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => openDialog('tags')}
			>
				<div>{$i18n.t('Tags')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					pinHandler();
				}}
			>
				{#if pinned}
					<BookmarkSlash strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Unpin')}</div>
				{:else}
					<Bookmark strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Pin')}</div>
				{/if}
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					renameHandler();
				}}
			>
				<Pencil strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Rename')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					cloneChatHandler();
				}}
			>
				<DocumentDuplicate strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Clone')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					archiveChatHandler();
				}}
			>
				<ArchiveBox strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Archive')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				>
					<Download strokeWidth="2" />

					<div class="flex items-center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					class="w-full rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
					transition={flyAndScale}
					sideOffset={8}
				>
					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
						on:click={() => {
							downloadPdf();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>
			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					deleteHandler();
				}}
			>
				<GarbageBin strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
