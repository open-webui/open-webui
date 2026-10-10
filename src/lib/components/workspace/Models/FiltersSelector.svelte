<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	type Filter = {
		id: string;
		name?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
			toggle?: boolean;
		};
	};
	const i18n = getContext<any>('i18n');
	export let filters: Filter[] = [];
	export let selectedFilterIds: string[] = [];
	export let defaultFilterIds: string[] = [];
	export let disabled = false;
</script>

<!-- Previous labels retained for i18n extraction:
{$i18n.t('Select Filter')}
{$i18n.t('To select filters here, add them to the "Functions" workspace first.')}
{$i18n.t('Default Filters')}
{$i18n.t('To select default filters here, enable toggleable filters for this model first.')}
-->
<TypeaheadSelector
	id="model-filtersselector"
	label={$i18n.t('Filters')}
	description={$i18n.t('Apply functions that process messages before or after the model responds.')}
	items={filters}
	selectedIds={selectedFilterIds}
	bind:defaultIds={defaultFilterIds}
	{disabled}
	placeholder={$i18n.t('Search filters')}
	emptyLabel={$i18n.t('No filters found')}
	emptyHint={$i18n.t('Add filters in the Functions workspace.')}
	workspaceHref={$user?.role === 'admin' ? '/admin/functions' : ''}
	variant="dropdown"
	on:select={(e) => {
		selectedFilterIds = selectedFilterIds.includes(e.detail.id)
			? selectedFilterIds.filter((id) => id !== e.detail.id)
			: [...selectedFilterIds, e.detail.id];
	}}
	on:enableall={(e) => {
		selectedFilterIds = [...new Set([...selectedFilterIds, ...e.detail.map((item) => item.id)])];
	}}
	on:clear={() => (selectedFilterIds = [])}
/>
