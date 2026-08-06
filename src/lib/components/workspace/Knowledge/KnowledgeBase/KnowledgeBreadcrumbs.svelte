<script lang="ts">
	import { afterUpdate, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let rootLabel: string = 'Root';
	export let breadcrumbs: { id: string; name: string }[] = [];
	export let onNavigate: (directoryId: string | null) => void = () => {};
	export let onMoveFile: (fileId: string, targetDirectoryId: string | null) => void = () => {};
	export let onMoveDir: (dirId: string, targetDirectoryId: string | null) => void = () => {};

	let breadcrumbEl: HTMLDivElement;
	let dragOverCrumb: number | null = null;

	afterUpdate(() => {
		if (breadcrumbEl) breadcrumbEl.scrollLeft = breadcrumbEl.scrollWidth;
	});

	const handleDragOver = (e: DragEvent, index: number) => {
		const hasFile = e.dataTransfer?.types.includes('application/x-kb-file-move');
		const hasDir = e.dataTransfer?.types.includes('application/x-kb-dir-move');
		if (!hasFile && !hasDir) return;
		e.preventDefault();
		e.stopPropagation();
		dragOverCrumb = index;
	};

	const handleDragLeave = (index: number) => {
		if (dragOverCrumb === index) dragOverCrumb = null;
	};

	const handleDrop = (e: DragEvent, targetDirId: string | null) => {
		e.preventDefault();
		e.stopPropagation();
		dragOverCrumb = null;
		const fileRaw = e.dataTransfer?.getData('application/x-kb-file-move');
		if (fileRaw) {
			try {
				const data = JSON.parse(fileRaw);
				if (data.fileId) onMoveFile(data.fileId, targetDirId);
			} catch {}
			return;
		}
		const dirRaw = e.dataTransfer?.getData('application/x-kb-dir-move');
		if (dirRaw) {
			try {
				const data = JSON.parse(dirRaw);
				if (data.dirId) onMoveDir(data.dirId, targetDirId);
			} catch {}
		}
	};
</script>

<div
	bind:this={breadcrumbEl}
	class="flex items-center flex-1 min-w-0 overflow-x-auto scrollbar-none"
>
	<button
		class="text-xs shrink-0 py-0.5 hover:underline transition
			{breadcrumbs.length === 0
			? 'text-gray-700 dark:text-gray-300'
			: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}
			{dragOverCrumb === -1 ? 'bg-gray-100 dark:bg-gray-800 rounded-lg' : ''}"
		on:click={() => onNavigate(null)}
		on:dragover={(e) => handleDragOver(e, -1)}
		on:dragleave={() => handleDragLeave(-1)}
		on:drop={(e) => handleDrop(e, null)}
	>
		{rootLabel}
	</button>

	{#each breadcrumbs as crumb, i}
		<ChevronRight className="size-3 shrink-0 mx-0.5 text-gray-300 dark:text-gray-600" />
		<button
			class="text-xs shrink-0 py-0.5 hover:underline transition
				{i === breadcrumbs.length - 1
				? 'text-gray-700 dark:text-gray-300'
				: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}
				{dragOverCrumb === i ? 'bg-gray-100 dark:bg-gray-800 rounded-lg' : ''}"
			on:click={() => onNavigate(crumb.id)}
			on:dragover={(e) => handleDragOver(e, i)}
			on:dragleave={() => handleDragLeave(i)}
			on:drop={(e) => handleDrop(e, crumb.id)}
		>
			{crumb.name}
		</button>
	{/each}
</div>
