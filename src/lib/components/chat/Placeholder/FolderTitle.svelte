<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import { selectedFolder, user } from '$lib/stores';
	import {
		loadFolderDetails,
		updateFolderDetails,
		removeFolderState,
		type FolderDetails
	} from '$lib/stores/folderStates';

	import {
		deleteFolderById,
		updateFolderById,
		createNewFolder,
		markFolderChatsReadById
	} from '$lib/apis/folders';
	import { getChatsByFolderId } from '$lib/apis/chats';
	import { refreshSidebar } from '$lib/stores/chatList';

	import FolderModal from '$lib/components/layout/Sidebar/Folders/FolderModal.svelte';
	import FolderShareModal from '$lib/components/layout/Sidebar/Folders/FolderShareModal.svelte';

	import FolderMenu from '$lib/components/layout/Sidebar/Folders/FolderMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let folder: FolderDetails | null = null;
	export let readOnly: boolean = false;
	export let onNewChat: () => void = () => {};
	export let folderTabActions: import('svelte').Snippet | undefined = undefined;
	$: folderTabActions = renderFolderActions;

	export let onUpdate: Function = (folderId) => {};
	export let onDelete: Function = (folderId) => {};

	export let showFolderModal = false;
	let showCreateSubFolderModal = false;
	let showShareModal = false;
	let showDeleteConfirm = false;
	let deleteFolderContents = true;

	const updateHandler = async ({ name, meta, data }) => {
		const targetFolder = folder;
		if (!targetFolder) return;
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const currentName = targetFolder.name;

		targetFolder.name = name;

		const res = await updateFolderById(localStorage.token, targetFolder.id, {
			name,
			...(meta ? { meta } : {}),
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			targetFolder.name = currentName;
			return null;
		});

		if (res) {
			updateFolderDetails(targetFolder.id, res);
			targetFolder.name = name;
			if (data) {
				targetFolder.data = data;
			}

			toast.success($i18n.t('Folder updated successfully'));

			const _folder = await loadFolderDetails(localStorage.token, targetFolder.id, true).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			const updatedFolder = { ...targetFolder, ..._folder };
			if ($selectedFolder?.id === targetFolder.id) selectedFolder.set(updatedFolder);
			onUpdate(updatedFolder);
		}
	};

	const deleteHandler = async () => {
		const targetFolder = folder;
		if (!targetFolder) return;
		const res = await deleteFolderById(
			localStorage.token,
			targetFolder.id,
			deleteFolderContents
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			removeFolderState(targetFolder.id);
			toast.success($i18n.t('Folder deleted successfully'));
			onDelete(targetFolder);
		}
	};

	const markAllReadHandler = async () => {
		const res = await markFolderChatsReadById(localStorage.token, folder.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!res) return;

		await refreshSidebar(localStorage.token);
	};

	const exportHandler = async () => {
		const chats = await getChatsByFolderId(localStorage.token, folder.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!chats) {
			return;
		}

		const blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});

		saveAs(blob, `folder-${folder.name}-export-${Date.now()}.json`);
	};

	const createSubFolderHandler = async ({ name, meta, data, parent_id }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const res = await createNewFolder(localStorage.token, {
			name,
			data,
			meta,
			parent_id
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Folder created successfully'));
			onUpdate();
		}
	};
</script>

{#snippet renderFolderActions()}
	{#if folder && !readOnly}
		<div class="flex shrink-0 items-center">
			<FolderMenu
				align="end"
				{onNewChat}
				onEdit={() => {
					showFolderModal = true;
				}}
				onDelete={() => {
					showDeleteConfirm = true;
				}}
				onExport={() => {
					exportHandler();
				}}
				onMarkAllRead={markAllReadHandler}
				onCreateSubFolder={() => {
					showCreateSubFolderModal = true;
				}}
				onShare={$user?.role === 'admin' ||
				(folder?.user_id === $user?.id && $user?.permissions?.sharing?.folders)
					? () => (showShareModal = true)
					: null}
			>
				<div
					class="flex size-4 items-center justify-center rounded text-gray-400 hover:bg-gray-200 hover:text-gray-700 dark:hover:bg-white/10 dark:hover:text-white"
				>
					<EllipsisHorizontal className="size-3" strokeWidth="1.5" />
				</div>
			</FolderMenu>
		</div>
	{/if}
{/snippet}

{#if folder}
	<FolderModal
		bind:show={showFolderModal}
		edit={true}
		folderId={folder.id}
		onSubmit={updateHandler}
	/>

	<FolderShareModal bind:show={showShareModal} {folder} />

	<FolderModal
		bind:show={showCreateSubFolderModal}
		parentId={folder.id}
		onSubmit={createSubFolderHandler}
	/>

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete folder?')}
		on:confirm={() => {
			deleteHandler();
		}}
	>
		<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3 mb-2">
			<!-- {$i18n.t('This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.', {
				NAME: folder.name
			})} -->

			{$i18n.t(`Are you sure you want to delete "{{NAME}}"?`, {
				NAME: folder.name
			})}
		</div>

		<div class="flex items-center gap-1.5">
			<input
				aria-label={$i18n.t('Delete all contents inside this folder')}
				type="checkbox"
				bind:checked={deleteFolderContents}
			/>

			<div class="text-xs text-gray-500">
				{$i18n.t('Delete all contents inside this folder')}
			</div>
		</div>
	</DeleteConfirmDialog>
{/if}
