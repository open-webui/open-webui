<script lang="ts">
	import { flyAndScale } from '$lib/utils/transitions';
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';
	import BarsArrowUp from '$lib/components/icons/BarsArrowUp.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import { config } from '$lib/stores';

	const i18n = getContext('i18n');

	export let onClose: Function = () => {};

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
	align="end"
>
	<Tooltip content={$i18n.t('Add Content')}>
		<button
			class=" p-1.5 rounded-xl hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition font-medium text-sm flex items-center space-x-1"
			on:click={(e) => {
				e.stopPropagation();
				show = true;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-44 rounded-xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
			sideOffset={4}
			side="bottom"
			align="end"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('upload', { type: 'files' });
				}}
			>
				<ArrowUpCircle strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Upload files')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('upload', { type: 'directory' });
				}}
			>
				<FolderOpen strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Upload directory')}</div>
			</DropdownMenu.Item>

			<Tooltip
				content={$i18n.t(
					'This option will delete all existing files in the collection and replace them with newly uploaded files.'
				)}
				className="w-full"
			>
				<DropdownMenu.Item
					class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						dispatch('sync', { type: 'directory' });
					}}
				>
					<ArrowPath strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Sync directory')}</div>
				</DropdownMenu.Item>
			</Tooltip>

			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
				on:click={() => {
					dispatch('upload', { type: 'text' });
				}}
			>
				<BarsArrowUp strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Add text content')}</div>
			</DropdownMenu.Item>

			{#if $config?.features?.enable_google_drive_folder_sync}
				<DropdownMenu.Item
					class="flex  gap-2  items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						dispatch('sync', { type: 'google-drive' });
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							d="M6.28 3l5.72 10H22l-5.72-10H6.28zm0 0L.56 13H10.28l5.72-10H6.28zm5.72 10l-5.72 10H16.28L22 13H12z"
						/>
					</svg>
					<div class="flex items-center">{$i18n.t('Sync Google Drive folder')}</div>
				</DropdownMenu.Item>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
