<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Valves from '$lib/components/common/Valves.svelte';

	const i18n = getContext('i18n');

	export let actions = [];
	export let selectedActionIds = [];

	export let valvesSpecs = {};
	export let valves = {};

	let _actions = {};

	onMount(() => {
		_actions = actions.reduce((acc, action) => {
			acc[action.id] = {
				...action,
				selected: selectedActionIds.includes(action.id)
			};

			return acc;
		}, {});
	});
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{$i18n.t('Actions')}</div>
	</div>

	<div class=" text-xs dark:text-gray-500">
		{$i18n.t('To select actions here, add them to the "Functions" workspace first.')}
	</div>

	<div class="flex flex-col">
		{#if actions.length > 0}
			<div class=" flex flex-col items-left mt-2 flex-wrap">
				{#each Object.keys(_actions) as action, actionIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={_actions[action].selected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									_actions[action].selected = e.detail === 'checked';
									selectedActionIds = Object.keys(_actions).filter((t) => _actions[t].selected);
								}}
							/>
						</div>

						<div class=" py-0.5 text-sm w-full capitalize font-medium">
							<Tooltip content={_actions[action].meta.description}>
								{_actions[action].name}
							</Tooltip>
						</div>
					</div>
					{#if _actions[action].selected}
						<Collapsible
							title={$i18n.t('Valves')}
							open={false}
							buttonClassName="w-full"
							className="mt-2"
						>
							<div slot="content">
								<Valves valvesSpec={valvesSpecs[action]} bind:valves={valves[action]} />
							</div>
						</Collapsible>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>
