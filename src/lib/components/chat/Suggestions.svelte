<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import { fly } from 'svelte/transition';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';

	// Randomize the prompt order once on component mount to keep animations consistent.
	let sortedPrompts = [];
	onMount(() => {
		sortedPrompts = [...(suggestionPrompts ?? [])].sort(() => Math.random() - 0.5);
	});

	// Configure Fuse.js for fuzzy search based on the prompt's content and title.
	const fuseOptions = {
		keys: ['content', 'title'],
		threshold: 0.5
	};

	// Create a new Fuse instance and compute the filtered list whenever sortedPrompts or inputValue changes.
	$: fuse = new Fuse(sortedPrompts, fuseOptions);
	$: filteredPrompts = inputValue.trim()
		? fuse.search(inputValue.trim()).map((result) => result.item)
		: sortedPrompts;
</script>

<!-- Suggestion header with icon; visibility is toggled based on available suggestions -->
<div
	class="mb-1 flex gap-1 text-sm font-medium items-center text-gray-400 dark:text-gray-600"
	style="visibility: {filteredPrompts.length > 0 ? 'visible' : 'hidden'}"
>
	<Bolt />
	{$i18n.t('Suggested')}
</div>

<!-- Scrollable container for the list of suggestions -->
<div class="h-40 overflow-auto scrollbar-none {className}">
	{#if filteredPrompts.length > 0}
		{#each filteredPrompts as prompt, idx (prompt.content)}
			<button
				in:fly={{ y: 10, delay: 50, duration: 200 }}
				class="flex flex-col flex-1 shrink-0 w-full justify-between px-3 py-2
					   rounded-xl bg-transparent hover:bg-black/5 dark:hover:bg-white/5
					   transition group"
				on:click={() => dispatch('select', prompt.content)}
			>
				<div class="flex flex-col text-left">
					{#if prompt.title && prompt.title[0] !== ''}
						<!-- Render the title if available -->
						<div
							class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
						>
							{prompt.title[0]}
						</div>
						<div class="text-xs text-gray-500 font-normal line-clamp-1">
							{prompt.title[1]}
						</div>
					{:else}
						<!-- Fallback to rendering the prompt content -->
						<div
							class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
						>
							{prompt.content}
						</div>
						<div class="text-xs text-gray-500 font-normal line-clamp-1">Prompt</div>
					{/if}
				</div>
			</button>
		{/each}
	{:else}
		<!-- Empty state: optionally, a message could be rendered here -->
	{/if}
</div>
