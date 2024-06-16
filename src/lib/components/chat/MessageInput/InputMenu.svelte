<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import { config } from '$lib/stores';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';

	const i18n = getContext('i18n');

	export let uploadFilesHandler: Function;

	export let selectedToolIds: string[] = [];
	export let webSearchEnabled: boolean;

	export let tools = {};
	export let onClose: Function;

	$: tools = Object.fromEntries(
		Object.keys(tools).map((toolId) => [
			toolId,
			{
				...tools[toolId],
				enabled: selectedToolIds.includes(toolId)
			}
		])
	);

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
			class="w-full max-w-[200px] rounded-xl px-1 py-1  border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
			sideOffset={15}
			alignOffset={-8}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			{#if Object.keys(tools).length > 0}
				<div class="  max-h-28 overflow-y-auto scrollbar-hidden">
					{#each Object.keys(tools) as toolId}
						<div
							class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
						>
							<div class="flex-1 flex items-center gap-2">
								<WrenchSolid />
								<Tooltip content={tools[toolId]?.description ?? ''} className="flex-1">
									<div class=" line-clamp-1">{tools[toolId].name}</div>
								</Tooltip>
							</div>

							<Switch
								bind:state={tools[toolId].enabled}
								on:change={(e) => {
									selectedToolIds = e.detail
										? [...selectedToolIds, toolId]
										: selectedToolIds.filter((id) => id !== toolId);
								}}
							/>
						</div>
					{/each}
				</div>

				<hr class="border-gray-100 dark:border-gray-800 my-1" />
			{/if}

			{#if $config?.features?.enable_web_search}
				<div
					class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
				>
					<div class="flex-1 flex items-center gap-2">
						<GlobeAltSolid />
						<div class=" line-clamp-1">{$i18n.t('Web Search')}</div>
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
				<div class=" line-clamp-1">{$i18n.t('Upload Files')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
