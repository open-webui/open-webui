<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { chapters, loadChapters, currentNovel, swLoading } from '$lib/stores/sw';
	import ChapterSidebar from '$lib/components/storyweaver/ChapterSidebar.svelte';
	import ChapterEditor from '$lib/components/storyweaver/ChapterEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let novelId = $page.params.id;
	let selectedChapterId = null;

	$: activeChapter = $chapters.find((c) => c.id === selectedChapterId) || null;

	onMount(async () => {
		const token = localStorage.getItem('token');
		if (token) {
			await loadChapters(token, novelId);
			// Auto-select first chapter if any
			if ($chapters.length > 0) {
				selectedChapterId = [...$chapters].sort((a, b) => a.order - b.order)[0].id;
			}
		}
	});

	function handleSelect(id) {
		selectedChapterId = id;
	}
</script>

<div class="flex h-[calc(100vh-80px)] overflow-hidden rounded-xl border dark:border-gray-800 shadow-sm bg-white dark:bg-gray-950">
	<!-- Sidebar -->
	<div class="w-64 flex-none border-r dark:border-gray-800 h-full">
		<ChapterSidebar {novelId} {selectedChapterId} onSelect={handleSelect} />
	</div>

	<!-- Editor -->
	<div class="flex-1 h-full overflow-hidden">
		{#if activeChapter}
			<ChapterEditor chapter={activeChapter} onSelect={handleSelect} />
		{:else if $swLoading}
			<div class="flex items-center justify-center h-full">
				<Spinner />
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center h-full text-gray-400 dark:text-gray-600 gap-4">
				<div class="p-6 rounded-full bg-gray-50 dark:bg-gray-900">
					<span class="text-4xl text-gray-300 dark:text-gray-800">✍️</span>
				</div>
				<p class="text-sm font-medium">Sélectionnez ou créez un chapitre pour commencer à écrire.</p>
			</div>
		{/if}
	</div>
</div>

<style>
	/* Animation or focus styles if needed */
</style>
