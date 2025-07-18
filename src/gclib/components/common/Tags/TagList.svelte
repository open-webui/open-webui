<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let tags = [];
</script>

<!--
	GoCaaS: https://godaddy-corp.atlassian.net/browse/GOCAAS-2625
		Restrict usage of tags for models in favor of CI/CD driven configuration.
-->

{#each tags as tag}
	<Tooltip content={tag.name}>
		<div
			class="relative group/tags px-1.5 py-[0.2px] gap-0.5 flex justify-between h-fit max-h-fit w-fit items-center rounded-full bg-gray-500/20 text-gray-700 dark:text-gray-200 transition"
		>
			<div class=" text-[0.7rem] font-medium self-center line-clamp-1 w-fit">
				{tag.name}
			</div>
		</div>
	</Tooltip>
{/each}
