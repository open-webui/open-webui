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

	$: selectableFilters = filters.filter((filter) => !filter.is_global);
	$: selectedFilters = filters.filter(
		(filter) => filter.is_global || selectedFilterIds.includes(filter.id)
	);

	const toggleFilter = (filter: Filter) => {
		selectedFilterIds = selectedFilterIds.includes(filter.id)
			? selectedFilterIds.filter((id) => id !== filter.id)
			: [...selectedFilterIds, filter.id];
	};
</script>

{#if filters.length > 0}
	<div>
		<div class="flex w-full items-center gap-2 mb-1">
			<div class=" self-center text-xs text-gray-500">{$i18n.t('Filters')}</div>

			{#if selectableFilters.length > 0}
				<TypeaheadSelector
					id="model-filters-selector"
					items={selectableFilters.map((filter) => ({
						...filter,
						description: filter.meta?.description
					}))}
					selectedIds={selectedFilterIds}
					placeholder={$i18n.t('Search filters')}
					triggerLabel={$i18n.t('Select Filter')}
					emptyLabel={$i18n.t('No filters found')}
					variant="dropdown"
					on:select={(e) => {
						toggleFilter(e.detail);
					}}
					on:enableall={(e) => {
						selectedFilterIds = [
							...new Set([...selectedFilterIds, ...e.detail.map((filter) => filter.id)])
						];
					}}
				/>
			{/if}
		</div>

		<!-- TODO: Filter order matters -->
		<div class="flex flex-col">
			<div class=" flex items-center flex-wrap mt-1">
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

		<div class=" text-xs dark:text-gray-700">
			{$i18n.t('To select filters here, add them to the "Functions" workspace first.')}
		</div>
	</div>
{/if}
