<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import { getContext, onMount } from 'svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Valves from '$lib/components/common/Valves.svelte';

	export let tools = [];

	export let valvesSpecs = {};
	export let valves = {};

	let _tools = {};

	export let selectedToolIds = [];

	const i18n = getContext('i18n');

	onMount(() => {
		_tools = tools.reduce((acc, tool) => {
			acc[tool.id] = {
				...tool,
				selected: selectedToolIds.includes(tool.id)
			};

			return acc;
		}, {});
	});
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{$i18n.t('Tools')}</div>
	</div>

	<div class=" text-xs dark:text-gray-500">
		{$i18n.t('To select toolkits here, add them to the "Tools" workspace first.')}
	</div>

	<div class="flex flex-col">
		{#if tools.length > 0}
			<div class=" flex flex-col items-left mt-2 flex-wrap">
				{#each Object.keys(_tools) as tool, toolIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={_tools[tool].selected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									_tools[tool].selected = e.detail === 'checked';
									selectedToolIds = Object.keys(_tools).filter((t) => _tools[t].selected);
								}}
							/>
						</div>

						<div class=" py-0.5 text-sm w-full capitalize font-medium">
							{_tools[tool].name}
						</div>
					</div>
					{#if _tools[tool].selected}
						<Collapsible
							title={$i18n.t('Valves')}
							open={false}
							buttonClassName="w-full"
							className="mt-2"
						>
							<div slot="content">
								<Valves valvesSpec={valvesSpecs[tool]} bind:valves={valves[tool]} />
							</div>
						</Collapsible>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>
