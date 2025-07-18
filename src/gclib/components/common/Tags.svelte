<script lang="ts">
	import TagList from '$gclib/components/common/Tags/TagList.svelte';

	export let tags = [];
</script>

<!--
	GoCaaS: https://godaddy-corp.atlassian.net/browse/GOCAAS-2625
		Restrict usage of tags for models in favor of CI/CD driven configuration.
-->

<div class="flex flex-row flex-wrap gap-1 line-clamp-1">
	<TagList {tags} />
	<!--
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
	-->
</div>
