<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	import { getContext } from 'svelte';

	type Tool = {
		id: string;
		name?: string;
		meta?: {
			description?: string;
		};
	};

	export let tools: Tool[] = [];
	export let selectedToolIds: string[] = [];

	const i18n = getContext('i18n') as any;

	$: selectedTools = tools.filter((tool) => selectedToolIds.includes(tool.id));

	const toggleTool = (tool: Tool) => {
		selectedToolIds = selectedToolIds.includes(tool.id)
			? selectedToolIds.filter((id) => id !== tool.id)
			: [...selectedToolIds, tool.id];
	};
</script>

<div>
	<div class="flex w-full items-center gap-2 mb-1">
		<div class=" self-center text-xs text-gray-500">{$i18n.t('Tools')}</div>

		{#if tools.length > 0}
			<TypeaheadSelector
				id="model-tools-selector"
				items={tools}
				selectedIds={selectedToolIds}
				placeholder={$i18n.t('Search tools')}
				triggerLabel={$i18n.t('Select Tool')}
				emptyLabel={$i18n.t('No tools found')}
				variant="dropdown"
				on:select={(e) => {
					toggleTool(e.detail);
				}}
				on:enableall={(e) => {
					selectedToolIds = [...new Set([...selectedToolIds, ...e.detail.map((tool) => tool.id)])];
				}}
			/>
		{/if}
	</div>

	<div class="flex flex-col mb-1">
		{#if tools.length > 0}
			<div class=" flex items-center flex-wrap mt-1">
				{#each selectedTools as tool, toolIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state="checked"
								on:change={(e) => {
									if (e.detail === 'unchecked') {
										selectedToolIds = selectedToolIds.filter((id) => id !== tool.id);
									}
								}}
							/>
						</div>

						<Tooltip content={tool.meta?.description ?? tool.id}>
							<div class=" py-0.5 text-xs capitalize">
								{tool.name}
							</div>
						</Tooltip>
					</div>
				{/each}

				{#if selectedTools.length > 0}
					<button
						type="button"
						class="py-0.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
						on:click={() => {
							selectedToolIds = [];
						}}
					>
						{$i18n.t('Disable all')}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<div class=" text-xs dark:text-gray-700">
		{$i18n.t(
			'To select toolkits here, add them to the "Tools" workspace or enable a tool server first.'
		)}
	</div>
</div>
