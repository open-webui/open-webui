<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { getContext } from 'svelte';
	import { settings, WEBUI_NAME } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';

	const i18n = getContext('i18n');

	// Default suggestions shipped by the backend config; listed so `i18n:parse` keeps their keys.
	const defaultSuggestionKeys = [
		$i18n.t('Help me study'),
		$i18n.t('vocabulary for a college entrance exam'),
		$i18n.t(
			"Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option."
		),
		$i18n.t('Give me ideas'),
		$i18n.t("for what to do with my kids' art"),
		$i18n.t(
			"What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter."
		),
		$i18n.t('Tell me a fun fact'),
		$i18n.t('about the Roman Empire'),
		$i18n.t('Tell me a random fun fact about the Roman Empire'),
		$i18n.t('Show me a code snippet'),
		$i18n.t("of a website's sticky header"),
		$i18n.t("Show me a code snippet of a website's sticky header in CSS and JavaScript."),
		$i18n.t('Explain options trading'),
		$i18n.t("if I'm familiar with buying and selling stocks"),
		$i18n.t(
			"Explain options trading in simple terms if I'm familiar with buying and selling stocks."
		),
		$i18n.t('Overcome procrastination'),
		$i18n.t('give me tips'),
		$i18n.t(
			'Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?'
		)
	];
	void defaultSuggestionKeys;

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';
	export let onSelect = () => {};

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

<div class="mb-1 flex gap-1 text-xs font-normal items-center text-gray-600 dark:text-gray-400">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{:else}
		<!-- Keine Vorschläge -->

		<div
			class="flex w-full {$settings?.landingPageMode === 'chat'
				? ' -mt-1'
				: 'text-center items-center justify-center'}  self-start text-gray-600 dark:text-gray-400"
		>
			<!-- LICENSE covers this Open WebUI footer identifier.
			Do not alter, remove, obscure, or replace it except as LICENSE permits:
			https://docs.openwebui.com/license. -->
			{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
		</div>
	{/if}
</div>

<div class="h-36 w-full">
	{#if filteredPrompts.length > 0}
		<div role="list" class="max-h-36 overflow-auto scrollbar-none items-start {className}">
			{#each filteredPrompts as prompt, idx (prompt.id || `${prompt.content}-${idx}`)}
				<!-- svelte-ignore a11y-no-interactive-element-to-noninteractive-role -->
				<button
					role="listitem"
					class="waterfall flex flex-col flex-1 shrink-0 w-full justify-between
				       px-2.5 py-1.5 rounded-lg bg-transparent transition-colors
				       hover:text-gray-950 dark:hover:text-white group"
					style="animation-delay: {idx * 45}ms"
					on:click={() => onSelect({ type: 'prompt', data: $i18n.t(prompt.content) })}
				>
					<div class="flex flex-col text-left leading-snug">
						{#if prompt.title && prompt.title[0] !== ''}
							<div
								class="text-sm font-normal group-hover:text-gray-950 dark:text-gray-300 dark:group-hover:text-white transition line-clamp-1"
							>
								{$i18n.t(prompt.title[0])}
							</div>
							<div
								class="text-xs text-gray-600 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-gray-100 font-normal line-clamp-1"
							>
								{$i18n.t(prompt.title[1])}
							</div>
						{:else}
							<div
								class="text-sm font-normal group-hover:text-gray-950 dark:text-gray-300 dark:group-hover:text-white transition line-clamp-1"
							>
								{$i18n.t(prompt.content)}
							</div>
							<div
								class="text-xs text-gray-600 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-gray-100 font-normal line-clamp-1"
							>
								{$i18n.t('Prompt')}
							</div>
						{/if}
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
			transform: translateY(6px);
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
