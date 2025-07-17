<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import FileItem from '$lib/components/common/FileItem.svelte';
	import { PROGRESS_API_BASE_URL } from '$lib/constants';

	export let selectedFileId = null;
	export let files = [];
	export let small = false;

	$: {
		for (const file of files) {
			if (file.status === 'processing' && !file._sseConnected) {
				file._sseConnected = true;
				setTimeout(() => handleUploadComplete(file.id), 100);
			}
		}
	}
		
	function handleUploadComplete(fileId: string) {
		const source = new EventSource(`${PROGRESS_API_BASE_URL}/process/file/stream`);
		
		source.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				const index = files.findIndex(f => f.id === fileId);
				if (index !== -1) {
					const progress = 50 + Math.ceil(data.progress / 2);
					files[index].progress = progress;

					if (data.progress >= 100) {
						files[index].status = 'done';
						source.close();
					}

					// Force progress bar update
					files = [...files];
				}
			} catch (err) {
				console.error("Failed to parse SSE message:", err);
			}
		};

		source.onerror = (err) => {
			console.error("SSE error", err);
			source.close();
		};
	}
	
</script>


<div class=" max-h-full flex flex-col w-full">
	{#each files as file}
		<div class="mt-1 px-2">

			<FileItem
			
				className="w-full"
				colorClassName="{selectedFileId === file.id
					? ' bg-gray-50 dark:bg-gray-850'
					: 'bg-transparent'} hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				{small}
				item={file}
				name={file?.name ?? file?.meta?.name}
				type="file"
				size={file?.size ?? file?.meta?.size ?? ''}
				loading={file.status === 'uploading' || file.status === 'processing'}
				dismissible
				on:click={() => {
					if (file.status === 'uploading' || file.status === 'processing' ) {
						return;
					}
					dispatch('click', file.id);
				}}
				on:dismiss={() => {
					if (file.status === 'uploading') {
						if(file.xhr) {
							file.xhr.abort();
						}
						
						const e = {id: file.itemId, status: file.status}
						
						dispatch('delete', e);
						return;
					}else if(file.status === 'processing'){
						const e = {id: file.itemId, status: file.status}
						dispatch('delete', e);
						return;						
					}
					const e = {id: file.id, status: file.status}
					dispatch('delete', e);
				}}
			/>

				{#if file.status === 'uploading' || file.status === 'processing'}
					<div>
						<p>{file.status}</p>
					</div>
					<div class="w-full bg-gray-200 rounded-full h-2 mt-1">
						<div
							class="bg-blue-600 h-2 rounded-full transition-all duration-200 ease-out"
							style="width: {file.progress || 0}%;"
						></div>
					</div>
				{/if}

				{#if file.status === 'error'}
					<div class="text-xs text-red-500 mt-1">Upload failed</div>
				{/if}

		</div>
	{/each}
</div>
