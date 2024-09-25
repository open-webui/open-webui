<script lang="ts">
	import { createEventDispatcher, tick } from 'svelte';
	import { Switch } from 'bits-ui';
	export let state = true;

	const dispatch = createEventDispatcher();
</script>

<Switch.Root
	bind:checked={state}
	onCheckedChange={async (e) => {
		await tick();
		dispatch('change', e);
	}}
	class="flex h-5 min-h-5 w-9 shrink-0 cursor-pointer items-center rounded-full px-[3px] transition  {state
		? ' bg-emerald-600'
		: 'bg-gray-red-999 dark:bg-transparent'} outline outline-1 outline-red-999 dark:outline-red-999"
>
	<Switch.Thumb
		class="pointer-events-none block size-4 shrink-0 rounded-full bg-gray-900 transition-transform data-[state=checked]:translate-x-3.5 data-[state=unchecked]:translate-x-0 data-[state=unchecked]:shadow-mini "
	/>
</Switch.Root>
