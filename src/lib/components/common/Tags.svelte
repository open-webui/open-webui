<script lang="ts">
	import TagList from './Tags/TagList.svelte';
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let tags = [];
	export let suggestionTags = [];
	export let disabled = false;

	$: tagNames = new Set(tags.map((t) => t.name));
	$: filteredSuggestionTags = suggestionTags.filter((t) => !tagNames.has(t.name));

	let inputValue = '';

	const addTag = () => {
		const value = inputValue.trim();
		if (value !== '') {
			dispatch('add', value);
			inputValue = '';
		}
	};
</script>

<div class="flex flex-wrap items-center gap-1 w-full">
	<TagList
		{tags}
		{disabled}
		on:delete={(e) => {
			dispatch('delete', e.detail);
		}}
	/>

	{#if !disabled}
		<input
			bind:value={inputValue}
			class="flex-1 min-w-24 {tags.length > 0
				? 'px-0.5'
				: ''} text-xs bg-transparent outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-500"
			placeholder={$i18n.t('Add a tag...')}
			list="suggestionTagOptions"
			on:keydown={(event) => {
				if (event.key === 'Enter' || event.key === ' ') {
					event.preventDefault();
					addTag();
				}
			}}
			on:input={() => {
				const value = inputValue.trim();
				if (value !== '' && filteredSuggestionTags.some((t) => t.name === value)) {
					addTag();
				}
			}}
		/>
	{/if}

	<datalist id="suggestionTagOptions">
		{#each filteredSuggestionTags as tag}
			<option value={tag.name} />
		{/each}
	</datalist>
</div>
