<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';

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
				<Folder className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Create Folder')}</div>
			</button>

			<hr class="border-gray-50/30 dark:border-gray-800/30 mx-1 my-0.5" />

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onEdit();
				}}
			>
				<Pencil className="size-3.5" />
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-3.5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.935-2.186 2.25 2.25 0 0 0-3.935 2.186Z"
					/>
				</svg>
				<div class="flex items-center">{$i18n.t('Share')}</div>
			</button>

			<hr class="border-gray-50/30 dark:border-gray-800/30 mx-1 my-0.5" />

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={() => {
					onDelete();
				}}
			>
				<GarbageBin className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
