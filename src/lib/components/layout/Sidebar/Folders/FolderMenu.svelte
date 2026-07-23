<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import EditPencil from '../icons/EditPencil.svelte';
	import FolderIcon from '../icons/Folder.svelte';
	import ShareIcon from '../icons/Share.svelte';
	import TrashIcon from '../icons/Trash.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '../icons/Download.svelte';

	export let align: 'start' | 'end' = 'start';
	export let onEdit = () => {};
	export let onExport = () => {};
	export let onShare = () => {};
	export let onDelete = () => {};
	export let onCreateSubFolder = () => {};

	let show = false;
</script>

<Dropdown
	bind:show
	{align}
	onOpenChange={(state) => {
		if (state === false) {
			dispatch('close');
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<button
			on:click={(e) => {
				e.stopPropagation();
				show = !show;
			}}
		>
			<slot />
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[170px]">
			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onCreateSubFolder();
				}}
			>
				<FolderIcon className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Create Project')}</div>
			</button>

			<hr class="border-gray-50/30 dark:border-gray-800/30 mx-1 my-0.5" />

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onEdit();
				}}
			>
				<EditPencil className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Edit')}</div>
			</button>

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onExport();
				}}
			>
				<Download className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Export')}</div>
			</button>

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onShare();
				}}
			>
				<ShareIcon className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Share')}</div>
			</button>

			<hr class="border-gray-50/30 dark:border-gray-800/30 mx-1 my-0.5" />

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onDelete();
				}}
			>
				<TrashIcon className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
