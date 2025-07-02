<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { settings, WEBUI_NAME } from '$lib/stores';
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

	$: if (suggestionPrompts) {
		sortedPrompts = [...(suggestionPrompts ?? [])].sort(() => Math.random() - 0.5);
		getFilteredPrompts(inputValue);
	}
</script>

<!-- <div class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-600 dark:text-gray-400">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{:else}
		

		<div
			class="flex w-full {$settings?.landingPageMode === 'chat'
				? ' -mt-1'
				: 'text-center items-center justify-center'}  self-start text-gray-600 dark:text-gray-400"
		>
			{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
		</div>
	{/if}
</div> -->

<div class="h-40 w-full">
	{#if filteredPrompts.length > 0}

		<div class="flex flex-wrap gap-3 mt-4 justify-center items-center">
			{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)}
				<button
					class="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium font-NotoKufi-Medium text-gray-1000 transition hover:bg-gray-50 dark:text-gray-100 dark:hover:bg-white/10"
					style="
						background: var(--Schemes-Surface, #FFF);
						box-shadow: 0px 0px 16px -8px rgba(28, 27, 27, 0.04);
						animation-delay: {idx * 60}ms;
					"
					on:click={() => dispatch('select', prompt.content)}
				>
					{#if prompt.icon}
						<span class="text-purple-600 text-lg">{@html prompt.icon}</span>
					{:else}
						<span class="text-purple-600 text-lg">✨</span>
					{/if}
					<span class="whitespace-nowrap">{prompt.title?.[0] ?? prompt.content}</span>
				</button>
			{/each}
		</div>


		<!-- <div class="max-h-40 overflow-auto scrollbar-none items-start {className}">
			{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)}
				<button
					class="waterfall flex flex-col flex-1 shrink-0 w-full justify-between
				       px-3 py-2 rounded-xl bg-transparent hover:bg-black/5
				       dark:hover:bg-white/5 transition group"
					style="animation-delay: {idx * 60}ms"
					on:click={() => dispatch('select', prompt.content)}
				>
					<div class="flex flex-col text-left">
						{#if prompt.title && prompt.title[0] !== ''}
							<div
								class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
							>
								{prompt.title[0]}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400 font-normal line-clamp-1">
								{prompt.title[1]}
							</div>
						{:else}
							<div
								class="font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
							>
								{prompt.content}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400 font-normal line-clamp-1">
								{$i18n.t('Prompt')}
							</div>
						{/if}
					</div>
				</button>
			{/each}
		</div> -->
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
