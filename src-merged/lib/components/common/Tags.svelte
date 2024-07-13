<script lang="ts">
	import TagInput from './Tags/TagInput.svelte';
	import TagList from './Tags/TagList.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let tags = [];

	export let deleteTag: Function;
	export let addTag: Function;
</script>

<div class="flex flex-row flex-wrap gap-1 line-clamp-1">
	<TagList
		{tags}
		on:delete={(e) => {
			deleteTag(e.detail);
		}}
	/>

	<TagInput
		label={tags.length == 0 ? $i18n.t('Add Tags') : ''}
		on:add={(e) => {
			addTag(e.detail);
		}}
	/>
</div>
