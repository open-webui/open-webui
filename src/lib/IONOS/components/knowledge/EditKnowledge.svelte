<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import type {
		KnowledgeFile,
		KnowledgeFileId,
		Knowledge,
	} from '$lib/apis/knowledge/types';
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME } from '$lib/stores';
	import { SUPPORTED_FILE_FORMATS } from './constants';
	import { remove, removeFile } from '$lib/IONOS/services/knowledge';
	import { files, init as initFiles, upload } from './uploader';
	import { getFiles } from './dataTransferItemConverter';
	import Spinner from '$lib/IONOS/components/icons/Spinner.svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Confirm from '$lib/IONOS/components/common/Confirm.svelte';
	import Filepicker from '$lib/IONOS/components/common/Filepicker.svelte';
	import DropUploadZone from './DropUploadZone.svelte';
	import KnowledgeFileList from './KnowledgeFileList.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
	import DialogHeader from '$lib/IONOS/components/common/DialogHeader.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');
	const dispatch = createEventDispatcher();

	export let knowledge: Knowledge;

	let confirmKnowledgeDeletion = false;
	let uploadRunning = false;

	async function onKnowledgeDeletionConfirmed(): Promise<void> {
		try {
			await remove(knowledge.id);
			toast.success($i18n.t('Knowledge removed successfully.', { ns: 'ionos' }));
		} catch (e) {
			console.error(`Error deleting knowledge ${knowledge.id}`, e);
			toast.error($i18n.t('Error deleting knowledge', { ns: 'ionos' }));
		}

		confirmKnowledgeDeletion = false;
		dispatch('deleted');
	}

	async function deleteFile({ detail: fileId }: { detail: KnowledgeFileId }): Promise<void> {
		try {
			await removeFile(knowledge.id, fileId);
			toast.success($i18n.t('File removed successfully.', { ns: 'ionos' }));
			files.update((files: KnowledgeFile[]) => {
				return files.filter((file) => file.id !== fileId);
			});
		} catch (e) {
			console.error(`Error deleting file ${fileId}`, e);
			toast.error($i18n.t('Error deleting file', { ns: 'ionos' }));
		}
	}

	async function onFilesSelected({ detail: files }: { detail: File[] }): Promise<void> {
		uploadRunning = true;
		try {
			await upload(knowledge.id, files);
			toast.success($i18n.t('{{count}} file(s) uploaded successfully', { count: files.length, ns: 'ionos' }));
		} catch {
			toast.error($i18n.t('Error uploading files', { count: files.length, ns: 'ionos' }));
		} finally {
			uploadRunning = false;
		}
	}

	async function onDrop(e: DragEvent): Promise<void> {
		if (!e.dataTransfer) {
			return;
		}

		const files = await getFiles(e.dataTransfer);

		if (files.length === 0) {
			// Can happen if only directories got dropped
			return;
		}

		uploadRunning = true;
		try {
			await upload(knowledge.id, files);
			toast.success($i18n.t('{{count}} file(s) uploaded successfully', { count: files.length, ns: 'ionos' }));
		} catch {
			toast.error($i18n.t('Error uploading files', { count: files.length, ns: 'ionos' }));
		} finally {
			uploadRunning = false;
		}
	}

	$: initFiles(knowledge.files ?? []);
</script>

<svelte:head>
	<title>
		{$i18n.t('Editing Knowledge "{{name}}"', { ns: 'ionos', name: knowledge.name })} | {$WEBUI_NAME}
	</title>
</svelte:head>

<Dialog
	dialogId="knowledge-editor"
	show={true}
	class="p-0"
>
	<DialogHeader
		slot="header"
		title={knowledge.name}
		on:close={() => { dispatch('close'); }}
		dialogId="knowledge-editor"
		class="p-[30px]"
	/>

	<div slot="content" class="flex flex-col min-w-[500px] min-h-[200px] relative p-5 text-blue-800">
		<div class="flex justify-end items-end pb-5 border-gray-200 border-b cursor-default" class:grow={$files.length === 0}>
			<Button
				on:click={() => { confirmKnowledgeDeletion = true; }}
				type={ButtonType.caution}
			>
				{$i18n.t('Delete knowledge base', { ns: 'ionos' })}
			</Button>
		</div>

		<DropUploadZone
			onDrop={onDrop}
		>
			<div class="flex flex-col justify-center py-5 border-b border-gray-200 cursor-default" class:grow={$files.length === 0}>
				<p class="block text-center">
					{$i18n.t('Drop your files here, or', { ns: 'ionos' })}
					<Filepicker on:selected={onFilesSelected}>
						<span class="underline">
							{$i18n.t('browse', { ns: 'ionos' })}
						</span>
					</Filepicker>
				</p>
				<p class="block text-sm text-gray-500 text-center">
					{$i18n.t('Supports {{list}}', { ns: 'ionos', list: SUPPORTED_FILE_FORMATS.join(', ') })}
				</p>
			</div>

			{#if $files.length > 0}
				<div class="overflow-y-scroll h-[300px]">
					<KnowledgeFileList
						items={$files}
						on:delete={deleteFile}
					/>
				</div>
			{:else}
				<div class="flex justify-center items-center overflow-y-scroll min-h-[150px]">
					{$i18n.t('You have no files in your collection', { ns: 'ionos' })}
				</div>
			{/if}

			{#if uploadRunning}
				<div class="absolute top-0 left-0 right-0 bottom-0 w-full h-full flex justify-center items-center bg-white/10">
					<Spinner />
				</div>
			{/if}
		</DropUploadZone>
	</div>
</Dialog>

<Confirm
	title={$i18n.t('Delete knowledge base?', { ns: 'ionos' })}
	show={confirmKnowledgeDeletion}
	confirmText={$i18n.t('Delete knowledge base', { ns: 'ionos' })}
	confirmHandler={onKnowledgeDeletionConfirmed}
	cancelHandler={() => { confirmKnowledgeDeletion = false; }}
>
	{$i18n.t('This action can not be undone', { ns: 'ionos' })}
</Confirm>
