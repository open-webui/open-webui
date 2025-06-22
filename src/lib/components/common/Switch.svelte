<script lang="ts">
	import { createEventDispatcher, tick } from 'svelte';
	import { Switch } from 'bits-ui';
	export let state = true;
	export let id = '';

	const dispatch = createEventDispatcher();

	$: dispatch('change', state);
</script>

<Switch.Root
	bind:checked={state}
	{id}
	class="flex h-5 min-h-5 w-9 shrink-0 cursor-pointer items-center rounded-full px-[3px] mx-[1px] transition  {state
		? ' bg-emerald-600'
		: 'bg-gray-200 dark:bg-transparent'} outline outline-1 outline-gray-100 dark:outline-gray-800"
>
	<Switch.Thumb
		class="pointer-events-none block size-4 shrink-0 rounded-full bg-white transition-transform data-[state=checked]:translate-x-3.5 data-[state=unchecked]:translate-x-0 data-[state=unchecked]:shadow-mini "
	/>
</Switch.Root>
