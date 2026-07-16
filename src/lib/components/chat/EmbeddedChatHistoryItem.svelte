<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	const i18n = getContext('i18n');

	export let item: any;
	export let title = '';
	export let selected = false;
	export let deleting = false;

	export let onSelect: (id: string) => void | Promise<void> = () => {};
	export let onDelete: (id: string) => void | Promise<void> = () => {};
	export let onMenuOpenChange: (id: string, state: boolean) => void = () => {};

	let showMenu = false;
</script>

<button
	type="button"
	class="group/item flex h-8 w-full cursor-pointer select-none items-center rounded-xl px-2 text-left text-[13px] font-normal text-gray-700 outline-hidden transition-colors duration-75 hover:bg-gray-50/40 dark:text-gray-100 dark:hover:bg-gray-800/40 {selected
		? 'bg-gray-50/70 dark:bg-gray-800/60'
		: ''}"
	on:click={() => onSelect(item.id)}
>
	<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
		<div class="min-w-0 truncate">{title}</div>

		{#if selected}
			<div class="shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
				{$i18n.t('Current')}
			</div>
		{/if}
	</div>

	<div class="ml-auto flex shrink-0 items-center gap-1.5 pl-2">
		<Dropdown
			bind:show={showMenu}
			align="end"
			sideOffset={-2}
			onOpenChange={(state) => {
				showMenu = state;
				onMenuOpenChange(item.id, state);
			}}
		>
			<Tooltip content={$i18n.t('More')} className="group-hover/item:opacity-100 opacity-0">
				<button
					type="button"
					aria-label={$i18n.t('More Options')}
					class="flex"
					on:click={(e) => {
						e.preventDefault();
						e.stopPropagation();
						showMenu = !showMenu;
						onMenuOpenChange(item.id, showMenu);
					}}
				>
					<EllipsisHorizontal className="size-4" strokeWidth="1.5" />
				</button>
			</Tooltip>

			<div slot="content">
				<DropdownMenu className="min-w-[160px] z-[9999999]">
					<button
						type="button"
						class="select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 transition"
						disabled={deleting}
						on:click={async (e) => {
							e.preventDefault();
							e.stopPropagation();
							showMenu = false;
							onMenuOpenChange(item.id, false);
							await onDelete(item.id);
						}}
					>
						<GarbageBin className="size-3.5" strokeWidth="1.5" />
						<div class="flex items-center">{$i18n.t('Delete')}</div>
					</button>
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
</button>
