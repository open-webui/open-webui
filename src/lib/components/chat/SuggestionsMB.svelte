<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { WEBUI_NAME, mobile, user } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';
	import ProductGrid from '$lib/components/common/ProductGrid.svelte';
	import { logActivity } from '$lib/utils/log-activity';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';
	export let numberOfSuggestions = 5;
	export let suggestionPerRow = 5;
	export let maxSuggestions = 20;
	export let promptSelected = null;

	export let sortedPrompts = [];

	const fuseOptions = {
		keys: ['content', 'title'],
		threshold: 0.5
	};

	let fuse;
	let filteredPrompts = [];

	// Initialize Fuse
	$: fuse = new Fuse(sortedPrompts, fuseOptions);
	$: numberOfSuggestions = $mobile ? 6 : 5;
	$: suggestionPerRow = $mobile ? 3 : 5;

	// Update the filteredPrompts if inputValue changes
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
			// If inputValue is empty, show any prompts that are available using following logic:

			// Always include pinned prompts
			filteredPrompts = sortedPrompts.filter((prompt) => prompt.pin === true);

			// Add non-pinned prompts at random if there is space
			const nonPinnedPrompts = sortedPrompts.filter((prompt) => !prompt.pin && prompt.in_season === true);
			const availableSpace = maxSuggestions - filteredPrompts.length;
			if (availableSpace > 0) {
				const randomNonPinnedPrompts = nonPinnedPrompts.sort(() => Math.random() - 0.5).slice(0, availableSpace);
				filteredPrompts = [...filteredPrompts, ...randomNonPinnedPrompts];
			}
			// Make the first prompt selected if there are any
			if (filteredPrompts.length > 0 && promptSelected == null) {
				const firstPrompt = filteredPrompts[0];
				firstPrompt.selected = true;
				promptSelected = firstPrompt;
			}
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

	function handlePromptClick(prompt) {
			dispatch('select', prompt.content)
			prompt.selected = true; // Mark the clicked prompt as selected
			promptSelected = prompt;
			logActivity(`Suggested Prompt Clicked: ${prompt.title[0]}`, $user?.id);
	}

</script>

<div class="mx-5">
	<div class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-400 dark:text-gray-600">
		<Bolt />
		{$i18n.t('Suggested')}
	</div>

	<div class="{($mobile ? 'h-60 flex-col' : 'h-40 flex-wrap')} overflow-auto scrollbar-none {className} flex gap-2 items-center">
		{#if filteredPrompts.length > 0}
			{#each filteredPrompts.slice(0, numberOfSuggestions).reduce((rows, prompt, idx) => {
				if (idx % suggestionPerRow === 0) rows.push([]);
				rows[rows.length - 1].push(prompt);
				return rows;
			}, []) as row, rowIdx}
				<div class="flex gap-2 { !$mobile ? 'items-center w-full' : '' }">
					{#each row as prompt, idx (prompt.id || prompt.content)}
						<button
							class="suggestion-btn waterfall
							bg-white hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 text-ellipsis overflow-auto
							{prompt.selected ? 'selected text-white' : ''}"
							style="animation-delay: {idx * 60}ms; overflow-wrap: break-word;"
							on:click={() => {
								filteredPrompts.forEach((p) => p.selected = false); // Reset selection
								handlePromptClick(prompt);
								prompt.selected = true;
							}}
						>
							{#if prompt.title && prompt.title[0] !== ''}
								<p class="{ !$mobile ? 'text-base' : 'text-sm' } font-normal ">
									{prompt.title[0]}
								</p>
							{:else}
								<p class="{ !$mobile ? 'text-base' : 'text-sm' } ">
									{prompt.content}
								</p>
							{/if}
						</button>
					{/each}
				</div>
			{/each}
		{/if}
	</div>
	<!-- Render Product List -->
	{#key promptSelected}
		{#if promptSelected}
			<ProductGrid
				chat_id={promptSelected.chat_id}
				gift_idea_id={{ id: 'random' }}
			/>
		{/if}
	{/key}
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
	.suggestion-btn {
		width: 100px;
		height: 100px;
		padding-left: 0.75rem;
		padding-right: 0.75rem;
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
		border-radius: 0.75rem;
		border: 1px solid #f3f4f6;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
		display: flex;
		flex-direction: column;
		flex: 1;
		justify-content: flex-start;
		text-align: left;
		transition: all 0.3s ease;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}
	.suggestion-btn.dark {
		background-color: #333333;
		border-color: #676767;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
	}
	.suggestion-btn:hover {
		background-color: #FFAFA7;
		color: white;
	}
	.suggestion-btn.selected {
		background-color: #EB5352;
		color: white;
	}
</style>