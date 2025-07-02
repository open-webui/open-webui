<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';

	export let show = false;

	export let side: 'bottom' | 'top' | 'right' | 'left' = 'bottom';
	export let align: 'start' | 'center' | 'end' = 'start';
	export let ariaLabel: string | undefined = undefined;

	const dispatch = createEventDispatcher();

	const changeFocus = async (elementId) => {
		setTimeout(() => {
			document.getElementById(elementId)?.focus();
		}, 10);
	};
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		dispatch('change', state);
		changeFocus(buttonID);
	}}
	typeahead={false}
>

	<DropdownMenu.Trigger aria-label={ariaLabel}>

		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full max-w-[130px] rounded-lg px-1 py-1.5 border border-gray-900 z-50 bg-gray-850 text-white"
			sideOffset={8}
			{side}
			{align}
			transition={flyAndScale}
		>
			<DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
