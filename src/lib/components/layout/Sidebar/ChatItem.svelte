<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto, invalidate, invalidateAll } from '$app/navigation';
	import { onMount, getContext, createEventDispatcher, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

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
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import { generateTitle } from '$lib/apis';

	export let className = '';

	export let id;
	export let title;

	export let selected = false;
	export let shiftKey = false;

	let chat = null;

	let mouseOver = false;
	let draggable = false;
	$: if (mouseOver) {
		loadChat();
	}

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
		} else {
			await updateChatById(localStorage.token, id, {
				title: title
			});

			if (id === $chatId) {
				_chatTitle.set(title);
			}

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));

			dispatch('change');
		}
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
		}
	};

	const deleteChatHandler = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			tags.set(await getAllTags(localStorage.token));
			if ($chatId === id) {
				await goto('/');

				await chatId.set('');
				await tick();
			}

			dispatch('change');
		}
	};

	const archiveChatHandler = async (id) => {
		await archiveChatById(localStorage.token, id);
		dispatch('change');
	};

	let itemElement;

	let generating = false;
	let doubleClicked = false;
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

	const chatTitleInputKeydownHandler = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			setTimeout(() => {
				const input = document.getElementById(`chat-title-input-${id}`);
				if (input) input.blur();
			}, 0);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			confirmEdit = false;
			chatTitle = '';
		}
	};

	const renameHandler = async () => {
		chatTitle = title;
		confirmEdit = true;

		await tick();

		setTimeout(() => {
			const input = document.getElementById(`chat-title-input-${id}`);
			if (input) input.focus();
		}, 0);
	};

	const generateTitleHandler = async () => {
		generating = true;
		if (!chat) {
			chat = await getChatById(localStorage.token, id);
		}

		const messages = (chat.chat?.messages ?? []).map((message) => {
			return {
				role: message.role,
				content: message.content
			};
		});

		const model = chat.chat.models.at(0) ?? chat.models.at(0) ?? '';

		chatTitle = '';

		const generatedTitle = await generateTitle(localStorage.token, model, messages).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (generatedTitle) {
			if (generatedTitle !== title) {
				editChatTitle(id, generatedTitle);
			}

			confirmEdit = false;
		} else {
			chatTitle = title;
		}

		generating = false;
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={id} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		deleteChatHandler(id);
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
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

<div
	bind:this={itemElement}
	class=" w-full {className} relative group flex items-center"
	draggable={draggable && !confirmEdit}
>
	{#if confirmEdit}
		<div
			class=" w-full flex justify-between text-neutrals-800 text-[16px] leading-[24px] font-medium {id ===
				$chatId || confirmEdit
				? 'bg-gray-200 dark:bg-gray-900'
				: selected
					? 'bg-gray-100 dark:bg-gray-950'
					: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis relative {generating
				? 'cursor-not-allowed'
				: ''}"
		>
			<input
				id="chat-title-input-{id}"
				bind:value={chatTitle}
				class="py-[8px] px-[8px] rounded-[8px] text-neutrals-800 text-[16px] leading-[24px] font-medium bg-transparent w-full outline-hidden mr-10"
				placeholder={generating ? $i18n.t('Generating...') : ''}
				on:keydown={chatTitleInputKeydownHandler}
				on:blur={async (e) => {
					// check if target is generate button
					if (e.relatedTarget?.id === 'generate-title-button') {
						return;
					}

					if (doubleClicked) {
						e.preventDefault();
						e.stopPropagation();

						await tick();
						setTimeout(() => {
							const input = document.getElementById(`chat-title-input-${id}`);
							if (input) input.focus();
						}, 0);

						doubleClicked = false;
						return;
					}

					if (chatTitle !== title) {
						editChatTitle(id, chatTitle);
					}

					confirmEdit = false;
					chatTitle = '';
				}}
			/>
		</div>
	{:else}
		<a
			class=" w-full flex items-center justify-between text-typography-titles link-style rounded-[8px] px-[16px] py-[15px] {id ===
				$chatId || confirmEdit
				? 'bg-gradient-bg-2 dark:bg-gray-900'
				: selected
					? 'bg-gradient-bg-2 dark:bg-gray-950'
					: ' group-hover:bg-gradient-bg-2 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis"
			href="/c/{id}"
			on:click={() => {
				dispatch('select');

				if ($mobile) {
					showSidebar.set(false);
				}
			}}
			on:dblclick={async (e) => {
				e.preventDefault();
				e.stopPropagation();

				doubleClicked = true;
				renameHandler();
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
			<div class=" flex items-center justify-between self-center flex-1 w-full">
				<div dir="auto" class="text-left self-center overflow-hidden w-full h-[20px]">
					{title}
				</div>
				{#if className === 'pinned'}<div class="visible group-hover:invisible">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
						>
							<path
								d="M12.9175 10.1761L14.4079 11.6665V12.9165H10.6258V17.4998L10.0008 18.1248L9.37583 17.4998V12.9165H5.59375V11.6665L7.08417 10.1761V4.1665H6.25083V2.9165H13.7508V4.1665H12.9175V10.1761ZM7.37583 11.6665H12.6258L11.6675 10.7082V4.1665H8.33417V10.7082L7.37583 11.6665Z"
								fill="#23282E"
							/>
						</svg>
					</div>{/if}
			</div>
		</a>
	{/if}

	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="
        {id === $chatId || confirmEdit
			? 'from-gray-200 dark:from-gray-900'
			: selected
				? 'from-gray-100 dark:from-gray-950'
				: 'invisible group-hover:visible '}
            absolute {className === 'pr-2'
			? 'right-[8px]'
			: 'right-1'} top-[10px] py-1 pr-0.5 mr-1.5 pl-5"
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
				<Tooltip content={$i18n.t('Generate')}>
					<button
						class=" self-center dark:hover:text-white transition"
						id="generate-title-button"
						on:click={(e) => {
							e.preventDefault();
							e.stopImmediatePropagation();
							e.stopPropagation();

							generateTitleHandler();
						}}
					>
						<Sparkles strokeWidth="2" />
					</button>
				</Tooltip>
			</div>
		{:else if shiftKey && mouseOver}
			<div class=" flex items-center self-center space-x-1.5">
				<Tooltip content={$i18n.t('Archive')} className="flex items-center">
					<button
						class=" self-center dark:hover:text-white transition"
						on:click={() => {
							archiveChatHandler(id);
						}}
						type="button"
					>
						<ArchiveBox className="size-4  translate-y-[0.5px]" strokeWidth="2" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Delete')}>
					<button
						class=" self-center dark:hover:text-white transition"
						on:click={() => {
							deleteChatHandler(id);
						}}
						type="button"
					>
						<GarbageBin strokeWidth="2" />
					</button>
				</Tooltip>
			</div>
		{:else}
			<div class="flex self-center z-10 items-end">
				<ChatMenu
					chatId={id}
					cloneChatHandler={() => {
						cloneChatHandler(id);
					}}
					shareHandler={() => {
						showShareChatModal = true;
					}}
					archiveChatHandler={() => {
						archiveChatHandler(id);
					}}
					{renameHandler}
					deleteHandler={() => {
						showDeleteConfirm = true;
					}}
					onClose={() => {
						dispatch('unselect');
					}}
					on:change={async () => {
						dispatch('change');
					}}
					on:tag={(e) => {
						dispatch('tag', e.detail);
					}}
				>
					<button
						aria-label="Chat Menu"
						class=" self-center dark:hover:text-white transition m-0"
						on:click={() => {
							dispatch('select');
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
						>
							<path
								d="M10 16.0578C9.65625 16.0578 9.36201 15.9354 9.11729 15.6905C8.87243 15.4458 8.75 15.1516 8.75 14.8078C8.75 14.4641 8.87243 14.1697 9.11729 13.9249C9.36201 13.6802 9.65625 13.5578 10 13.5578C10.3438 13.5578 10.638 13.6802 10.8827 13.9249C11.1276 14.1697 11.25 14.4641 11.25 14.8078C11.25 15.1516 11.1276 15.4458 10.8827 15.6905C10.638 15.9354 10.3438 16.0578 10 16.0578ZM10 11.2501C9.65625 11.2501 9.36201 11.1277 9.11729 10.8828C8.87243 10.6381 8.75 10.3438 8.75 10.0001C8.75 9.65634 8.87243 9.36211 9.11729 9.11738C9.36201 8.87252 9.65625 8.75009 10 8.75009C10.3438 8.75009 10.638 8.87252 10.8827 9.11738C11.1276 9.36211 11.25 9.65634 11.25 10.0001C11.25 10.3438 11.1276 10.6381 10.8827 10.8828C10.638 11.1277 10.3438 11.2501 10 11.2501ZM10 6.44238C9.65625 6.44238 9.36201 6.32002 9.11729 6.0753C8.87243 5.83044 8.75 5.53613 8.75 5.19238C8.75 4.84863 8.87243 4.5544 9.11729 4.30967C9.36201 4.06481 9.65625 3.94238 10 3.94238C10.3438 3.94238 10.638 4.06481 10.8827 4.30967C11.1276 4.5544 11.25 4.84863 11.25 5.19238C11.25 5.53613 11.1276 5.83044 10.8827 6.0753C10.638 6.32002 10.3438 6.44238 10 6.44238Z"
								fill="#23282E"
							/>
						</svg>
					</button>
				</ChatMenu>

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
							class="w-4 h-4"
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
</div>
