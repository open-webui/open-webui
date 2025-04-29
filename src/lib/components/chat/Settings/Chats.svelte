<script lang="ts">
	import { chats, scrollPaginationEnabled, currentChatPage } from '$lib/stores';

	import { archiveAllChats, deleteAllChats, getChatList } from '$lib/apis/chats';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from '$lib/utils/toast';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Chats
	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showConfirm = false;
	let confirmTitle = '';
	let confirmMessage = '';
	let onConfirm = () => {};

	const archiveAllChatsHandler = async () => {
		await goto('/');
		await archiveAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
		toast.success($i18n.t('Archiving all chats'));
	};

	const deleteAllChatsHandler = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
		toast.success($i18n.t('Deleting all chats'));
	};

	const confirmArchiveAll = () => {
		showConfirm = true;
		confirmTitle = $i18n.t('Archive All Chats');
		confirmMessage = $i18n.t('Are you sure you want to archive all chats?');
		onConfirm = archiveAllChatsHandler;
	};
	const confirmDeleteAll = () => {
		showConfirm = true;
		confirmTitle = $i18n.t('Delete All Chats');
		confirmMessage = $i18n.t('Are you sure you want to delete all chats?');
		onConfirm = deleteAllChatsHandler;
	};

	const announceConfirmation = () => {
		toast.announce($i18n.t('Are you sure? Please confirm or cancel'));
	};
</script>

<ConfirmDialog
	bind:show={showConfirm}
	title={confirmTitle}
	message={confirmMessage}
	on:confirm={onConfirm}
/>
<div class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-2 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="flex flex-col">
			<button
				id="archive-all-chats"
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					confirmArchiveAll();
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="size-4"
					>
						<path
							d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
						/>
						<path
							fill-rule="evenodd"
							d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087Zm6.163 3.75A.75.75 0 0 1 10 12h4a.75.75 0 0 1 0 1.5h-4a.75.75 0 0 1-.75-.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<h3 class=" self-center text-sm font-medium">{$i18n.t('Archive All Chats')}</h3>
			</button>

			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					confirmDeleteAll();
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm7 7a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1 0-1.5h4.5A.75.75 0 0 1 11 9Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<h3 class=" self-center text-sm font-medium">{$i18n.t('Delete All Chats')}</h3>
			</button>
		</div>
	</div>
</div>
