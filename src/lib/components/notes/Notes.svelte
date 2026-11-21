<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto, tab: pageTab, active } = getPageContext();

	import WorkspaceAccessModal from '$lib/components/workspace/common/WorkspaceAccessModal.svelte';
	let accessModal: WorkspaceAccessModal;
	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';
	import { closePageTabs } from '$lib/stores/chatViewStates';
	import fileSaver from 'file-saver';

	const { saveAs } = fileSaver;

	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { onMount, getContext, onDestroy } from 'svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	import {
		WEBUI_NAME,
		config,
		user,
		pinnedNotes,
		mobile,
		showSidebar,
		settings
	} from '$lib/stores';
	import {
		createNewNote,
		deleteNoteById,
		getNoteById,
		getNoteList,
		searchNotes,
		toggleNotePinnedStatusById,
		getPinnedNoteList
	} from '$lib/apis/notes';
	import { capitalizeFirstLetter, copyToClipboard, getTimeRange } from '$lib/utils';
	import { downloadNote, createNoteHandler } from './utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import FileNavIcon from '../chat/FileNav/Icon.svelte';
	import Dropdown from '../common/Dropdown.svelte';
	import DropdownMenu from '../common/DropdownMenu.svelte';
	import DropdownSub from '../common/DropdownSub.svelte';
	import Check from '../icons/Check.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import XMark from '../icons/XMark.svelte';
	import Loader from '../common/Loader.svelte';
	import SidebarIcon from '../icons/Sidebar.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';

	let loaded = false;

	let importFiles = '';
	let importDocumentFiles: FileList | null = null;
	let notesImportInputElement: HTMLInputElement;
	let selectedNote = null;
	let openNoteMenuId: string | null = null;
	let showDeleteConfirm = false;
	let shiftKey = false;

	let notes = {};

	let items = null;
	let total = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let searchController: AbortController;

	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let displayOption: string | null = null;
	let viewOption: string | null = null;
	let permission: string | null = null;

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

		try {
			await downloadNote(note, type);
		} catch (error) {
			toast.error(String(error));
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			closePageTabs(`/notes/${id}`);
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
		allItemsLoaded = false;
		itemsLoading = false;
		notes = {};
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded || itemsLoading) return;
		page += 1;
		await getItemsPage();
	};

	const init = async () => {
		reset();
		await getItemsPage();
	};

	const handleSearchInput = () => {
		searchController?.abort();
		itemsLoading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (loaded) {
				init();
			}
		}, 300);
	};

	$: if (
		loaded &&
		$active &&
		sortKey !== undefined &&
		sortDirection !== undefined &&
		permission !== undefined &&
		viewOption !== undefined
	) {
		init();
	}

	const noteUrl = (note) =>
		query && note.data?.page_id
			? `/notes/${note.id}?page=${encodeURIComponent(note.data.page_id)}&search=${encodeURIComponent(query)}`
			: `/notes/${note.id}`;

	$: filterCount = (viewOption ? 1 : 0) + (permission ? 1 : 0);

	const setViewOption = (value: string | null) => {
		viewOption = value;
		if (value) localStorage.noteViewOption = value;
		else delete localStorage.noteViewOption;
		// The access filter only applies to notes others can share with you.
		if (value === 'created') permission = null;
	};

	const setDisplayOption = (value: string | null) => {
		displayOption = value;
		if (value) localStorage.noteDisplayOption = value;
		else delete localStorage.noteDisplayOption;
	};

	const newNoteHandler = async () => {
		const res = await createNoteHandler(dayjs().locale($i18n.language).format('YYYY-MM-DD'));
		if (res) goto(`/notes/${res.id}`);
	};

	const menuLabel = 'px-2 pt-1.5 pb-0.5 text-xs text-base-400 dark:text-base-500';
	const iconButton =
		'relative flex size-6.5 shrink-0 items-center justify-center rounded-full border border-base-100 bg-base-50/60 text-base-500 transition-colors hover:bg-base-100 hover:text-base-900 aria-expanded:bg-base-100 aria-expanded:text-base-900 dark:border-base-850 dark:bg-base-850/50 dark:text-base-400 dark:hover:bg-base-850 dark:hover:text-base-0 dark:aria-expanded:bg-base-850 dark:aria-expanded:text-base-0';

	// Same payload as sidebar page links, so a note can be dropped into split view;
	// the text/plain note entry still lets the chat composer attach it.
	const noteDragStartHandler = (event: DragEvent, note) => {
		if (!event.dataTransfer) return;
		event.dataTransfer.setData(
			'application/x-open-webui-page',
			JSON.stringify({ type: 'page', href: noteUrl(note), label: note.title })
		);
		event.dataTransfer.setData('application/x-open-webui-drag', '');
		event.dataTransfer.setData('text/plain', JSON.stringify({ type: 'note', id: note.id }));
		event.dataTransfer.effectAllowed = 'copyMove';
	};

	const getItemsPage = async () => {
		searchController?.abort();
		searchController = new AbortController();
		const { signal } = searchController;

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
			sortKey ? sortDirection : null,
			signal
		).catch(() => {
			return [];
		});

		if (signal.aborted) return;

		if (res) {
			total = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items && page > 1) {
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

		let keyboardFocusedElement: Element | null = null;
		const onFocusIn = (event: FocusEvent) => {
			const target = event.target as Element;
			keyboardFocusedElement = target.matches(':focus-visible:not(input, textarea)')
				? target
				: null;
		};

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Shift' && document.activeElement !== keyboardFocusedElement) {
				shiftKey = true;
				openNoteMenuId = null;
			}
		};

		const onKeyUp = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('focusin', onFocusIn);
		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);

		return () => {
			searchController?.abort();
			clearTimeout(searchDebounceTimer);

			window.removeEventListener('focusin', onFocusIn);
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);

			if (dropzoneElement) {
				dropzoneElement?.removeEventListener('dragover', onDragOver);
				dropzoneElement?.removeEventListener('drop', onDrop);
				dropzoneElement?.removeEventListener('dragleave', onDragLeave);
			}
		};
	});
	import PageTitle from '$lib/components/common/PageTitle.svelte';
</script>

<WorkspaceAccessModal bind:this={accessModal} resourceType="notes" onUpdated={init} />

<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
<PageTitle title={$i18n.t('Notes') + ' / ' + $WEBUI_NAME} />

<FilesOverlay show={dragged} />

<div id="notes-container" class="w-full min-h-full h-full">
	{#if loaded && items !== null && total !== null}
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
			<div class=" text-sm text-base-500 truncate">
				{$i18n.t('This will delete')} <span class="  font-normal">{selectedNote.title}</span>.
			</div>
		</DeleteConfirmDialog>

		<div class="space-y-1">
			<div class="flex h-8 items-center gap-1">
				{#if $mobile && !pageTab}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class="cursor-pointer flex rounded-lg hover:bg-base-100 dark:hover:bg-base-850 transition"
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
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

				<label
					class="flex h-full min-w-0 flex-1 items-center gap-2 px-1 text-base-400 dark:text-base-500"
				>
					<FileNavIcon name="search" size={14} class="shrink-0" />
					<input
						class="min-w-0 flex-1 bg-transparent text-[0.8125rem] text-base-800 outline-hidden placeholder:text-base-400 dark:text-base-100 dark:placeholder:text-base-500"
						bind:value={query}
						on:input={handleSearchInput}
						on:keydown={(event) => {
							if (event.key === 'Escape' && query) {
								query = '';
								handleSearchInput();
							}
						}}
						placeholder={$i18n.t('Search Notes')}
						aria-label={$i18n.t('Search Notes')}
					/>
					{#if query}
						<button
							type="button"
							class="flex size-4 shrink-0 items-center justify-center rounded-full hover:text-base-700 dark:hover:text-base-200"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								handleSearchInput();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					{/if}
				</label>

				<div class="flex shrink-0 items-center gap-1">
					<Dropdown align="end">
						<button
							type="button"
							class="{iconButton} {filterCount ? 'text-base-800 dark:text-base-100' : ''}"
							aria-label={$i18n.t('Filter')}
							title={$i18n.t('Filter')}
						>
							<svg
								class="size-3.75"
								viewBox="0 0 16 16"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-linecap="round"
								aria-hidden="true"><path d="M2.5 4h11M4.5 8h7M6.5 12h3" /></svg
							>
							{#if filterCount}
								<span
									class="absolute -right-0.5 -top-0.5 size-1.5 rounded-full bg-base-800 dark:bg-base-100"
								></span>
							{/if}
						</button>

						<DropdownMenu slot="content" className="w-48">
							<div class={menuLabel}>{$i18n.t('Show')}</div>
							{#each [[null, 'All'], ['created', 'Created by you'], ['shared', 'Shared with you']] as const as [value, label]}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={viewOption === value}
									on:click={() => setViewOption(value)}
								>
									<span class="flex-1 text-left">{$i18n.t(label)}</span>
									{#if viewOption === value}<Check className="size-3! shrink-0" />{/if}
								</button>
							{/each}

							{#if [null, 'shared'].includes(viewOption)}
								<hr class="border-base-50/30 dark:border-base-800/30" />
								<div class={menuLabel}>{$i18n.t('Access')}</div>
								{#each [[null, 'Write'], ['read_only', 'Read Only']] as const as [value, label]}
									<button
										type="button"
										role="menuitemradio"
										aria-checked={permission === value}
										on:click={() => (permission = value)}
									>
										<span class="flex-1 text-left">{$i18n.t(label)}</span>
										{#if permission === value}<Check className="size-3! shrink-0" />{/if}
									</button>
								{/each}
							{/if}

							{#if filterCount}
								<hr class="border-base-50/30 dark:border-base-800/30" />
								<button
									type="button"
									on:click={() => {
										setViewOption(null);
										permission = null;
									}}
								>
									<XMark className="size-3.5" />{$i18n.t('Clear filters')}
								</button>
							{/if}
						</DropdownMenu>
					</Dropdown>

					<Dropdown align="end">
						<button
							type="button"
							class={iconButton}
							aria-label={$i18n.t('Display options')}
							title={$i18n.t('Display options')}
						>
							<AdjustmentsHorizontal className="size-3.75" />
						</button>

						<DropdownMenu slot="content" className="w-48">
							<div class={menuLabel}>{$i18n.t('Layout')}</div>
							<!-- i18n:parse cannot see keys passed in as variables, so these keep them in the locale files: $i18n.t('List') $i18n.t('Grid') -->
							{#each [[null, 'List', 'list'], ['grid', 'Grid', 'grid']] as const as [value, label, icon]}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={displayOption === value}
									on:click={() => setDisplayOption(value)}
								>
									<FileNavIcon name={icon} size={14} />
									<span class="flex-1 text-left">{$i18n.t(label)}</span>
									{#if displayOption === value}<Check className="size-3! shrink-0" />{/if}
								</button>
							{/each}

							<hr class="border-base-50/30 dark:border-base-800/30" />

							<DropdownSub contentClass="select-none z-50" maxWidth={320} sideOffset={6}>
								<button
									slot="trigger"
									type="button"
									class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] outline-hidden"
								>
									<span class="min-w-0 flex-1 truncate text-left">{$i18n.t('Ordering')}</span>
									<span class="truncate text-base-500 dark:text-base-400"
										>{sortKey === 'name' ? $i18n.t('Title') : $i18n.t('Updated')}</span
									>
									<ChevronRight className="size-3.5 shrink-0 text-base-400 rtl:rotate-180" />
								</button>
								{#each [['updated_at', 'Updated'], ['name', 'Title']] as const as [value, label]}
									<button
										type="button"
										role="menuitemradio"
										aria-checked={sortKey === value}
										on:click={() => {
											if (sortKey !== value) setSortKey(value);
										}}
									>
										<span class="flex-1 text-left">{$i18n.t(label)}</span>
										{#if sortKey === value}<Check className="size-3! shrink-0" />{/if}
									</button>
								{/each}
								<hr class="border-base-50/30 dark:border-base-800/30" />
								{#each [['asc', 'Ascending'], ['desc', 'Descending']] as const as [value, label]}
									<button
										type="button"
										role="menuitemradio"
										aria-checked={sortDirection === value}
										on:click={() => (sortDirection = value)}
									>
										<span class="flex-1 text-left">{$i18n.t(label)}</span>
										{#if sortDirection === value}<Check className="size-3! shrink-0" />{/if}
									</button>
								{/each}
							</DropdownSub>
						</DropdownMenu>
					</Dropdown>

					<Dropdown align="end" closeOnSelect>
						<button
							type="button"
							class={iconButton}
							aria-label={$i18n.t('New Note')}
							title={$i18n.t('New Note')}
						>
							<Plus className="size-3.5" strokeWidth="2" />
						</button>

						<DropdownMenu slot="content" className="w-44">
							<button type="button" on:click={newNoteHandler}>
								<FileNavIcon name="file-plus" size={14} />
								<span class="flex-1 text-left">{$i18n.t('New Note')}</span>
							</button>
							<button type="button" on:click={() => notesImportInputElement?.click()}>
								<FileNavIcon name="upload" size={14} />
								<span class="flex-1 text-left">{$i18n.t('Import txt/md')}</span>
							</button>
						</DropdownMenu>
					</Dropdown>
				</div>
			</div>

			{#if items !== null && total !== null}
				{#if (items ?? []).length > 0}
					{@const groupedNotes = groupNotes(items)}

					<div class="@container h-full my-1">
						<div>
							{#if displayOption === null}
								<div
									class="flex w-full items-center gap-2 px-2 pb-2 text-xs text-base-400 dark:text-base-600"
								>
									<div class="flex min-w-0 flex-1 items-center">
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
									</div>

									<div class="ml-2 flex shrink-0 items-center justify-end gap-2">
										<div class="hidden w-44 shrink-0 md:block"></div>
										<div class="size-5 shrink-0"></div>
										<button
											class="flex w-24 shrink-0 items-center justify-end gap-1 py-0.5 text-right"
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
								</div>
							{/if}

							{#each groupedNotes as [timeRange, notesList], idx}
								<div class="w-full px-2 pb-1 text-xs text-base-500 dark:text-base-500">
									{$i18n.t(timeRange)}
								</div>

								{#if displayOption === null}
									<div
										class="{groupedNotes.length - 1 !== idx ? 'mb-3' : ''} gap-y-0.5 flex flex-col"
									>
										<!-- Preserve the former row label for i18n extraction: $i18n.t('Open note') -->
										{#each notesList as note, idx (note.id)}
											<div
												class="group flex min-h-8 w-full items-center gap-2 rounded-xl px-2 py-[0.375rem] text-left transition hover:bg-base-50 focus-within:bg-base-50 dark:hover:bg-base-900 dark:focus-within:bg-base-900"
												role="presentation"
												draggable="true"
												on:dragstart={(e) => noteDragStartHandler(e, note)}
												on:click={(e) => {
													if (e.target instanceof Element && e.target.closest('a')) return;
													goto(noteUrl(note));
												}}
											>
												<div class="flex min-w-0 flex-1 items-center gap-2">
													<Tooltip content={note.title} className="min-w-0" placement="top-start">
														<a
															href={noteUrl(note)}
															dir="auto"
															class="focus-ring block h-[1.25rem] truncate rounded text-[0.8125rem] leading-5 text-base-800 group-hover:underline focus-visible:underline dark:text-base-200"
														>
															{note.title}
														</a>
													</Tooltip>

													<Tooltip
														content={dayjs(note.updated_at / 1000000)
															.locale($i18n.language)
															.format('LLLL')}
													>
														<div
															class="shrink-0 truncate text-[0.6875rem] leading-5 text-base-400 dark:text-base-600"
														>
															{dayjs(note.updated_at / 1000000)
																.locale($i18n.language)
																.fromNow()}
														</div>
													</Tooltip>
												</div>

												<div class="ml-2 flex shrink-0 items-center justify-end gap-2">
													<div
														class="hidden max-w-44 shrink-0 truncate text-right text-[0.6875rem] leading-5 text-base-500 dark:text-base-500 md:block"
													>
														<Tooltip
															content={note?.user?.email ?? $i18n.t('Deleted User')}
															className="min-w-0"
															placement="top-start"
														>
															<span class="flex min-w-0 max-w-44 items-center gap-1.75">
																<ProfileImage
																	src={note?.user?.id
																		? `/api/v1/users/${note.user.id}/profile/image`
																		: '/user.png'}
																	className="size-4 shrink-0 rounded-full!"
																/>
																<span class="min-w-0 max-w-24 truncate">
																	{capitalizeFirstLetter(
																		note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
																	)}
																</span>
															</span>
														</Tooltip>
													</div>

													{#if shiftKey}
														<Tooltip content={$i18n.t('Delete')}>
															<button
																class="flex {($settings?.highContrastMode ?? false)
																	? 'size-6'
																	: 'size-5'} shrink-0 items-center justify-center rounded-lg text-base-400 transition hover:text-base-700 dark:text-base-500 dark:hover:text-base-200"
																type="button"
																aria-label={$i18n.t('Delete')}
																on:click={(e) => {
																	e.preventDefault();
																	e.stopPropagation();
																	deleteNoteHandler(note.id);
																}}
															>
																<GarbageBin className="size-3.5" />
															</button>
														</Tooltip>
													{:else}
														<NoteMenu
															onAccess={(note.user_id === $user?.id &&
																$user?.permissions?.sharing?.notes) ||
															$user?.role === 'admin'
																? () => accessModal.open(note.id)
																: null}
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
															isPinned={$pinnedNotes.some((n) => n.id === note.id)}
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
																class="flex {($settings?.highContrastMode ?? false)
																	? 'size-6'
																	: 'size-5'} shrink-0 items-center justify-center rounded-lg text-base-400 transition hover:text-base-700 dark:text-base-500 dark:hover:text-base-200"
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
													{/if}
												</div>
											</div>
										{/each}
									</div>
								{:else if displayOption === 'grid'}
									<div
										class="{groupedNotes.length - 1 !== idx
											? 'mb-3'
											: ''} grid grid-cols-[repeat(auto-fill,minmax(min(104px,100%),1fr))] gap-1.5 p-2"
									>
										{#each notesList as note, idx (note.id)}
											<div class="group relative min-w-0 self-start rounded-xl">
												<a
													href={noteUrl(note)}
													on:dragstart={(e) => noteDragStartHandler(e, note)}
													class="focus-ring flex min-w-0 flex-col items-center gap-1 rounded-xl px-1 pt-2 pb-1.5 text-center transition-colors duration-75 hover:bg-base-50/60 dark:hover:bg-base-0/4"
													aria-label={note.title}
												>
													<span
														class="flex h-[5.75rem] w-full shrink-0 items-center justify-center"
														aria-hidden="true"
													>
														<span
															class="relative h-[5.75rem] w-[4.75rem] overflow-hidden rounded-lg border border-base-200 bg-base-0 shadow-xs dark:border-base-700 dark:bg-base-850"
														>
															<!-- Earlier wording, kept so i18n:parse does not drop its translations: $i18n.t('No content') -->
															{#if note.data?.content?.md?.trim()}
																<span
																	dir="auto"
																	class="absolute left-0 top-0 block w-full whitespace-pre-line break-words p-1.5 text-left text-[10px] leading-[13px] text-base-500 dark:text-base-400"
																	><span class="block text-base-800 dark:text-base-200"
																		>{note.title}</span
																	>{note.data.content.md.slice(0, 600)}</span
																>
																<span
																	class="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-linear-to-t from-base-0 from-15% to-transparent dark:from-base-850"
																></span>
															{:else}
																<span class="flex h-full w-full items-center justify-center">
																	<FileNavIcon
																		name="page-text"
																		size={20}
																		strokeWidth={1.2}
																		class="text-base-400 dark:text-base-500"
																	/>
																</span>
															{/if}
														</span>
													</span>

													<Tooltip content={note.title} className="w-full min-w-0" placement="top">
														<span
															dir="auto"
															class="block w-full min-w-0 shrink-0 truncate text-[0.8125rem] leading-[18px] text-base-800 dark:text-base-200"
														>
															{note.title}
														</span>
													</Tooltip>

													<Tooltip
														content={dayjs(note.updated_at / 1000000)
															.locale($i18n.language)
															.format('LLLL')}
														className="w-full min-w-0"
													>
														<span
															class="block w-full min-w-0 truncate text-xs leading-4 text-base-500 dark:text-base-400"
														>
															{dayjs(note.updated_at / 1000000)
																.locale($i18n.language)
																.fromNow()}
														</span>
													</Tooltip>
												</a>

												{#if shiftKey}
													<Tooltip content={$i18n.t('Delete')}>
														<button
															class="absolute top-2.5 left-[calc(50%_+_12px)] flex size-6 items-center justify-center rounded-md bg-base-0/90 text-base-500 shadow-xs backdrop-blur-sm transition hover:text-base-800 dark:bg-base-800/90 dark:text-base-400 dark:hover:text-base-100"
															type="button"
															aria-label={$i18n.t('Delete')}
															on:click={(e) => {
																e.preventDefault();
																e.stopPropagation();
																deleteNoteHandler(note.id);
															}}
														>
															<GarbageBin className="size-3.5" />
														</button>
													</Tooltip>
												{:else}
													<NoteMenu
														onAccess={(note.user_id === $user?.id &&
															$user?.permissions?.sharing?.notes) ||
														$user?.role === 'admin'
															? () => accessModal.open(note.id)
															: null}
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
														isPinned={$pinnedNotes.some((n) => n.id === note.id)}
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
															class="absolute top-2.5 left-[calc(50%_+_12px)] flex size-6 items-center justify-center rounded-md bg-base-0/90 text-base-500 shadow-xs backdrop-blur-sm transition hover:text-base-800 group-hover:opacity-100 group-focus-within:opacity-100 dark:bg-base-800/90 dark:text-base-400 dark:hover:text-base-100 max-md:opacity-100 {openNoteMenuId ===
															note.id
																? 'opacity-100'
																: 'opacity-0'}"
															type="button"
															aria-label={$i18n.t('Note Menu')}
														>
															<FileNavIcon name="three-dots" size={12} strokeWidth={1.4} />
														</button>
													</NoteMenu>
												{/if}
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
						<div class="max-w-sm text-center text-base-900 dark:text-base-100">
							<div class="mb-1.5 text-sm">
								{$i18n.t('No Notes')}
							</div>

							<div class="text-xs leading-5 text-base-500">
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
