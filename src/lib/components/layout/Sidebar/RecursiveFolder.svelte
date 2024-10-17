<script>
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import ChevronDown from '../../icons/ChevronDown.svelte';
	import ChevronRight from '../../icons/ChevronRight.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';

	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import {
		updateFolderIsExpandedById,
		updateFolderNameById,
		updateFolderParentIdById
	} from '$lib/apis/folders';
	import { toast } from 'svelte-sonner';
	import { updateChatFolderIdById } from '$lib/apis/chats';
	import ChatItem from './ChatItem.svelte';

	export let open = true;

	export let folders;
	export let folderId;

	export let className = '';

	export let parentDragged = false;

	let folderElement;

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

			try {
				// get data from the drag event
				const dataTransfer = e.dataTransfer.getData('text/plain');
				const data = JSON.parse(dataTransfer);
				console.log(data);

				const { type, id } = data;

				if (type === 'folder') {
					if (id === folderId) {
						return;
					}
					// Move the folder
					const res = await updateFolderParentIdById(localStorage.token, id, folderId).catch(
						(error) => {
							toast.error(error);
							return null;
						}
					);

					if (res) {
						dispatch('update');
					}
				} else if (type === 'chat') {
					// Move the chat
					const res = await updateChatFolderIdById(localStorage.token, id, folderId).catch(
						(error) => {
							toast.error(error);
							return null;
						}
					);

					if (res) {
						dispatch('update');
					}
				}
			} catch (error) {
				console.error(error);
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

	onMount(() => {
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
			folderElement.addEventListener('dragover', onDragOver);
			folderElement.removeEventListener('drop', onDrop);
			folderElement.removeEventListener('dragleave', onDragLeave);

			folderElement.removeEventListener('dragstart', onDragStart);
			folderElement.removeEventListener('drag', onDrag);
			folderElement.removeEventListener('dragend', onDragEnd);
		}
	});

	const nameUpdateHandler = async () => {
		if (name === '') {
			toast.error("Folder name can't be empty");
			return;
		}

		if (name === folders[folderId].name) {
			edit = false;
			return;
		}

		const currentName = folders[folderId].name;

		name = name.trim();
		folders[folderId].name = name;

		const res = await updateFolderNameById(localStorage.token, folderId, name).catch((error) => {
			toast.error(error);

			folders[folderId].name = currentName;
			return null;
		});

		if (res) {
			folders[folderId].name = name;
		}
	};

	const isExpandedUpdateHandler = async () => {
		const res = await updateFolderIsExpandedById(localStorage.token, folderId, open).catch(
			(error) => {
				toast.error(error);
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
</script>

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
			class="absolute top-0 left-0 w-full h-full rounded-sm bg-[hsla(258,88%,66%,0.1)] bg-opacity-50 dark:bg-opacity-10 z-50 pointer-events-none touch-none"
		></div>
	{/if}

	<Collapsible
		bind:open
		className="w-full"
		buttonClassName="w-full"
		on:change={(e) => {
			dispatch('open', e.detail);
		}}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="w-full group">
			<button
				class="w-full py-1.5 px-2 rounded-md flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-500 font-medium hover:bg-gray-100 dark:hover:bg-gray-900 transition"
				on:dblclick={() => {
					name = folders[folderId].name;
					edit = true;

					// focus on the input
					setTimeout(() => {
						const input = document.getElementById(`folder-${folderId}-input`);
						input.focus();
					}, 0);
				}}
			>
				<div class="text-gray-300 dark:text-gray-600">
					{#if open}
						<ChevronDown className=" size-3" strokeWidth="2.5" />
					{:else}
						<ChevronRight className=" size-3" strokeWidth="2.5" />
					{/if}
				</div>

				<div class="translate-y-[0.5px] flex-1 justify-start text-start">
					{#if edit}
						<input
							id="folder-{folderId}-input"
							type="text"
							bind:value={name}
							on:blur={() => {
								nameUpdateHandler();
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
									edit = false;
								}
							}}
							class="w-full h-full bg-transparent text-gray-500 dark:text-gray-500 outline-none"
						/>
					{:else}
						{folders[folderId].name}
					{/if}
				</div>

				<div class=" hidden group-hover:flex dark:text-gray-300">
					<button
						on:click={(e) => {
							e.stopPropagation();
							console.log('clicked');
						}}
					>
						<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
					</button>
				</div>
			</button>
		</div>

		<div slot="content" class="w-full">
			{#if folders[folderId].childrenIds || folders[folderId].items?.chats}
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
								on:update={(e) => {
									dispatch('update', e.detail);
								}}
							/>
						{/each}
					{/if}

					{#if folders[folderId].items?.chats}
						{#each folders[folderId].items.chats as chat (chat.id)}
							<ChatItem id={chat.id} title={chat.title} />
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	</Collapsible>
</div>
