<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { chats, user, settings, scrollPaginationEnabled, currentChatPage } from '$lib/stores';

	import {
		archiveAllChats,
		deleteAllChats,
		getAllChats,
		getChatList,
		importChat
	} from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/ArchivedChatsModal.svelte';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Chats
	let importFiles;

	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;

	let chatImportInputElement: HTMLInputElement;

	$: if (importFiles) {
		console.log(importFiles);

		let reader = new FileReader();
		reader.onload = (event) => {
			let chats = JSON.parse(event.target.result);
			console.log(chats);
			if (getImportOrigin(chats) == 'openai') {
				try {
					chats = convertOpenAIChats(chats);
				} catch (error) {
					console.log('Unable to import chats:', error);
				}
			}
			importChats(chats);
		};

		if (importFiles.length > 0) {
			reader.readAsText(importFiles[0]);
		}
	}

	const importChats = async (_chats) => {
		for (const chat of _chats) {
			console.log(chat);

			if (chat.chat) {
				await importChat(
					localStorage.token,
					chat.chat,
					chat.meta ?? {},
					false,
					null,
					chat?.created_at ?? null,
					chat?.updated_at ?? null
				);
			} else {
				// Legacy format
				await importChat(localStorage.token, chat, {}, false, null);
			}
		}

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const exportChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `chat-export-${Date.now()}.json`);
	};

	const archiveAllChatsHandler = async () => {
		await goto('/');
		await archiveAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const deleteAllChatsHandler = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const handleArchivedChatsChange = async () => {
		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));

		scrollPaginationEnabled.set(true);
	};
</script>

<ArchivedChatsModal bind:show={showArchivedChatsModal} onUpdate={handleArchivedChatsChange} />

<div id="tab-chats" class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-2 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="flex flex-col">
			<input
				id="chat-import-input"
				bind:this={chatImportInputElement}
				bind:files={importFiles}
				type="file"
				accept=".json"
				hidden
			/>
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					chatImportInputElement.click();
				}}
			>
				<div class=" self-center mr-3">
					<ArrowUpTray className="w-4 h-4" />
				</div>
				<div class=" self-center text-sm font-medium">{$i18n.t('Import Chats')}</div>
			</button>

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						exportChats();
					}}
				>
					<div class=" self-center mr-3">
						<ArrowDownTray className="w-4 h-4" />
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Export Chats')}</div>
				</button>
			{/if}
		</div>

		<hr class=" border-gray-100 dark:border-gray-850" />

		<div class="flex flex-col">
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					showArchivedChatsModal = true;
				}}
			>
				<div class=" self-center mr-3">
					<ArchiveBox className="w-4 h-4" />
				</div>
				<div class=" self-center text-sm font-medium">{$i18n.t('Archived Chats')}</div>
			</button>

			{#if showArchiveConfirm}
				<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
					<div class="flex items-center space-x-3">
						<ArchiveBox className="w-4 h-4" />
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div class="flex space-x-1.5 items-center">
						<button
							class="hover:text-white transition"
							on:click={() => {
								archiveAllChatsHandler();
								showArchiveConfirm = false;
							}}
						>
							<Check className="w-4 h-4" />
						</button>
						<button
							class="hover:text-white transition"
							on:click={() => {
								showArchiveConfirm = false;
							}}
						>
							<XMark className="w-4 h-4" />
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showArchiveConfirm = true;
					}}
				>
					<div class=" self-center mr-3">
						<ArchiveBox className="w-4 h-4" />
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Archive All Chats')}</div>
				</button>
			{/if}

			{#if showDeleteConfirm}
				<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
					<div class="flex items-center space-x-3">
						<Trash className="w-4 h-4" />
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div class="flex space-x-1.5 items-center">
						<button
							class="hover:text-white transition"
							on:click={() => {
								deleteAllChatsHandler();
								showDeleteConfirm = false;
							}}
						>
							<Check className="w-4 h-4" />
						</button>
						<button
							class="hover:text-white transition"
							on:click={() => {
								showDeleteConfirm = false;
							}}
						>
							<XMark className="w-4 h-4" />
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showDeleteConfirm = true;
					}}
				>
					<div class=" self-center mr-3">
						<Trash className="w-4 h-4" />
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Delete All Chats')}</div>
				</button>
			{/if}
		</div>
	</div>
</div>
