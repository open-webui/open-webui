<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	import Fuse from 'fuse.js';

	const { saveAs } = fileSaver;

	import jsPDF from 'jspdf';
	import html2canvas from 'html2canvas-pro';

	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	async function loadLocale(locales) {
		for (const locale of locales) {
			try {
				dayjs.locale(locale);
				break; // Stop after successfully loading the first available locale
			} catch (error) {
				console.error(`Could not load locale '${locale}':`, error);
			}
		}
	}

	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { goto } from '$app/navigation';
	import { onMount, getContext, onDestroy } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import { createNewNotePlus, deleteNotePlusById, getNotesPlus } from '$lib/apis/noteplus';
	import { capitalizeFirstLetter, copyToClipboard, getTimeRange } from '$lib/utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import NotePlusMenu from './NotesPlus/NotePlusMenu.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import { marked } from 'marked';
	import XMark from '../icons/XMark.svelte';

	const i18n = getContext('i18n');
	let loaded = false;

	let importFiles = '';
	let query = '';

	let noteItems = [];
	let fuse = null;

	let selectedNote = null;
	let notes = {};
	let dragged = false;
	
	export let selectedCategory = null;

	$: if (fuse) {
		notes = groupNotes(
			query
				? fuse.search(query).map((e) => {
						return e.item;
					})
				: noteItems
		);
	}
	
	// Re-filter when selectedCategory changes
	$: selectedCategory, fuse && (notes = groupNotes(
		query
			? fuse.search(query).map((e) => e.item)
			: noteItems
	));

	let showDeleteConfirm = false;

	const groupNotes = (res) => {
		console.log('Grouping notes:', res);
		console.log('Selected category:', selectedCategory);
		
		if (!Array.isArray(res)) {
			return {}; // or throw new Error("Notes response is not an array")
		}

		// Filter by selected category if provided
		if (selectedCategory && typeof selectedCategory === 'object') {
			res = res.filter(note => {
				// If major category is selected
				if (selectedCategory.level === 'major') {
					return note.category_major === selectedCategory.major;
				}
				// If middle category is selected
				else if (selectedCategory.level === 'middle') {
					return note.category_major === selectedCategory.major &&
						   note.category_middle === selectedCategory.middle;
				}
				// If minor category is selected
				else if (selectedCategory.level === 'minor') {
					return note.category_major === selectedCategory.major &&
						   note.category_middle === selectedCategory.middle &&
						   note.category_minor === selectedCategory.minor;
				}
				return true;
			});
		}

		// Build the grouped object
		const grouped: Record<string, any[]> = {};
		for (const note of res) {
			const timeRange = getTimeRange(note.updated_at / 1000000000);
			if (!grouped[timeRange]) {
				grouped[timeRange] = [];
			}
			grouped[timeRange].push({
				...note,
				timeRange
			});
		}
		return grouped;
	};

	const init = async () => {
		noteItems = await getNotesPlus(localStorage.token, true);

		fuse = new Fuse(noteItems, {
			keys: ['title', 'category_major', 'category_middle', 'category_minor']
		});
	};

	const createNoteHandler = async () => {
		// Parse selected category if provided
		let major = 'General';
		let middle = 'Notes';
		let minor = 'Default';
		
		if (selectedCategory && typeof selectedCategory === 'object') {
			if (selectedCategory.major) major = selectedCategory.major;
			if (selectedCategory.middle) middle = selectedCategory.middle;
			if (selectedCategory.minor) minor = selectedCategory.minor;
		}
		
		const res = await createNewNotePlus(localStorage.token, {
			// YYYY-MM-DD
			title: dayjs().format('YYYY-MM-DD'),
			data: {
				content: {
					json: {},
					html: '',
					md: ''
				}
			},
			category_major: major,
			category_middle: middle,
			category_minor: minor,
			meta: null,
			access_control: {}
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// Dispatch event for category tree refresh
			window.dispatchEvent(new CustomEvent('noteplus:created'));
			goto(`/noteplus/${res.id}`);
		}
	};

	const downloadHandler = async (type) => {
		console.log('downloadHandler', type);
		console.log('selectedNote', selectedNote);
		if (type === 'md') {
			const blob = new Blob([selectedNote.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${selectedNote.title}.md`);
		} else if (type === 'pdf') {
			await downloadPdf(selectedNote);
		}
	};

	const downloadPdf = async (note) => {
		try {
			// Define a fixed virtual screen size
			const virtualWidth = 1024; // Fixed width (adjust as needed)
			const virtualHeight = 1400; // Fixed height (adjust as needed)

			// STEP 1. Get a DOM node to render
			const html = note.data?.content?.html ?? '';
			let node;
			if (html instanceof HTMLElement) {
				node = html;
			} else {
				// If it's HTML string, render to a temporary hidden element
				const container = document.createElement('div');
				container.innerHTML = marked.parse(note.data?.content?.md);
				container.classList.add('markdown');
				container.classList.add('prose');
				container.classList.add('w-full');
				container.classList.add('dark:prose-invert');
				container.classList.add('prose-p:my-3');
				container.classList.add('prose-headings:my-4');
				container.classList.add('line-clamp-4');
				container.classList.add('max-w-full');
				container.style.position = 'absolute';
				container.style.left = '-9999px';
				container.style.maxWidth = `${virtualWidth}px`;
				// Ensure minimum width for rendering
				container.style.width = `${virtualWidth}px`;
				document.body.appendChild(container);
				node = container;
			}

			// STEP 2. Render to canvas (fixed virtual size)
			const canvas = await html2canvas(node, {
				width: virtualWidth, // Fixed width
				height: virtualHeight, // Fixed height
				scale: 1, // Fixed scale for consistency
				useCORS: true,
				logging: false,
				// Optional: remove scrollbars if any
				scrollX: 0,
				scrollY: 0,
				// Optional: white background
				backgroundColor: '#FFFFFF'
			});

			// STEP 3. Calculate PDF dimensions
			const imgWidth = 210; // A4 width in mm
			const imgHeight = (canvas.height * imgWidth) / canvas.width; // Calculate proportional height

			// Create PDF with a large enough page height
			const pdf = new jsPDF('p', 'mm', [imgWidth, imgHeight + 10]); // +10 for some padding

			// Add the image
			const imgData = canvas.toDataURL('image/png');
			pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight);

			// Save the PDF
			pdf.save(`${note.title}.pdf`);

			// Clean up
			if (typeof html === 'string') {
				document.body.removeChild(node);
			}
		} catch (error) {
			console.error('Error generating PDF:', error);
			// Handle the error (e.g., show an error message to the user)
		}
	};

	const shareHandler = async () => {
		console.log('shareHandler');
		if (navigator.share) {
			navigator.share({
				title: selectedNote.title,
				text: selectedNote.data.content.md
			});
		} else {
			toast.error('Sharing is not supported on this device');
		}
	};

	const deleteHandler = async () => {
		const res = await deleteNotePlusById(localStorage.token, selectedNote.id).catch((e) => {
			toast.error(e);
			return null;
		});

		if (res) {
			// Dispatch event for category tree refresh
			window.dispatchEvent(new CustomEvent('noteplus:deleted'));
			await init();
		}

		selectedNote = null;
		showDeleteConfirm = false;
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being dragged.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		console.log(e);

		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				// TODO: Handle file import for NotePlus
			}
		}

		dragged = false;
	};

	onDestroy(() => {
		console.log('destroy');
		const dropzoneElement = document.getElementById('notes-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});

	onMount(async () => {
		await init();
		loaded = true;

		const dropzoneElement = document.getElementById('notes-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Notes+')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<FilesOverlay show={dragged} />

<div id="notes-container" class="w-full min-h-full h-full">
	{#if loaded}
		<DeleteConfirmDialog
			bind:show={showDeleteConfirm}
			title={$i18n.t('Delete note?')}
			on:confirm={() => {
				deleteHandler();
				showDeleteConfirm = false;
			}}
		>
			<div class=" text-sm text-gray-500">
				{$i18n.t('This will delete')} <span class="  font-semibold">{selectedNote?.title}</span>.
			</div>
		</DeleteConfirmDialog>

		<div class="flex h-full">
			<!-- Main Content -->
			<div class="flex-1 flex flex-col">
				<!-- Search Bar -->
				<div class="flex flex-col gap-1 px-3.5 py-2 border-b border-gray-200 dark:border-gray-800">
					<div class=" flex flex-1 items-center w-full space-x-2">
						<div class="flex flex-1 items-center">
							<div class=" self-center ml-1 mr-3">
								<Search className="size-3.5" />
							</div>
							<input
								class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
								bind:value={query}
								placeholder={$i18n.t('Search Notes+')}
							/>

							{#if query}
								<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
									<button
										class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
										on:click={() => {
											query = '';
										}}
									>
										<XMark className="size-3" strokeWidth="2" />
									</button>
								</div>
						{/if}
					</div>
				</div>
			</div>

				<!-- Notes Content -->
				<div class="px-4.5 @container flex-1 overflow-y-auto pt-2">
			{#if Object.keys(notes).length > 0}
				<div class="pb-10">
					{#each Object.keys(notes) as timeRange}
						<div class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium pb-2.5">
							{$i18n.t(timeRange)}
						</div>

						<div
							class="mb-5 gap-2.5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
						>
							{#each notes[timeRange] as note, idx (note.id)}
								<div
									class=" flex space-x-4 cursor-pointer w-full px-4.5 py-4 bg-gray-50 dark:bg-gray-850 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition"
								>
									<div class=" flex flex-1 space-x-4 cursor-pointer w-full">
										<a
											href={`/noteplus/${note.id}`}
											class="w-full -translate-y-0.5 flex flex-col justify-between"
										>
											<div class="flex-1">
												<div class="  flex items-center gap-2 self-center mb-1 justify-between">
													<div class="flex-1">
														<div class=" font-semibold line-clamp-1 capitalize">{note.title}</div>
														{#if note.category_major}
															<div class="text-[10px] text-gray-400 dark:text-gray-500 line-clamp-1">
																{note.category_major}{note.category_middle ? ` / ${note.category_middle}` : ''}{note.category_minor ? ` / ${note.category_minor}` : ''}
															</div>
														{/if}
													</div>

													<div>
														<NotePlusMenu
															onDownload={(type) => {
																selectedNote = note;
																downloadHandler(type);
															}}
															onCopyLink={async () => {
																const baseUrl = window.location.origin;
																const res = await copyToClipboard(`${baseUrl}/noteplus/${note.id}`);

																if (res) {
																	toast.success($i18n.t('Copied link to clipboard'));
																} else {
																	toast.error($i18n.t('Failed to copy link'));
																}
															}}
															onDelete={() => {
																selectedNote = note;
																showDeleteConfirm = true;
															}}
														>
															<button
																class="self-center w-fit text-sm p-1 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																type="button"
															>
																<EllipsisHorizontal className="size-5" />
															</button>
														</NotePlusMenu>
													</div>
												</div>

												<div
													class=" text-xs text-gray-500 dark:text-gray-500 mb-3 line-clamp-3 min-h-10"
												>
													{#if note.data?.content?.md}
														{note.data?.content?.md}
													{:else}
														{$i18n.t('No content')}
													{/if}
												</div>
											</div>

											<div class=" text-xs px-0.5 w-full flex justify-between items-center">
												<div>
													{dayjs(note.updated_at / 1000000).fromNow()}
												</div>
												<Tooltip
													content={note?.user?.email ?? $i18n.t('Deleted User')}
													className="flex shrink-0"
													placement="top-start"
												>
													<div class="shrink-0 text-gray-500">
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</div>
												</Tooltip>
											</div>
										</a>
									</div>
								</div>
							{/each}
						</div>
					{/each}
				</div>
			{:else}
				<div class="w-full h-full flex flex-col items-center justify-center">
					<div class="pb-20 text-center">
						<div class=" text-xl font-medium text-gray-400 dark:text-gray-600">
							{$i18n.t('No Notes')}
						</div>

						<div class="mt-1 text-sm text-gray-300 dark:text-gray-700">
							{$i18n.t('Create your first note by clicking on the plus button below.')}
						</div>
					</div>
				</div>
			{/if}
			</div>
		</div>

		<div class="absolute bottom-5 right-5">
			<div class="flex gap-0.5 justify-end w-full">
				<Tooltip content={$i18n.t('Create Note')}>
					<button
						class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
						type="button"
						on:click={async () => {
							createNoteHandler();
						}}
					>
						<Plus className="size-4.5" strokeWidth="2.5" />
					</button>
				</Tooltip>
			</div>
		</div>
		</div>
	{:else}
		<div class="w-full h-full flex flex-col items-center justify-center">
			<Spinner className="size-6" />
		</div>
	{/if}
</div>