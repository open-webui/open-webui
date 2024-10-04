<script lang="ts">
	import FileItem from '$lib/components/common/FileItem.svelte';

	export let files = [];
</script>

<div class=" max-h-full flex flex-col w-full">
	{#each files as file (file.id)}
		<div class="mt-2 px-2">
			<FileItem
				className="w-full"
				colorClassName="bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				{file}
				name={file.meta.name}
				type="file"
				dismissible
			/>
		</div>
	{/each}
</div>
