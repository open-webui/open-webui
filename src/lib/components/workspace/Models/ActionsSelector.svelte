<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let actions = [];
	export let selectedActionIds = [];

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

{#if actions.length > 0}
	<div>
		<div class="flex w-full justify-between mb-1">
			<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Actions')}</div>
		</div>

		<div class="flex flex-col">
			<div class=" flex items-center flex-wrap">
				{#each Object.keys(_actions) as action, actionIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={_actions[action].is_global
									? 'checked'
									: _actions[action].selected
										? 'checked'
										: 'unchecked'}
								disabled={_actions[action].is_global}
								on:change={(e) => {
									if (!_actions[action].is_global) {
										_actions[action].selected = e.detail === 'checked';
										selectedActionIds = Object.keys(_actions).filter((t) => _actions[t].selected);
									}
								}}
							/>
						</div>

						<div class=" py-0.5 text-sm w-full capitalize font-medium">
							<Tooltip content={_actions[action].meta.description}>
								{_actions[action].name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
