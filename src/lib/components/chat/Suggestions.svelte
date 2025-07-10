<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { settings, WEBUI_NAME } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';
	import MaterialIcon from '$lib/components/common/MaterialIcon.svelte';

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

<div class="w-full flex items-center justify-center">
	{#if filteredPrompts.length > 0}
		<div class="flex flex-wrap gap-3 mt-4 justify-center items-center w-full">
			{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)}
				<div class="relative rounded-lg backdrop-blur-md bg-white/90">
					<div class="absolute inset-0 border border-white rounded-lg pointer-events-none"></div>
					<button
					class="flex items-center gap-1 p-2.5 w-full font-heading font-medium text-sm leading-[22px] text-left whitespace-nowrap overflow-hidden text-ellipsis transition 
							bg-white text-neutral-800 hover:bg-gray-50 
							dark:bg-gray-900 dark:text-gray-100 dark:hover:bg-white/10 dark:hover:text-gray-900"
					style="animation-delay: {idx * 60}ms;"
					on:click={() => dispatch('select', prompt.content)}
					>
					{#if prompt.icon_name}
						<MaterialIcon name={prompt.icon_name} class="w-[18px] h-[18px]" color="{prompt.icon_color}" />
					{:else}
						<MaterialIcon name="lightbulb" class="w-[18px] h-[18px]" />
					{/if}

					<span class="font-heading font-medium text-sm leading-[22px] whitespace-nowrap">
						{prompt.title?.[0] ?? prompt.content}
					</span>
					</button>

				</div>
			{/each}
		</div>
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
