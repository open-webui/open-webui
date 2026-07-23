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

	$: selectableActions = actions.filter((action) => !action.is_global);
	$: selectedActions = actions.filter(
		(action) => action.is_global || selectedActionIds.includes(action.id)
	);

	const toggleAction = (action: Action) => {
		selectedActionIds = selectedActionIds.includes(action.id)
			? selectedActionIds.filter((id) => id !== action.id)
			: [...selectedActionIds, action.id];
	};
</script>

{#if actions.length > 0}
	<div>
		<div class="flex w-full items-center gap-2 mb-1">
			<div class=" self-center text-xs text-gray-500">{$i18n.t('Actions')}</div>

			{#if selectableActions.length > 0}
				<TypeaheadSelector
					id="model-actions-selector"
					items={selectableActions.map((action) => ({
						...action,
						description: action.meta?.description
					}))}
					selectedIds={selectedActionIds}
					placeholder={$i18n.t('Search actions')}
					triggerLabel={$i18n.t('Select Action')}
					emptyLabel={$i18n.t('No actions found')}
					variant="dropdown"
					on:select={(e) => {
						toggleAction(e.detail);
					}}
					on:enableall={(e) => {
						selectedActionIds = [
							...new Set([...selectedActionIds, ...e.detail.map((action) => action.id)])
						];
					}}
				/>
			{/if}
		</div>

		<div class="flex flex-col">
			<div class=" flex items-center flex-wrap mt-1">
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

				{#if selectedActionIds.length > 0}
					<button
						type="button"
						class="py-0.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
						on:click={() => {
							selectedActionIds = [];
						}}
					>
						{$i18n.t('Disable all')}
					</button>
				{/if}
			</div>
		</div>

		<div class=" text-xs dark:text-gray-700">
			{$i18n.t('To select actions here, add them to the "Functions" workspace first.')}
		</div>
	</div>
{/if}
