<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { DropdownMenu } from 'bits-ui';
	import { getContext, tick } from 'svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadChatAsPDF } from '$lib/apis/utils';
	import { copyToClipboard, createMessagesList } from '$lib/utils';

	import {
		showOverview,
		showControls,
		showArtifacts,
		mobile,
		temporaryChatEnabled,
		theme,
		user,
		settings,
		folders,
		showEmbeds,
		artifactContents
	} from '$lib/stores';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getChatById } from '$lib/apis/chats';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Download from '$lib/components/icons/Download.svelte';

	const i18n = getContext('i18n');

	export let shareEnabled: boolean = false;

	export let shareHandler: Function;
	export let moveChatHandler: Function;

	export let archiveChatHandler: Function;

	// export let tagHandler: Function;

	export let chat;
	export let onClose: Function = () => {};

	let showFullMessages = false;

	const getChatAsText = async () => {
		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const chatText = messages.reduce((a, message, i, arr) => {
			return `${a}### ${message.role.toUpperCase()}\n${message.content}\n\n`;
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

					// Wait for DOM update/layout
					await new Promise((r) => setTimeout(r, 100));

					// Render entire content once
					const canvas = await html2canvas(clonedElement, {
						backgroundColor: isDarkMode ? '#000' : '#fff',
						useCORS: true,
						scale: 2, // increase resolution
						width: virtualWidth
					});

					document.body.removeChild(clonedElement);

					const pdf = new jsPDF('p', 'mm', 'a4');
					const pageWidthMM = 210;
					const pageHeightMM = 297;

					// Convert page height in mm to px on canvas scale for cropping
					// Get canvas DPI scale:
					const pxPerMM = canvas.width / virtualWidth; // width in px / width in px?
					// Since 1 page width is 210 mm, but canvas width is 800 px at scale 2
					// Assume 1 mm = px / (pageWidthMM scaled)
					// Actually better: Calculate scale factor from px/mm:
					// virtualWidth px corresponds directly to 210mm in PDF, so pxPerMM:
					const pxPerPDFMM = canvas.width / pageWidthMM; // canvas px per PDF mm

					// Height in px for one page slice:
					const pagePixelHeight = Math.floor(pxPerPDFMM * pageHeightMM);

					let offsetY = 0;
					let page = 0;

					while (offsetY < canvas.height) {
						// Height of slice
						const sliceHeight = Math.min(pagePixelHeight, canvas.height - offsetY);

						// Create temp canvas for slice
						const pageCanvas = document.createElement('canvas');
						pageCanvas.width = canvas.width;
						pageCanvas.height = sliceHeight;

						const ctx = pageCanvas.getContext('2d');

						// Draw the slice of original canvas onto pageCanvas
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

						// Calculate image height in PDF units keeping aspect ratio
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

					showFullMessages = false;
				} catch (error) {
					console.error('Error generating PDF', error);
				}
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
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[200px] rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition"
			sideOffset={8}
			side="bottom"
			align="end"
			transition={flyAndScale}
		>
			<!-- <DropdownMenu.Item
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

			{#if $mobile && ($user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true))}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					id="chat-controls-button"
					on:click={async () => {
						await showControls.set(true);
						await showOverview.set(false);
						await showArtifacts.set(false);
						await showEmbeds.set(false);
					}}
				>
					<AdjustmentsHorizontal className=" size-4" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Controls')}</div>
				</DropdownMenu.Item>
			{/if}

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
				id="chat-overview-button"
				on:click={async () => {
					await showControls.set(true);
					await showOverview.set(true);
					await showArtifacts.set(false);
					await showEmbeds.set(false);
				}}
			>
				<Map className=" size-4" strokeWidth="1.5" />
				<div class="flex items-center">{$i18n.t('Overview')}</div>
			</DropdownMenu.Item>

			{#if ($artifactContents ?? []).length > 0}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					id="chat-overview-button"
					on:click={async () => {
						await showControls.set(true);
						await showArtifacts.set(true);
						await showOverview.set(false);
						await showEmbeds.set(false);
					}}
				>
					<Cube className=" size-4" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Artifacts')}</div>
				</DropdownMenu.Item>
			{/if}

			<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />

			{#if !$temporaryChatEnabled && ($user?.role === 'admin' || ($user.permissions?.chat?.share ?? true))}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					id="chat-share-button"
					on:click={() => {
						shareHandler();
					}}
				>
					<Share strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Share')}</div>
				</DropdownMenu.Item>
			{/if}

			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
				>
					<Download strokeWidth="1.5" />

					<div class="flex items-center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					class="w-full rounded-2xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white border border-gray-100  dark:border-gray-800 shadow-lg max-h-52 overflow-y-auto scrollbar-hidden"
					transition={flyAndScale}
					sideOffset={8}
				>
					{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
						<DropdownMenu.Item
							class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
							on:click={() => {
								downloadJSONExport();
							}}
						>
							<div class="flex items-center line-clamp-1">{$i18n.t('Export chat (.json)')}</div>
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
						on:click={() => {
							downloadPdf();
						}}
					>
						<div class="flex items-center line-clamp-1">{$i18n.t('PDF document (.pdf)')}</div>
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>

			<DropdownMenu.Item
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
			</DropdownMenu.Item>

			{#if !$temporaryChatEnabled && chat?.id}
				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />

				<DropdownMenu.Sub>
					<DropdownMenu.SubTrigger
						class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl select-none w-full"
					>
						<Folder strokeWidth="1.5" />

						<div class="flex items-center">{$i18n.t('Move')}</div>
					</DropdownMenu.SubTrigger>
					<DropdownMenu.SubContent
						class="w-full rounded-2xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white border border-gray-100  dark:border-gray-800 shadow-lg max-h-52 overflow-y-auto scrollbar-hidden"
						transition={flyAndScale}
						sideOffset={8}
					>
						{#each $folders.sort((a, b) => b.updated_at - a.updated_at) as folder}
							<DropdownMenu.Item
								class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
								on:click={() => {
									moveChatHandler(chat?.id, folder?.id);
								}}
							>
								<Folder strokeWidth="1.5" />

								<div class="flex items-center">{folder?.name ?? 'Folder'}</div>
							</DropdownMenu.Item>
						{/each}
					</DropdownMenu.SubContent>
				</DropdownMenu.Sub>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						archiveChatHandler();
					}}
				>
					<ArchiveBox className="size-4" strokeWidth="1.5" />
					<div class="flex items-center">{$i18n.t('Archive')}</div>
				</DropdownMenu.Item>

				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1" />

				<div class="flex p-1">
					<Tags chatId={chat.id} />
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
