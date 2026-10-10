<script lang="ts">
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { getContext, onMount } from 'svelte';
	import { config, settings, user } from '$lib/stores';

	import KnowledgeSelector from './Knowledge/KnowledgeSelector.svelte';
	import FileItemModal from '$lib/components/common/FileItemModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { uploadFile } from '$lib/apis/files';

	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let selectedItems = [];
	export let disabled = false;
	let showPicker = false;
	let picker: KnowledgeSelector;
	let valueElement: HTMLElement | null = null;
	const i18n = getContext('i18n');

	let loaded = false;

	let filesInputElement = null;
	let inputFiles = null;

	let showItemModal = false;
	let selectedItemIdx = null;

	$: if (selectedItems == null) {
		selectedItems = [];
	}

	const uploadFileHandler = async (file, fullContext: boolean = false) => {
		if (disabled) return null;
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

{#if showItemModal && selectedItemIdx !== null && selectedItems[selectedItemIdx]}
	<FileItemModal bind:show={showItemModal} bind:item={selectedItems[selectedItemIdx]} edit={true} />
{/if}

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

{#if loaded}
	<KnowledgeSelector
		bind:this={picker}
		anchorElement={valueElement}
		bind:show={showPicker}
		{selectedItems}
		{disabled}
		on:select={(e) => {
			if (
				!disabled &&
				!selectedItems.find((item) => item.id === e.detail.id && item.type === e.detail.type)
			) {
				selectedItems = [...selectedItems, e.detail];
			}
		}}
	>
		<button
			type="button"
			{disabled}
			aria-expanded={showPicker}
			class="grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal disabled:cursor-default sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
		>
			<span class="text-gray-600 dark:text-gray-400"
				><slot name="label"
					><ModelSettingsLabel
						label={$i18n.t('Knowledge')}
						description={$i18n.t(
							'Attach knowledge bases, notes, or files for this model to reference in chats.'
						)}
					/></slot
				></span
			>
			<span
				bind:this={valueElement}
				class="flex min-w-0 items-center gap-1 text-gray-900 dark:text-gray-100"
			>
				<span class="min-w-0 [overflow-wrap:anywhere]"
					>{selectedItems
						.slice(0, 3)
						.map((item) => item.name || item.id)
						.join(', ') || $i18n.t('None')}</span
				>
				{#if selectedItems.length > 3}<span class="shrink-0 text-gray-500"
						>+{selectedItems.length - 3}</span
					>{/if}
				{#if selectedItems.some((item) => item.status === 'uploading')}<Spinner
						className="size-3.5 shrink-0"
					/>{/if}
			</span>
			<ChevronRight className="size-3 text-gray-400" />
		</button>
		<div slot="selected">
			<div class="flex flex-col pb-1">
				{#if selectedItems?.length > 0}
					<div class="flex flex-col">
						{#each selectedItems as file, fileIdx}
							<Tooltip content={file.description || file.name || file.id}>
								<div
									class="flex min-h-7 w-full items-center gap-2 rounded-xl px-2 py-1 text-xs font-normal text-gray-900 hover:bg-gray-50 dark:text-gray-100 dark:hover:bg-gray-800"
								>
									<button
										{disabled}
										type="button"
										class="flex min-w-0 flex-1 items-center gap-2 text-left"
										aria-label={$i18n.t('Edit')}
										on:click={() => {
											selectedItemIdx = fileIdx;
											showPicker = false;
											showItemModal = true;
										}}
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
									</button>

									{#if file.status === 'uploading'}
										<div class="shrink-0 text-gray-400 dark:text-gray-500">
											{$i18n.t('Uploading')}
										</div>
									{/if}

									<button
										{disabled}
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
					</div>
				{/if}

				<!-- {knowledge} -->
			</div>
		</div>
		<div slot="actions" class="flex w-full items-center gap-3">
			{#if selectedItems.length}
				<button
					type="button"
					{disabled}
					class="text-left hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => (selectedItems = [])}>{$i18n.t('Clear')}</button
				>
			{/if}
			{#if $user?.role === 'admin' || $user?.permissions?.chat?.file_upload}
				<button
					type="button"
					{disabled}
					class="hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => filesInputElement.click()}>{$i18n.t('Upload Files')}</button
				>
			{/if}
			<div class="ml-auto flex items-center gap-3">
				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
					<a
						href="/workspace/knowledge"
						target="_blank"
						rel="noreferrer"
						class="hover:text-gray-900 dark:hover:text-gray-100">{$i18n.t('Manage')}</a
					>
				{/if}
				<button
					type="button"
					class="hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => picker.close()}>{$i18n.t('Done')}</button
				>
			</div>
		</div>
	</KnowledgeSelector>
{/if}
