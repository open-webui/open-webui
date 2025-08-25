<script lang="ts">
	import { onMount, getContext, setContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, functions, config, user, showArchivedChats } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { writable } from 'svelte/store';
	import { page } from '$app/stores';
	import { getNotePlusCategoryTree, getNotePlusByCategory, getNotePlusById } from '$lib/apis/noteplus';

	import CategoryTree from '$lib/components/noteplus/CategoryTree.svelte';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';
	import ArrowRight from '$lib/components/icons/ArrowRight.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let categorySearchQuery = '';

	// Create stores to persist state across page navigation
	const showCategoryPane = writable(true);
	const categoryTree = writable({});
	const selectedCategory = writable(null);
	const relatedNotes = writable([]);

	// Share stores with child components via context
	setContext('noteplus', {
		showCategoryPane,
		categoryTree,
		selectedCategory,
		relatedNotes
	});

	// Local variables for reactive statements
	let localShowCategoryPane = true;
	let localCategoryTree = {};
	let localSelectedCategory = null;
	let localRelatedNotes = [];

	// Subscribe to stores
	$: localShowCategoryPane = $showCategoryPane;
	$: localCategoryTree = $categoryTree;
	$: localSelectedCategory = $selectedCategory;
	$: localRelatedNotes = $relatedNotes;

	const loadRelatedNotes = async () => {
		if (!localSelectedCategory) {
			relatedNotes.set([]);
			return;
		}

		try {
			// Parse selected category - handle both object and string formats
			let major = null;
			let middle = null;
			let minor = null;
			
			if (typeof localSelectedCategory === 'object') {
				major = localSelectedCategory.major || null;
				middle = localSelectedCategory.middle || null;
				minor = localSelectedCategory.minor || null;
			} else if (typeof localSelectedCategory === 'string') {
				const parts = localSelectedCategory.split('/');
				major = parts[0] || null;
				middle = parts[1] || null;
				minor = parts[2] || null;
			}

			// Fetch notes for selected category
			const notes = await getNotePlusByCategory(localStorage.token, major, middle, minor);
			
			// Filter out current note if in edit mode
			const currentNoteId = $page.params.id;
			const filteredNotes = currentNoteId ? notes.filter(note => note.id !== currentNoteId) : notes;
			relatedNotes.set(filteredNotes);
		} catch (error) {
			console.error('Failed to load related notes:', error);
			relatedNotes.set([]);
		}
	};

	onMount(async () => {
		if (
			!(
				($config?.features?.enable_noteplus ?? false) &&
				($user?.role === 'admin' || ($user?.permissions?.features?.noteplus ?? true))
			)
		) {
			// If the feature is not enabled, redirect to the home page
			goto('/');
		}

		loaded = true;

		// Load category tree
		try {
			const tree = await getNotePlusCategoryTree(localStorage.token);
			categoryTree.set(tree);
		} catch (error) {
			console.error('Failed to load category tree:', error);
		}
	});

	// React to page changes to update selected category
	$: if (loaded && $page.params.id && $page.params.id !== 'create') {
		// Auto-select category based on current note
		getNotePlusById(localStorage.token, $page.params.id)
			.then(currentNote => {
				if (currentNote) {
					const categoryPath = [];
					if (currentNote.category_major) categoryPath.push(currentNote.category_major);
					if (currentNote.category_middle) categoryPath.push(currentNote.category_middle);
					if (currentNote.category_minor) categoryPath.push(currentNote.category_minor);
					
					if (categoryPath.length > 0) {
						selectedCategory.set(categoryPath.join('/'));
						loadRelatedNotes();
					}
				}
			})
			.catch(error => {
				console.error('Failed to load note for category:', error);
			});
	}
</script>

<svelte:head>
	<title>
		{$i18n.t('Notes+')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div class="w-full h-full flex {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''}">
		<PaneGroup direction="horizontal" class="w-full h-full">
			{#if localShowCategoryPane}
				<Pane defaultSize={20} minSize={15} maxSize={30} class="h-full bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
					<div class="h-full flex flex-col">
						<!-- Action Bar -->
						<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-800">
							<div class="flex items-center justify-between mb-2">
								<h3 class="text-sm font-medium">{$i18n.t('Note+')}</h3>
								<button
									class="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded transition-colors"
									on:click={() => {
										showCategoryPane.set(false);
									}}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
										<path fill-rule="evenodd" d="M15.79 14.77a.75.75 0 01-1.06.02l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 111.04 1.08L11.832 10l3.938 3.71a.75.75 0 01.02 1.06z" clip-rule="evenodd" />
									</svg>
								</button>
							</div>
							<!-- New Note Button -->
							<button
								class="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
								on:click={async () => {
									const { createNewNotePlus } = await import('$lib/apis/noteplus');
									const dayjs = (await import('$lib/dayjs')).default;
									
									// Parse selected category if provided
									let major = 'General';
									let middle = 'Notes';
									let minor = 'Default';
									
									if (localSelectedCategory && typeof localSelectedCategory === 'object') {
										if (localSelectedCategory.major) major = localSelectedCategory.major;
										if (localSelectedCategory.middle) middle = localSelectedCategory.middle;
										if (localSelectedCategory.minor) minor = localSelectedCategory.minor;
									} else if (localSelectedCategory && typeof localSelectedCategory === 'string') {
										const parts = localSelectedCategory.split('/');
										if (parts[0]) major = parts[0];
										if (parts[1]) middle = parts[1];
										if (parts[2]) minor = parts[2];
									}
									
									const res = await createNewNotePlus(localStorage.token, {
										title: dayjs().format('YYYY-MM-DD'),
										data: {
											content: {
												json: {},
												html: '',
												md: ''
											}
										},
										category_major: major,
										category_middle: middle,
										category_minor: minor,
										meta: null,
										access_control: {}
									}).catch((error) => {
										console.error('Failed to create note:', error);
										return null;
									});
								
									if (res) {
										// Dispatch event for category tree refresh
										window.dispatchEvent(new CustomEvent('noteplus:created'));
										goto(`/noteplus/${res.id}`);
									}
								}}
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
									<path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
								</svg>
								{$i18n.t('New Note+')}
							</button>
						</div>
						
						<div class="flex-1 overflow-y-auto">
							<!-- Search Bar -->
							<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-800">
								<div class="flex items-center gap-2">
									<div class="relative flex-1">
										<input
											type="text"
											placeholder={$i18n.t('Search categories...')}
											class="w-full px-8 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
											bind:value={categorySearchQuery}
										/>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">
											<path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
										</svg>
										{#if categorySearchQuery}
											<button
												class="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition"
												on:click={() => {
													categorySearchQuery = '';
												}}
											>
												<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
													<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
												</svg>
											</button>
										{/if}
									</div>
									<!-- Refresh Button -->
									<button
										class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 transition"
										title={$i18n.t('Refresh categories')}
										on:click={async () => {
											const tree = await getNotePlusCategoryTree(localStorage.token);
											categoryTree.set(tree);
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
											<path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
										</svg>
									</button>
								</div>
						</div>
							
							<!-- Categories Tree -->
							<div class="p-3">
								<CategoryTree 
									categoryTree={localCategoryTree}
									selectedCategory={localSelectedCategory}
									searchQuery={categorySearchQuery}
									on:select={async (e) => {
										selectedCategory.set(e.detail);
										await loadRelatedNotes();
									}}
								/>
							</div>
							
							<!-- Related Notes Section -->
							{#if localRelatedNotes.length > 0}
								<div class="px-3 pb-3">
									<h4 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
										{$i18n.t('Related Notes')}
									</h4>
									<div class="space-y-1">
										{#each localRelatedNotes as note}
											<button
												class="w-full text-left px-2 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors {$page.params.id === note.id ? 'bg-gray-100 dark:bg-gray-800' : ''}"
												on:click={() => {
													goto(`/noteplus/${note.id}`);
												}}
											>
												<div class="truncate font-medium">
													{note.title || $i18n.t('Untitled')}
												</div>
												<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
													{new Date(note.updated_at / 1000000).toLocaleDateString()}
												</div>
											</button>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</Pane>
				
				<PaneResizer class="relative">
					<div
						class="z-10 absolute -left-[0.1rem] top-[50%] text-gray-400 transition rounded-full bg-gray-50 dark:bg-gray-850"
					>
						<ArrowRight className="size-[0.7rem]" strokeWidth="4" />
					</div>
				</PaneResizer>
			{:else}
				<!-- Collapsed sidebar toggle -->
				<div class="flex items-start pt-2 pl-1 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
					<button
						class="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded transition-colors"
						on:click={() => {
							showCategoryPane.set(true);
						}}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
						</svg>
					</button>
				</div>
			{/if}
			
			<!-- Main content area -->
			<Pane class="h-full overflow-hidden">
				<slot />
			</Pane>
		</PaneGroup>
	</div>
{/if}