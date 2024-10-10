<script lang="ts">
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestionPrompts = [];
	export let className = '';

	let prompts = [];

	$: prompts = (suggestionPrompts ?? [])
		.reduce((acc, current) => [...acc, ...[current]], [])
		.sort(() => Math.random() - 0.5);
</script>

{#if prompts.length > 0}
	<div class="mb-1 flex gap-1 text-sm font-medium items-center text-gray-400 dark:text-gray-600">
		<Bolt />
		{$i18n.t('Suggested')}
	</div>
{/if}

<div class=" h-40 max-h-full overflow-auto scrollbar-none {className}">
	{#each prompts as prompt, promptIdx}
		<button
			class="flex flex-col flex-1 shrink-0 w-full justify-between px-3 py-2 rounded-xl bg-transparent hover:bg-black/5 dark:hover:bg-white/5 transition group"
			on:click={() => {
				dispatch('select', prompt.content);
			}}
		>
			<div class="flex flex-col text-left">
				{#if prompt.title && prompt.title[0] !== ''}
					<div
						class="  font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
					>
						{prompt.title[0]}
					</div>
					<div class="text-xs text-gray-500 font-normal line-clamp-1">{prompt.title[1]}</div>
				{:else}
					<div
						class="  font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-1"
					>
						{prompt.content}
					</div>

					<div class="text-xs text-gray-500 font-normal line-clamp-1">Prompt</div>
				{/if}
			</div>
		</button>
	{/each}
</div>
