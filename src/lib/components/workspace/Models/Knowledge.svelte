<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { config, knowledge, settings, user } from '$lib/stores';

	import KnowledgeSelector from './Knowledge/KnowledgeSelector.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { uploadFile } from '$lib/apis/files';

	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let selectedItems = [];
	const i18n = getContext('i18n');

	let loaded = false;

	let filesInputElement = null;
	let inputFiles = null;

	$: if (selectedItems === null || selectedItems === undefined) {
		selectedItems = [];
	}

	const uploadFileHandler = async (file, fullContext: boolean = false) => {
		if ($user?.role !== 'admin' && !($user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return null;
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId,
			...(fullContext ? { context: 'full' } : {})
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		selectedItems = [...selectedItems, fileItem];

		try {
			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (uploadedFile) {
				console.log('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.collection_name =
					uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;
				fileItem.url = `${uploadedFile.id}`;

				selectedItems = selectedItems;
			} else {
				selectedItems = selectedItems.filter((item) => item?.itemId !== tempItemId);
			}
		} catch (e) {
			toast.error(`${e}`);
			selectedItems = selectedItems.filter((item) => item?.itemId !== tempItemId);
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);

		inputFiles.forEach(async (file) => {
			console.log('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.log('File exceeds max size limit:', {
					fileSize: file.size,
					maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
				});
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (!file['type'].startsWith('image/')) {
				uploadFileHandler(file);
			} else {
				toast.error($i18n.t(`Unsupported file type.`));
			}
		});
	};

	onMount(async () => {
		loaded = true;
	});
</script>

<input
	bind:this={filesInputElement}
	bind:files={inputFiles}
	type="file"
	hidden
	multiple
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			const _inputFiles = Array.from(inputFiles);
			inputFilesHandler(_inputFiles);
		} else {
			toast.error($i18n.t(`File not found.`));
		}

		filesInputElement.value = '';
	}}
/>

<div>
	<div class="mb-2">
		<div class="flex w-full items-center gap-2 mb-1">
			<div class="min-w-0">
				<slot name="label">
					<div class=" self-center text-xs text-gray-500">
						{$i18n.t('Knowledge')}
					</div>
				</slot>
			</div>

			{#if loaded}
				<div class="flex shrink-0 items-center gap-2">
					<div class="min-w-0">
						<KnowledgeSelector
							on:select={(e) => {
								const item = e.detail;
								const current = selectedItems ?? [];

								if (!current.find((k) => k.id === item.id)) {
									selectedItems = [
										...current,
										{
											...item
										}
									];
								}
							}}
						>
							<div
								class="flex min-w-0 items-center bg-transparent text-xs text-gray-500 outline-hidden hover:underline dark:text-gray-400"
							>
								<span class="truncate">{$i18n.t('Select Knowledge')}</span>
							</div>
						</KnowledgeSelector>
					</div>

					{#if $user?.role === 'admin' || $user?.permissions?.chat?.file_upload}
						<button
							class="self-center bg-transparent text-xs text-gray-500 hover:underline dark:text-gray-400"
							type="button"
							aria-label={$i18n.t('Upload Files')}
							on:click={() => {
								filesInputElement.click();
							}}
						>
							{$i18n.t('Upload')}
						</button>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<div class="flex flex-col mb-1">
		{#if selectedItems?.length > 0}
			<div class=" flex flex-wrap items-center gap-1.5 mb-2.5">
				{#each selectedItems as file, fileIdx}
					<Tooltip content={file.description || file.name || file.id}>
						<div
							class="flex max-w-56 items-center gap-1.5 py-0.5 pr-2 text-xs text-gray-700 dark:text-gray-200"
						>
							<div class="shrink-0 text-gray-500 dark:text-gray-400">
								{#if file.status === 'uploading'}
									<Spinner className="size-3.5" />
								{:else if file.type === 'collection'}
									<Database className="size-3.5" />
								{:else if file.type === 'note'}
									<PageEdit className="size-3.5" />
								{:else if file.type === 'chat'}
									<ChatBubble className="size-3.5" />
								{:else if file.type === 'folder'}
									<Folder className="size-3.5" />
								{:else}
									<DocumentPage className="size-3.5" />
								{/if}
							</div>

							<div class="min-w-0 truncate">
								{file.name || file.id}
							</div>

							{#if file.status === 'uploading'}
								<div class="shrink-0 text-gray-400 dark:text-gray-500">
									{$i18n.t('Uploading')}
								</div>
							{/if}

							<button
								type="button"
								class="flex size-4 shrink-0 items-center justify-center text-gray-400 dark:text-gray-500"
								aria-label={$i18n.t('Remove File')}
								on:click={() => {
									selectedItems = selectedItems.filter((_, idx) => idx !== fileIdx);
								}}
							>
								<XMark className="size-3" />
							</button>
						</div>
					</Tooltip>
				{/each}

				<button
					type="button"
					class="py-0.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
					on:click={() => {
						selectedItems = [];
					}}
				>
					{$i18n.t('Disable all')}
				</button>
			</div>
		{/if}

		<!-- {knowledge} -->
	</div>

	<div class=" text-xs dark:text-gray-700">
		{$i18n.t('To attach knowledge base here, add them to the "Knowledge" workspace first.')}
	</div>
</div>
