<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { config, knowledge, settings, user } from '$lib/stores';

	import Selector from './Knowledge/Selector.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { uploadFile } from '$lib/apis/files';

	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let selectedItems = [];
	const i18n = getContext('i18n');

	let loaded = false;

	let filesInputElement = null;
	let inputFiles = [];

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
				fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

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
		if (!$knowledge) {
			knowledge.set(await getKnowledgeBases(localStorage.token));
		}
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
	<!-- PII Warning -->
	<div
		class="mb-3 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg"
	>
		<div class="flex items-start space-x-2">
			<div class="flex-shrink-0">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5"
				>
					<path
						fill-rule="evenodd"
						d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div class="text-sm text-yellow-800 dark:text-yellow-200">
				{$i18n.t('PII masking is not yet supported in custom models')}
			</div>
		</div>
	</div>

	<slot name="label">
		<div class="mb-2">
			<div class="flex w-full justify-between mb-1">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Knowledge')}
				</div>
			</div>

			<div class=" text-xs dark:text-gray-500">
				{$i18n.t('To attach knowledge base here, add them to the "Knowledge" workspace first.')}
			</div>
		</div>
	</slot>

	<div class="flex flex-col">
		{#if selectedItems?.length > 0}
			<div class=" flex flex-wrap items-center gap-2 mb-2.5">
				{#each selectedItems as file, fileIdx}
					<FileItem
						{file}
						item={file}
						name={file.name}
						modal={true}
						edit={true}
						loading={file.status === 'uploading'}
						type={file?.legacy
							? `Legacy${file.type ? ` ${file.type}` : ''}`
							: (file?.type ?? 'collection')}
						dismissible
						on:dismiss={(e) => {
							selectedItems = selectedItems.filter((_, idx) => idx !== fileIdx);
						}}
					/>
				{/each}
			</div>
		{/if}

		{#if loaded}
			<div class="flex flex-wrap flex-row text-sm gap-1">
				<Selector
					knowledgeItems={$knowledge || []}
					on:select={(e) => {
						const item = e.detail;

						if (!selectedItems.find((k) => k.id === item.id)) {
							selectedItems = [
								...selectedItems,
								{
									...item
								}
							];
						}
					}}
				>
					<div
						class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-850 rounded-3xl"
					>
						{$i18n.t('Select Knowledge')}
					</div>
				</Selector>

				{#if $user?.role === 'admin' || $user?.permissions?.chat?.file_upload}
					<button
						class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-850 rounded-3xl"
						type="button"
						on:click={() => {
							filesInputElement.click();
						}}>{$i18n.t('Upload Files')}</button
					>
				{/if}
			</div>
		{/if}
		<!-- {knowledge} -->
	</div>
</div>
