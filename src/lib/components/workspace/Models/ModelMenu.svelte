<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';
	import MessageEditIcon from '$lib/components/icons/MessageEditIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import ShareIcon from '$lib/components/icons/ShareIcon.svelte';

	import { config } from '$lib/stores';

	const i18n = getContext('i18n');

	export let user;
	export let model;

	export let shareHandler: Function;
	export let cloneHandler: Function;
	export let exportHandler: Function;

	export let hideHandler: Function;
	export let deleteHandler: Function;
	export let onClose: Function;

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[160px] rounded-lg px-1 py-1.5 border border-gray-300/30 dark:border-customGray-700 z-50 bg-white dark:bg-customGray-900 dark:text-white shadow"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
				<DropdownMenu.Item>
					<a
						class="flex w-full items-center gap-2 self-center text-xs dark:text-cusromGray-100 px-3 py-2 dark:text-gray-300 dark:hover:bg-customGray-950 dark:hover:text-white hover:bg-black/5 rounded-md"
						type="button"
						href={`/workspace/models/edit?id=${encodeURIComponent(model.id)}`}
					>
						<MessageEditIcon width={14} height={13}/>
						<div class="flex items-center">{$i18n.t('Edit')}</div>
					</a>
				</DropdownMenu.Item>
			
			<!-- {#if $config?.features.enable_community_sharing}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950  rounded-md dark:hover:text-white"
					on:click={() => {
						shareHandler();
					}}
				>
					<ShareIcon />
					<div class="flex items-center ">{$i18n.t('Share')}</div>
				</DropdownMenu.Item>
			{/if} -->

			<!-- <DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					cloneHandler();
				}}
			>
				<DocumentDuplicate />

				<div class="flex items-center">{$i18n.t('Clone')}</div>
			</DropdownMenu.Item> -->

			<!-- <DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					exportHandler();
				}}
			>
				<ArrowDownTray />

				<div class="flex items-center">{$i18n.t('Export')}</div>
			</DropdownMenu.Item>

			<hr class="border-gray-100 dark:border-gray-800 my-1" /> -->
			
				<DropdownMenu.Item
					class="flex  gap-2  items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
					on:click={() => {
						deleteHandler();
					}}
				>
					<DeleteIcon />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
