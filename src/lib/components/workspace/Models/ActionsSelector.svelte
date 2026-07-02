<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';

	type Action = {
		id: string;
		name?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
		};
	};

	const i18n = getContext('i18n') as any;

	export let actions: Action[] = [];
	export let selectedActionIds: string[] = [];

	$: selectedActions = actions.filter(
		(action) => action.is_global || selectedActionIds.includes(action.id)
	);
	$: availableActions = actions.filter(
		(action) => !action.is_global && !selectedActionIds.includes(action.id)
	);

	const selectAction = (action: Action) => {
		selectedActionIds = [...selectedActionIds, action.id];
	};
</script>

{#if actions.length > 0}
	<div>
		<div class="flex w-full justify-between mb-1">
			<div class=" self-center text-xs text-gray-500">{$i18n.t('Actions')}</div>
		</div>

		<div class="flex flex-col">
			<TypeaheadSelector
				id="model-actions-selector"
				items={availableActions}
				className="w-48 max-w-full"
				placeholder={$i18n.t('Search actions')}
				on:select={(e) => {
					selectAction(e.detail);
				}}
			/>

			<div class=" flex items-center flex-wrap">
				{#each selectedActions as action, actionIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state="checked"
								disabled={action.is_global}
								on:change={(e) => {
									if (!action.is_global && e.detail === 'unchecked') {
										selectedActionIds = selectedActionIds.filter((id) => id !== action.id);
									}
								}}
							/>
						</div>

						<div class=" py-0.5 text-xs capitalize">
							<Tooltip content={action.meta?.description ?? action.id}>
								{action.name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
