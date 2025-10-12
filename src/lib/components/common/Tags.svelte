<script lang="ts">
	import TagInput from './Tags/TagInput.svelte';
	import TagList from './Tags/TagList.svelte';
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let tags = [];
</script>

<ul class="flex flex-row flex-wrap gap-[0.3rem] line-clamp-1">
	<TagList
		{tags}
		on:delete={(e) => {
			dispatch('delete', e.detail);
		}}
	/>

	<TagInput
		label={tags.length == 0 ? $i18n.t('Add Tags') : ''}
		on:add={(e) => {
			dispatch('add', e.detail);
		}}
	/>
</ul>
