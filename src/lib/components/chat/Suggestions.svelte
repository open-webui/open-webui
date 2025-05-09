<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';

	let sortedPrompts = [];

	const fuseOptions = {
		keys: ['content', 'title'],
		threshold: 0.5
	};

	let fuse;
	let filteredPrompts = [];

	// Initialize Fuse
	$: fuse = new Fuse(sortedPrompts, fuseOptions);

	// Update the filteredPrompts if inputValue changes
	$: getFilteredPrompts(inputValue);

	// Helper function to check if arrays are the same
	function arraysEqual(a, b) {
		if (a.length !== b.length) return false;
		for (let i = 0; i < a.length; i++) {
			if ((a[i].id ?? a[i].content) !== (b[i].id ?? b[i].content)) {
				return false;
			}
		}
		return true;
	}

	const getFilteredPrompts = (inputValue) => {
		if (inputValue.length > 500) {
			filteredPrompts = [];
		} else {
			const newFilteredPrompts =
				inputValue.trim() && fuse
					? fuse.search(inputValue.trim()).map((result) => result.item)
					: sortedPrompts;

			// Compare with the oldFilteredPrompts
			// If there's a difference, update array + version
			if (!arraysEqual(filteredPrompts, newFilteredPrompts)) {
				filteredPrompts = newFilteredPrompts;
			}
		}
	};

	// Add validation and transformation of input prompts
	$: {

		// Ensure prompts are in the correct format
		const formattedPrompts = suggestionPrompts.map((prompt) => {
			if (typeof prompt === 'string') {
				return { title: prompt, content: prompt };
			}
			return prompt;
		});

		// Filter out any invalid prompts
		sortedPrompts = formattedPrompts.filter((prompt) => prompt && (prompt.content || prompt.title));

	}
</script>

<div class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-400 dark:text-gray-600">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{/if}
</div>

<div class="h-40 overflow-auto scrollbar-none {className} items-start">
	{#if filteredPrompts.length > 0}
		{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)}
			<button
				class="waterfall flex flex-col flex-1 shrink-0 w-full justify-between
					   px-3 py-2 rounded-xl bg-transparent hover:bg-black/5
					   dark:hover:bg-white/5 transition group"
				style="animation-delay: {idx * 60}ms"
				on:click={() => {
					window._paq?.push(['trackEvent', 'Suggestions', 'Select', prompt.content]);
					dispatch('select', prompt.content);
				}}
			>
				<div class="flex flex-col text-left">
					{#if prompt.title}
						<div
							class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
						>
							{prompt.title}
						</div>
						<div class="text-xs text-gray-500 font-normal line-clamp-1">
							{prompt.content}
						</div>
					{:else}
						<div
							class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
						>
							{prompt.content}
						</div>
						<div class="text-xs text-gray-500 font-normal line-clamp-1">{$i18n.t('Prompt')}</div>
					{/if}
				</div>
			</button>
		{/each}
	{/if}
</div>

<style>
	/* Waterfall animation for the suggestions */
	@keyframes fadeInUp {
		0% {
			opacity: 0;
			transform: translateY(20px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.waterfall {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
	}
</style>
