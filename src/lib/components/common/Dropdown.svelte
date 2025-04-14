<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';

	interface Props {
		show?: boolean;
		side?: string;
		align?: string;
		children?: import('svelte').Snippet;
		content?: import('svelte').Snippet;
	}

	let {
		show = $bindable(false),
		side = 'bottom',
		align = 'start',
		children,
		content
	}: Props = $props();
	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		{@render children?.()}
	</DropdownMenu.Trigger>

	{#if content}{@render content()}{:else}
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
	{/if}
</DropdownMenu.Root>
