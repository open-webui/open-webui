<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { user } from '$lib/stores';
	import { refreshChatList } from '$lib/stores/chatList';

	import { archiveAllChats, deleteAllChats, getAllChats, importChats } from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import SharedChatsModal from '$lib/components/layout/SharedChatsModal.svelte';
	import FilesModal from '$lib/components/layout/FilesModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import UserSettingRow from './UserSettingRow.svelte';
	import UserSettingSection from './UserSettingSection.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Chats
	let importFiles;

	let showArchiveConfirmDialog = false;
	let showDeleteConfirmDialog = false;
	let showSharedChatsModal = false;
	let showFilesModal = false;

	let chatImportInputElement: HTMLInputElement;
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';

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

		await refreshChatList(localStorage.token, { refreshPinned: true });
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

		await refreshChatList(localStorage.token, { clearPinned: true });
	};

	const deleteAllChatsHandler = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		await refreshChatList(localStorage.token);
	};
</script>

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

<div id="tab-chats" class="flex flex-col h-full text-sm">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('Data Controls')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<input
			id="chat-import-input"
			bind:this={chatImportInputElement}
			bind:files={importFiles}
			type="file"
			accept=".json"
			hidden
		/>

		<UserSettingSection title={$i18n.t('Chats')} first>
			{#if $user?.role === 'admin' || ($user.permissions?.chat?.import ?? true)}
				<UserSettingRow
					label={$i18n.t('Import Chats')}
					description={$i18n.t('Import chat history from a JSON export file.')}
				>
					<button
						class={actionButtonClass}
						on:click={() => {
							chatImportInputElement.click();
						}}
						type="button"
					>
						{$i18n.t('Import')}
					</button>
				</UserSettingRow>
			{/if}

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<UserSettingRow
					label={$i18n.t('Export Chats')}
					description={$i18n.t('Download your chat history as a JSON export.')}
				>
					<button
						class={actionButtonClass}
						on:click={() => {
							exportChats();
						}}
						type="button"
					>
						{$i18n.t('Export')}
					</button>
				</UserSettingRow>
			{/if}

			<UserSettingRow
				label={$i18n.t('Shared Chats')}
				description={$i18n.t('Review and manage chats you have shared.')}
			>
				<button
					class={actionButtonClass}
					on:click={() => {
						showSharedChatsModal = true;
					}}
					type="button"
				>
					{$i18n.t('Manage')}
				</button>
			</UserSettingRow>

			<UserSettingRow
				label={$i18n.t('Archive All Chats')}
				description={$i18n.t('Move every chat into the archive after confirmation.')}
			>
				<button
					class={actionButtonClass}
					on:click={() => {
						showArchiveConfirmDialog = true;
					}}
					type="button"
				>
					{$i18n.t('Archive All')}
				</button>
			</UserSettingRow>

			<UserSettingRow
				label={$i18n.t('Delete All Chats')}
				description={$i18n.t('Permanently delete every chat after confirmation.')}
			>
				<button
					class={actionButtonClass}
					on:click={() => {
						showDeleteConfirmDialog = true;
					}}
					type="button"
				>
					{$i18n.t('Delete All')}
				</button>
			</UserSettingRow>
		</UserSettingSection>

		<UserSettingSection title={$i18n.t('Files')}>
			<UserSettingRow
				label={$i18n.t('Manage Files')}
				description={$i18n.t('Open the file manager for uploaded files.')}
			>
				<button
					class={actionButtonClass}
					on:click={() => {
						showFilesModal = true;
					}}
					type="button"
				>
					{$i18n.t('Manage')}
				</button>
			</UserSettingRow>
		</UserSettingSection>
	</div>
</div>
