<script lang="ts">
	import { Switch } from 'bits-ui';

	import { createEventDispatcher, tick, getContext } from 'svelte';
	import { settings } from '$lib/stores';

	import Tooltip from './Tooltip.svelte';
	export let state = true;
	export let id = '';
	export let ariaLabelledbyId = '';
	export let ariaLabel = '';
	export let tooltip = false;

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
</script>

<Tooltip
	content={typeof tooltip === 'string'
		? tooltip
		: typeof tooltip === 'boolean' && tooltip
			? state
				? $i18n.t('Enabled')
				: $i18n.t('Disabled')
			: ''}
	placement="top"
>
	<Switch.Root
		bind:checked={state}
		{id}
		aria-labelledby={ariaLabelledbyId || undefined}
		aria-label={ariaLabel || undefined}
		class="relative h-4 min-h-4 w-7 shrink-0 cursor-pointer rounded-full mx-[1px] transition-colors duration-150 {($settings?.highContrastMode ??
		false)
			? 'focus:outline focus:outline-2 focus:outline-gray-800 focus:dark:outline-gray-200'
			: 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400 dark:focus-visible:outline-gray-500'} {state
			? 'bg-gray-900 dark:bg-white'
			: 'bg-gray-300 dark:bg-gray-700'}"
		onCheckedChange={async () => {
			await tick();
			dispatch('change', state);
		}}
	>
		<Switch.Thumb
			class="pointer-events-none absolute top-[0.125rem] block h-3 w-3 shrink-0 rounded-full transition-all duration-150 data-[state=checked]:left-[0.875rem] data-[state=checked]:bg-white data-[state=checked]:dark:bg-black data-[state=unchecked]:left-[0.125rem] data-[state=unchecked]:bg-white data-[state=unchecked]:dark:bg-gray-500"
		/>
	</Switch.Root>
</Tooltip>
