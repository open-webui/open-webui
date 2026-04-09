<script lang="ts">
	import { activeKB, swLoading } from '$lib/stores/sw';
	import { Search, ExternalLink, X, User, MapPin, Sword, Calendar, Book } from 'lucide-svelte';
	import { slide } from 'svelte/transition';

	let searchQuery = '';
	let searchResults = [];

	$: {
		if (!$activeKB || searchQuery.trim() === '') {
			searchResults = [];
		} else {
			const query = searchQuery.toLowerCase();
			const results = [];

			const sections = [
				{ id: 'universe_docs', icon: Book, label: 'Univers' },
				{ id: 'characters', icon: User, label: 'Personnage' },
				{ id: 'locations', icon: MapPin, label: 'Lieu' },
				{ id: 'objects', icon: Sword, label: 'Objet' },
				{ id: 'timeline', icon: Calendar, label: 'Éphéméride' }
			];

			sections.forEach((section) => {
				const items = $activeKB[section.id] || [];
				items.forEach((item) => {
					// Search in all fields
					const content = JSON.stringify(item).toLowerCase();
					if (content.includes(query)) {
						results.push({
							...item,
							sectionLabel: section.label,
							sectionIcon: section.icon
						});
					}
				});
			});

			searchResults = results;
		}
	}

	function getItemTitle(item) {
		return item.name || item.title || item.tag || 'Sans nom';
	}

	function getItemPrimaryInfo(item) {
		return item.description || item.content || item.traits || item.details || '';
	}
</script>

<div class="flex flex-col h-full bg-gray-50 dark:bg-gray-900 border-l dark:border-gray-800 w-[350px]">
	<div class="p-4 border-b dark:border-gray-800 bg-white dark:bg-gray-950">
		<div class="flex items-center justify-between mb-4">
			<h3 class="font-bold text-sm dark:text-gray-100 uppercase tracking-wider">Recherche KB</h3>
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 cursor-pointer">
				<Search size={16} />
			</div>
		</div>

		<div class="relative">
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Rechercher partout..."
				class="w-full pl-9 pr-4 py-2 bg-gray-100 dark:bg-gray-800 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none dark:text-gray-200"
			/>
			<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
				<Search size={14} />
			</div>
			{#if searchQuery}
				<button
					class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
					on:click={() => (searchQuery = '')}
				>
					<X size={14} />
				</button>
			{/if}
		</div>
	</div>

	<div class="flex-1 overflow-y-auto p-4 custom-scrollbar">
		{#if searchQuery.trim() === ''}
			<div class="flex flex-col items-center justify-center h-40 text-gray-400 text-center gap-2">
				<Book size={32} strokeWidth={1} />
				<p class="text-xs">Saisissez un mot-clé pour lancer une recherche globale dans votre Knowledge Base.</p>
			</div>
		{:else if searchResults.length === 0}
			<div class="text-center py-8 text-gray-500 text-sm">Aucun résultat trouvé pour "{searchQuery}".</div>
		{:else}
			<div class="space-y-3">
				{#each searchResults as item (item.id)}
					<div
						class="p-3 bg-white dark:bg-gray-850 rounded-xl border border-transparent hover:border-blue-200 dark:hover:border-blue-900 shadow-sm transition-all group"
						transition:slide
					>
						<div class="flex items-start justify-between mb-1">
							<div class="flex items-center gap-2">
								<svelte:component this={item.sectionIcon} size={14} class="text-blue-500" />
								<span class="text-[10px] font-bold uppercase text-gray-400 tracking-tighter">{item.sectionLabel}</span>
							</div>
						</div>
						<h4 class="text-sm font-bold dark:text-gray-100 mb-1">{getItemTitle(item)}</h4>
						<p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-3 leading-relaxed">
							{getItemPrimaryInfo(item)}
						</p>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: #8884;
		border-radius: 10px;
	}
</style>
