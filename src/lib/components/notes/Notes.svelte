<script lang="ts">
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	import Fuse from 'fuse.js';

	const { saveAs } = fileSaver;

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

	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext, onDestroy } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import { createNewNote, deleteNoteById, getNotes } from '$lib/apis/notes';
	import { capitalizeFirstLetter, copyToClipboard, getTimeRange } from '$lib/utils';

	import { downloadPdf } from './utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import XMark from '../icons/XMark.svelte';

	const i18n = getContext('i18n');
	let loaded = false;

	let importFiles = '';
	let query = '';

	let noteItems = [];
	let fuse = null;

	let selectedNote = null;
	let notes = {};
	$: if (fuse) {
		notes = groupNotes(
			query
				? fuse.search(query).map((e) => {
						return e.item;
					})
				: noteItems
		);
	}

	let showDeleteConfirm = false;

	const groupNotes = (res) => {
		console.log(res);
		if (!Array.isArray(res)) {
			return {}; // or throw new Error("Notes response is not an array")
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
		noteItems = await getNotes(localStorage.token, true);

		fuse = new Fuse(noteItems, {
			keys: ['title']
		});
	};

	const createNoteHandler = async (content?: string) => {
		//  $i18n.t('New Note'),
		const res = await createNewNote(localStorage.token, {
			// YYYY-MM-DD
			title: dayjs().format('YYYY-MM-DD'),
			data: {
				content: {
					json: null,
					html: content ?? '',
					md: content ?? ''
				}
			},
			meta: null,
			access_control: {}
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/notes/${res.id}`);
		}
	};

	const downloadHandler = async (type) => {
		if (type === 'txt') {
			const blob = new Blob([selectedNote.data.content.md], { type: 'text/plain' });
			saveAs(blob, `${selectedNote.title}.txt`);
		} else if (type === 'md') {
			const blob = new Blob([selectedNote.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${selectedNote.title}.md`);
		} else if (type === 'pdf') {
			try {
				await downloadPdf(selectedNote);
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			init();
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		// Check if all the file is a markdown file and extract name and content

		for (const file of inputFiles) {
			if (file.type !== 'text/markdown') {
				toast.error($i18n.t('Only markdown files are allowed'));
				return;
			}

			const reader = new FileReader();
			reader.onload = async (event) => {
				const content = event.target.result;
				let name = file.name.replace(/\.md$/, '');

				if (typeof content !== 'string') {
					toast.error($i18n.t('Invalid file content'));
					return;
				}

				// Create a new note with the content
				const res = await createNewNote(localStorage.token, {
					title: name,
					data: {
						content: {
							json: null,
							html: marked.parse(content ?? ''),
							md: content
						}
					},
					meta: null,
					access_control: {}
				}).catch((error) => {
					toast.error(`${error}`);
					return null;
				});

				if (res) {
					init();
				}
			};

			reader.readAsText(file);
		}
	};

	let dragged = false;

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
				inputFilesHandler(inputFiles);
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
		if ($page.url.searchParams.get('content') !== null) {
			const content = $page.url.searchParams.get('content') ?? '';
			createNoteHandler(content);
			return;
		}

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
		{$i18n.t('Notes')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<FilesOverlay show={dragged} />

<div id="notes-container" class="w-full min-h-full h-full">
	{#if loaded}
		<DeleteConfirmDialog
			bind:show={showDeleteConfirm}
			title={$i18n.t('Delete note?')}
			on:confirm={() => {
				deleteNoteHandler(selectedNote.id);
				showDeleteConfirm = false;
			}}
		>
			<div class=" text-sm text-gray-500 truncate">
				{$i18n.t('This will delete')} <span class="  font-semibold">{selectedNote.title}</span>.
			</div>
		</DeleteConfirmDialog>

		<div class="flex flex-col gap-1 px-3.5">
			<div class=" flex flex-1 items-center w-full space-x-2">
				<div class="flex flex-1 items-center">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Notes')}
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

		<div class="px-4.5 @container h-full pt-2">
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
									class=" flex space-x-4 cursor-pointer w-full px-4.5 py-4 border border-gray-50 dark:border-gray-850 bg-transparent dark:hover:bg-gray-850 hover:bg-white rounded-2xl transition"
								>
									<div class=" flex flex-1 space-x-4 cursor-pointer w-full">
										<a
											href={`/notes/${note.id}`}
											class="w-full -translate-y-0.5 flex flex-col justify-between"
										>
											<div class="flex-1">
												<div class="  flex items-center gap-2 self-center mb-1 justify-between">
													<div class=" font-semibold line-clamp-1 capitalize">{note.title}</div>

													<div>
														<NoteMenu
															onDownload={(type) => {
																selectedNote = note;

																downloadHandler(type);
															}}
															onCopyLink={async () => {
																const baseUrl = window.location.origin;
																const res = await copyToClipboard(`${baseUrl}/notes/${note.id}`);

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
														</NoteMenu>
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

		<div class="absolute bottom-0 left-0 right-0 p-5 max-w-full flex justify-end">
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

				<!-- <button
				class="cursor-pointer p-2.5 flex rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition shadow-xl"
			>
				<SparklesSolid className="size-4" />
			</button> -->
			</div>
		</div>

		<!-- {#if $user?.role === 'admin'}
		<div class=" flex justify-end w-full mb-3">
			<div class="flex space-x-2">
				<input
					id="notes-import-input"
					bind:files={importFiles}
					type="file"
					accept=".md"
					hidden
					on:change={() => {
						console.log(importFiles);

						const reader = new FileReader();
						reader.onload = async (event) => {
							console.log(event.target.result);
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={() => {
						const notesImportInputElement = document.getElementById('notes-import-input');
						if (notesImportInputElement) {
							notesImportInputElement.click();
						}
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Notes')}</div>

					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>
			</div>
		</div>
	{/if} -->
	{:else}
		<div class="w-full h-full flex justify-center items-center">
			<Spinner className="size-5" />
		</div>
	{/if}
</div>
