<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { getContext, createEventDispatcher, onMount } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';

	let sortedPrompts = [];
	onMount(() => {
		sortedPrompts = [...(suggestionPrompts ?? [])].sort(() => Math.random() - 0.5);
	});

	const fuseOptions = {
		keys: ['content', 'title'],
		threshold: 0.5
	};

	let fuse;
	let filteredPrompts = [];

	// Track the number of updates to filteredPrompts
	let version = 0;

	// Fuzzy search
	$: fuse = new Fuse(sortedPrompts, fuseOptions);
	// Update filteredPrompts + version whenever inputValue changes
	$: {
		filteredPrompts = inputValue.trim()
			? fuse.search(inputValue.trim()).map((result) => result.item)
			: sortedPrompts;
		version = version + 1;
	}
</script>

<div
	class="mb-1 flex gap-1 text-sm font-medium items-center text-gray-400 dark:text-gray-600"
	style="visibility: {filteredPrompts.length > 0 ? 'visible' : 'hidden'}"
>
	<Bolt />
	{$i18n.t('Suggested')}
</div>

<div class="h-40 overflow-auto scrollbar-none {className}">
	{#if filteredPrompts.length > 0}
		{#each filteredPrompts as prompt, idx ((prompt.id || prompt.content) + version)}
			<button
				class="waterfall-anim flex flex-col flex-1 shrink-0 w-full justify-between
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
						<div class="text-xs text-gray-500 font-normal line-clamp-1">
							{prompt.title[1]}
						</div>
					{:else}
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
		<!-- No suggestions -->
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

	.waterfall-anim {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
	}
</style>
