<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	type Tool = {
		id: string;
		name?: string;
		meta?: {
			description?: string;
		};
	};
	const i18n = getContext<any>('i18n');
	export let tools: Tool[] = [];
	export let selectedToolIds: string[] = [];
	export let disabled = false;
</script>

<!-- Previous labels retained for i18n extraction:
{$i18n.t('Select Tool')}
{$i18n.t('To select toolkits here, add them to the "Tools" workspace or enable a tool server first.')}
-->
<TypeaheadSelector
	id="model-toolsselector"
	label={$i18n.t('Tools')}
	description={$i18n.t(
		'Connect tools this model can call to retrieve information or perform actions.'
	)}
	items={tools}
	selectedIds={selectedToolIds}
	{disabled}
	placeholder={$i18n.t('Search tools')}
	emptyLabel={$i18n.t('No tools found')}
	emptyHint={$i18n.t('Add tools in the Tools workspace or connect a tool server.')}
	workspaceHref={$user?.role === 'admin' || $user?.permissions?.workspace?.tools
		? '/workspace/tools'
		: ''}
	variant="dropdown"
	on:select={(e) => {
		selectedToolIds = selectedToolIds.includes(e.detail.id)
			? selectedToolIds.filter((id) => id !== e.detail.id)
			: [...selectedToolIds, e.detail.id];
	}}
	on:enableall={(e) => {
		selectedToolIds = [...new Set([...selectedToolIds, ...e.detail.map((item) => item.id)])];
	}}
	on:clear={() => (selectedToolIds = [])}
/>
