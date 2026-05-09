<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let filters = [];
	export let selectedFilterIds = [];

	let _filters = {};

	$: _filters = filters.reduce((acc, filter) => {
		acc[filter.id] = {
			...filter,
			selected: selectedFilterIds.includes(filter.id)
		};

		return acc;
	}, {});
</script>

{#if filters.length > 0}
	<div>
		<div class="flex w-full justify-between mb-1">
			<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Filters')}</div>
		</div>

		<!-- TODO: Filter order matters -->
		<div class="flex flex-col">
			<div class=" flex items-center flex-wrap">
				{#each Object.keys(_filters) as filter, filterIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={_filters[filter].is_global
									? 'checked'
									: _filters[filter].selected
										? 'checked'
										: 'unchecked'}
								disabled={_filters[filter].is_global}
								on:change={(e) => {
									if (_filters[filter].is_global) return;

									const filterId = _filters[filter].id;
									const isChecked = e.detail === 'checked';

									selectedFilterIds = isChecked
										? selectedFilterIds.includes(filterId)
											? selectedFilterIds
											: [...selectedFilterIds, filterId]
										: selectedFilterIds.filter((t) => t !== filterId);
								}}
							/>
						</div>

						<div class=" py-0.5 text-sm w-full capitalize font-medium">
							<Tooltip content={_filters[filter].meta.description}>
								{_filters[filter].name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
