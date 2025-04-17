<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import UploadIcon from '$lib/components/icons/UploadIcon.svelte';

	export let uploadFileHandler;

	let inputFiles: FileList | null = null;
	let isDragging = false;
	let uploading = false;

	const i18n = getContext('i18n');

	async function handleFiles(files: FileList | File[]) {
		if (!files || files.length === 0) {
			toast.error($i18n.t(`File not found.`));
			return;
		}
		uploading = true;
		await Promise.all([...files].map(uploadFileHandler));
		uploading = false;
	}
</script>

<div
	class={`w-full border-2 dark:bg-customGray-900/50 border-dashed h-[100px] rounded-md px-4 py-8 text-center cursor-pointer transition ${
		isDragging
			? 'border-customViolet-300 bg-blue-50 dark:bg-customGray-950'
			: 'border-gray-300 dark:border-[#0F0F0F]'
	}`}
	on:click={() => document.getElementById('files-input')?.click()}
	on:dragenter|preventDefault={() => (isDragging = true)}
	on:dragover|preventDefault={() => (isDragging = true)}
	on:dragleave|preventDefault={() => (isDragging = false)}
	on:drop|preventDefault={(e) => {
		isDragging = false;
		if (e.dataTransfer?.files?.length) {
			handleFiles(e.dataTransfer.files);
		}
	}}
>
	{#if uploading}
		<div class="flex flex-col items-center text-xs text-gray-600 dark:text-customGray-100/50">
			<div class="h-[16px]"></div>
			{$i18n.t('Uploading...')}
		</div>
	{:else}
		<div class="flex flex-col items-center text-xs text-gray-600 dark:text-customGray-100/50">
			<UploadIcon />
			<p>
				{$i18n.t('Upload Files')}
			</p>
		</div>
	{/if}
</div>

<input
	id="files-input"
	bind:files={inputFiles}
	type="file"
	multiple
	hidden
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			await handleFiles(inputFiles);
			inputFiles = null;
		} else {
			toast.error($i18n.t(`File not found.`));
		}
	}}
/>
