<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import { config } from '$lib/stores';

	const i18n = getContext('i18n');

	export let uploadFilesHandler: Function;
	export let webSearchEnabled: boolean;

	export let onClose: Function;

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
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[190px] rounded-xl px-1 py-1  border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
			sideOffset={15}
			alignOffset={-8}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			{#if $config?.features?.enable_web_search}
				<div
					class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
				>
					<div class="flex-1 flex items-center gap-2">
						<GlobeAltSolid />
						<div class="flex items-center">{$i18n.t('Web Search')}</div>
					</div>

					<Switch bind:state={webSearchEnabled} />
				</div>

				<hr class="border-gray-100 dark:border-gray-800 my-1" />
			{/if}

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800  rounded-xl"
				on:click={() => {
					uploadFilesHandler();
				}}
			>
				<DocumentArrowUpSolid />
				<div class="flex items-center">{$i18n.t('Upload Files')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
