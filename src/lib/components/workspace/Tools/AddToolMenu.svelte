<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Github from '$lib/components/icons/Github.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import Link from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let createHandler: Function;
	export let importFromLinkHandler: Function;

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
>
	<Tooltip content={$i18n.t('Create')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[190px] text-sm rounded-xl px-1 py-1 dark:text-white shadow-lg  border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					createHandler();
					show = false;
				}}
			>
				<div class=" self-center mr-2">
					<PencilSolid />
				</div>
				<div class=" self-center truncate">{$i18n.t('New Tool')}</div>
			</button>

			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
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
		</DropdownMenu.Content>
	</div>
</Dropdown>
