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
	$: availableTools = tools.filter((tool) => !selectedToolIds.includes(tool.id));

	const selectTool = (tool: Tool) => {
		selectedToolIds = [...selectedToolIds, tool.id];
	};
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-xs text-gray-500">{$i18n.t('Tools')}</div>
	</div>

	<div class="flex flex-col mb-1">
		{#if tools.length > 0}
			<TypeaheadSelector
				id="model-tools-selector"
				items={availableTools}
				className="w-48 max-w-full"
				placeholder={$i18n.t('Search tools')}
				on:select={(e) => {
					selectTool(e.detail);
				}}
			/>

			<div class=" flex items-center flex-wrap">
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
			</div>
		{/if}
	</div>

	<div class=" text-xs dark:text-gray-700">
		{$i18n.t('To select toolkits here, add them to the "Tools" workspace first.')}
	</div>
</div>
