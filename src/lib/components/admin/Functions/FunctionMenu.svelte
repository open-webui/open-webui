<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';

	const i18n = getContext('i18n');

	interface Props {
		func: any;
		editHandler: Function;
		shareHandler: Function;
		cloneHandler: Function;
		exportHandler: Function;
		deleteHandler: Function;
		toggleGlobalHandler: Function;
		onClose: Function;
		children?: import('svelte').Snippet;
	}

	let {
		func = $bindable(),
		editHandler,
		shareHandler,
		cloneHandler,
		exportHandler,
		deleteHandler,
		toggleGlobalHandler,
		onClose,
		children
	}: Props = $props();

	let show = $state(false);
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
		{@render children?.()}
	</Tooltip>

	{#snippet content()}
		<div>
			<DropdownMenu.Content
				class="w-full max-w-[180px] rounded-xl px-1 py-1.5 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
				align="start"
				side="bottom"
				sideOffset={-2}
				transition={flyAndScale}
			>
				{#if ['filter', 'action'].includes(func.type)}
					<div
						class="flex gap-2 justify-between items-center px-3 py-2 text-sm font-medium cursor-pointerrounded-md"
					>
						<div class="flex gap-2 items-center">
							<GlobeAlt />

							<div class="flex items-center">{$i18n.t('Global')}</div>
						</div>

						<div>
							<Switch on:change={toggleGlobalHandler} bind:state={func.is_global} />
						</div>
					</div>

					<hr class="border-gray-100 dark:border-gray-850 my-1" />
				{/if}

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800  rounded-md"
					on:click={() => {
						editHandler();
					}}
				>
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						viewBox="0 0 24 24"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>

					<div class="flex items-center">{$i18n.t('Edit')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800  rounded-md"
					on:click={() => {
						shareHandler();
					}}
				>
					<Share />
					<div class="flex items-center">{$i18n.t('Share')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						cloneHandler();
					}}
				>
					<DocumentDuplicate />

					<div class="flex items-center">{$i18n.t('Clone')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						exportHandler();
					}}
				>
					<ArrowDownTray />

					<div class="flex items-center">{$i18n.t('Export')}</div>
				</DropdownMenu.Item>

				<hr class="border-gray-100 dark:border-gray-850 my-1" />

				<DropdownMenu.Item
					class="flex  gap-2  items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						deleteHandler();
					}}
				>
					<GarbageBin strokeWidth="2" />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</div>
	{/snippet}
</Dropdown>
