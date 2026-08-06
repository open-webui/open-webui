<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
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
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot>
			<button
				class="p-1 rounded-lg text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				aria-label={$i18n.t('More Options')}
			>
				<EllipsisHorizontal className="size-5" />
			</button>
		</slot>
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[170px]">
			{#if isProduction}
				<Tooltip content={$i18n.t('Cannot delete the production version')} placement="top">
					<div
						class="flex h-[1.6875rem] items-center gap-2 rounded-xl px-2 text-[13px] opacity-40 cursor-not-allowed"
					>
						<GarbageBin className="size-3.5" />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</div>
				</Tooltip>
			{:else}
				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => {
						show = false;
						showDeleteConfirmDialog = true;
					}}
				>
					<GarbageBin className="size-3.5" />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</button>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
