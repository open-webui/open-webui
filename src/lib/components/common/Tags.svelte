<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let tags = [];
	export let suggestionTags = [];
	export let placeholder = '';

	let inputValue = '';
	let inputElement: HTMLInputElement;

	const addTag = () => {
		const value = inputValue.trim();
		if (value && !tags.some((t) => t.name === value)) {
			dispatch('add', value);
			inputValue = '';
		}
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			addTag();
		} else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
			dispatch('delete', tags[tags.length - 1].name);
		}
	};
</script>

<div
	class="flex flex-wrap items-center gap-1.5 min-h-[38px] px-3 py-1.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus-within:ring-1 focus-within:ring-gray-300 dark:focus-within:ring-gray-700 transition"
	on:click={() => inputElement?.focus()}
	role="button"
	tabindex="-1"
>
	{#each tags as tag}
		<span
			class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md"
		>
			{tag.name}
			<button
				type="button"
				class="hover:text-red-500 transition"
				on:click|stopPropagation={() => dispatch('delete', tag.name)}
				aria-label={$i18n.t('Remove tag')}
			>
				<XMark className="size-3" strokeWidth="2.5" />
			</button>
		</span>
	{/each}
	<input
		bind:this={inputElement}
		bind:value={inputValue}
		class="flex-1 min-w-[80px] text-sm bg-transparent outline-none placeholder:text-gray-400"
		placeholder={tags.length === 0 ? (placeholder || $i18n.t('Add Tags')) : ''}
		list="tagSuggestions"
		on:keydown={handleKeydown}
		on:blur={() => {
			if (inputValue.trim()) addTag();
		}}
	/>
	{#if suggestionTags.length > 0}
		<datalist id="tagSuggestions">
			{#each suggestionTags as tag}
				<option value={tag.name} />
			{/each}
		</datalist>
	{/if}
</div>
