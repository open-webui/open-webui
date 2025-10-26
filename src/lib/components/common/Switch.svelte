<script lang="ts">
	import { Switch } from 'bits-ui';

	import { createEventDispatcher, tick, getContext } from 'svelte';
	import { settings } from '$lib/stores';

	import Tooltip from './Tooltip.svelte';
	export let state = true;
	export let id = '';
	export let ariaLabelledbyId = '';
	export let tooltip = false;

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
</script>

<Tooltip
	content={tooltip ? (state ? $i18n.t('Enabled') : $i18n.t('Disabled')) : ''}
	placement="top"
>
	<Switch.Root
		bind:checked={state}
		{id}
		aria-labelledby={ariaLabelledbyId}
		class="flex h-[18px] min-h-[18px] w-8 shrink-0 cursor-pointer items-center rounded-full px-1 mx-[1px] transition  {($settings?.highContrastMode ??
		false)
			? 'focus:outline focus:outline-2 focus:outline-gray-800 focus:dark:outline-gray-200'
			: 'outline outline-1 outline-gray-100 dark:outline-gray-800'} {state
			? ' bg-emerald-500 dark:bg-emerald-700'
			: 'bg-gray-200 dark:bg-transparent'}"
		onCheckedChange={async () => {
			await tick();
			dispatch('change', state);
		}}
	>
		<Switch.Thumb
			class="pointer-events-none block size-3 shrink-0 rounded-full bg-white transition-transform data-[state=checked]:translate-x-3 data-[state=unchecked]:translate-x-0 data-[state=unchecked]:shadow-mini "
		/>
	</Switch.Root>
</Tooltip>
