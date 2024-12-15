<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';
	import { createPicker } from '$lib/utils/google-drive-picker';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import { config } from '$lib/stores';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';

	const i18n = getContext('i18n');

	export let uploadFilesHandler: Function;
	export let uploadGoogleDriveHandler: Function;

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
							<div class="flex-1">
								<Tooltip
									content={tools[toolId]?.description ?? ''}
									placement="top-start"
									className="flex flex-1  gap-2 items-center"
								>
									<WrenchSolid />

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
				class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					uploadFilesHandler();
				}}
			>
				<DocumentArrowUpSolid />
				<div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					uploadGoogleDriveHandler();
				}}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 87.3 78" class="w-5 h-5">
					<path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
					<path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47"/>
					<path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335"/>
					<path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
					<path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
					<path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
				</svg>
				<div class="line-clamp-1">{$i18n.t('Google Drive')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
