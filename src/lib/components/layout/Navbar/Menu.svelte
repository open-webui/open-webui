<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, setContext, tick } from 'svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import { saveChatPdf, saveTextPdf } from '$lib/utils/pdf';
	import { getOutputText } from '$lib/components/chat/Messages/structuredOutput';

	import {
		mobile,
		temporaryChat,
		theme,
		user,
		settings,
		folders,
		visibleControls
	} from '$lib/stores';

	import { getChatById } from '$lib/apis/chats';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import TagPicker from '$lib/components/chat/TagPicker.svelte';
	import Tag from '$lib/components/icons/Tag.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import EditPencilIcon from '$lib/components/layout/Sidebar/icons/EditPencil.svelte';

	const i18n = getContext('i18n');
	setContext('exporting', true);

	export let shareEnabled: boolean = false;
	export let readOnly: boolean = false;

	export let shareHandler: Function;
	export let renameHandler: Function;
	export let moveChatHandler: Function;

	export let archiveChatHandler: Function;
	export let deleteChatHandler: Function;

	// export let tagHandler: Function;

	export let chat;
	export let onClose: Function = () => {};
	export let scrollToTop: (() => void) | null = null;
	/** Overrides the global temporary chat state for chats with their own (side chats). */
	export let temporary: boolean | null = null;
	$: isTemporary = temporary ?? $temporaryChat;

	let showFullMessages = false;
	let show = false;

	const getChatAsText = async () => {
		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const chatText = messages.reduce((a, message, i, arr) => {
			const content = getOutputText(message.output) || message.content || '';
			return `${a}### ${message.role.toUpperCase()}\n${content}\n\n`;
		}, '');

		return chatText.trim();
	};

	const downloadTxt = async () => {
		const chatText = await getChatAsText();

		let blob = new Blob([chatText], {
			type: 'text/plain'
		});

		saveAs(blob, `chat-${chat.chat.title}.txt`);
	};

	const downloadPdf = async () => {
		const filename = `chat-${chat.chat.title}.pdf`;
		if (!($settings?.stylizedPdfExport ?? true)) {
			await saveTextPdf(await getChatAsText(), filename);
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
		if (chat.id) {
			let chatObj = null;

			if ((chat?.id ?? '').startsWith('local') || isTemporary) {
				chatObj = chat;
			} else {
				chatObj = await getChatById(localStorage.token, chat.id);
			}

			let blob = new Blob([JSON.stringify([chatObj])], {
				type: 'application/json'
			});
			saveAs(blob, `chat-export-${Date.now()}.json`);
		}
	};
</script>

{#if showFullMessages}
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
	bind:show
	closeOnSelect
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
	align="start"
	sideOffset={8}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="select-none min-w-[12.5rem] max-w-[12.5rem] transition">
			<!-- <DropdownMenu.Item draggable="false"
				class="flex gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal  cursor-pointer dark:hover:bg-base-800 rounded-xl"
				on:click={async () => {
					await showSettings.set(!$showSettings);
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-3.5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
					/>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
					/>
				</svg>
				<div class="flex items-center">{$i18n.t('Settings')}</div>
			</DropdownMenu.Item> -->
			<!-- Settings commented out block above -->

			{#if scrollToTop}
				<button
					draggable="false"
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
					on:click={() => {
						scrollToTop();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-3.5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18"
						/>
					</svg>
					<div class="flex items-center">{$i18n.t('Scroll to Top')}</div>
				</button>
			{/if}

			{#if scrollToTop}
				<hr class="border-base-50/30 dark:border-base-800/30 mx-1 my-0.5" />
			{/if}

			{#if !readOnly && !isTemporary && ($user?.role === 'admin' || ($user.permissions?.chat?.share ?? true))}
				<button
					draggable="false"
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
					id="chat-share-button"
					on:click={() => {
						shareHandler();
					}}
				>
					<Share className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Share')}</div>
				</button>
			{/if}

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<DropdownSub contentClass="select-none z-50">
					<button
						slot="trigger"
						draggable="false"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
					>
						<Download className="size-3.5" strokeWidth="1.5" />

						<div class="flex items-center">{$i18n.t('Download')}</div>
					</button>

					<button
						draggable="false"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
						on:click={() => {
							downloadJSONExport();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Export chat (.json)')}</div>
					</button>

					<button
						draggable="false"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</button>

					<button
						draggable="false"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
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

			{#if (!readOnly || $folders.find((folder) => folder.id === chat?.folder_id)?.user_id === $user?.id) && !isTemporary && chat?.id}
				<button
					draggable="false"
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
					on:click={() => {
						renameHandler();
					}}
				>
					<EditPencilIcon className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Rename')}</div>
				</button>
			{/if}

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<button
					draggable="false"
					class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
					id="chat-copy-button"
					on:click={async () => {
						const res = await copyToClipboard(await getChatAsText()).catch((e) => {
							console.error(e);
						});

						if (res) {
							toast.success($i18n.t('Copied to clipboard'));
						}
					}}
				>
					<Clipboard className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Copy')}</div>
				</button>
			{/if}

			{#if !readOnly && !isTemporary && chat?.id}
				<hr class="border-base-50/30 dark:border-base-800/30 mx-1 my-0.5" />

				{#if $folders.length > 0}
					<DropdownSub contentClass="select-none z-50" maxWidth={200}>
						<button
							slot="trigger"
							draggable="false"
							class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
						>
							<Folder className="size-3.5" strokeWidth="1.5" />

							<div class="flex items-center">{$i18n.t('Move')}</div>
						</button>
						{#each $folders.sort((a, b) => b.updated_at - a.updated_at) as folder}
							{#if folder?.id}
								<button
									draggable="false"
									class="flex h-[1.6875rem] w-full items-center gap-2 overflow-hidden rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-base-50/40 dark:hover:bg-base-800/40"
									on:click={() => {
										moveChatHandler(chat.id, folder.id);
									}}
								>
									<div class="shrink-0">
										<Folder className="size-3.5" strokeWidth="1.5" />
									</div>

									<div class="truncate">{folder.name ?? 'Folder'}</div>
								</button>
							{/if}
						{/each}
					</DropdownSub>
				{/if}

				{#if $visibleControls['chat.archive']}
					<button
						draggable="false"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
						on:click={() => {
							archiveChatHandler();
						}}
					>
						<ArchiveBox className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">
							{chat?.archived ? $i18n.t('Unarchive') : $i18n.t('Archive')}
						</div>
					</button>
				{/if}

				{#if $user?.role === 'admin' || ($user?.permissions?.chat?.delete ?? true)}
					<button
						draggable="false"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
						on:click={() => {
							deleteChatHandler();
						}}
					>
						<GarbageBin className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				{/if}

				{#if $visibleControls['chat.tags']}
					<hr class="border-base-50/30 dark:border-base-800/30 mx-1 my-0.5" />

					<!-- Same picker as folder chats. -->
					<DropdownSub contentClass="select-none z-50 w-52" maxWidth={240}>
						<button
							slot="trigger"
							draggable="false"
							class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] cursor-pointer select-none hover:bg-base-50/40 dark:hover:bg-base-800/40"
						>
							<Tag className="size-3.5" strokeWidth="1.5" />
							<div class="flex flex-1 items-center">{$i18n.t('Tags')}</div>
							{#if chat?.meta?.tags?.length}<span class="text-xs tabular-nums text-base-400"
									>{chat.meta.tags.length}</span
								>{/if}
							<ChevronRight className="size-3.5 shrink-0 text-base-400 rtl:rotate-180" />
						</button>
						<TagPicker
							id={chat.id}
							onChange={(next) => {
								if (chat?.meta) chat.meta.tags = next.map((tag) => tag.id);
							}}
						/>
					</DropdownSub>
				{/if}
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
