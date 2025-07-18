<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			dispatch('close');
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[228px] rounded-lg   z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				class="flex justify-between items-center px-[16px] py-[11px] text-[17px] leading-[22px] cursor-pointer"
				on:click={() => {
					dispatch('rename');
				}}
			>
				
				<div class="flex items-center">{$i18n.t('Rename')}</div>
				<Pencil strokeWidth="2" />
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex justify-between items-center px-[16px] py-[11px] text-[17px] leading-[22px] cursor-pointer"
				on:click={() => {
					dispatch('export');
				}}
			>
				

				<div class="flex items-center">{$i18n.t('Export')}</div>
				<Download strokeWidth="2" />
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex justify-between items-center px-[16px] py-[11px] text-[17px] leading-[22px] cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('delete');
				}}
			>
				
				<div class="flex items-center">{$i18n.t('Delete')}</div>
				<GarbageBin strokeWidth="2" />
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
