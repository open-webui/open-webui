<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let filters = [];
	export let selectedFilterIds = [];
</script>

{#if filters.length > 0}
	<div>
		<div class="flex w-full justify-between mb-1">
			<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Filters')}</div>
		</div>

		<!-- TODO: Filter order matters -->
		<div class="flex flex-col">
			<div class=" flex items-center flex-wrap">
				{#each filters as filter}
					{@const isSelected = filter.is_global || selectedFilterIds.includes(filter.id)}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={isSelected ? 'checked' : 'unchecked'}
								disabled={filter.is_global}
								on:change={(e) => {
									if (filter.is_global) return;

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
		</div>
	</div>
{/if}
