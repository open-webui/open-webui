<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let filters = [];
	export let selectedFilterIds = [];
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-xs text-gray-500 font-medium">{$i18n.t('Default Filters')}</div>
	</div>

	<div class="flex flex-col">
		{#if filters.length > 0}
			<div class=" flex items-center flex-wrap">
				{#each filters as filter}
					{@const isSelected = selectedFilterIds.includes(filter.id)}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={isSelected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									if (e.detail === 'checked') {
										if (!selectedFilterIds.includes(filter.id)) {
											selectedFilterIds = [...selectedFilterIds, filter.id];
										}
									} else {
										selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
									}
								}}
							/>
						</div>

						<div class=" py-0.5 text-sm w-full capitalize font-medium">
							<Tooltip content={filter.meta.description}>
								{filter.name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
