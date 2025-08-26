<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { getNotePlusCategoryTree } from '$lib/apis/noteplus';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Folder from '../icons/Folder.svelte';
	import FolderOpen from '../icons/FolderOpen.svelte';
	import Document from '../icons/Document.svelte';
	import { createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let selectedCategory = null;
	export let searchQuery = '';

	let categoryTree = {};
	let expandedCategories = new Set(['General']); // 기본으로 General 카테고리 열기
	let isLoading = false;
	let totalNoteCount = 0;
	
	// Filter categories based on search query
	function filterCategories(tree, query) {
		if (!query) return tree;
		
		const lowerQuery = query.toLowerCase();
		const filtered = {};
		
		for (const [majorName, majorCategory] of Object.entries(tree)) {
			if (majorName.toLowerCase().includes(lowerQuery)) {
				// Include entire major category if name matches
				filtered[majorName] = majorCategory;
				expandedCategories.add(majorName);
			} else if (majorCategory.children) {
				// Check middle categories
				const filteredMiddle = {};
				for (const [middleName, middleCategory] of Object.entries(majorCategory.children)) {
					if (middleName.toLowerCase().includes(lowerQuery)) {
						filteredMiddle[middleName] = middleCategory;
						expandedCategories.add(majorName);
						expandedCategories.add(`${majorName}/${middleName}`);
					} else if (middleCategory.children) {
						// Check minor categories
						const filteredMinor = {};
						for (const [minorName, minorCategory] of Object.entries(middleCategory.children)) {
							if (minorName.toLowerCase().includes(lowerQuery)) {
								filteredMinor[minorName] = minorCategory;
								expandedCategories.add(majorName);
								expandedCategories.add(`${majorName}/${middleName}`);
							}
						}
						if (Object.keys(filteredMinor).length > 0) {
							filteredMiddle[middleName] = {
								...middleCategory,
								children: filteredMinor
							};
						}
					}
				}
				if (Object.keys(filteredMiddle).length > 0) {
					filtered[majorName] = {
						...majorCategory,
						children: filteredMiddle
					};
				}
			}
		}
		
		return filtered;
	}
	
	$: filteredTree = filterCategories(categoryTree, searchQuery);

	const toggleCategory = (path) => {
		if (expandedCategories.has(path)) {
			expandedCategories.delete(path);
		} else {
			expandedCategories.add(path);
		}
		expandedCategories = expandedCategories;
	};

	const selectCategory = (category) => {
		// Check if we're currently in a noteplus document page
		if ($page.route.id?.includes('/noteplus/[id]')) {
			// Navigate to noteplus list page with selected category
			// Store the selected category in sessionStorage to be used by the list page
			if (category) {
				sessionStorage.setItem('noteplus_selected_category', JSON.stringify(category));
			} else {
				sessionStorage.removeItem('noteplus_selected_category');
			}
			goto('/noteplus');
		} else {
			// We're already on the list page, just update the selection
			selectedCategory = category;
			dispatch('select', category);
		}
	};

	const init = async () => {
		isLoading = true;
		try {
			categoryTree = await getNotePlusCategoryTree(localStorage.token);
			console.log('Category tree loaded:', categoryTree);
			
			// Calculate total note count
			totalNoteCount = 0;
			for (const majorCategory of Object.values(categoryTree)) {
				totalNoteCount += majorCategory.note_count || 0;
			}
		} catch (error) {
			console.error('Failed to load category tree:', error);
			// 기본 카테고리 구조
			categoryTree = {
				'General': {
					note_count: 0,
					children: {
						'Notes': {
							note_count: 0,
							children: {
								'Default': {
									note_count: 0
								}
							}
						}
					}
				}
			};
			totalNoteCount = 0;
		} finally {
			isLoading = false;
		}
	};

	// Refresh function that can be called externally
	export const refresh = async () => {
		await init();
	};

	// Event listeners for auto-refresh
	const handleNotePlusUpdate = () => {
		refresh();
	};

	onMount(() => {
		init();
		
		// Add event listeners for noteplus CRUD operations
		window.addEventListener('noteplus:created', handleNotePlusUpdate);
		window.addEventListener('noteplus:updated', handleNotePlusUpdate);
		window.addEventListener('noteplus:deleted', handleNotePlusUpdate);
	});

	onDestroy(() => {
		// Remove event listeners
		window.removeEventListener('noteplus:created', handleNotePlusUpdate);
		window.removeEventListener('noteplus:updated', handleNotePlusUpdate);
		window.removeEventListener('noteplus:deleted', handleNotePlusUpdate);
	});
</script>

<div class="h-full">
	<!-- All Notes -->
	<button
		class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition mb-1 {selectedCategory === null ? 'bg-blue-50 dark:bg-gray-800 border-l-2 border-blue-500' : ''}"
		on:click={() => selectCategory(null)}
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2 text-sm">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4 text-gray-500 dark:text-gray-400">
					<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
				</svg>
				<span class="text-gray-700 dark:text-gray-300 font-medium">{$i18n.t('All Notes')}</span>
			</div>
			<span class="text-xs text-gray-500 dark:text-gray-400">
				({totalNoteCount})
			</span>
		</div>
	</button>

	<!-- Category Tree -->
	<div class="space-y-1">
		{#each Object.entries(filteredTree) as [majorName, majorCategory]}
			<div class="mb-1">
				<!-- Major Category -->
				<div
					class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center justify-between {selectedCategory?.level === 'major' && selectedCategory?.name === majorName ? 'bg-blue-50 dark:bg-gray-800 border-l-2 border-blue-500' : ''}"
				>
					<button
						class="flex items-center gap-2 text-sm flex-1"
						on:click={() => selectCategory({
							level: 'major',
							major: majorName,
							name: majorName
						})}
					>
						<button
							class="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
							on:click|stopPropagation={() => toggleCategory(majorName)}
						>
							{#if expandedCategories.has(majorName)}
								<ChevronDown className="size-3.5 text-gray-500 dark:text-gray-400" />
							{:else}
								<ChevronRight className="size-3.5 text-gray-500 dark:text-gray-400" />
							{/if}
						</button>
						{#if expandedCategories.has(majorName)}
							<FolderOpen className="size-4 text-gray-500 dark:text-gray-400" />
						{:else}
							<Folder className="size-4 text-gray-500 dark:text-gray-400" />
						{/if}
						<span class="text-gray-700 dark:text-gray-300">{majorName}</span>
					</button>
					<span class="text-xs text-gray-500 dark:text-gray-400">
						({majorCategory.note_count})
					</span>
				</div>

				<!-- Middle Categories -->
				{#if expandedCategories.has(majorName) && majorCategory.children}
					<div class="ml-6">
						{#each Object.entries(majorCategory.children) as [middleName, middleCategory]}
							<div class="mb-1">
								<div
									class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center justify-between {selectedCategory?.level === 'middle' && selectedCategory?.name === middleName && selectedCategory?.major === majorName ? 'bg-blue-50 dark:bg-gray-800 border-l-2 border-blue-500' : ''}"
								>
									<button
										class="flex items-center gap-2 text-sm flex-1"
										on:click={() => selectCategory({
											level: 'middle',
											major: majorName,
											middle: middleName,
											name: middleName
										})}
									>
										<button
											class="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
											on:click|stopPropagation={() => toggleCategory(`${majorName}/${middleName}`)}
										>
											{#if expandedCategories.has(`${majorName}/${middleName}`)}
												<ChevronDown className="size-3.5 text-gray-500 dark:text-gray-400" />
											{:else}
												<ChevronRight className="size-3.5 text-gray-500 dark:text-gray-400" />
											{/if}
										</button>
										{#if expandedCategories.has(`${majorName}/${middleName}`)}
											<FolderOpen className="size-4 text-gray-500 dark:text-gray-400" />
										{:else}
											<Folder className="size-4 text-gray-500 dark:text-gray-400" />
										{/if}
										<span class="text-gray-700 dark:text-gray-300">{middleName}</span>
									</button>
									<span class="text-xs text-gray-500 dark:text-gray-400">
										({middleCategory.note_count})
									</span>
								</div>

								<!-- Minor Categories -->
								{#if expandedCategories.has(`${majorName}/${middleName}`) && middleCategory.children}
									<div class="ml-8">
										{#each Object.entries(middleCategory.children) as [minorName, minorCategory]}
											<button
												class="w-full text-left px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center justify-between {selectedCategory?.level === 'minor' && selectedCategory?.name === minorName && selectedCategory?.major === majorName && selectedCategory?.middle === middleName ? 'bg-blue-50 dark:bg-gray-800 border-l-2 border-blue-500' : ''}"
												on:click={() => selectCategory({
													level: 'minor',
													major: majorName,
													middle: middleName,
													minor: minorName,
													name: minorName
												})}
											>
												<div class="flex items-center gap-2 text-sm">
													<Folder className="size-4 text-gray-500 dark:text-gray-400" />
													<span class="text-gray-700 dark:text-gray-300">{minorName}</span>
												</div>
												<span class="text-xs text-gray-500 dark:text-gray-400">
													({minorCategory.note_count})
												</span>
											</button>
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>