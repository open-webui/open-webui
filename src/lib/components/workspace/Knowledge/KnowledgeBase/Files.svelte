<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import FileItem from '$lib/components/common/FileItem.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let selectedFileId = null;
	export let files = [];

	export let small = false;
	export let loading = false;
	export let hasMore = false;
	export let scrollContainer: HTMLElement | null = null;
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
				loading={file.status === 'uploading'}
				dismissible
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

	{#if hasMore}
		<Loader
			{scrollContainer}
			on:visible={(e) => {
				if (!loading) {
					dispatch('loadmore');
				}
			}}
		>
			<div class="w-full flex justify-center py-2 text-xs animate-pulse items-center gap-2">
				<Spinner className="size-4" />
				<div>Loading more files...</div>
			</div>
		</Loader>
	{/if}
</div>
