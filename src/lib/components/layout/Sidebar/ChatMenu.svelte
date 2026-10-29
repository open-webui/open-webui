<script lang="ts">
	import { getContext, tick } from 'svelte';

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

	export let onPinChange: () => void = () => {};

	const pinHandler = async () => {
		await toggleChatPinnedStatusById(localStorage.token, chatId);
		onPinChange();
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

		const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
			import('jspdf'),
			import('html2canvas-pro')
		]);

		if ($settings?.stylizedPdfExport ?? true) {
			showFullMessages = true;
			await tick();

			const containerElement = document.getElementById('full-messages-container');
			if (containerElement) {
				try {
					const isDarkMode = document.documentElement.classList.contains('dark');
					const virtualWidth = 800; // px, fixed width for cloned element

					// Clone and style
					const clonedElement = containerElement.cloneNode(true);
					clonedElement.classList.add('text-black');
					clonedElement.classList.add('dark:text-white');
					clonedElement.style.width = `${virtualWidth}px`;
					clonedElement.style.position = 'absolute';
					clonedElement.style.left = '-9999px';
					clonedElement.style.height = 'auto';
					document.body.appendChild(clonedElement);

					// Override content-visibility so html2canvas can capture all messages
					clonedElement.querySelectorAll('.message-virtualized').forEach((el) => {
						el.style.contentVisibility = 'visible';
					});

					// Let the browser compute layout for the cloned element
					await new Promise((r) => requestAnimationFrame(r));

					const pdf = new jsPDF('p', 'mm', 'a4');
					const pageWidthMM = 210;
					const pageHeightMM = 297;

					const pagePixelHeight = Math.floor((virtualWidth * pageHeightMM) / pageWidthMM);
					const rootTop = clonedElement.getBoundingClientRect().top;
					const contentHeight = Math.ceil(clonedElement.getBoundingClientRect().height);

					const blocks = [];
					const trackedElements = new Set();
					const collectBlocks = (element) => {
						const children = Array.from(element.children);
						const splittable =
							children.length > 0 &&
							(getComputedStyle(element).display === 'contents' ||
								(element.getBoundingClientRect().height > pagePixelHeight / 4 &&
									!Array.from(element.childNodes).some(
										(childNode) =>
											childNode.nodeType === Node.TEXT_NODE && childNode.textContent?.trim()
									) &&
									children.every(
										(child) => !getComputedStyle(child).display.startsWith('inline')
									)));

						if (element !== clonedElement) trackedElements.add(element);

						if (splittable) {
							children.forEach(collectBlocks);
						} else {
							const { top, bottom } = element.getBoundingClientRect();
							blocks.push({ element, top: top - rootTop, bottom: bottom - rootTop });
						}
					};
					collectBlocks(clonedElement);

					clonedElement.setAttribute('data-pdf-root', '');

					let offsetY = 0;
					let page = 0;

					while (offsetY < contentHeight) {
						const sliceHeight = Math.min(pagePixelHeight, contentHeight - offsetY);
						const sliceBlocks = blocks.filter(
							(block) => block.bottom > offsetY && block.top < offsetY + sliceHeight
						);

						const keptElements = new Set();
						for (const { element } of sliceBlocks) {
							for (
								let current = element;
								current && current !== clonedElement;
								current = current.parentElement
							) {
								keptElements.add(current);
							}
						}

						const anchor = sliceBlocks.find((block) => block.bottom > block.top);
						anchor?.element.setAttribute('data-pdf-anchor', '');

						const canvas = await html2canvas(clonedElement, {
							backgroundColor: isDarkMode ? '#000' : '#fff',
							useCORS: true,
							logging: false,
							scale: 2, // increase resolution
							width: virtualWidth,
							height: sliceHeight,
							y: offsetY,
							ignoreElements: (element) =>
								(element.parentElement === document.body &&
									element !== clonedElement &&
									!['STYLE', 'LINK'].includes(element.tagName)) ||
								(trackedElements.has(element) && !keptElements.has(element)),
							onclone: (clonedDocument) => {
								const clonedRoot = clonedDocument.querySelector('[data-pdf-root]');
								const clonedAnchor = clonedDocument.querySelector('[data-pdf-anchor]');
								if (!clonedRoot || !clonedAnchor) return;

								const spacer = clonedDocument.createElement('div');
								clonedRoot.prepend(spacer);

								let spacerHeight = 0;
								for (let pass = 0; pass < 2; pass++) {
									spacerHeight +=
										anchor.top -
										(clonedAnchor.getBoundingClientRect().top -
											clonedRoot.getBoundingClientRect().top);
									spacer.style.height = `${spacerHeight}px`;
								}
							}
						});

						anchor?.element.removeAttribute('data-pdf-anchor');

						const imgData = canvas.toDataURL('image/jpeg', 0.7);
						const imgHeightMM = (sliceHeight * pageWidthMM) / virtualWidth;

						if (page > 0) pdf.addPage();

						if (isDarkMode) {
							pdf.setFillColor(0, 0, 0);
							pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
						}

						pdf.addImage(imgData, 'JPEG', 0, 0, pageWidthMM, imgHeightMM);

						offsetY += sliceHeight;
						page++;
					}

					document.body.removeChild(clonedElement);

					pdf.save(`chat-${chat.chat.title}.pdf`);

					showFullMessages = false;
				} catch (error) {
					console.error('Error generating PDF', error);
				}
			}
		} else {
			console.log('Downloading PDF');

			const chatText = await getChatAsText(chat);

			const doc = new jsPDF();

			// Margins
			const left = 15;
			const top = 20;
			const right = 15;
			const bottom = 20;

			const pageWidth = doc.internal.pageSize.getWidth();
			const pageHeight = doc.internal.pageSize.getHeight();
			const usableWidth = pageWidth - left - right;
			const usableHeight = pageHeight - top - bottom;

			// Font size and line height
			const fontSize = 8;
			doc.setFontSize(fontSize);
			const lineHeight = fontSize * 1; // adjust if needed

			// Split the markdown into lines (handles \n)
			const paragraphs = chatText.split('\n');

			let y = top;

			for (let paragraph of paragraphs) {
				// Wrap each paragraph to fit the width
				const lines = doc.splitTextToSize(paragraph, usableWidth);

				for (let line of lines) {
					// If the line would overflow the bottom, add a new page
					if (y + lineHeight > pageHeight - bottom) {
						doc.addPage();
						y = top;
					}
					doc.text(line, left, y);
					y += lineHeight * 0.5;
				}
				// Add empty line at paragraph breaks
				y += lineHeight * 0.1;
			}

			doc.save(`chat-${chat.chat.title}.pdf`);
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
					class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
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
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
					>
						<DownloadIcon className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Download')}</div>
					</button>

					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
						on:click={() => {
							downloadJSONExport();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Export chat (.json)')}</div>
					</button>

					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</button>

					<button
						role="menuitem"
						draggable="false"
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 select-none w-full"
						on:click={() => {
							downloadPdf();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
					</button>
				</DropdownSub>
			{/if}

			<button
				role="menuitem"
				draggable="false"
				class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
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
					class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
					on:click={() => {
						markUnreadHandler();
					}}
				>
					<ChatCheckIcon className="size-3.5" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Mark as unread')}</div>
				</button>

				<hr class="border-gray-50/30 dark:border-gray-800/30 mx-1 my-0.5" />

				<button
					role="menuitem"
					draggable="false"
					class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
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
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
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
							class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 select-none w-full"
						>
							<FolderIcon className="size-3.5" />
							<div class="flex items-center">{$i18n.t('Move')}</div>
						</button>

						{#each $folders.sort((a, b) => b.updated_at - a.updated_at) as folder}
							<button
								role="menuitem"
								draggable="false"
								class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 overflow-hidden w-full"
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
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
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
						class="flex h-[1.6875rem] gap-2 items-center rounded-xl px-2 text-[0.8125rem] cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900 w-full"
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
