<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { getContext, createEventDispatcher } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';

	const i18n = getContext('i18n') as any;
	const dispatch = createEventDispatcher();

	export let suggestionPrompts: any[] = [];
	export let className: string = '';
	export let inputValue: string = '';

	let sortedPrompts: any[] = [];
	let filteredPrompts: any[] = [];

	const fuseOptions = {
		keys: ['content', 'title'],
		threshold: 0.5
	};

	let fuse: Fuse<any>;

	/* -----------------------------
	   Fuse initialization
	----------------------------- */
	$: fuse = new Fuse(sortedPrompts, fuseOptions);

	/* -----------------------------
	   Array equality check
	----------------------------- */
	function arraysEqual(a: any[], b: any[]): boolean {
		if (a.length !== b.length) return false;
		for (let i = 0; i < a.length; i++) {
			if ((a[i].id ?? a[i].content) !== (b[i].id ?? b[i].content)) {
				return false;
			}
		}
		return true;
	}

	/* -----------------------------
	   Filter logic
	----------------------------- */
	const getFilteredPrompts = (value: string): void => {
		if (value.length > 500) {
			filteredPrompts = [];
			return;
		}

		const next =
			value.trim() && fuse
				? fuse.search(value.trim()).map((r: any) => r.item)
				: sortedPrompts;

		if (!arraysEqual(filteredPrompts, next)) {
			filteredPrompts = next;
		}
	};

	$: getFilteredPrompts(inputValue);

	$: if (suggestionPrompts) {
		sortedPrompts = [...suggestionPrompts].sort(() => Math.random() - 0.5);
		getFilteredPrompts(inputValue);
	}
</script>

<!-- =============================
     HEADER
============================= -->
<div class="mb-2 flex items-center gap-1 text-xs font-medium text-gray-400 dark:text-gray-500">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{:else}
		<div class="w-full text-center">
			{$WEBUI_NAME} · v{WEBUI_VERSION}
		</div>
	{/if}
</div>

<!-- =============================
     SUGGESTION LIST
============================= -->
<!-- <div class="max-h-48 overflow-auto scrollbar-none space-y-1 {className}">
	{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)} -->
	<div class="overflow-hidden space-y-1 {className}">
	{#each filteredPrompts.slice(0, 2) as prompt, idx (prompt.id || prompt.content)}

		<button
			type="button"
			class="
				w-full text-left rounded-xl px-4 py-3
				bg-white dark:bg-transparent
				border border-transparent
				hover:bg-gray-50 dark:hover:bg-white/5
				hover:border-gray-200 dark:hover:border-white/10
				transition
				group
			"
			style="animation-delay: {idx * 60}ms"
			on:click={() => dispatch('select', prompt.content)}
		>
			<div class="flex flex-col gap-0.5">
				<!-- TITLE -->
				<div
					class="text-sm font-medium text-gray-900 dark:text-gray-200
					       group-hover:text-black dark:group-hover:text-white
					       line-clamp-1"
				>
					{#if prompt.title && prompt.title[0]}
						{prompt.title[0]}
					{:else}
						{prompt.content}
					{/if}
				</div>

				<!-- SUBTITLE -->
				<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
					{#if prompt.title && prompt.title[1]}
						{prompt.title[1]}
					{:else}
						{$i18n.t('Prompt')}
					{/if}
				</div>
			</div>
		</button>
	{/each}
</div>

<style>
	/* Waterfall animation */
	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	button {
		opacity: 0;
		animation: fadeInUp 180ms ease forwards;
	}
</style>
