<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { settings, WEBUI_NAME, mobile } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';
	import MaterialIcon from '$lib/components/common/MaterialIcon.svelte';
	import SuggestionsIcon from '$lib/components/icons/SuggestionsIcon.svelte';

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

<div class="w-full max-w-[800px] m-auto flex items-center justify-center">
	{#if suggestionPrompts.length > 0}
	<div
	class="gap-[8px] mt-4 w-full {$mobile
		? 'flex overflow-x-auto scrollbar-none items-center'
		: 'grid justify-center'}"
	style={!$mobile ? 'grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));' : ''}
>
			{#each suggestionPrompts as prompt, idx (prompt.id || prompt.content)}
				<button
					class="flex {$mobile
						? 'items-center gap-[4px] flex-shrink-0'
						: 'shadow-custom3 flex-col items-start'} text-typography-subtext hover:text-typography-titles border border-[#E5EBF3] hover:border-[#90C9FF] p-[16px] rounded-[8px] whitespace-nowrap overflow-hidden text-ellipsis transition
							bg-light-bg dark:border-[#2D3642] dark:hover:border-[#004280] dark:hover:text-white"
					style="animation-delay: {idx * 60}ms;"
					on:click={() => dispatch('select', prompt.content)}
				>
					{#if prompt.icon_name}
						<SuggestionsIcon name={prompt.icon_name} />
					{:else}
						<MaterialIcon name="lightbulb" class="w-[24px] h-[24px]" />
					{/if}
					<div
						class="w-full text-left {$mobile
							? ' '
							: ' mt-[12px]'} text-[14px] leading-[22px] whitespace-nowrap"
					>
						{prompt.title?.[0] ?? prompt.content}
					</div>
				</button>
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
