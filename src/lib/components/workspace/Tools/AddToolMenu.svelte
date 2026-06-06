<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
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
		<div
			class="min-w-[190px] rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		>
			<button
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				on:click={async () => {
					createHandler();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<Pencil />
				</div>
				<div class=" self-center truncate">{$i18n.t('New Tool')}</div>
			</button>

			<button
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl w-full"
				on:click={async () => {
					importFromLinkHandler();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<Link />
				</div>
				<div class=" self-center truncate">{$i18n.t('Import From Link')}</div>
			</button>
		</div>
	</div>
</Dropdown>
