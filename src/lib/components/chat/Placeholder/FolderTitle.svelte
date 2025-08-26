<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import DOMPurify from 'dompurify';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import { selectedFolder } from '$lib/stores';

	import { deleteFolderById, updateFolderById } from '$lib/apis/folders';
	import { getChatsByFolderId } from '$lib/apis/chats';

	import FolderModal from '$lib/components/layout/Sidebar/Folders/FolderModal.svelte';

	import Folder from '$lib/components/icons/Folder.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FolderMenu from '$lib/components/layout/Sidebar/Folders/FolderMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let folder = null;

	export let onUpdate: Function = (folderId) => {};
	export let onDelete: Function = (folderId) => {};

	let showFolderModal = false;
	let showDeleteConfirm = false;

	const updateHandler = async ({ name, data }) => {
		if (name === '') {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const currentName = folder.name;

		name = name.trim();
		folder.name = name;

		const res = await updateFolderById(localStorage.token, folder.id, {
			name,
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			folder.name = currentName;
			return null;
		});

		if (res) {
			folder.name = name;
			if (data) {
				folder.data = data;
			}

			toast.success($i18n.t('Folder updated successfully'));
			selectedFolder.set(folder);
			onUpdate(folder);
		}
	};

	const deleteHandler = async () => {
		const res = await deleteFolderById(localStorage.token, folder.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Folder deleted successfully'));
			onDelete(folder);
		}
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
</script>

{#if folder}
	<FolderModal bind:show={showFolderModal} edit={true} {folder} onSubmit={updateHandler} />

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete folder?')}
		on:confirm={() => {
			deleteHandler();
		}}
	>
		<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3">
			{@html DOMPurify.sanitize(
				$i18n.t(
					'This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.',
					{
						NAME: folder.name
					}
				)
			)}
		</div>
	</DeleteConfirmDialog>

	<div class="mb-3 px-6 @md:max-w-3xl justify-between w-full flex relative group items-center">
		<div class="text-center flex gap-3.5 items-center">
			<div class=" rounded-full bg-gray-50 dark:bg-gray-800 p-3 w-fit">
				<Folder className="size-4.5" strokeWidth="2" />
			</div>

			<div class="text-3xl">
				{folder.name}
			</div>
		</div>

		<div class="flex items-center translate-x-2.5">
			<FolderMenu
				align="end"
				onEdit={() => {
					showFolderModal = true;
				}}
				onDelete={() => {
					showDeleteConfirm = true;
				}}
				onExport={() => {
					exportHandler();
				}}
			>
				<button class="p-1.5 dark:hover:bg-gray-850 rounded-full touch-auto" on:click={(e) => {}}>
					<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
				</button>
			</FolderMenu>
		</div>
	</div>
{/if}
