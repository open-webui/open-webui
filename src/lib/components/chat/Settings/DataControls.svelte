<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import {
		chats,
		user,
		settings,
		scrollPaginationEnabled,
		currentChatPage,
		pinnedChats
	} from '$lib/stores';

	import {
		archiveAllChats,
		deleteAllChats,
		getAllChats,
		getChatList,
		getPinnedChatList,
		importChats
	} from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/ArchivedChatsModal.svelte';
	import SharedChatsModal from '$lib/components/layout/SharedChatsModal.svelte';
	import FilesModal from '$lib/components/layout/FilesModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Chats
	let importFiles;

	let showArchiveConfirmDialog = false;
	let showDeleteConfirmDialog = false;
	let showArchivedChatsModal = false;
	let showSharedChatsModal = false;
	let showFilesModal = false;

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
			importChatsHandler(chats);
		};

		if (importFiles.length > 0) {
			reader.readAsText(importFiles[0]);
		}
	}

	const importChatsHandler = async (_chats) => {
		const res = await importChats(
			localStorage.token,
			_chats.map((chat) => {
				if (chat.chat) {
					return {
						chat: chat.chat,
						meta: chat.meta ?? {},
						pinned: false,
						folder_id: chat?.folder_id ?? null,
						created_at: chat?.created_at ?? null,
						updated_at: chat?.updated_at ?? null
					};
				} else {
					// Legacy format
					return {
						chat: chat,
						meta: {},
						pinned: false,
						folder_id: null,
						created_at: chat?.created_at ?? null,
						updated_at: chat?.updated_at ?? null
					};
				}
			})
		);
		if (res) {
			toast.success(`Successfully imported ${res.length} chats.`);
		}

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		pinnedChats.set(await getPinnedChatList(localStorage.token));
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
		pinnedChats.set([]);
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
<SharedChatsModal bind:show={showSharedChatsModal} />
<FilesModal bind:show={showFilesModal} />

<ConfirmDialog
	title={$i18n.t('Archive All Chats')}
	message={$i18n.t('Are you sure you want to archive all chats? This action cannot be undone.')}
	bind:show={showArchiveConfirmDialog}
	on:confirm={archiveAllChatsHandler}
	on:cancel={() => {
		showArchiveConfirmDialog = false;
	}}
/>

<ConfirmDialog
	title={$i18n.t('Delete All Chats')}
	message={$i18n.t('Are you sure you want to delete all chats? This action cannot be undone.')}
	bind:show={showDeleteConfirmDialog}
	on:confirm={deleteAllChatsHandler}
	on:cancel={() => {
		showDeleteConfirmDialog = false;
	}}
/>

<div id="tab-chats" class="flex flex-col h-full justify-between text-sm">
	<div class="space-y-3 overflow-y-scroll max-h-[28rem] md:max-h-full">
		<input
			id="chat-import-input"
			bind:this={chatImportInputElement}
			bind:files={importFiles}
			type="file"
			accept=".json"
			hidden
		/>

		<div>
			<div class="mb-1 text-sm font-medium">{$i18n.t('Chats')}</div>

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs">{$i18n.t('Import Chats')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							chatImportInputElement.click();
						}}
						type="button"
					>
						<span class="self-center">{$i18n.t('Import')}</span>
					</button>
				</div>
			</div>

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<div>
					<div class="py-0.5 flex w-full justify-between">
						<div class="self-center text-xs">{$i18n.t('Export Chats')}</div>
						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								exportChats();
							}}
							type="button"
						>
							<span class="self-center">{$i18n.t('Export')}</span>
						</button>
					</div>
				</div>
			{/if}

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs">{$i18n.t('Archived Chats')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							showArchivedChatsModal = true;
						}}
						type="button"
					>
						<span class="self-center">{$i18n.t('Manage')}</span>
					</button>
				</div>
			</div>

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs">{$i18n.t('Shared Chats')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							showSharedChatsModal = true;
						}}
						type="button"
					>
						<span class="self-center">{$i18n.t('Manage')}</span>
					</button>
				</div>
			</div>

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs">{$i18n.t('Archive All Chats')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							showArchiveConfirmDialog = true;
						}}
						type="button"
					>
						<span class="self-center">{$i18n.t('Archive All')}</span>
					</button>
				</div>
			</div>

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs">{$i18n.t('Delete All Chats')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							showDeleteConfirmDialog = true;
						}}
						type="button"
					>
						<span class="self-center">{$i18n.t('Delete All')}</span>
					</button>
				</div>
			</div>
		</div>

		<div>
			<div class="mb-1 text-sm font-medium">{$i18n.t('Files')}</div>

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div class="self-center text-xs">{$i18n.t('Manage Files')}</div>
					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							showFilesModal = true;
						}}
						type="button"
					>
						<span class="self-center">{$i18n.t('Manage')}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</div>
