<script lang="ts">
	import type i18nType from '$lib/i18n';
	import { toast } from 'svelte-sonner';
	import { getContext, tick } from 'svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import { getOutputText } from '$lib/components/chat/Messages/structuredOutput';

	import {
		showControls,
		showArtifacts,
		mobile,
		temporaryChatEnabled,
		user,
		settings,
		folders,
		showEmbeds,
		artifactContents
	} from '$lib/stores';

	import { getChatById } from '$lib/apis/chats';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import {
		canvasToBlob,
		copyBlobToClipboard,
		renderChatMessagesToCanvas
	} from '$lib/components/chat/export';

	const i18n: typeof i18nType = getContext('i18n');

	export let shareEnabled: boolean = false;
	export let readOnly: boolean = false;

	export let shareHandler: Function;
	export let moveChatHandler: Function;

	export let archiveChatHandler: Function;
	export let deleteChatHandler: Function;

	// export let tagHandler: Function;

	export let chat;
	export let onClose: Function = () => {};
	export let scrollToTop: (() => void) | null = null;

	let showFullMessages = false;

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

	const getFullMessagesCanvas = async () => {
		showFullMessages = true;
		await tick();

		const containerElement = document.getElementById('full-messages-container');
		if (!containerElement) {
			throw new Error('Full messages container not found');
		}

		try {
			return await renderChatMessagesToCanvas(containerElement);
		} finally {
			showFullMessages = false;
		}
	};

	const copyImage = async () => {
		try {
			const blobPromise = getFullMessagesCanvas().then((canvas) => canvasToBlob(canvas));
			let copied = false;

			try {
				copied = await copyBlobToClipboard(blobPromise);
			} catch (error) {
				console.error('Error copying chat image to clipboard', error);
			}

			if (copied) {
				toast.success($i18n.t('Image copied to clipboard'));
			} else {
				const blob = await blobPromise;
				saveAs(blob, `chat-${chat.chat.title}.png`);
				toast.success($i18n.t('Image clipboard is not supported; image downloaded instead'));
			}
		} catch (error) {
			console.error('Error copying chat image', error);
			toast.error($i18n.t('Failed to copy image'));
		}
	};

	const downloadPdf = async () => {
		const { default: jsPDF } = await import('jspdf');

		if ($settings?.stylizedPdfExport ?? true) {
			try {
				const isDarkMode = document.documentElement.classList.contains('dark');
				const canvas = await getFullMessagesCanvas();

				const pdf = new jsPDF('p', 'mm', 'a4');
				const pageWidthMM = 210;
				const pageHeightMM = 297;
				const pxPerPDFMM = canvas.width / pageWidthMM;
				const pagePixelHeight = Math.floor(pxPerPDFMM * pageHeightMM);

				let offsetY = 0;
				let page = 0;

				while (offsetY < canvas.height) {
					const sliceHeight = Math.min(pagePixelHeight, canvas.height - offsetY);
					const pageCanvas = document.createElement('canvas');
					pageCanvas.width = canvas.width;
					pageCanvas.height = sliceHeight;

					const ctx = pageCanvas.getContext('2d');
					if (!ctx) {
						throw new Error('Failed to create canvas context');
					}

					ctx.drawImage(
						canvas,
						0,
						offsetY,
						canvas.width,
						sliceHeight,
						0,
						0,
						canvas.width,
						sliceHeight
					);

					const imgData = pageCanvas.toDataURL('image/jpeg', 0.7);
					const imgHeightMM = (sliceHeight * pageWidthMM) / canvas.width;

					if (page > 0) pdf.addPage();

					if (isDarkMode) {
						pdf.setFillColor(0, 0, 0);
						pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
					}

					pdf.addImage(imgData, 'JPEG', 0, 0, pageWidthMM, imgHeightMM);

					offsetY += sliceHeight;
					page++;
				}

				pdf.save(`chat-${chat.chat.title}.pdf`);
			} catch (error) {
				console.error('Error generating PDF', error);
			}
		} else {
			console.log('Downloading PDF');

			const chatText = await getChatAsText();

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
		if (chat.id) {
			let chatObj = null;

			if ((chat?.id ?? '').startsWith('local') || $temporaryChatEnabled) {
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
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
	align="end"
	sideOffset={8}
>
	<slot />

	<div slot="content">
		<div
			class="select-none min-w-[200px] max-w-[200px] rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
		>
			<!-- <DropdownMenu.Item draggable="false"
				class="flex gap-2 items-center px-3 py-1.5 text-sm  cursor-pointer dark:hover:bg-gray-800 rounded-xl"
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
					class="size-4"
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
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
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
						class="size-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18"
						/>
					</svg>
					<div class="flex items-center">{$i18n.t('Scroll to Top')}</div>
				</button>

				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />
			{/if}

			{#if ($artifactContents ?? []).length > 0}
				<button
					draggable="false"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					id="chat-artifacts-button"
					on:click={async () => {
						await showControls.set(true);
						await showArtifacts.set(true);
						await showEmbeds.set(false);
					}}
				>
					<Cube className=" size-4" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Artifacts')}</div>
				</button>

				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />
			{/if}

			{#if !readOnly && !$temporaryChatEnabled && ($user?.role === 'admin' || ($user.permissions?.chat?.share ?? true))}
				<button
					draggable="false"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					id="chat-share-button"
					on:click={() => {
						shareHandler();
					}}
				>
					<Share strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Share')}</div>
				</button>
			{/if}

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<DropdownSub>
					<button
						slot="trigger"
						draggable="false"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					>
						<Download strokeWidth="1.5" />

						<div class="flex items-center">{$i18n.t('Download')}</div>
					</button>

					<button
						draggable="false"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
						on:click={() => {
							downloadJSONExport();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Export chat (.json)')}</div>
					</button>

					<button
						draggable="false"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</button>

					<button
						draggable="false"
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
						on:click={() => {
							downloadPdf();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
					</button>
				</DropdownSub>

				<button
					draggable="false"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					on:click={() => {
						copyImage();
					}}
				>
					<Photo className="size-4" strokeWidth="1.5" />
					<div class="flex items-center line-clamp-1">{$i18n.t('Copy as image')}</div>
				</button>
			{/if}

			<button
				draggable="false"
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
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
				<Clipboard className=" size-4" strokeWidth="1.5" />
				<div class="flex items-center">{$i18n.t('Copy')}</div>
			</button>

			{#if !readOnly && !$temporaryChatEnabled && chat?.id}
				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />

				{#if $folders.length > 0}
					<DropdownSub maxWidth={200}>
						<button
							slot="trigger"
							draggable="false"
							class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
						>
							<Folder strokeWidth="1.5" />

							<div class="flex items-center">{$i18n.t('Move')}</div>
						</button>
						{#each $folders.sort((a, b) => b.updated_at - a.updated_at) as folder}
							{#if folder?.id}
								<button
									draggable="false"
									class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl overflow-hidden w-full"
									on:click={() => {
										moveChatHandler(chat.id, folder.id);
									}}
								>
									<div class="shrink-0">
										<Folder strokeWidth="1.5" />
									</div>

									<div class="truncate">{folder.name ?? 'Folder'}</div>
								</button>
							{/if}
						{/each}
					</DropdownSub>
				{/if}

				<button
					draggable="false"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					on:click={() => {
						archiveChatHandler();
					}}
				>
					<ArchiveBox className="size-4" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Archive')}</div>
				</button>

				<button
					draggable="false"
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					on:click={() => {
						deleteChatHandler();
					}}
				>
					<GarbageBin strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</button>

				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />

				<div class="flex p-1 max-h-28 overflow-y-auto">
					<Tags chatId={chat.id} />
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
