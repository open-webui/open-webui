<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';

	const i18n = getContext('i18n');

	export let func;

	export let editHandler: Function;
	export let shareHandler: Function;
	export let cloneHandler: Function;
	export let exportHandler: Function;
	export let deleteHandler: Function;
	export let toggleGlobalHandler: Function;

	export let onClose: Function;

	let show = false;
</script>

<Dropdown
	bind:show
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<div
			class="min-w-[180px] rounded-xl p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
		>
			{#if ['filter', 'action'].includes(func.type)}
				<div
					class="flex gap-2 justify-between items-center px-3 py-1.5 text-sm font-medium cursor-pointerrounded-md"
				>
					<div class="flex gap-2 items-center">
						<GlobeAlt />
						<div class="flex items-center">{$i18n.t('Global')}</div>
					</div>

					<div>
						<Switch on:change={toggleGlobalHandler} bind:state={func.is_global} />
					</div>
				</div>

				<hr class="border-gray-50 dark:border-gray-850/30 my-1" />
			{/if}

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md w-full"
				on:click={() => {
					editHandler();
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="w-4 h-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
					/>
				</svg>

				<div class="flex items-center">{$i18n.t('Edit')}</div>
			</button>

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md w-full"
				on:click={() => {
					shareHandler();
				}}
			>
				<Share />
				<div class="flex items-center">{$i18n.t('Share')}</div>
			</button>

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md w-full"
				on:click={() => {
					cloneHandler();
				}}
			>
				<DocumentDuplicate />
				<div class="flex items-center">{$i18n.t('Clone')}</div>
			</button>

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md w-full"
				on:click={() => {
					exportHandler();
				}}
			>
				<Download />
				<div class="flex items-center">{$i18n.t('Export')}</div>
			</button>

			<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md w-full"
				on:click={() => {
					deleteHandler();
				}}
			>
				<GarbageBin strokeWidth="2" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</div>
	</div>
</Dropdown>
