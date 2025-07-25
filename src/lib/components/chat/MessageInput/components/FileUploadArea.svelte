<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import FileItem from '$lib/components/common/FileItem.svelte';
	import FilesOverlay from '../FilesOverlay.svelte';
	import { processFile, validateFileType, removeFile as removeFileUtil } from '../utils/fileProcessing';
	import { cloudStorageService } from '../services/cloudStorageService';
	import type { FileItem as FileItemType, FileUploadOptions } from '../types';
	
	export let files: FileItemType[] = [];
	export let options: FileUploadOptions = {};
	export let isDragging = false;
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	let fileInput: HTMLInputElement;
	
	async function handleFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files) {
			await processFiles(Array.from(input.files));
		}
		// Reset input
		input.value = '';
	}
	
	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
		
		if (event.dataTransfer?.files) {
			await processFiles(Array.from(event.dataTransfer.files));
		}
	}
	
	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		isDragging = true;
	}
	
	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
	}
	
	async function processFiles(fileList: File[]) {
		for (const file of fileList) {
			// Validate file type
			if (!validateFileType(file, options.acceptedTypes)) {
				toast.error($i18n.t('File type not supported: {{type}}', { type: file.type }));
				continue;
			}
			
			// Process file
			const processedFile = await processFile(file, options);
			if (processedFile) {
				dispatch('fileAdd', processedFile);
			}
		}
	}
	
	async function handleGoogleDrive() {
		const cloudFile = await cloudStorageService.pickFromGoogleDrive();
		if (cloudFile) {
			const file = await cloudStorageService.convertCloudFileToFile(cloudFile);
			await processFiles([file]);
		}
	}
	
	async function handleOneDrive() {
		const cloudFile = await cloudStorageService.pickFromOneDrive();
		if (cloudFile) {
			const file = await cloudStorageService.convertCloudFileToFile(cloudFile);
			await processFiles([file]);
		}
	}
	
	async function handleRemoveFile(fileId: string) {
		await removeFileUtil(fileId);
		dispatch('fileRemove', fileId);
	}
	
	function handlePaste(event: ClipboardEvent) {
		const items = event.clipboardData?.items;
		if (!items) return;
		
		const files: File[] = [];
		
		for (const item of items) {
			if (item.kind === 'file') {
				const file = item.getAsFile();
				if (file) {
					files.push(file);
				}
			}
		}
		
		if (files.length > 0) {
			event.preventDefault();
			processFiles(files);
		}
	}
</script>

<div
	class="relative w-full"
	on:drop={handleDrop}
	on:dragover={handleDragOver}
	on:dragleave={handleDragLeave}
	on:paste={handlePaste}
>
	<input
		bind:this={fileInput}
		type="file"
		multiple
		class="hidden"
		accept={options.acceptedTypes?.join(',')}
		on:change={handleFileSelect}
	/>
	
	{#if files.length > 0}
		<FilesOverlay
			{files}
			on:remove={(e) => handleRemoveFile(e.detail)}
		/>
	{/if}
	
	{#if isDragging}
		<div class="absolute inset-0 bg-blue-500 bg-opacity-20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center z-50">
			<div class="text-blue-600 dark:text-blue-400 font-medium">
				{$i18n.t('Drop files here')}
			</div>
		</div>
	{/if}
	
	<slot {fileInput} {handleGoogleDrive} {handleOneDrive} />
</div>