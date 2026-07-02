<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';

	type Filter = {
		id: string;
		name?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
		};
	};

	const i18n = getContext('i18n') as any;

	export let filters: Filter[] = [];
	export let selectedFilterIds: string[] = [];

	$: selectedFilters = filters.filter(
		(filter) => filter.is_global || selectedFilterIds.includes(filter.id)
	);
	$: availableFilters = filters.filter(
		(filter) => !filter.is_global && !selectedFilterIds.includes(filter.id)
	);

	const selectFilter = (filter: Filter) => {
		selectedFilterIds = [...selectedFilterIds, filter.id];
	};
</script>

{#if filters.length > 0}
	<div>
		<div class="flex w-full justify-between mb-1">
			<div class=" self-center text-xs text-gray-500">{$i18n.t('Filters')}</div>
		</div>

		<!-- TODO: Filter order matters -->
		<div class="flex flex-col">
			<TypeaheadSelector
				id="model-filters-selector"
				items={availableFilters.map((filter) => ({
					...filter,
					description: filter.meta?.description
				}))}
				className="w-48 max-w-full"
				placeholder={$i18n.t('Search filters')}
				on:select={(e) => {
					selectFilter(e.detail);
				}}
			/>

			<div class=" flex items-center flex-wrap">
				{#each selectedFilters as filter}
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

						<div class=" py-0.5 text-xs capitalize">
							<Tooltip content={filter.meta?.description ?? filter.id}>
								{filter.name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
