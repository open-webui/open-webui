<script context="module">
	let closeActiveHoverPreview = null;
	// Drag data can't be read until the drop
	/** @type {string | null} */
	let draggedFolderId = null;
</script>

<script>
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';

	const i18n = getContext('i18n');
	const appLayout = getContext('appLayout');
	const dispatch = createEventDispatcher();

	import DOMPurify from 'dompurify';
	import { LinkPreview } from 'bits-ui';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { navigating, page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import {
		activeChatTabId,
		chatId,
		chatTabRequest,
		config,
		mobile,
		selectedFolder,
		settings,
		showSidebar,
		user
	} from '$lib/stores';
	import {
		folderStates,
		folderChatPageKey,
		loadFolderChatPage,
		loadFolderDetails,
		setFolderSidebarPage,
		updateFolderChatLists,
		markFolderRead,
		updateFolderDetails,
		removeFolderState,
		isCancelledFolderRequest
	} from '$lib/stores/folderStates';
	import { pendingChatRequest } from '$lib/stores/chatCache';
	import { refreshFolderChatLists } from '$lib/stores/chatList';
	import { sortFolders } from '$lib/utils/folders';
	import { updateNoteFolderIdById } from '$lib/apis/notes';
	import { createNoteHandler } from '$lib/components/notes/utils';
	import dayjs from '$lib/dayjs';

	import {
		deleteFolderById,
		updateFolderIsExpandedById,
		updateFolderById,
		updateFolderParentIdById,
		createNewFolder,
		markFolderChatsReadById
	} from '$lib/apis/folders';
	import {
		getChatById,
		getChatsByFolderId,
		updateChatFolderIdById,
		importChats
	} from '$lib/apis/chats';

	import ChevronDown from './icons/ChevronDown.svelte';
	import ChevronRight from './icons/ChevronRight.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';

	import FolderIcon from '$lib/components/icons/Folder.svelte';
	import MoreHorizontal from './icons/MoreHorizontal.svelte';

	import ChatItem from './ChatItem.svelte';
	import FolderHoverPreview from './FolderHoverPreview.svelte';
	import FolderMenu from './Folders/FolderMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import FolderModal from './Folders/FolderModal.svelte';
	import FolderShareModal from './Folders/FolderShareModal.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';

	export let folderRegistry = {};
	export let open = false;

	export let folders;
	export let folderId;
	export let shiftKey = false;

	export let className = '';

	export let deleteFolderContents = true;

	export let parentDragged = false;

	export let onDelete = () => {};
	export let onItemMove = () => {};
	/** @type {(id: string, targetId: string, position: 'before' | 'after') => void} */
	export let onReorder = () => {};
	export let onFolderUnreadCounts = () => {};

	let folderElement;
	/** @type {HTMLElement} */
	let rowElement;

	let openPreview = false;
	let showFolderModal = false;
	let showShareModal = false;
	let edit = false;

	let showCreateSubFolderModal = false;
	let createSubFolderParentId = null;

	let draggedOver = false;
	let dropPosition = 'inside';
	let dragged = false;

	$: if ($mobile || edit || dragged || parentDragged || draggedOver || showFolderModal) {
		openPreview = false;
	}

	const closeHoverPreview = () => {
		if (openPreview) {
			openPreview = false;
		}
	};

	$: if (openPreview && closeActiveHoverPreview !== closeHoverPreview) {
		closeActiveHoverPreview?.();
		closeActiveHoverPreview = closeHoverPreview;
	}

	let name = '';

	const formatUnreadCount = (count) =>
		new Intl.NumberFormat(undefined, {
			notation: 'compact',
			compactDisplay: 'short'
		}).format(count);

	const isUnreadChat = (chat) =>
		!(chat.active ?? false) &&
		(chat.last_read_at == null ||
			(typeof chat.updated_at === 'number' &&
				typeof chat.last_read_at === 'number' &&
				chat.updated_at > chat.last_read_at));

	const sortFolderChats = (items) =>
		[...items].sort(
			(a, b) =>
				Number(isUnreadChat(b)) - Number(isUnreadChat(a)) ||
				Number(b.updated_at ?? 0) - Number(a.updated_at ?? 0)
		);

	const mergeFolderChats = (items, nextItems) => {
		const merged = [...items];
		const indexById = new Map(merged.map((chat, index) => [chat.id, index]));

		for (const chat of nextItems) {
			if (!chat?.id) {
				continue;
			}

			const index = indexById.get(chat.id);
			if (index === undefined) {
				indexById.set(chat.id, merged.length);
				merged.push(chat);
			} else {
				merged[index] = { ...merged[index], ...chat };
			}
		}

		return sortFolderChats(merged);
	};

	const applyReadState = (data) => {
		if (data?.folder_unread_counts) {
			onFolderUnreadCounts(data.folder_unread_counts);
		}

		if (typeof data?.last_read_at === 'number') {
			updateFolderChatLists({ id: data.chat_id, last_read_at: data.last_read_at });
			void refreshFolderChatLists();
		}
	};

	const markAllReadHandler = async () => {
		const res = await markFolderChatsReadById(localStorage.token, folderId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!res) return;

		if (res.folder_unread_counts) {
			onFolderUnreadCounts(res.folder_unread_counts);
		}

		for (const readFolderId of res.folder_ids ?? []) {
			if (readFolderId !== folderId) {
				folderRegistry[readFolderId]?.setFolderItems?.();
			}
		}

		for (const id of res.folder_ids ?? [folderId]) markFolderRead(id, $user?.id);
		void refreshFolderChatLists();
	};

	$: isWritable = !folders[folderId]?.shared || folders[folderId]?.permission === 'write';

	/** @param {any} e */
	const getDropPosition = (e) => {
		// Only folders reorder, and shared folders keep their place
		if (draggedFolderId && !folders[folderId]?.shared && rowElement.contains(e.target)) {
			const rect = rowElement.getBoundingClientRect();
			const offset = (e.clientY - rect.top) / rect.height;
			if (offset < 0.25) return 'before';
			if (offset > 0.75) return 'after';
		}
		return 'inside';
	};

	const onDragOver = (e) => {
		e.stopPropagation();
		if (dragged || parentDragged || !isWritable) {
			return;
		}
		e.preventDefault();
		draggedOver = true;
		dropPosition = getDropPosition(e);
	};

	const onDrop = async (e) => {
		e.preventDefault();
		e.stopPropagation();
		if (dragged || parentDragged || !isWritable) {
			return;
		}

		if (folderElement.contains(e.target)) {
			console.log('Dropped on the Button');

			if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
				// Iterate over all items in the DataTransferItemList use functional programming
				for (const item of Array.from(e.dataTransfer.items)) {
					// If dropped items aren't files, reject them
					if (item.kind === 'file') {
						const file = item.getAsFile();
						if (file && file.type === 'application/json') {
							console.log('Dropped file is a JSON file!');

							// Read the JSON file with FileReader
							const reader = new FileReader();
							reader.onload = async function (event) {
								try {
									const fileContent = JSON.parse(event.target.result);
									open = true;
									dispatch('import', {
										folderId: folderId,
										items: fileContent
									});
								} catch (error) {
									console.error('Error parsing JSON file:', error);
								}
							};

							// Start reading the file
							reader.readAsText(file);
						} else {
							console.error('Only JSON file types are supported.');
						}

						console.log(file);
					} else {
						// Handle the drag-and-drop data for folders or chats (same as before)
						const dataTransfer = e.dataTransfer.getData('text/plain');

						try {
							const data = JSON.parse(dataTransfer);
							console.log(data);

							const { type, id, item } = data;

							if (type === 'folder') {
								const position = getDropPosition(e);
								if (position !== 'inside') {
									draggedOver = false;
									onReorder(id, folderId, position);
									return;
								}

								open = true;
								if (id === folderId) {
									return;
								}
								// Move the folder
								const res = await updateFolderParentIdById(localStorage.token, id, folderId).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);

								if (res) {
									updateFolderDetails(id, res);
									dispatch('update');
								}
							} else if (type === 'note') {
								const res = await updateNoteFolderIdById(localStorage.token, id, folderId).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);

								if (res) {
									toast.success($i18n.t('Note moved successfully'));
									void refreshFolderChatLists();
								}
							} else if (type === 'chat') {
								open = true;

								let chat = await getChatById(localStorage.token, id).catch((error) => {
									return null;
								});
								if (!chat && item) {
									if (!($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true))) {
										toast.error($i18n.t('Access prohibited'));
										return;
									}

									chat = await importChats(localStorage.token, [
										{
											chat: item.chat,
											meta: item?.meta ?? {},
											pinned: false,
											folder_id: null,
											created_at: item?.created_at ?? null,
											updated_at: item?.updated_at ?? null
										}
									]).catch((error) => {
										toast.error(`${error}`);
										return null;
									});
								}

								if (chat && chat.folder_id !== folderId) {
									// Move the chat
									const res = await updateChatFolderIdById(
										localStorage.token,
										chat.id,
										folderId
									).catch((error) => {
										toast.error(`${error}`);
										return null;
									});

									if (res) updateFolderChatLists(res, folderId);
									onItemMove({
										originFolderId: chat.folder_id,
										targetFolderId: folderId,
										e
									});

									if (res) {
										dispatch('update');
										void refreshFolderChatLists();
									}
								}
							}
						} catch (error) {
							console.log('Error parsing dataTransfer:', error);
						}

						// Only process the first non-file item; all share the same
						// text/plain payload, so continuing would duplicate the move.
						break;
					}
				}
			}

			setFolderItems();
			draggedOver = false;
		}
	};

	const onDragLeave = (e) => {
		e.preventDefault();
		if (dragged || parentDragged || !isWritable) {
			return;
		}

		draggedOver = false;
	};

	const dragImage = new Image();
	dragImage.src =
		'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

	let x;
	let y;

	const onDragStart = (event) => {
		event.stopPropagation();
		event.dataTransfer.setDragImage(dragImage, 0, 0);

		// Set the data to be transferred
		event.dataTransfer.setData(
			'text/plain',
			JSON.stringify({
				type: 'folder',
				id: folderId
			})
		);
		event.dataTransfer.setData('application/x-open-webui-drag', '');

		dragged = true;
		draggedFolderId = folderId;
		folderElement.style.opacity = '0.5'; // Optional: Visual cue to show it's being dragged
	};

	const onDrag = (event) => {
		event.stopPropagation();

		x = event.clientX;
		y = event.clientY;
	};

	const onDragEnd = (event) => {
		event.stopPropagation();

		folderElement.style.opacity = '1'; // Reset visual cue after drag
		dragged = false;
		draggedFolderId = null;
	};

	onMount(async () => {
		open = folders[folderId].is_expanded;
		folderRegistry[folderId] = {
			setFolderItems,
			setChatActive: /** @param {string} id */ (id) => {
				const found = chats?.some((chat) => chat.id === id) ?? false;
				return found;
			},
			setChatReadAt: /** @param {string} id */ (id) => {
				const found = chats?.some((chat) => chat.id === id) ?? false;
				return found;
			},
			setAllChatsRead: () => markFolderRead(folderId, $user?.id)
		};
		if (folderElement) {
			folderElement.addEventListener('dragover', onDragOver);
			folderElement.addEventListener('drop', onDrop);
			folderElement.addEventListener('dragleave', onDragLeave);

			// Event listener for when dragging starts
			folderElement.addEventListener('dragstart', onDragStart);
			// Event listener for when dragging occurs (optional)
			folderElement.addEventListener('drag', onDrag);
			// Event listener for when dragging ends
			folderElement.addEventListener('dragend', onDragEnd);
		}

		if (folders[folderId]?.new) {
			delete folders[folderId].new;
			await tick();
			renameHandler();
		}
	});

	onDestroy(() => {
		delete folderRegistry[folderId];

		if (closeActiveHoverPreview === closeHoverPreview) {
			closeActiveHoverPreview = null;
		}

		if (folderElement) {
			folderElement.removeEventListener('dragover', onDragOver);
			folderElement.removeEventListener('drop', onDrop);
			folderElement.removeEventListener('dragleave', onDragLeave);

			folderElement.removeEventListener('dragstart', onDragStart);
			folderElement.removeEventListener('drag', onDrag);
			folderElement.removeEventListener('dragend', onDragEnd);
		}
	});

	let showDeleteConfirm = false;

	const deleteHandler = async () => {
		const res = await deleteFolderById(localStorage.token, folderId, deleteFolderContents).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			removeFolderState(folderId);
			toast.success($i18n.t('Folder deleted successfully'));
			onDelete(folderId);
		}
	};

	const updateHandler = async ({ name, meta, data }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const currentName = folders[folderId].name;

		folders[folderId].name = name;

		const res = await updateFolderById(localStorage.token, folderId, {
			name,
			...(meta ? { meta } : {}),
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			folders[folderId].name = currentName;
			return null;
		});

		if (res) {
			updateFolderDetails(folderId, res);
			folders[folderId].name = name;
			if (data) {
				folders[folderId].data = data;
			}

			// toast.success($i18n.t('Folder name updated successfully'));
			toast.success($i18n.t('Folder updated successfully'));

			if ($selectedFolder?.id === folderId) {
				const folder = await loadFolderDetails(localStorage.token, folderId, true).catch(
					(error) => {
						toast.error(`${error}`);
						return null;
					}
				);

				if (folder) {
					await selectedFolder.set(folder);
				}
			}
			dispatch('update');
		}
	};

	const isExpandedUpdateHandler = async () => {
		const res = await updateFolderIsExpandedById(localStorage.token, folderId, open).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);
	};

	let isExpandedUpdateTimeout;

	const isExpandedUpdateDebounceHandler = () => {
		clearTimeout(isExpandedUpdateTimeout);
		isExpandedUpdateTimeout = setTimeout(() => {
			isExpandedUpdateHandler();
		}, 500);
	};

	/** @type {import('$lib/stores/folderStates').FolderChat[] | null} */
	let chats = null;
	let chatsPage = 1;
	let hasMoreChats = false;
	let chatsLoading = false;
	let queuedReload = false;
	let wasOpen = false;

	$: {
		const retained = $folderStates[folderId];
		chatsPage = retained?.sidebarPage ?? 1;
		const pages = Array.from(
			{ length: chatsPage },
			(_, index) => retained?.chatPages[folderChatPageKey({ page: index + 1 })]
		);
		chats = pages.some(Boolean)
			? mergeFolderChats(
					[],
					pages.flatMap((page) => page?.chats ?? [])
				)
			: null;
		hasMoreChats = pages.at(-1)?.has_more ?? false;
	}

	export const setFolderItems = async (append = false, refresh = true) => {
		if (!open) return;
		if (chatsLoading) {
			if (refresh) queuedReload = true;
			return;
		}
		chatsLoading = true;
		try {
			const nextPage = append ? chatsPage + 1 : chatsPage;
			await Promise.all(
				Array.from({ length: append ? 1 : nextPage }, (_, index) =>
					loadFolderChatPage(
						localStorage.token,
						folderId,
						{ page: append ? nextPage : index + 1 },
						!append && refresh
					)
				)
			);
			if (append) setFolderSidebarPage(folderId, nextPage);
		} catch (error) {
			if (!isCancelledFolderRequest(error)) toast.error(`${error}`);
		} finally {
			chatsLoading = false;
			if (queuedReload) {
				queuedReload = false;
				void setFolderItems();
			}
		}
	};

	$: if (open !== wasOpen) {
		wasOpen = open;
		if (open) void setFolderItems(false, false);
	}

	$: current = $navigating?.to
		? $navigating.to.params?.folderId === folderId
		: $selectedFolder?.id === folderId &&
			!$activeChatTabId &&
			!($pendingChatRequest && $pendingChatRequest.id === $page.params.id);

	const openFolderHandler = async () => {
		await goto(`/folders/${folderId}`, { keepFocus: true });
		if ($mobile) showSidebar.set(false);
	};

	const newNoteHandler = async () => {
		const note = await createNoteHandler(
			dayjs().locale($i18n.language).format('YYYY-MM-DD'),
			'',
			'',
			folderId
		);
		if (!note) return;

		if (appLayout?.openPageTab)
			appLayout.openPageTab({ href: `/notes/${note.id}`, label: note.title });
		else await goto(`/notes/${note.id}`);
		if ($mobile) showSidebar.set(false);
		void refreshFolderChatLists(folderId);
	};

	const renameHandler = async () => {
		console.log('Edit');
		await tick();
		name = folders[folderId].name;
		edit = true;

		await tick();
		await tick();

		const input = document.getElementById(`folder-${folderId}-input`);
		if (input) {
			input.focus();
			input.select();
		}
	};

	const exportHandler = async () => {
		const chats = await getChatsByFolderId(localStorage.token, folderId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!chats) {
			return;
		}

		const blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});

		saveAs(blob, `folder-${folders[folderId].name}-export-${Date.now()}.json`);
	};

	const createSubFolderHandler = async ({ name, meta, data, parent_id }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const res = await createNewFolder(localStorage.token, {
			name,
			data,
			meta,
			parent_id
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Folder created successfully'));
			dispatch('update');
		}
	};
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete folder?')}
	on:confirm={() => {
		deleteHandler();
	}}
>
	<div class=" text-sm text-base-700 dark:text-base-300 flex-1 line-clamp-3 mb-2">
		<!-- {$i18n.t('This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.', {
				NAME: folders[folderId].name
			})} -->

		{$i18n.t(`Are you sure you want to delete "{{NAME}}"?`, {
			NAME: folders[folderId].name
		})}
	</div>

	<div class="flex items-center gap-1.5">
		<input
			aria-label={$i18n.t('Delete all contents inside this folder')}
			type="checkbox"
			bind:checked={deleteFolderContents}
		/>

		<div class="text-xs text-base-500">
			{$i18n.t('Delete all contents inside this folder')}
		</div>
	</div>
</DeleteConfirmDialog>

<FolderShareModal bind:show={showShareModal} folder={folders[folderId]} />

<FolderModal bind:show={showFolderModal} edit={true} {folderId} onSubmit={updateHandler} />

<FolderModal
	bind:show={showCreateSubFolderModal}
	parentId={createSubFolderParentId}
	onSubmit={createSubFolderHandler}
/>

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div
			class="w-fit max-w-40 rounded-lg bg-base-0/95 px-2.5 py-1.5 text-xs text-base-600 shadow-sm ring-1 ring-base-1000/5 dark:bg-base-850/95 dark:text-base-300 dark:ring-base-0/10"
		>
			<div class="flex items-center gap-1.5">
				<FolderIcon className="size-3.5 shrink-0" strokeWidth="2" />
				<div class="min-w-0 truncate">
					{folders[folderId].name}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div
	bind:this={folderElement}
	class="relative {className}"
	role="listitem"
	draggable={!folders[folderId]?.shared}
>
	{#if draggedOver && dropPosition === 'inside'}
		<div
			class="pointer-events-none absolute inset-0 z-50 touch-none bg-base-1000/[0.02] ring-1 ring-inset ring-base-1000/10 dark:bg-base-0/[0.02] dark:ring-base-0/10"
		></div>
	{:else if draggedOver}
		<div
			class="pointer-events-none absolute inset-x-1 z-50 h-px rounded-[1px] bg-base-800/20 dark:bg-base-200/20 {dropPosition ===
			'before'
				? 'top-0'
				: 'bottom-0'}"
		></div>
	{/if}

	<Collapsible
		bind:open
		className="w-full"
		buttonClassName="w-full"
		onChange={(state) => {
			dispatch('open', state);
		}}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="w-full group">
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
			<div
				bind:this={rowElement}
				id="folder-{folderId}-button"
				class="relative w-full py-1 px-1.5 rounded-xl flex items-center gap-1.5 transition {current
					? ($settings?.highContrastMode ?? false)
						? 'bg-base-1000/[0.035] dark:bg-base-0/[0.06]'
						: 'bg-base-1000/[0.035] dark:bg-base-0/[0.045]'
					: 'hover:bg-base-100 dark:hover:bg-base-900'}"
				on:click|stopPropagation
			>
				<button
					class="text-base-600 dark:text-base-400 transition-all p-1 hover:bg-base-100 dark:hover:bg-base-900 rounded-lg"
					aria-label={open
						? $i18n.t('Collapse {{name}}', { name: folders[folderId]?.name })
						: $i18n.t('Expand {{name}}', { name: folders[folderId]?.name })}
					id="folder-{folderId}-expand-button"
					aria-expanded={open}
					on:click={(e) => {
						e.stopPropagation();
						e.stopImmediatePropagation();
						open = !open;
						isExpandedUpdateDebounceHandler();
					}}
				>
					{#if folders[folderId]?.meta?.icon}
						<div class="flex group-hover:hidden transition-all">
							<Emoji className="size-3.5" shortCode={folders[folderId].meta.icon} />
						</div>

						<div class="hidden group-hover:flex transition-all p-[0.0625rem]">
							{#if open}
								<ChevronDown className=" size-3" strokeWidth="1.5" />
							{:else}
								<ChevronRight className=" size-3" strokeWidth="1.5" />
							{/if}
						</div>
					{:else}
						<div class="flex group-hover:hidden transition-all">
							<FolderIcon className="size-3.5" strokeWidth="2" />
						</div>

						<div class="hidden group-hover:flex transition-all p-[0.0625rem]">
							{#if open}
								<ChevronDown className=" size-3" strokeWidth="1.5" />
							{:else}
								<ChevronRight className=" size-3" strokeWidth="1.5" />
							{/if}
						</div>
					{/if}
				</button>

				<div class="flex min-w-0 flex-1 self-stretch items-center gap-1.5 text-start">
					{#if edit}
						<input
							aria-label={$i18n.t('Rename')}
							id="folder-{folderId}-input"
							type="text"
							bind:value={name}
							on:blur={(e) => {
								// Opening the folder focuses its composer while a rename is in progress.
								// A composer the user pressed is active; one focused by the page is not.
								const input = e.currentTarget;
								const composer = e.relatedTarget?.closest('[data-composer-id]');
								if (composer && !composer.matches(':active')) {
									setTimeout(() => input.focus());
									return;
								}

								updateHandler({ name });
								edit = false;
							}}
							on:click={(e) => {
								// Prevent accidental collapse toggling when clicking inside input
								e.stopPropagation();
							}}
							on:mousedown={(e) => {
								// Prevent accidental collapse toggling when clicking inside input
								e.stopPropagation();
							}}
							on:keydown={(e) => {
								if (e.key === 'Enter') {
									e.currentTarget.blur();
								}
							}}
							class="w-full h-full pr-6 bg-transparent outline-hidden"
						/>
					{:else}
						<LinkPreview.Root
							openDelay={300}
							closeDelay={0}
							disabled={$mobile || dragged || parentDragged || draggedOver}
							bind:open={openPreview}
						>
							<LinkPreview.Trigger
								href={`/folders/${folderId}`}
								draggable="false"
								class="flex min-w-0 flex-1 self-stretch -my-1 -ms-1.5 ps-1.5 items-center gap-1.5 pr-6"
								ondblclick={(e) => {
									if (!isWritable || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
									renameHandler();
								}}
								onclick={(e) => {
									openPreview = false;
									e.stopPropagation();
									if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
									e.preventDefault();
									// A double click's second click only renames.
									if (e.detail < 2) openFolderHandler();
								}}
								onkeydown={(e) => {
									if (e.currentTarget !== e.target) return;
									if (e.key === ' ' && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey) {
										e.preventDefault();
										openFolderHandler();
									}
								}}
							>
								<div class="min-w-0 truncate">
									{folders[folderId].name}
								</div>

								{#if !folders[folderId]?.shared && (folders[folderId]?.unread_count ?? 0) > 0}
									<div
										class="inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-md bg-sky-500/10 px-1 text-[0.625rem] font-semibold leading-4 text-sky-600 dark:bg-sky-400/10 dark:text-sky-300"
										title={$i18n.t('Unread or waiting for approval')}
									>
										{formatUnreadCount(folders[folderId].unread_count)}
									</div>
								{/if}
							</LinkPreview.Trigger>
							{#if openPreview}
								<FolderHoverPreview
									folder={folders[folderId]}
									{isWritable}
									onEdit={() => {
										openPreview = false;
										showFolderModal = true;
									}}
								/>
							{/if}
						</LinkPreview.Root>
					{/if}
				</div>

				{#if isWritable}
					<div
						class="absolute z-10 right-2 hover-reveal pointer-coarse:opacity-100! pointer-coarse:pointer-events-auto! self-center flex items-center dark:text-base-300"
						role="presentation"
						on:pointerdown={() => (openPreview = false)}
					>
						<FolderMenu
							onNewChat={async () => {
								if ($selectedFolder?.id !== folderId) await openFolderHandler();
								if ($page.params.folderId === folderId || $selectedFolder?.id === folderId)
									chatTabRequest.set({ folderId });
								if ($mobile) showSidebar.set(false);
							}}
							onNewNote={($config?.features?.enable_notes ?? false) &&
							($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
								? newNoteHandler
								: null}
							onEdit={() => {
								showFolderModal = true;
							}}
							onDelete={() => {
								showDeleteConfirm = true;
							}}
							onExport={() => {
								exportHandler();
							}}
							onCreateSubFolder={() => {
								createSubFolderParentId = folderId;
								showCreateSubFolderModal = true;
							}}
							onMarkAllRead={markAllReadHandler}
							onShare={$user?.role === 'admin' ||
							(folders[folderId]?.user_id === $user?.id && $user?.permissions?.sharing?.folders)
								? () => (showShareModal = true)
								: null}
						>
							<div
								class="flex size-5 items-center justify-center self-center dark:hover:text-base-0 transition m-0 touch-auto"
							>
								<MoreHorizontal className="size-3.5" strokeWidth="2" />
							</div>
						</FolderMenu>
					</div>
				{/if}
			</div>
		</div>

		<div slot="content" class="w-full">
			{#if (folders[folderId]?.childrenIds ?? []).length > 0 || chats !== null || hasMoreChats || chatsLoading}
				<div
					class="ml-3 pl-1 mt-[0.0625rem] flex flex-col overflow-y-auto scrollbar-hidden border-s border-base-100 dark:border-base-900"
				>
					{#if folders[folderId]?.childrenIds}
						{@const children = sortFolders(
							folders[folderId].childrenIds.map((id) => folders[id]),
							$settings?.folderOrder?.[folderId]
						)}

						{#if children.length > 0}
							<div role="list">
								{#each children as childFolder (`${folderId}-${childFolder.id}`)}
									<svelte:self
										bind:folderRegistry
										{folders}
										folderId={childFolder.id}
										{shiftKey}
										parentDragged={dragged || parentDragged}
										{onItemMove}
										{onReorder}
										{onDelete}
										{onFolderUnreadCounts}
										on:import={(e) => {
											dispatch('import', e.detail);
										}}
										on:update={(e) => {
											dispatch('update', e.detail);
										}}
										on:change={(e) => {
											dispatch('change', e.detail);
										}}
									/>
								{/each}
							</div>
						{/if}
					{/if}

					{#if chats === null && chatsLoading}
						<div class="flex gap-1 px-2 py-1.5" aria-label={$i18n.t('Loading')}>
							<span class="size-1 rounded-full bg-base-400 animate-pulse dark:bg-base-600"></span>
							<span
								class="size-1 rounded-full bg-base-400 animate-pulse [animation-delay:150ms] dark:bg-base-600"
							></span>
							<span
								class="size-1 rounded-full bg-base-400 animate-pulse [animation-delay:300ms] dark:bg-base-600"
							></span>
						</div>
					{/if}

					{#if chats !== null && chats.length === 0 && !chatsLoading}
						<div class="px-2 py-0.5 text-[0.6875rem] text-base-400 dark:text-base-600">
							{$i18n.t('No chats')}
						</div>
					{/if}

					{#if (chats ?? []).length > 0}
						<div role="list">
							{#each chats ?? [] as chat (chat.id)}
								<div role="listitem">
									<ChatItem
										id={chat.id}
										title={chat.title}
										createdAt={chat.created_at}
										updatedAt={chat.updated_at}
										lastReadAt={chat.last_read_at}
										active={chat.active ?? false}
										pendingApproval={chat.pending_approval ?? false}
										ownerName={chat.owner_name ?? null}
										participants={chat.participants ?? []}
										ownerUserId={folders[folderId]?.showOwnerInfo ||
										folders[folderId]?.shared ||
										chat.user_id !== $user?.id
											? chat.user_id
											: null}
										readonly={chat.user_id !== $user?.id}
										canMove={folders[folderId]?.user_id === $user?.id}
										canRename={folders[folderId]?.user_id === $user?.id}
										{shiftKey}
										onReadStateChange={applyReadState}
										on:change={(e) => {
											dispatch('change', e.detail);
										}}
									/>
								</div>
							{/each}
						</div>
					{/if}

					{#if hasMoreChats}
						<button
							class="w-full px-2 py-0.5 text-left text-[0.6875rem] text-base-400 transition hover:text-base-700 disabled:cursor-not-allowed dark:text-base-600 dark:hover:text-base-300"
							disabled={chatsLoading}
							on:click={() => setFolderItems(true)}
						>
							{#if chatsLoading}
								<div class="flex gap-1 px-2 py-1.5" aria-label={$i18n.t('Loading')}>
									<span class="size-1 rounded-full bg-base-400 animate-pulse dark:bg-base-600"
									></span>
									<span
										class="size-1 rounded-full bg-base-400 animate-pulse [animation-delay:150ms] dark:bg-base-600"
									></span>
									<span
										class="size-1 rounded-full bg-base-400 animate-pulse [animation-delay:300ms] dark:bg-base-600"
									></span>
								</div>
							{:else}
								{$i18n.t('Show more')}
							{/if}
						</button>
					{/if}
				</div>
			{/if}
		</div>
	</Collapsible>
</div>
