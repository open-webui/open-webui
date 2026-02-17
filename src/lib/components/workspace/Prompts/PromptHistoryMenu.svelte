<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	const i18n = getContext('i18n');

	export let isProduction = false;
	export let onDelete: Function;
	export let onClose: Function;

	let show = false;
	let showDeleteConfirmDialog = false;
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	title={$i18n.t('Delete Version')}
	message={$i18n.t(
		"Are you sure you want to delete this version? Child versions will be relinked to this version's parent."
	)}
	confirmLabel={$i18n.t('Delete')}
	onConfirm={() => {
		onDelete();
	}}
/>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot>
			<button
				class="p-1 rounded-lg text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
			>
				<EllipsisHorizontal className="size-5" />
			</button>
		</slot>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[170px] rounded-2xl p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={-2}
			side="bottom"
			align="end"
			transition={flyAndScale}
		>
			{#if isProduction}
				<Tooltip content={$i18n.t('Cannot delete the production version')} placement="top">
					<div
						class="flex gap-2 items-center px-3 py-1.5 text-sm rounded-xl opacity-40 cursor-not-allowed"
					>
						<GarbageBin />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</div>
				</Tooltip>
			{:else}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						show = false;
						showDeleteConfirmDialog = true;
					}}
				>
					<GarbageBin />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</DropdownMenu.Item>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
