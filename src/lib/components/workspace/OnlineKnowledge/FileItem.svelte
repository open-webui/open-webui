<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import Document from '../../icons/Document.svelte';
	import ItemMenu from './ItemMenu.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let file: {
		id: string;
		folderId: string;
		name: string;
		size: number;
		type: string;
		content: string | null;
		createdAt: number;
	};
	export let viewMode: 'list' | 'grid' = 'list';
	export let formatFileSize: (bytes: number) => string;

	// Get file type info
	const getFileTypeInfo = (mimeType: string): { color: string; label: string } => {
		if (mimeType === 'application/pdf') {
			return { color: 'bg-error-100 dark:bg-error-500/20 text-error-500', label: 'PDF' };
		}
		if (mimeType === 'text/plain') {
			return { color: 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400', label: 'TXT' };
		}
		if (mimeType === 'text/csv') {
			return { color: 'bg-success-100 dark:bg-success-500/20 text-success-500', label: 'CSV' };
		}
		if (mimeType.startsWith('image/')) {
			return { color: 'bg-primary-100 dark:bg-primary-500/20 text-primary-500', label: 'IMG' };
		}
		return { color: 'bg-gray-100 dark:bg-gray-700 text-gray-500', label: 'FILE' };
	};

	$: fileTypeInfo = getFileTypeInfo(file.type);

	// Get file extension
	const getFileExtension = (filename: string): string => {
		const parts = filename.split('.');
		return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : '';
	};
</script>

{#if viewMode === 'list'}
	<button
		class="flex items-center w-full px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-850/50 rounded-2xl transition group"
		on:click={() => dispatch('click', file)}
	>
		<!-- File Icon -->
		<div class="size-12 shrink-0 flex justify-center items-center {fileTypeInfo.color} rounded-xl mr-3 relative">
			<Document className="size-6" />
			{#if getFileExtension(file.name)}
				<span class="absolute bottom-1 text-[8px] font-bold">{getFileExtension(file.name)}</span>
			{/if}
		</div>

		<!-- File Info -->
		<div class="flex-1 min-w-0 text-left">
			<div class="font-medium text-sm truncate text-gray-900 dark:text-white">{file.name}</div>
			<div class="text-xs text-gray-500">
				{formatFileSize(file.size)}
			</div>
		</div>

		<!-- Menu -->
		<div class="opacity-0 group-hover:opacity-100 transition-opacity" on:click|stopPropagation>
			<ItemMenu
				on:delete={() => dispatch('delete', file)}
			/>
		</div>
	</button>
{:else}
	<!-- Grid View -->
	<button
		class="flex flex-col items-center p-4 hover:bg-gray-50 dark:hover:bg-gray-850/50 rounded-2xl transition group relative"
		on:click={() => dispatch('click', file)}
	>
		<!-- Menu Button (absolute positioned) -->
		<div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity" on:click|stopPropagation>
			<ItemMenu
				on:delete={() => dispatch('delete', file)}
			/>
		</div>

		<!-- File Icon / Preview -->
		{#if file.type.startsWith('image/') && file.content}
			<div class="size-16 shrink-0 rounded-xl mb-2 overflow-hidden bg-gray-100 dark:bg-gray-800">
				<img src={file.content} alt={file.name} class="w-full h-full object-cover" />
			</div>
		{:else}
			<div class="size-16 shrink-0 flex flex-col justify-center items-center {fileTypeInfo.color} rounded-xl mb-2">
				<Document className="size-6" />
				{#if getFileExtension(file.name)}
					<span class="text-[8px] font-bold mt-0.5">{getFileExtension(file.name)}</span>
				{/if}
			</div>
		{/if}

		<!-- File Info -->
		<div class="w-full text-center">
			<div class="font-medium text-sm truncate text-gray-900 dark:text-white">{file.name}</div>
			<div class="text-xs text-gray-500">
				{formatFileSize(file.size)}
			</div>
		</div>
	</button>
{/if}
