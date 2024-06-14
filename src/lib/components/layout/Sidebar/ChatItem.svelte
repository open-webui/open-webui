<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	import {
		archiveChatById,
		cloneChatById,
		deleteChatById,
		getChatList,
		updateChatById
	} from '$lib/apis/chats';
	import { chatId, chats, mobile, showSidebar } from '$lib/stores';

	import ChatMenu from './ChatMenu.svelte';
	import ShareChatModal from '$lib/components/chat/ShareChatModal.svelte';

	export let chat;

	let showShareChatModal = false;

	export let selected = false;

	let confirmEdit = false;
	let confirmDelete = false;

	let chatTitle = '';

	const editChatTitle = async (id, _title) => {
		if (_title === '') {
			toast.error($i18n.t('Title cannot be an empty string.'));
		} else {
			await updateChatById(localStorage.token, id, {
				title: _title
			});
			await chats.set(await getChatList(localStorage.token));
		}
	};

	const deleteChat = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(error);
			confirmDelete = false;

			return null;
		});

		if (res) {
			if ($chatId === id) {
				goto('/');
			}
			await chats.set(await getChatList(localStorage.token));
		}
	};

	const cloneChatHandler = async (id) => {
		const res = await cloneChatById(localStorage.token, id).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);
			await chats.set(await getChatList(localStorage.token));
		}
	};

	const archiveChatHandler = async (id) => {
		await archiveChatById(localStorage.token, id);
		await chats.set(await getChatList(localStorage.token));
	};

	const focusEdit = async (node: HTMLInputElement) => {
		node.focus();
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={chat.id} />

<div class=" w-full pr-2 relative group">
	{#if confirmEdit}
		<div
			class=" w-full flex justify-between rounded-xl px-3 py-2 {chat.id === $chatId ||
			confirmEdit ||
			confirmDelete
				? 'bg-gray-200 dark:bg-gray-900'
				: selected
				? 'bg-gray-100 dark:bg-gray-950'
				: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis"
		>
			<input
				use:focusEdit
				bind:value={chatTitle}
				class=" bg-transparent w-full outline-none mr-10"
			/>
		</div>
	{:else}
		<a
			class=" w-full flex justify-between rounded-xl px-3 py-2 {chat.id === $chatId ||
			confirmEdit ||
			confirmDelete
				? 'bg-gray-200 dark:bg-gray-900'
				: selected
				? 'bg-gray-100 dark:bg-gray-950'
				: ' group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}  whitespace-nowrap text-ellipsis"
			href="/c/{chat.id}"
			on:click={() => {
				dispatch('select');

				if ($mobile) {
					showSidebar.set(false);
				}
			}}
			on:dblclick={() => {
				chatTitle = chat.title;
				confirmEdit = true;
			}}
			on:mouseover={(e) => {
				if (e.shiftKey) {
					// Your code here
					console.log('hi');
				}
			}}
			on:focus={(e) => {}}
			draggable="false"
		>
			<div class=" flex self-center flex-1 w-full">
				<div class=" text-left self-center overflow-hidden w-full h-[20px]">
					{chat.title}
				</div>
			</div>
		</a>
	{/if}

	<div
		class="

        {chat.id === $chatId || confirmEdit || confirmDelete
			? 'from-gray-200 dark:from-gray-900'
			: selected
			? 'from-gray-100 dark:from-gray-950'
			: 'invisible group-hover:visible from-gray-100 dark:from-gray-950'}
            absolute right-[10px] top-[10px] pr-2 pl-5 bg-gradient-to-l from-80%

              to-transparent"
	>
		{#if confirmEdit}
			<div class="flex self-center space-x-1.5 z-10">
				<button
					class=" self-center dark:hover:text-white transition"
					on:click={() => {
						editChatTitle(chat.id, chatTitle);
						confirmEdit = false;
						chatTitle = '';
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
				<button
					class=" self-center dark:hover:text-white transition"
					on:click={() => {
						confirmEdit = false;
						chatTitle = '';
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</button>
			</div>
		{:else if confirmDelete}
			<div class="flex self-center space-x-1.5 z-10">
				<button
					class=" self-center dark:hover:text-white transition"
					on:click={() => {
						deleteChat(chat.id);
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
				<button
					class=" self-center dark:hover:text-white transition"
					on:click={() => {
						confirmDelete = false;
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</button>
			</div>
		{:else}
			<div class="flex self-center space-x-1 z-10">
				<ChatMenu
					chatId={chat.id}
					cloneChatHandler={() => {
						cloneChatHandler(chat.id);
					}}
					shareHandler={() => {
						showShareChatModal = true;
					}}
					archiveChatHandler={() => {
						archiveChatHandler(chat.id);
					}}
					renameHandler={() => {
						confirmEdit = true;
					}}
					deleteHandler={() => {
						confirmDelete = true;
					}}
					onClose={() => {
						selected = false;
					}}
				>
					<button
						aria-label="Chat Menu"
						class=" self-center dark:hover:text-white transition"
						on:click={() => {
							dispatch('select');
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
				</ChatMenu>

				{#if chat.id === $chatId}
					<!-- Shortcut support using "delete-chat-button" id -->
					<button
						id="delete-chat-button"
						class="hidden"
						on:click={() => {
							confirmDelete = true;
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
