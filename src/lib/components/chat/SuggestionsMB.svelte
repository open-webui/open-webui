<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { WEBUI_NAME, mobile } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';
	export let numberOfSuggestions = 5;
	export let numberOfSuggestionsMobile = 9;

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
	// Only increase version if something wirklich geändert hat
	$: getFilteredPrompts(inputValue);

	// Helper function to check if arrays are the same
	// (based on unique IDs oder content)
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
		}
		else if (inputValue.trim() === '') {
			// If inputValue is empty, show all prompts
			filteredPrompts = sortedPrompts.filter((prompt) => prompt.pin === true); // Only pinned prompts
		} else if (inputValue.length > 0) {
			const newFilteredPrompts = [
				...(inputValue.trim() && fuse
					? fuse.search(inputValue.trim()).map((result) => result.item)
					: sortedPrompts.filter((prompt) => !prompt.pin)), // Exclude already included pinned prompts
				...sortedPrompts.filter((prompt) => prompt.pin === true) // Always include pinned prompts
			];

			// Compare with the oldFilteredPrompts
			// If there's a difference, update array + version
			if (!arraysEqual(filteredPrompts, newFilteredPrompts)) {
				filteredPrompts = newFilteredPrompts;
			}
		}
	};

	$: if (suggestionPrompts) {
		sortedPrompts = [...(suggestionPrompts ?? [])].sort(() => Math.random() - 0.5);
		getFilteredPrompts(inputValue);
	}
</script>

<div class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-400 dark:text-gray-600">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{:else}
		<!-- Keine Vorschläge -->

		<div
			class="flex w-full text-center items-center justify-center self-start text-gray-400 dark:text-gray-600"
		>
			{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
		</div>
	{/if}
</div>

{#if !$mobile}
	<div class="h-40 overflow-auto scrollbar-none {className} flex flex-wrap gap-2 items-start">
		{#if filteredPrompts.length > 0}
			{#each filteredPrompts.slice(0, numberOfSuggestions) as prompt, idx (prompt.id || prompt.content)}
				<button
					class="waterfall flex flex-col flex-1 shrink-0 w-[100px] h-[100px] justify-start text-left
									px-3 py-2 rounded-xl border border-gray-100 bg-white hover:bg-gray-100
									dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700 transition group shadow-sm"
					style="animation-delay: {idx * 60}ms; overflow-wrap: break-word;"
					on:click={() => dispatch('select', prompt.content)}
				>
					{#if prompt.title && prompt.title[0] !== ''}
						<p class="text-base font-normal text-gray-800 dark:text-gray-200 text-ellipsis overflow-auto">
							{prompt.title[0]}
						</p>
					{:else}
						<p class="font-medium text-gray-800 dark:text-gray-200 text-ellipsis overflow-auto">
							{prompt.content}
						</p>
					{/if}
				</button>
			{/each}
		{/if}
	</div>
{:else}
	<div class="h-80 overflow-auto scrollbar-none {className} flex flex-col gap-2 items-center">
		{#if filteredPrompts.length > 0}
			{#each filteredPrompts.slice(0, numberOfSuggestionsMobile).reduce((rows, prompt, idx) => {
				if (idx % 3 === 0) rows.push([]);
				rows[rows.length - 1].push(prompt);
				return rows;
			}, []) as row, rowIdx}
				<div class="flex gap-2">
					{#each row as prompt, idx (prompt.id || prompt.content)}
						<button
							class="waterfall flex flex-col flex-1 shrink-0 w-[100px] h-[100px] justify-center text-left
											px-3 py-2 rounded-xl border border-gray-100 bg-white hover:bg-gray-100
											dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700 transition group shadow-sm"
							style="animation-delay: {(rowIdx * 3 + idx) * 60}ms; overflow-wrap: break-word;"
							on:click={() => dispatch('select', prompt.content)}
						>
							{#if prompt.title && prompt.title[0] !== ''}
								<p class="text-base font-normal text-gray-800 dark:text-gray-200 text-ellipsis overflow-auto">
									{prompt.title[0]}
								</p>
							{:else}
								<p class="font-sm text-gray-800 dark:text-gray-200 text-ellipsis overflow-auto">
									{prompt.content}
								</p>
							{/if}
						</button>
					{/each}
				</div>
			{/each}
		{/if}
	</div>
{/if}

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