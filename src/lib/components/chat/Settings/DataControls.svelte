<script lang="ts">
	import { canManageChats } from '$lib/utils/settings-access';
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
						variables: chat?.variables ?? {},
						pinned: false,
						archived: chat?.archived ?? false,
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
	title={$i18n.t('settings.personal.dataControls.archiveAllChats.label')}
	message={$i18n.t('Are you sure you want to archive all chats? This action cannot be undone.')}
	bind:show={showArchiveConfirmDialog}
	on:confirm={archiveAllChatsHandler}
	on:cancel={() => {
		showArchiveConfirmDialog = false;
	}}
/>

<ConfirmDialog
	title={$i18n.t('settings.personal.dataControls.deleteAllChats.label')}
	message={$i18n.t('Are you sure you want to delete all chats? This action cannot be undone.')}
	bind:show={showDeleteConfirmDialog}
	on:confirm={deleteAllChatsHandler}
	on:cancel={() => {
		showDeleteConfirmDialog = false;
	}}
/>

<div id="tab-chats" class="flex flex-col h-full text-sm">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.personal.dataControls.title')}
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

		<UserSettingSection
			title={$i18n.t('settings.personal.dataControls.sections.chats.title')}
			first
		>
			{#if canManageChats({ user: $user, config: null }, 'import')}
				<UserSettingRow
					label={$i18n.t('settings.personal.dataControls.importChats.label')}
					description={$i18n.t('settings.personal.dataControls.importChats.description')}
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

			{#if canManageChats({ user: $user, config: null }, 'export')}
				<UserSettingRow
					label={$i18n.t('settings.personal.dataControls.exportChats.label')}
					description={$i18n.t('settings.personal.dataControls.exportChats.description')}
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
				label={$i18n.t('settings.personal.dataControls.sharedChats.label')}
				description={$i18n.t('settings.personal.dataControls.sharedChats.description')}
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
				label={$i18n.t('settings.personal.dataControls.archiveAllChats.label')}
				description={$i18n.t('settings.personal.dataControls.archiveAllChats.description')}
			>
				<button
					class={actionButtonClass}
					on:click={() => {
						showArchiveConfirmDialog = true;
					}}
					type="button"
				>
					{$i18n.t('settings.personal.dataControls.archiveAll.label')}
				</button>
			</UserSettingRow>

			{#if canManageChats({ user: $user, config: null }, 'delete')}
				<UserSettingRow
					label={$i18n.t('settings.personal.dataControls.deleteAllChats.label')}
					description={$i18n.t('settings.personal.dataControls.deleteAllChats.description')}
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
			{/if}
		</UserSettingSection>

		<UserSettingSection title={$i18n.t('settings.personal.dataControls.sections.files.title')}>
			<UserSettingRow
				label={$i18n.t('settings.personal.dataControls.manageFiles.label')}
				description={$i18n.t('settings.personal.dataControls.manageFiles.description')}
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
