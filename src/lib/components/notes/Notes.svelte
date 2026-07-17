<script lang="ts">
	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';

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

	import { onMount, getContext, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { goto } from '$app/navigation';
	import { WEBUI_NAME, config, user, pinnedNotes, mobile, showSidebar } from '$lib/stores';
	import {
		createNewNote,
		deleteNoteById,
		getNoteById,
		getNoteList,
		searchNotes,
		toggleNotePinnedStatusById,
		getPinnedNoteList
	} from '$lib/apis/notes';
	import { capitalizeFirstLetter, copyToClipboard, formatNumber, getTimeRange } from '$lib/utils';
	import { downloadPdf, createNoteHandler } from './utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import XMark from '../icons/XMark.svelte';
	import DropdownOptions from '../common/DropdownOptions.svelte';
	import Loader from '../common/Loader.svelte';
	import SidebarIcon from '../icons/Sidebar.svelte';
	import SplitCreateButton from '../common/SplitCreateButton.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';

	let loaded = false;

	let importFiles = '';
	let importDocumentFiles: FileList | null = null;
	let notesImportInputElement: HTMLInputElement;
	let selectedNote = null;
	let openNoteMenuId: string | null = null;
	let showDeleteConfirm = false;

	let notes = {};

	let items = null;
	let total = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let displayOption = null;
	let viewOption = null;
	let permission = null;

	let page = 1;

	let itemsLoading = false;
	let allItemsLoaded = false;

	const downloadHandler = async (type) => {
		// Fetch the full note since the list response may not contain full content
		const note = await getNoteById(localStorage.token, selectedNote.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!note) return;

		if (type === 'txt') {
			const blob = new Blob([note.data.content.md], { type: 'text/plain' });
			saveAs(blob, `${note.title}.txt`);
		} else if (type === 'md') {
			const blob = new Blob([note.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${note.title}.md`);
		} else if (type === 'pdf') {
			try {
				await downloadPdf(note);
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
			pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
			init();
		}
	};

	const inputFilesHandler = async (inputFiles: File[]) => {
		let imported = false;

		for (const file of inputFiles) {
			const isSupportedFile =
				file.type === 'text/markdown' ||
				file.type === 'text/plain' ||
				/\.(md|txt)$/i.test(file.name);

			if (!isSupportedFile) {
				toast.error('Only txt and md files are allowed');
				return;
			}

			const content = await file.text();
			const name = file.name.replace(/\.(md|txt)$/i, '');

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
				access_grants: []
			}).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				imported = true;
			}
		}

		if (imported) {
			init();
		}
	};

	const reset = () => {
		page = 1;
		items = null;
		total = null;
		allItemsLoaded = false;
		itemsLoading = false;
		notes = {};
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage();
	};

	const init = async () => {
		reset();
		await getItemsPage();
	};

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (loaded) {
				init();
			}
		}, 300);
	};

	$: if (
		loaded &&
		sortKey !== undefined &&
		sortDirection !== undefined &&
		permission !== undefined &&
		viewOption !== undefined
	) {
		init();
	}

	const getItemsPage = async () => {
		itemsLoading = true;

		if (viewOption === 'created') {
			permission = null;
		}

		const res = await searchNotes(
			localStorage.token,
			query,
			viewOption,
			permission,
			sortKey,
			page,
			sortKey ? sortDirection : null
		).catch(() => {
			return [];
		});

		if (res) {
			total = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items) {
				const existingIds = new Set(items.map((item) => item.id));
				const newItems = pageItems.filter((item) => !existingIds.has(item.id));
				items = [...items, ...newItems];
			} else {
				items = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	const groupNotes = (res) => {
		if (!Array.isArray(res)) {
			return []; // Return empty array for invalid input
		}

		// Build the grouped object while tracking order
		const grouped: Record<string, any[]> = {};
		const orderedKeys: string[] = [];

		for (const note of res) {
			const timeRange = getTimeRange(note.updated_at / 1000000000);
			if (!grouped[timeRange]) {
				grouped[timeRange] = [];
				orderedKeys.push(timeRange);
			}
			grouped[timeRange].push({
				...note,
				timeRange
			});
		}

		// Return as array of [timeRange, notes] to preserve insertion order
		return orderedKeys.map((key) => [key, grouped[key]] as [string, any[]]);
	};

	const setSortKey = (key: string) => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = key === 'updated_at' ? 'desc' : 'asc';
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

	const onDrop = async (e: DragEvent) => {
		e.preventDefault();
		console.log(e);

		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer.files) as File[];
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				await inputFilesHandler(inputFiles);
			}
		}

		dragged = false;
	};

	onMount(() => {
		viewOption = localStorage?.noteViewOption ?? null;
		displayOption = localStorage?.noteDisplayOption ?? null;

		loaded = true;

		const dropzoneElement = document.getElementById('notes-container');
		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);

		return () => {
			clearTimeout(searchDebounceTimer);

			if (dropzoneElement) {
				dropzoneElement?.removeEventListener('dragover', onDragOver);
				dropzoneElement?.removeEventListener('drop', onDrop);
				dropzoneElement?.removeEventListener('dragleave', onDragLeave);
			}
		};
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
		<input
			id="notes-import-input"
			bind:this={notesImportInputElement}
			bind:files={importDocumentFiles}
			type="file"
			accept=".txt,.md,text/plain,text/markdown"
			multiple
			hidden
			on:change={async () => {
				if (!importDocumentFiles || importDocumentFiles.length === 0) return;

				try {
					await inputFilesHandler(Array.from(importDocumentFiles));
					toast.success($i18n.t('Imported notes successfully'));
				} catch (error) {
					toast.error(`${error}`);
				} finally {
					importDocumentFiles = null;
					notesImportInputElement.value = '';
				}
			}}
		/>

		<DeleteConfirmDialog
			bind:show={showDeleteConfirm}
			title={$i18n.t('Delete note?')}
			on:confirm={() => {
				deleteNoteHandler(selectedNote.id);
				showDeleteConfirm = false;
			}}
		>
			<div class=" text-sm text-gray-500 truncate">
				{$i18n.t('This will delete')} <span class="  font-normal">{selectedNote.title}</span>.
			</div>
		</DeleteConfirmDialog>

		<div class="flex items-center gap-0.5 md:gap-1 mb-1">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class="self-center p-1.5">
								<SidebarIcon className="size-4" />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="flex w-full items-center">
				<div class="flex items-center gap-1 py-1 min-w-0">
					<span class="min-w-fit px-1 text-sm select-none">{$i18n.t('Notes')}</span>
					<span class="text-sm text-gray-500 dark:text-gray-500">
						{total === null ? '' : formatNumber(total)}
					</span>
				</div>

				<div class="ml-auto flex items-center gap-1">
					<SplitCreateButton
						actions={[
							{
								id: 'notes-new',
								label: $i18n.t('Create'),
								onClick: async () => {
									const res = await createNoteHandler(dayjs().format('YYYY-MM-DD'));

									if (res) {
										goto(`/notes/${res.id}`);
									}
								}
							},
							{
								id: 'notes-import',
								label: $i18n.t('Import txt/md'),
								onClick: () => notesImportInputElement?.click()
							}
						]}
					/>
				</div>
			</div>
		</div>

		<div class="space-y-1">
			<div class="flex h-8 flex-1 items-center w-full gap-2">
				<div class="flex min-w-0 flex-1 items-center">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						on:input={handleSearchInput}
						placeholder={$i18n.t('Search Notes')}
					/>

					{#if query}
						<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
							<button
								class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								on:click={() => {
									query = '';
									handleSearchInput();
								}}
							>
								<XMark className="size-3" strokeWidth="2" />
							</button>
						</div>
					{/if}
				</div>

				<div
					class="flex max-w-[55%] shrink-0 overflow-x-auto scrollbar-none"
					on:wheel={(e) => {
						if (e.deltaY !== 0) {
							e.preventDefault();
							e.currentTarget.scrollLeft += e.deltaY;
						}
					}}
				>
					<div
						class="flex w-fit gap-0.5 text-center text-sm rounded-full bg-transparent whitespace-nowrap"
					>
						<DropdownOptions
							align="end"
							bind:value={viewOption}
							items={[
								{ value: null, label: $i18n.t('All') },
								{ value: 'created', label: $i18n.t('Created by you') },
								{ value: 'shared', label: $i18n.t('Shared with you') }
							]}
							onChange={(value) => {
								if (value) {
									localStorage.noteViewOption = value;
								} else {
									delete localStorage.noteViewOption;
								}
							}}
						/>

						{#if [null, 'shared'].includes(viewOption)}
							<DropdownOptions
								align="end"
								bind:value={permission}
								items={[
									{ value: null, label: $i18n.t('Write') },
									{ value: 'read_only', label: $i18n.t('Read Only') }
								]}
							/>
						{/if}

						<DropdownOptions
							align="end"
							bind:value={displayOption}
							items={[
								{ value: null, label: $i18n.t('List') },
								{ value: 'grid', label: $i18n.t('Grid') }
							]}
							onChange={() => {
								if (displayOption) {
									localStorage.noteDisplayOption = displayOption;
								} else {
									delete localStorage.noteDisplayOption;
								}
							}}
						/>
					</div>
				</div>
			</div>

			{#if items !== null && total !== null}
				{#if (items ?? []).length > 0}
					{@const groupedNotes = groupNotes(items)}

					<div class="@container h-full my-1">
						<div>
							{#if displayOption === null}
								<div
									class="flex w-full items-center gap-2 px-2 pb-2 text-xs text-gray-400 dark:text-gray-600"
								>
									<div class="flex min-w-0 flex-1 items-center gap-3">
										<button
											class="flex min-w-0 items-center gap-1 py-0.5 text-left"
											type="button"
											on:click={() => setSortKey('name')}
										>
											{$i18n.t('Title')}
											{#if sortKey === 'name'}
												{#if sortDirection === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											{/if}
										</button>

										<button
											class="flex shrink-0 items-center gap-1 py-0.5 text-left"
											type="button"
											on:click={() => setSortKey('updated_at')}
										>
											{$i18n.t('Updated at')}
											{#if sortKey === 'updated_at'}
												{#if sortDirection === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											{/if}
										</button>
									</div>

									<div class="hidden w-44 shrink-0 md:block"></div>
								</div>
							{/if}

							{#each groupedNotes as [timeRange, notesList], idx}
								<div class="w-full px-2 pb-1 text-xs text-gray-500 dark:text-gray-500">
									{$i18n.t(timeRange)}
								</div>

								{#if displayOption === null}
									<div
										class="{groupedNotes.length - 1 !== idx ? 'mb-3' : ''} gap-y-0.5 flex flex-col"
									>
										{#each notesList as note, idx (note.id)}
											<button
												type="button"
												aria-label={$i18n.t('Open note')}
												class="group flex min-h-8 w-full items-center gap-2 rounded-xl px-2 py-[6px] text-left transition hover:bg-gray-50 focus-within:bg-gray-50 dark:hover:bg-gray-900 dark:focus-within:bg-gray-900"
												on:click={() => {
													goto(`/notes/${note.id}`);
												}}
											>
												<div class="flex min-w-0 flex-1 items-center gap-2">
													<Tooltip content={note.title} className="min-w-0" placement="top-start">
														<div
															dir="auto"
															class="h-[20px] truncate text-[13px] leading-5 text-gray-800 hover:underline dark:text-gray-200"
														>
															{note.title}
														</div>
													</Tooltip>

													<Tooltip content={dayjs(note.updated_at / 1000000).format('LLLL')}>
														<div
															class="shrink-0 truncate text-[11px] leading-5 text-gray-400 dark:text-gray-600"
														>
															{dayjs(note.updated_at / 1000000).fromNow()}
														</div>
													</Tooltip>
												</div>

												<div class="ml-2 flex shrink-0 items-center justify-end gap-2">
													<div
														class="hidden max-w-44 shrink-0 truncate text-right text-[11px] leading-5 text-gray-500 dark:text-gray-500 md:block"
													>
														<Tooltip
															content={note?.user?.email ?? $i18n.t('Deleted User')}
															className="min-w-0"
															placement="top-start"
														>
															<div class="truncate">
																{capitalizeFirstLetter(
																	note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
																)}
															</div>
														</Tooltip>
													</div>

													<NoteMenu
														show={openNoteMenuId === note.id}
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
														isPinned={note.is_pinned ?? false}
														onPin={async () => {
															await toggleNotePinnedStatusById(localStorage.token, note.id);
															pinnedNotes.set(
																await getPinnedNoteList(localStorage.token).catch(() => [])
															);
															init();
														}}
														onChange={(state) => {
															openNoteMenuId = state ? note.id : null;
														}}
													>
														<button
															class="flex size-5 shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200"
															type="button"
															aria-label={$i18n.t('Note Menu')}
															on:click={(e) => {
																e.preventDefault();
																e.stopPropagation();
																openNoteMenuId = openNoteMenuId === note.id ? null : note.id;
															}}
														>
															<EllipsisHorizontal className="size-3.5" />
														</button>
													</NoteMenu>
												</div>
											</button>
										{/each}
									</div>
								{:else if displayOption === 'grid'}
									<div
										class="{groupedNotes.length - 1 !== idx
											? 'mb-5'
											: ''} gap-2.5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
									>
										{#each notesList as note, idx (note.id)}
											<div
												class="group flex min-h-32 w-full flex-col rounded-lg bg-gray-50/40 p-2.5 text-left transition hover:bg-gray-100/60 focus-within:bg-gray-100/60 dark:bg-gray-900/30 dark:hover:bg-gray-900 dark:focus-within:bg-gray-900"
											>
												<div class="flex items-start gap-2">
													<a href={`/notes/${note.id}`} class="min-w-0 flex-1">
														<Tooltip content={note.title} placement="top-start">
															<div
																class="truncate text-[13px] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
															>
																{note.title}
															</div>
														</Tooltip>
													</a>

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
														isPinned={note.is_pinned ?? false}
														onPin={async () => {
															await toggleNotePinnedStatusById(localStorage.token, note.id);
															pinnedNotes.set(
																await getPinnedNoteList(localStorage.token).catch(() => [])
															);
															init();
														}}
													>
														<button
															class="flex size-5 items-center justify-center rounded-lg text-gray-400 transition hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200"
															type="button"
															aria-label={$i18n.t('Note Menu')}
														>
															<EllipsisHorizontal className="size-3.5" />
														</button>
													</NoteMenu>
												</div>

												<a href={`/notes/${note.id}`} class="mt-1 flex min-h-0 flex-1 flex-col">
													<div
														class="line-clamp-3 text-xs leading-5 text-gray-500 dark:text-gray-500"
													>
														{#if note.data?.content?.md}
															{note.data?.content?.md}
														{:else}
															{$i18n.t('No content')}
														{/if}
													</div>

													<div
														class="mt-auto flex w-full items-center justify-between gap-2 pt-3 text-[11px] leading-4 text-gray-500 dark:text-gray-500"
													>
														<Tooltip
															content={note?.user?.email ?? $i18n.t('Deleted User')}
															className="min-w-0"
															placement="top-start"
														>
															<div class="truncate">
																{capitalizeFirstLetter(
																	note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
																)}
															</div>
														</Tooltip>

														<Tooltip content={dayjs(note.updated_at / 1000000).format('LLLL')}>
															<div class="shrink-0">
																{dayjs(note.updated_at / 1000000).fromNow()}
															</div>
														</Tooltip>
													</div>
												</a>
											</div>
										{/each}
									</div>
								{/if}
							{/each}

							{#if !allItemsLoaded}
								<Loader
									on:visible={(e) => {
										if (!itemsLoading) {
											loadMoreItems();
										}
									}}
								>
									<div
										class="w-full flex justify-center py-4 text-xs animate-pulse items-center gap-2"
									>
										<Spinner className=" size-4" />
										<div class=" ">{$i18n.t('Loading...')}</div>
									</div>
								</Loader>
							{/if}
						</div>
					</div>
				{:else}
					<div class="flex min-h-[calc(100dvh-13rem)] w-full flex-col items-center justify-center">
						<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
							<div class="mb-1.5 text-sm">
								{$i18n.t('No Notes')}
							</div>

							<div class="text-xs leading-5 text-gray-500">
								{$i18n.t('Create your first note from the Create menu.')}
							</div>
						</div>
					</div>
				{/if}
			{:else}
				<div class="w-full h-full flex justify-center items-center py-10">
					<Spinner className="size-4" />
				</div>
			{/if}
		</div>
	{:else}
		<div class="w-full h-full flex justify-center items-center">
			<Spinner className="size-4" />
		</div>
	{/if}
</div>
