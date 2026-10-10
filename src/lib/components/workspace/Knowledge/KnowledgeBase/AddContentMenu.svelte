<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';
	import BarsArrowUp from '$lib/components/icons/BarsArrowUp.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import NewFolderAlt from '$lib/components/icons/NewFolderAlt.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import ArrowUturnLeft from '$lib/components/icons/ArrowUturnLeft.svelte';

	const i18n = getContext('i18n');

	export let onClose: Function = () => {};

	export let onSync: Function = () => {};
	export let onUpload: Function = (data) => {};
	export let onReset: Function = () => {};

	let show = false;
</script>

<Dropdown
	closeOnSelect
	bind:show
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
	align="end"
>
	<Tooltip content={$i18n.t('Add Content')}>
		<button
			class="px-1 py-1.5 rounded-xl bg-transparent transition text-xs flex items-center text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
			aria-label={$i18n.t('Add Content')}
			on:click={(e) => {
				e.stopPropagation();
				show = true;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				class="w-4 h-4"
			>
				<path stroke-linecap="round" d="M12 5v14M5 12h14" />
			</svg>
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[12.5rem] transition">
			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onUpload({ type: 'new_directory' });
				}}
			>
				<NewFolderAlt />
				<div class="flex items-center">{$i18n.t('New directory')}</div>
			</button>

			<hr class="my-1 border-gray-100 dark:border-gray-800" />

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onUpload({ type: 'files' });
				}}
			>
				<ArrowUpCircle strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Upload files')}</div>
			</button>

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onUpload({ type: 'directory' });
				}}
			>
				<FolderOpen strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Upload directory')}</div>
			</button>

			<Tooltip
				content={$i18n.t(
					'Sync a local directory with this knowledge base. Only new and modified files will be uploaded. The directory structure will be mirrored.'
				)}
				className="w-full"
			>
				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => {
						onSync();
					}}
				>
					<ArrowPath strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Sync directory')}</div>
				</button>
			</Tooltip>

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onUpload({ type: 'web' });
				}}
			>
				<GlobeAlt strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Add webpage')}</div>
			</button>

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onUpload({ type: 'text' });
				}}
			>
				<BarsArrowUp strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Add text content')}</div>
			</button>

			<hr class="my-1 border-gray-100 dark:border-gray-800" />

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-xs hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					onReset();
				}}
			>
				<ArrowUturnLeft strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Reset')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
