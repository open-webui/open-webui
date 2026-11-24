<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, setContext, tick } from 'svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import {
		getChatById,
		getChatPinnedStatusById,
		toggleChatPinnedStatusById
	} from '$lib/apis/chats';
	import { chats, folders, settings, theme, user, visibleControls } from '$lib/stores';
	import { createMessagesList } from '$lib/utils';
	import { saveChatPdf, saveTextPdf } from '$lib/utils/pdf';
	import { getOutputText } from '$lib/components/chat/Messages/structuredOutput';
	import ArchiveBoxIcon from '$lib/components/icons/ArchiveBox.svelte';
	import CopyIcon from './icons/Copy.svelte';
	import DownloadIcon from './icons/Download.svelte';
	import EditPencilIcon from './icons/EditPencil.svelte';
	import FolderIcon from './icons/Folder.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import PinIcon from './icons/Pin.svelte';
	import PinSlashIcon from './icons/PinSlash.svelte';
	import ShareIcon from './icons/Share.svelte';
	import TrashIcon from './icons/Trash.svelte';
	import ChatCheckIcon from '$lib/components/icons/ChatCheck.svelte';

	const i18n = getContext('i18n');
	setContext('exporting', true);

	export let shareHandler: Function;
	export let moveChatHandler: Function;

	export let cloneChatHandler: Function;
	export let archiveChatHandler: Function;
	export let renameHandler: Function;
	export let deleteHandler: Function;
	export let onOpen: () => void = () => {};
	export let onClose: Function;
	export let markUnreadHandler: Function = () => {};

	export let chatId = '';
	export let archived = false;
	export let readonly = false;

	let show = false;
	let pinned = false;

	let chat = null;
	let showFullMessages = false;

	export let onPinChange: (chat: {
		pinned: boolean;
		folder_id: string | null;
	}) => void | Promise<void> = () => {};

	const pinHandler = async () => {
		const chat = await toggleChatPinnedStatusById(localStorage.token, chatId);
		await onPinChange(chat);
	};

	const checkPinned = async () => {
		pinned = await getChatPinnedStatusById(localStorage.token, chatId);
	};

	const getChatAsText = async (chat) => {
		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const chatText = messages.reduce((a, message, i, arr) => {
			const content = getOutputText(message.output) || message.content || '';
			return `${a}### ${message.role.toUpperCase()}\n${content}\n\n`;
		}, '');

		return chatText.trim();
	};

	const downloadTxt = async () => {
		const chat = await getChatById(localStorage.token, chatId);
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
		chat = await getChatById(localStorage.token, chatId);
		if (!chat) {
			return;
		}

		const filename = `chat-${chat.chat.title}.pdf`;
		if (!($settings?.stylizedPdfExport ?? true)) {
			await saveTextPdf(await getChatAsText(chat), filename);
			return;
		}

		showFullMessages = true;
		await tick();
		try {
			await saveChatPdf(document.getElementById('full-messages-container')!, filename);
		} finally {
			showFullMessages = false;
		}
	};

	const downloadJSONExport = async () => {
		const chat = await getChatById(localStorage.token, chatId);

		if (chat) {
			let blob = new Blob([JSON.stringify([chat])], {
				type: 'application/json'
			});
			saveAs(blob, `chat-export-${Date.now()}.json`);
		}
	};

	$: if (show && !readonly) {
		checkPinned();
	}
</script>

{#if chat && showFullMessages}
	<div class="hidden w-full h-full flex-col">
		<div id="full-messages-container">
			<Messages
				className="h-full flex pt-4 pb-8 w-full"
				chatId={`chat-preview-${chat?.id ?? ''}`}
				user={$user}
				readOnly={true}
				history={chat.chat.history}
				messages={chat.chat.messages}
				autoScroll={true}
				sendMessage={() => {}}
				continueResponse={() => {}}
				regenerateResponse={() => {}}
				messagesCount={null}
				editCodeBlock={false}
			/>
		</div>
	</div>
{/if}

<Dropdown
	closeOnSelect
	bind:show
	onOpenChange={(state) => {
		if (state) {
			onOpen();
		} else {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="select-none min-w-[12.5rem] transition">
			{#if !readonly && ($user?.role === 'admin' || ($user.permissions?.chat?.share ?? true))}
				<button
					role="menuitem"
					draggable="false"
					class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
					on:click={() => {
						shareHandler();
					}}
				>
					<ShareIcon className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Share')}</div>
				</button>
			{/if}

			{#if !readonly && ($user?.role === 'admin' || ($user.permissions?.chat?.export ?? true))}
				<DropdownSub contentClass="select-none z-50">
					<button
						role="menuitem"
						slot="trigger"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
					>
						<DownloadIcon className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Download')}</div>
					</button>

					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
						on:click={() => {
							downloadJSONExport();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Export chat (.json)')}</div>
					</button>

					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</button>

					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 select-none w-full"
						on:click={() => {
							toast.promise(downloadPdf(), {
								loading: $i18n.t('Preparing download...'),
								error: $i18n.t('Download failed')
							});
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
					</button>
				</DropdownSub>
			{/if}

			<button
				role="menuitem"
				draggable="false"
				class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
				on:click={() => {
					renameHandler();
				}}
			>
				<EditPencilIcon className="size-3.5" strokeWidth="1.5" />
				<div class="flex items-center">{$i18n.t('Rename')}</div>
			</button>

			{#if !readonly}
				<button
					role="menuitem"
					draggable="false"
					class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
					on:click={() => {
						markUnreadHandler();
					}}
				>
					<ChatCheckIcon className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Mark as unread')}</div>
				</button>

				<hr class="border-base-50/30 dark:border-base-800/30 mx-1 my-0.5" />

				<button
					role="menuitem"
					draggable="false"
					class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
					on:click={() => {
						pinHandler();
					}}
				>
					{#if pinned}
						<PinSlashIcon className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Unpin')}</div>
					{:else}
						<PinIcon className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Pin')}</div>
					{/if}
				</button>

				{#if $user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true)}
					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
						on:click={() => {
							cloneChatHandler();
						}}
					>
						<CopyIcon className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Clone')}</div>
					</button>
				{/if}

				{#if chatId && $folders.length > 0}
					<DropdownSub contentClass="select-none z-50 max-h-52 overflow-y-auto scrollbar-hidden">
						<button
							role="menuitem"
							slot="trigger"
							draggable="false"
							class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 select-none w-full"
						>
							<FolderIcon className="size-3.5" />
							<div class="flex items-center">{$i18n.t('Move')}</div>
						</button>

						{#each $folders.sort((a, b) => b.updated_at - a.updated_at) as folder}
							<button
								role="menuitem"
								draggable="false"
								class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 overflow-hidden w-full"
								on:click={() => {
									moveChatHandler(chatId, folder.id);
								}}
							>
								<div class="shrink-0">
									<FolderIcon className="size-3.5" />
								</div>

								<div class="truncate">{folder?.name ?? 'Folder'}</div>
							</button>
						{/each}
					</DropdownSub>
				{/if}

				{#if $visibleControls['chat.archive']}
					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
						on:click={() => {
							archiveChatHandler();
						}}
					>
						<ArchiveBoxIcon className="size-3.5" strokeWidth="1.7" />
						<div class="flex items-center">
							{archived ? $i18n.t('Unarchive') : $i18n.t('Archive')}
						</div>
					</button>
				{/if}

				{#if $user?.role === 'admin' || ($user?.permissions?.chat?.delete ?? true)}
					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-100 dark:hover:bg-base-900 w-full"
						on:click={() => {
							deleteHandler();
						}}
					>
						<TrashIcon className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				{/if}
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
