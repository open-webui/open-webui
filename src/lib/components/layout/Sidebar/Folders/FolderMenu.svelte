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
	import RenameIcon from '$lib/components/icons/RenameIcon.svelte';
	import ExportIcon from '$lib/components/icons/ExportIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';

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
			class="w-full max-w-[160px] rounded-lg border border-lightGray-400 dark:border-customGray-700 px-1 py-1.5  z-50 bg-gray-50 dark:bg-customGray-900 dark:text-white shadow-lg"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				class="font-medium flex gap-2 items-center px-2 py-1.5 text-sm  text-lightGray-100 dark:text-customGray-100 dark:hover:text-white cursor-pointer hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md"
				on:click={() => {
					dispatch('rename');
				}}
			>
				<RenameIcon/>
				<div class="flex items-center">{$i18n.t('Rename')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="font-medium flex gap-2 items-center px-2 py-1.5 text-sm  text-lightGray-100 dark:text-customGray-100 dark:hover:text-white cursor-pointer hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md"
				on:click={() => {
					dispatch('export');
				}}
			>
				<ExportIcon/>

				<div class="flex items-center">{$i18n.t('Export')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="font-medium flex  gap-2  items-center px-2 py-1.5 text-sm text-lightGray-100 dark:text-customGray-100 dark:hover:text-white cursor-pointer hover:bg-lightGray-700 dark:hover:bg-customGray-950 rounded-md"
				on:click={() => {
					dispatch('delete');
				}}
			>
				<DeleteIcon/>
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
