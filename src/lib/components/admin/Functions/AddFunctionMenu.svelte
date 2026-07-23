<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Link from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let createHandler: Function;
	export let importFromLinkHandler: Function;

	export let onClose: Function = () => {};

	let show = false;
</script>

<Dropdown
	bind:show
	sideOffset={6}
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Create')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[190px]">
			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={async () => {
					createHandler();
					show = false;
				}}
			>
				<div class="self-center">
					<Pencil className="size-3.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('New Function')}</div>
			</button>

			<button
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
				on:click={async () => {
					importFromLinkHandler();
					show = false;
				}}
			>
				<div class="self-center">
					<Link className="size-3.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Import From Link')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
