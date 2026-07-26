<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	const i18n = getContext('i18n');

	export let onExport: null | Function = null;
	export let onClose: Function = () => {};

	let show = false;

	const closeMenu = () => {
		show = false;
		onClose();
	};
</script>

<Dropdown
	bind:show
	align="end"
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot
			><button
				class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
				type="button"
				aria-label={$i18n.t('More Options')}
				on:click={(e) => {
					e.preventDefault();
					e.stopPropagation();
					show = !show;
				}}
			>
				<EllipsisHorizontal className="size-4" />
			</button>
		</slot>
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[170px]">
			{#if onExport}
				<button
					class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => {
						onExport();
						closeMenu();
					}}
				>
					<Download className="size-3.5" />
					<div class="flex items-center">{$i18n.t('Export')}</div>
				</button>
			{/if}

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
				on:click={() => {
					dispatch('delete');
					closeMenu();
				}}
			>
				<GarbageBin className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
