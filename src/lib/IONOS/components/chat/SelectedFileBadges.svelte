<!-- Extracted from Open WebUI's MessageInput.svelte -->

<script lang="ts">
	import { deleteFileById } from '$lib/apis/files';
	import FileItem from '$lib/IONOS/components/common/FileItem.svelte';

	export let files = [];
</script>

<div class="mx-1 h-full flex items-center flex-wrap gap-2">
	{#each files as file, fileIdx}
		<FileItem
			item={file}
			name={file.name}
			type={file.type}
			size={file?.size}
			small={true}
			className="px-1 py-1 rounded-full"
			colorClassName="bg-blue-100 text-blue-500"
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
