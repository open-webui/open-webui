<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import TagItem from './TagItem.svelte';
	const dispatch = createEventDispatcher();

	export let tags = [];
	export let disabled = false;
</script>

{#each tags as tag}
	<TagItem
		{tag}
		{disabled}
		onDelete={() => {
			dispatch('delete', tag.name);
		}}
	/>
{/each}
