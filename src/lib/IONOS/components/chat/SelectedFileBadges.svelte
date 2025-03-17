<!-- Extracted from Open WebUI's MessageInput.svelte -->

<script lang="ts">
	import { deleteFileById } from '$lib/apis/files';
	import FileItem from '$lib/components/common/FileItem.svelte';

	export let files = [];
</script>

<div class="mx-1 mt-2.5 mb-1 flex items-center flex-wrap gap-2">
	{#each files as file, fileIdx}
		<FileItem
			item={file}
			name={file.name}
			type={file.type}
			size={file?.size}
			loading={file.status === 'uploading'}
			dismissible={true}
			edit={true}
			on:dismiss={async () => {
				if (file.type !== 'collection' && !file?.collection) {
					if (file.id) {
						// This will handle both file deletion and Chroma cleanup
						await deleteFileById(localStorage.token, file.id);
					}
				}

				// Remove from UI state
				files.splice(fileIdx, 1);
				files = files;
			}}
			on:click={() => {
				console.log(file);
			}}
		/>
	{/each}
</div>
