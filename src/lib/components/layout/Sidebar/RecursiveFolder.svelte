<script>
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import DOMPurify from 'dompurify';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import { chatId, mobile, selectedFolder, showSidebar } from '$lib/stores';

	import {
		deleteFolderById,
		updateFolderIsExpandedById,
		updateFolderById,
		updateFolderParentIdById
	} from '$lib/apis/folders';
	import {
		getChatById,
		getChatsByFolderId,
		importChat,
		updateChatFolderIdById
	} from '$lib/apis/chats';

	import ChevronDown from '../../icons/ChevronDown.svelte';
	import ChevronRight from '../../icons/ChevronRight.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';

	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	import ChatItem from './ChatItem.svelte';
	import FolderMenu from './Folders/FolderMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import FolderModal from './Folders/FolderModal.svelte';
	import { goto } from '$app/navigation';

	export let open = false;

	export let folders;
	export let folderId;
	export let shiftKey = false;

	export let className = '';

	export let parentDragged = false;

	export let onDelete = (e) => {};

	let folderElement;

	let showFolderModal = false;
	let edit = false;

	let draggedOver = false;
	let dragged = false;

	let name = '';

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

						try {
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
									chat = await importChat(
										localStorage.token,
										item.chat,
										item?.meta ?? {},
										false,
										null,
										item?.created_at ?? null,
										item?.updated_at ?? null
									).catch((error) => {
										toast.error(`${error}`);
										return null;
									});
								}

								// Move the chat
								const res = await updateChatFolderIdById(
									localStorage.token,
									chat.id,
									folderId
								).catch((error) => {
									toast.error(`${error}`);
									return null;
								});

								if (res) {
									dispatch('update');
								}
							}
						} catch (error) {
							console.log('Error parsing dataTransfer:', error);
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

		if (folders[folderId]?.new) {
			delete folders[folderId].new;

			await tick();
			renameHandler();
		}
	});

	onDestroy(() => {
		if (folderElement) {
			folderElement.addEventListener('dragover', onDragOver);
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
			onDelete(folderId);
		}
	};

	const updateHandler = async ({ name, data }) => {
		if (name === '') {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const currentName = folders[folderId].name;

		name = name.trim();
		folders[folderId].name = name;

		const res = await updateFolderById(localStorage.token, folderId, {
			name,
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			folders[folderId].name = currentName;
			return null;
		});

		if (res) {
			folders[folderId].name = name;
			if (data) {
				folders[folderId].data = data;
			}

			// toast.success($i18n.t('Folder name updated successfully'));
			toast.success($i18n.t('Folder updated successfully'));

			if ($selectedFolder?.id === folderId) {
				selectedFolder.set(folders[folderId]);
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

	const isExpandedUpdateDebounceHandler = (open) => {
		clearTimeout(isExpandedUpdateTimeout);
		isExpandedUpdateTimeout = setTimeout(() => {
			isExpandedUpdateHandler();
		}, 500);
	};

	$: isExpandedUpdateDebounceHandler(open);

	const renameHandler = async () => {
		console.log('Edit');
		await tick();
		name = folders[folderId].name;

		edit = true;
		await tick();

		const input = document.getElementById(`folder-${folderId}-input`);

		if (input) {
			input.focus();
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

<FolderModal
	bind:show={showFolderModal}
	edit={true}
	folder={folders[folderId]}
	onSubmit={updateHandler}
/>

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
				class="relative w-full py-1.5 px-2 rounded-md flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-500 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition {$selectedFolder?.id ===
				folderId
					? 'bg-gray-100 dark:bg-gray-900'
					: ''}"
				on:dblclick={() => {
					renameHandler();
				}}
				on:click={async (e) => {
					await goto('/');

					selectedFolder.set(folders[folderId]);

					if ($mobile) {
						showSidebar.set(!$showSidebar);
					}
				}}
			>
				<button
					class="text-gray-300 dark:text-gray-600"
					on:click={(e) => {
						e.stopPropagation();
					}}
				>
					{#if open}
						<ChevronDown className=" size-3" strokeWidth="2.5" />
					{:else}
						<ChevronRight className=" size-3" strokeWidth="2.5" />
					{/if}
				</button>

				<div class="translate-y-[0.5px] flex-1 justify-start text-start line-clamp-1">
					{#if edit}
						<input
							id="folder-{folderId}-input"
							type="text"
							bind:value={name}
							on:focus={(e) => {
								e.target.select();
							}}
							on:blur={() => {
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
									updateHandler({ name });
									edit = false;
								}
							}}
							class="w-full h-full bg-transparent text-gray-500 dark:text-gray-500 outline-hidden"
						/>
					{:else}
						{folders[folderId].name}
					{/if}
				</div>

				<button
					class="absolute z-10 right-2 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
					on:pointerup={(e) => {
						e.stopPropagation();
					}}
					on:click={(e) => e.stopPropagation()}
				>
					<FolderMenu
						onEdit={() => {
							showFolderModal = true;
						}}
						onDelete={() => {
							showDeleteConfirm = true;
						}}
						onExport={() => {
							exportHandler();
						}}
					>
						<button class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto" on:click={(e) => {}}>
							<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
						</button>
					</FolderMenu>
				</button>
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
								{shiftKey}
								parentDragged={dragged}
								{onDelete}
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
					{/if}

					{#if folders[folderId].items?.chats}
						{#each folders[folderId].items.chats as chat (chat.id)}
							<ChatItem
								id={chat.id}
								title={chat.title}
								{shiftKey}
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
