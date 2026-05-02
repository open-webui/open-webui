<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { flyAndScale } from '$lib/utils/transitions';

	export let show = false;
	export let side = 'bottom';
	export let align = 'start';
	export let closeOnOutsideClick = true;

	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	{closeOnOutsideClick}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full max-w-[130px] rounded-xl p-1 border-hairline border-gray-200 dark:border-gray-700 z-50 bg-white dark:bg-gray-850 text-gray-800 dark:text-white shadow-sm"
			sideOffset={8}
			{side}
			{align}
			transition={flyAndScale}
		>
			<DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">{$i18n.t('Profile')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">{$i18n.t('Profile')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">{$i18n.t('Profile')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
