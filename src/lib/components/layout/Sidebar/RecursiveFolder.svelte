<script>
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import DOMPurify from 'dompurify';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import ChevronDown from '../../icons/ChevronDown.svelte';
	import ChevronRight from '../../icons/ChevronRight.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';
	import Plus from '../../icons/Plus.svelte';
	
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { pendingFolderId, pendingFolderName, mobile, showSidebar } from '$lib/stores';

	import {
		deleteFolderById,
		updateFolderIsExpandedById,
		updateFolderParentIdById
	} from '$lib/apis/folders';
	import { toast } from 'svelte-sonner';
	import {
		getChatById,
		getChatsByFolderId,
		importChat,
		updateChatFolderIdById
	} from '$lib/apis/chats';

	import ChatItem from './ChatItem.svelte';
	import FolderMenu from './Folders/FolderMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let open = false;

	export let folders;
	export let folderId;

	export let className = '';

	export let parentDragged = false;

	let folderElement;

	let draggedOver = false;
	let dragged = false;

	const onDragOver = (e) => {
		e.preventDefault();
		e.stopPropagation();
		if (dragged || parentDragged) {
			return;
		}
		draggedOver = true;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		e.stopPropagation();
		if (dragged || parentDragged) {
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
						const data = JSON.parse(dataTransfer);
						console.log(data);

						const { type, id, item } = data;

						if (type === 'folder') {
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
								dispatch('update');
							}
						} else if (type === 'chat') {
							open = true;

							let chat = await getChatById(localStorage.token, id).catch((error) => {
								return null;
							});
							if (!chat && item) {
								chat = await importChat(localStorage.token, item.chat, item?.meta ?? {});
							}

							// Move the chat
							const res = await updateChatFolderIdById(localStorage.token, chat.id, folderId).catch(
								(error) => {
									toast.error(`${error}`);
									return null;
								}
							);

							if (res) {
								dispatch('update');
							}
						}
					}
				}
			}

			draggedOver = false;
		}
	};

	const onDragLeave = (e) => {
		e.preventDefault();
		if (dragged || parentDragged) {
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

		dragged = true;
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
	};

	onMount(async () => {
		open = folders[folderId].is_expanded;
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

	});

	onDestroy(() => {
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
		const res = await deleteFolderById(localStorage.token, folderId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Folder deleted successfully'));
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

	const isExpandedUpdateDebounceHandler = (open) => {
		clearTimeout(isExpandedUpdateTimeout);
		isExpandedUpdateTimeout = setTimeout(() => {
			isExpandedUpdateHandler();
		}, 500);
	};

	$: isExpandedUpdateDebounceHandler(open);

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
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete folder?')}
	on:confirm={() => {
		deleteHandler();
	}}
>
	<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3">
		{@html DOMPurify.sanitize(
			$i18n.t('This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.', {
				NAME: folders[folderId].name
			})
		)}
	</div>
</DeleteConfirmDialog>

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div class=" bg-black/80 backdrop-blur-2xl px-2 py-1 rounded-lg w-fit max-w-40">
			<div class="flex items-center gap-1">
				<FolderOpen className="size-3.5" strokeWidth="2" />
				<div class=" text-xs text-white line-clamp-1">
					{folders[folderId].name}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div bind:this={folderElement} class="relative {className}" draggable="true">
	{#if draggedOver}
		<div
			class="absolute top-0 left-0 w-full h-full rounded-xs bg-gray-100/50 dark:bg-gray-700/20 bg-opacity-50 dark:bg-opacity-10 z-50 pointer-events-none touch-none"
		></div>
	{/if}

	<Collapsible
		bind:open
		className="w-full"
		buttonClassName="w-full"
		hide={(folders[folderId]?.childrenIds ?? []).length === 0 &&
			(folders[folderId].items?.chats ?? []).length === 0}
		onChange={(state) => {
			dispatch('open', state);
		}}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="w-full group">
			<button
				id="folder-{folderId}-button"
				class="relative w-full py-1.5 px-2 rounded-md flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-500 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition"
			>
				<div class="text-gray-300 dark:text-gray-600">
					{#if open}
						<ChevronDown className=" size-3" strokeWidth="2.5" />
					{:else}
						<ChevronRight className=" size-3" strokeWidth="2.5" />
					{/if}
				</div>

				<div class="translate-y-[0.5px] flex-1 justify-start text-start line-clamp-1">
					{folders[folderId].name}
				</div>

				<div class="absolute z-10 right-2 invisible group-hover:visible self-center flex items-center gap-1 dark:text-gray-300">
				    <!-- Plus Button -->
				    <button
					class="p-0.5 dark:hover:bg-gray-850 hover:bg-gray-200 rounded-lg touch-auto" on:click={(e) => {
						e.stopPropagation();
						dispatch('createChatInFolder', { folderId });
					}}
					on:pointerup={(e) => {
					    e.stopPropagation();
					}}
					title={$i18n.t('Create new chat in folder')}
				    >
					<Plus className="size-3.5" strokeWidth="2.5" />
				    </button>
				
				    <!-- Three-dot Menu -->
				    <FolderMenu
					on:editFolder={() => {
					    dispatch('editFolder', folders[folderId]);
					}}
					on:delete={() => {
					    showDeleteConfirm = true;
					}}
					on:export={() => {
					    exportHandler();
					}}
				    >
					<button class="p-0.5 dark:hover:bg-gray-850 hover:bg-gray-200 rounded-lg touch-auto" on:click={(e) => {}}>
					    <EllipsisHorizontal className="size-4" strokeWidth="2.5" />
					</button>
				    </FolderMenu>
				</div>
			</button>
		</div>

		<div slot="content" class="w-full">
			{#if (folders[folderId]?.childrenIds ?? []).length > 0 || (folders[folderId].items?.chats ?? []).length > 0}
				<div
					class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900"
				>
					{#if folders[folderId]?.childrenIds}
						{@const children = folders[folderId]?.childrenIds
							.map((id) => folders[id])
							.sort((a, b) =>
								a.name.localeCompare(b.name, undefined, {
									numeric: true,
									sensitivity: 'base'
								})
							)}

						{#each children as childFolder (`${folderId}-${childFolder.id}`)}
							<svelte:self
								{folders}
								folderId={childFolder.id}
								parentDragged={dragged}
								on:import={(e) => {
									dispatch('import', e.detail);
								}}
								on:update={(e) => {
									dispatch('update', e.detail);
								}}
								on:change={(e) => {
									dispatch('change', e.detail);
								}}
								on:editFolder={(e) => {
									dispatch('editFolder', e.detail);
								}}
								on:createChatInFolder={(e) => {
								    dispatch('createChatInFolder', e.detail);
								}}
							/>
						{/each}
					{/if}

					{#if folders[folderId].items?.chats}
						{#each folders[folderId].items.chats as chat (chat.id)}
							<ChatItem
								id={chat.id}
								title={chat.title}
								on:change={(e) => {
									dispatch('change', e.detail);
								}}
							/>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	</Collapsible>
</div>
