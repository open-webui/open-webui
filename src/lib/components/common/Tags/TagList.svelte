<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import TagItem from './TagItem.svelte';
	const dispatch = createEventDispatcher();

	export let tags = [];
</script>

{#each tags as tag}
	<TagItem
		{tag}
		onDelete={() => {
			dispatch('delete', tag.name);
		}}
	/>
{/each}
