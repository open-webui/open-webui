<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto, invalidate, invalidateAll } from '$app/navigation';
	import { onMount, getContext, createEventDispatcher, tick, onDestroy } from 'svelte';
	import { fly } from 'svelte/transition';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');

	const dispatch = createEventDispatcher();

	import {
		archiveChatById,
		cloneChatById,
		deleteChatById,
		getAllTags,
		getChatById,
		getChatList,
		getChatListByTagName,
		getPinnedChatList,
		updateChatById
	} from '$lib/apis/chats';
	import {
		chatId,
		chatTitle as _chatTitle,
		chats,
		mobile,
		pinnedChats,
		showSidebar,
		currentChatPage,
		tags
	} from '$lib/stores';

	import ChatMenu from './ChatMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ShareChatModal from '$lib/components/chat/ShareChatModal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Document from '$lib/components/icons/Document.svelte';

	export let className = '';

	export let id;
	export let title;

	export let selected = false;
	export let isCurrentChat = false;
	export let showSelectionMode = false;
	export let isFirstInList = false;

	let chat = null;

	let mouseOver = false;
	let draggable = false;
	let buttonID = '';

	$: if (mouseOver) {
		loadChat();
	}
	$: buttonID = `chat-menu-${id}`;

	const loadChat = async () => {
		if (!chat) {
			draggable = false;
			chat = await getChatById(localStorage.token, id);
			draggable = true;
		}
	};

	let showShareChatModal = false;
	let confirmEdit = false;

	let chatTitle = title;

	const editChatTitle = async (id, title) => {
		if (title === '') {
			toast.error($i18n.t('Title cannot be an empty string.'));
			return;
		}

		await updateChatById(localStorage.token, id, { title });

		if (id === $chatId) {
			_chatTitle.set(title);
		}

		dispatch('change', { type: 'rename', chatId: id, title });

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		await pinnedChats.set(await getPinnedChatList(localStorage.token));
	};

	const cloneChatHandler = async (id) => {
		const res = await cloneChatById(
			localStorage.token,
			id,
			$i18n.t('Clone of {{TITLE}}', {
				TITLE: title
			})
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));
			toast.success($i18n.t('Chat cloned successfully. You are now in the new chat.'));
		}
	};

	const deleteChatHandler = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// Update stores reactively
			tags.set(await getAllTags(localStorage.token));

			// If deleting the current chat, navigate away first
			if ($chatId === id) {
				// Clear chatId first to prevent selection count issues
				await chatId.set('');
				await goto('/');
				await tick();
			}

			// Update chat lists immediately to ensure reactive state
			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));

			dispatch('change', { buttonID: null });
		}
	};

	const archiveChatHandler = async (id) => {
		await archiveChatById(localStorage.token, id);
		dispatch('change', { buttonID: null });
		toast.success($i18n.t('Chat archived successfully'));
	};

	const focusEdit = async (node: HTMLInputElement) => {
		node.focus();
	};

	let itemElement;

	let dragged = false;
	let x = 0;
	let y = 0;

	const dragImage = new Image();
	dragImage.src =
		'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

	const onDragStart = (event) => {
		event.stopPropagation();

		event.dataTransfer.setDragImage(dragImage, 0, 0);

		// Set the data to be transferred
		event.dataTransfer.setData(
			'text/plain',
			JSON.stringify({
				type: 'chat',
				id: id,
				item: chat
			})
		);

		dragged = true;
		itemElement.style.opacity = '0.5'; // Optional: Visual cue to show it's being dragged
	};

	const onDrag = (event) => {
		event.stopPropagation();

		x = event.clientX;
		y = event.clientY;
	};

	const onDragEnd = (event) => {
		event.stopPropagation();

		itemElement.style.opacity = '1'; // Reset visual cue after drag
		dragged = false;
	};

	onMount(() => {
		if (itemElement) {
			// Event listener for when dragging starts
			itemElement.addEventListener('dragstart', onDragStart);
			// Event listener for when dragging occurs (optional)
			itemElement.addEventListener('drag', onDrag);
			// Event listener for when dragging ends
			itemElement.addEventListener('dragend', onDragEnd);
		}
	});

	onDestroy(() => {
		if (itemElement) {
			itemElement.removeEventListener('dragstart', onDragStart);
			itemElement.removeEventListener('drag', onDrag);
			itemElement.removeEventListener('dragend', onDragEnd);
		}
	});

	let showDeleteConfirm = false;
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={id} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		deleteChatHandler(id);
	}}
>
	<div class=" text-sm text-gray-800 dark:text-gray-200 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="  font-semibold">{title}</span>.
	</div>
</DeleteConfirmDialog>

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div class=" bg-black/80 backdrop-blur-2xl px-2 py-1 rounded-lg w-fit max-w-40">
			<div class="flex items-center gap-1">
				<Document className=" size-[18px]" strokeWidth="2" />
				<div class=" text-xs text-white line-clamp-1">
					{title}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div bind:this={itemElement} class=" w-full {className} relative group" {draggable}>
	{#if confirmEdit}
		<div
			class=" w-full flex justify-between rounded-lg px-[11px] py-[6px] {id === $chatId ||
			confirmEdit
				? 'bg-gray-200 dark:bg-gray-900'
				: selected
					? 'bg-blue-100 dark:bg-blue-900 border-2 border-blue-300 dark:border-blue-700'
					: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-950'} whitespace-nowrap text-ellipsis"
		>
			<input
				use:focusEdit
				bind:value={chatTitle}
				id="chat-title-input-{id}"
				class="bg-transparent w-full outline-none mr-10"
				on:keydown={(e) => {
					if (e.key === 'Enter') {
						editChatTitle(id, chatTitle);
						confirmEdit = false;
						chatTitle = '';
					}
				}}
			/>
		</div>
	{:else}
		<Tooltip
			content={title}
			placement="bottom-start"
			popperOptions={{
				modifiers: [
					{
						name: 'offset',
						options: {
							offset: ({ reference }) => [reference.width / 2, 4]
						}
					}
				]
			}}
		>
			<a
				class=" w-full flex justify-between rounded-lg px-[11px] py-[6px]
				{isCurrentChat && !selected
					? 'bg-gray-200 dark:bg-gray-900'
					: selected
						? 'bg-blue-100 dark:bg-blue-900 border-2 border-blue-300 dark:border-blue-700'
						: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-950'} whitespace-nowrap text-ellipsis"
				href="/c/{id}"
				on:click={(e) => {
					// Check if the click was on the checkbox area, bulk actions, or chat menu
					const target = e.target;
					const clickedCheckbox = target && target.closest && target.closest('.checkbox-area');
					const clickedBulkAction = target && target.closest && target.closest('button[title]');
					const clickedDropdown =
						target && target.closest && target.closest('[data-dropdown-trigger]');

					if (clickedDropdown) {
						// Dropdown/menu clicked - do nothing, let it handle its own logic
						e.preventDefault();
						return;
					} else if (clickedBulkAction) {
						// Bulk action buttons handle their own clicks
						return;
					} else if (clickedCheckbox) {
						// Clicked on checkbox - toggle selection
						e.preventDefault();
						if (selected) {
							dispatch('unselect');
						} else {
							dispatch('select');
						}
					} else {
						// Normal navigation
						dispatch('navigate');
						if ($mobile) {
							showSidebar.set(false);
						}
					}
				}}
				on:dblclick={() => {
					chatTitle = title;
					confirmEdit = true;
				}}
				on:mouseenter={(e) => {
					mouseOver = true;
				}}
				on:mouseleave={(e) => {
					mouseOver = false;
				}}
				on:focus={(e) => {}}
				draggable="false"
			>
				<div class=" flex self-center flex-1 w-full">
					{#if showSelectionMode || mouseOver}
						<!-- Show checkbox when in selection mode or on hover -->
						<div
							class="checkbox-area mr-2 flex items-center cursor-pointer p-1 -m-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
						>
							{#if selected}
								<!-- Selected checkbox -->
								<svg
									xmlns="http://www.w3.org/2000/svg"
									class="w-4 h-4 text-blue-600 dark:text-blue-400"
									viewBox="0 0 20 20"
									fill="currentColor"
								>
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{:else}
								<!-- Empty checkbox -->
								<div class="w-4 h-4 border-2 border-gray-300 dark:border-gray-600 rounded"></div>
							{/if}
						</div>
					{:else if isCurrentChat}
						<!-- Current chat indicator -->
						<div class="mr-2 flex items-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-4 h-4 text-gray-600 dark:text-gray-400"
								viewBox="0 0 20 20"
								fill="currentColor"
							>
								<path
									fill-rule="evenodd"
									d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					{/if}
					<div class=" text-left self-center overflow-hidden w-full h-[20px]">
						<span class="truncate">{title}</span>
					</div>
				</div>
			</a>
		</Tooltip>
	{/if}

	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="
        {id === $chatId || confirmEdit
			? 'from-gray-200 dark:from-gray-900'
			: selected
				? 'from-blue-100 dark:from-blue-900'
				: 'invisible group-hover:visible from-gray-100 dark:from-gray-950'}
            absolute {className === 'pr-2'
			? 'right-[8px]'
			: 'right-0'}  top-[4px] py-1 pr-0.5 mr-1.5 pl-5 bg-gradient-to-l from-80%

              to-transparent"
		on:mouseenter={(e) => {
			mouseOver = true;
		}}
		on:mouseleave={(e) => {
			mouseOver = false;
		}}
	>
		{#if confirmEdit}
			<div
				class="flex self-center items-center space-x-1.5 z-10 translate-y-[0.5px] -translate-x-[0.5px]"
			>
				<Tooltip content={$i18n.t('Confirm')}>
					<button
						class="self-center dark:hover:text-white transition"
						on:click={() => {
							editChatTitle(id, chatTitle);
							confirmEdit = false;
							chatTitle = '';
							toast.success($i18n.t('Chat title saved.'));
						}}
					>
						<Check className=" size-3.5" strokeWidth="2.5" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Cancel')}>
					<button
						class=" self-center dark:hover:text-white transition"
						on:click={() => {
							confirmEdit = false;
							chatTitle = '';
							toast.success($i18n.t('Chat title rename cancelled'));
						}}
					>
						<XMark strokeWidth="2.5" />
					</button>
				</Tooltip>
			</div>
		{:else}
			<div class="flex self-center space-x-1 z-10">
				<Tooltip content={$i18n.t('Chat Menu')}>
					<ChatMenu
						ariaLabel={$i18n.t('Chat Menu')}
						chatId={id}
						{buttonID}
						cloneChatHandler={() => {
							cloneChatHandler(id);
						}}
						archiveChatHandler={() => {
							archiveChatHandler(id);
						}}
						renameHandler={async () => {
							chatTitle = title;
							confirmEdit = true;

							await tick();
							const input = document.getElementById(`chat-title-input-${id}`);
							if (input) {
								input.focus();
							}
						}}
						buttonClass="dark:hover:bg-gray-850 rounded-lg touch-auto"
						onClose={() => {
							// Do nothing - menu closing should not affect selection
						}}
						on:change={async (e) => {
							dispatch('change', e.detail);
						}}
						on:tag={(e) => {
							dispatch('tag', e.detail);
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
							/>
						</svg>
					</ChatMenu>
				</Tooltip>
				{#if id === $chatId}
					<!-- Shortcut support using "delete-chat-button" id -->
					<button
						id="delete-chat-button"
						class="hidden"
						on:click={() => {
							showDeleteConfirm = true;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-3 h-3"
						>
							<path
								d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
							/>
						</svg>
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Bulk Actions removed from ChatItem - now handled in Sidebar -->

	<!-- Bulk Actions (appear next to first chat when any chats selected) -->
	{#if isFirstInList && showSelectionMode}
		<div
			style="position: fixed; top: 205px; left: 265px; z-index: 9999;"
			class="flex items-center space-x-1 bg-white dark:bg-gray-800 rounded-md shadow-lg px-2 py-1 border border-gray-200 dark:border-gray-600"
			in:fly={{ x: 100, duration: 300, delay: 100 }}
			out:fly={{ x: 100, duration: 200 }}
		>
			<!-- Select All Button -->
			<button
				class="px-2 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors font-medium"
				on:click|stopPropagation={(e) => {
					e.preventDefault();
					dispatch('selectAll');
				}}
				title={$i18n.t('Select All')}
			>
				{$i18n.t('All')}
			</button>

			<!-- Clear Selection Button -->
			<button
				class="px-2 py-1 text-xs bg-gray-500 hover:bg-gray-600 text-white rounded transition-colors font-medium"
				on:click|stopPropagation={(e) => {
					e.preventDefault();
					dispatch('clearSelection');
				}}
				title={$i18n.t('Clear Selection')}
			>
				{$i18n.t('Clear')}
			</button>

			<!-- Delete Selected Button -->
			<button
				class="px-2 py-1 text-xs bg-red-500 hover:bg-red-600 text-white rounded transition-colors font-medium"
				on:click|stopPropagation={(e) => {
					e.preventDefault();
					dispatch('deleteSelected');
				}}
				title={$i18n.t('Delete Selected')}
			>
				{$i18n.t('Delete')}
			</button>
		</div>
	{/if}
</div>
