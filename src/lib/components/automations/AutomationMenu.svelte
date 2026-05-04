<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let editHandler: Function;
	export let runHandler: Function = () => {};
	export let deleteHandler: Function;
	export let onClose: Function = () => {};

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
			class="min-w-[170px] rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		>
			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				draggable="false"
				on:click={() => {
					editHandler();
					show = false;
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
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				draggable="false"
				on:click={() => {
					runHandler();
					show = false;
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
						d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z"
					/>
				</svg>

				<div class="flex items-center">{$i18n.t('Run Now')}</div>
			</button>

			<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

			<button
				class="select-none flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				draggable="false"
				on:click={() => {
					deleteHandler();
					show = false;
				}}
			>
				<GarbageBin />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</div>
	</div>
</Dropdown>
