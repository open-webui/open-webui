<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	type Action = {
		id: string;
		name?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
		};
	};
	const i18n = getContext<any>('i18n');
	export let actions: Action[] = [];
	export let selectedActionIds: string[] = [];
	export let disabled = false;
</script>

<TypeaheadSelector
	id="model-actionsselector"
	label={$i18n.t('Actions')}
	description={$i18n.t('Add custom action buttons to model responses.')}
	items={actions}
	selectedIds={selectedActionIds}
	{disabled}
	placeholder={$i18n.t('Search actions')}
	emptyLabel={$i18n.t('No actions found')}
	emptyHint={$i18n.t('Add actions in the Functions workspace.')}
	workspaceHref={$user?.role === 'admin' ? '/admin/functions' : ''}
	variant="dropdown"
	on:select={(e) => {
		selectedActionIds = selectedActionIds.includes(e.detail.id)
			? selectedActionIds.filter((id) => id !== e.detail.id)
			: [...selectedActionIds, e.detail.id];
	}}
	on:enableall={(e) => {
		selectedActionIds = [...new Set([...selectedActionIds, ...e.detail.map((item) => item.id)])];
	}}
	on:clear={() => (selectedActionIds = [])}
/>
