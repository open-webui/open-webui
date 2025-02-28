<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import FileItem from '$lib/components/common/FileItem.svelte';

	interface Props {
		selectedFileId?: any;
		files?: any;
		small?: boolean;
	}

	let { selectedFileId = null, files = [], small = false }: Props = $props();
</script>

<div class=" max-h-full flex flex-col w-full">
	{#each files as file}
		<div class="mt-1 px-2">
			<FileItem
				name={file?.name ?? file?.meta?.name}
				className="w-full"
				colorClassName="{selectedFileId === file.id
					? ' bg-gray-50 dark:bg-gray-850'
					: 'bg-transparent'} hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				dismissible
				item={file}
				loading={file.status === 'uploading'}
				size={file?.size ?? file?.meta?.size ?? ''}
				{small}
				type="file"
				on:click={() => {
					if (file.status === 'uploading') {
						return;
					}

					dispatch('click', file.id);
				}}
				on:dismiss={() => {
					if (file.status === 'uploading') {
						return;
					}

					dispatch('delete', file.id);
				}}
			/>
		</div>
	{/each}
</div>
