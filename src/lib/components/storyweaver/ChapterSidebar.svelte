<script lang="ts">
	import { chapters, addChapter, removeChapter, reorderChaptersAction, swLoading } from '$lib/stores/sw';
	import { getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Plus, Trash2, GripVertical } from 'lucide-svelte';
	import Sortable from 'sortablejs';

	const i18n = getContext('i18n');

	export let novelId: string;
	export let selectedChapterId: string | null = null;
	export let onSelect: (id: string) => void;

	let container: HTMLElement;
	let sortable: Sortable;

	$: sortedChapters = [...$chapters].sort((a, b) => a.order - b.order);

	onMount(() => {
		sortable = new Sortable(container, {
			animation: 150,
			handle: '.drag-handle',
			onEnd: async (evt) => {
				const token = localStorage.getItem('token');
				if (!token) return;

				const orderedIds = Array.from(container.children).map((el) => el.getAttribute('data-id'));
				await reorderChaptersAction(token, novelId, orderedIds);
			}
		});
	});

	async function handleAddChapter() {
		const token = localStorage.getItem('token');
		if (!token) return;

		const nextOrder = sortedChapters.length > 0 ? Math.max(...sortedChapters.map((c) => c.order)) + 1 : 0;
		const newChapter = await addChapter(token, novelId, {
			title: `Chapitre ${sortedChapters.length + 1}`,
			order: nextOrder
		});

		if (newChapter) {
			toast.success('Chapitre ajouté');
			onSelect(newChapter.id);
		}
	}

	async function handleDeleteChapter(id: string) {
		if (!confirm('Voulez-vous vraiment supprimer ce chapitre ?')) return;
		const token = localStorage.getItem('token');
		if (!token) return;

		const success = await removeChapter(token, id);
		if (success) {
			toast.success('Chapitre supprimé');
			if (selectedChapterId === id) {
				selectedChapterId = null;
			}
		}
	}
</script>

<div class="flex flex-col h-full bg-gray-50 dark:bg-gray-900 overflow-hidden border-r dark:border-gray-800">
	<div class="p-4 flex justify-between items-center border-b dark:border-gray-800 bg-white dark:bg-gray-950">
		<h2 class="font-bold text-lg dark:text-gray-100">Sommaire</h2>
		<button
			class="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
			on:click={handleAddChapter}
			title="Nouveau chapitre"
		>
			<Plus size={18} />
		</button>
	</div>

	<div class="flex-1 overflow-y-auto p-2" bind:this={container}>
		{#each sortedChapters as chapter (chapter.id)}
			<div
				data-id={chapter.id}
				class="group flex items-center gap-2 p-2 mb-1 rounded-lg border transition-all cursor-pointer {selectedChapterId ===
				chapter.id
					? 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800'
					: 'bg-white dark:bg-gray-850 border-transparent hover:border-gray-200 dark:hover:border-gray-700'}"
				on:click={() => onSelect(chapter.id)}
			>
				<button class="drag-handle cursor-grab active:cursor-grabbing text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
					<GripVertical size={16} />
				</button>

				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium truncate dark:text-gray-200">
						{chapter.title || 'Sans titre'}
					</p>
					<p class="text-xs text-gray-500 dark:text-gray-400 capitalize">
						{chapter.status || 'draft'}
					</p>
				</div>

				<button
					class="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
					on:click|stopPropagation={() => handleDeleteChapter(chapter.id)}
				>
					<Trash2 size={14} />
				</button>
			</div>
		{/each}

		{#if sortedChapters.length === 0}
			<div class="text-center py-8 text-gray-500 dark:text-gray-400 italic text-sm">
				Aucun chapitre.
			</div>
		{/if}
	</div>
</div>
