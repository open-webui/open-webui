<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, onMount } from 'svelte';

	import { config, user, tools as _tools } from '$lib/stores';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import { getTools } from '$lib/apis/tools';

	const i18n = getContext('i18n');

	export let uploadFilesHandler: Function;

	export let availableToolIds: string[] = [];
	export let selectedToolIds: string[] = [];

	export let webSearchEnabled: boolean;

	export let onClose: Function;

	let tools = {};
	let show = false;

	$: if (show) {
		init();
	}

	$: if (tools) {
		selectedToolIds = Object.keys(tools).filter((toolId) => tools[toolId]?.enabled ?? false);
	}

	const init = async () => {
		console.log('init');
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		tools = $_tools.reduce((a, tool, i, arr) => {
			a[tool.id] = {
				name: tool.name,
				description: tool.meta.description,
				enabled: selectedToolIds.includes(tool.id)
			};
			return a;
		}, {});
	};
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
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
							on:click={() => {
								tools[toolId].enabled = !tools[toolId].enabled;
							}}
						>
							<div class="flex-1 truncate">
								<Tooltip
									content={tools[toolId]?.description ?? ''}
									placement="top-start"
									className="flex flex-1 gap-2 items-center"
								>
									<WrenchSolid />

									<div class=" truncate">{tools[toolId].name}</div>
								</Tooltip>
							</div>

							<div class=" flex-shrink-0">
								<Switch state={tools[toolId].enabled} />
							</div>
						</button>
					{/each}
				</div>

				<hr class="border-gray-100 dark:border-gray-800 my-1" />
			{/if}

			{#if $config?.features?.enable_web_search}
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
					on:click={() => {
						webSearchEnabled = !webSearchEnabled;
					}}
				>
					<div class="flex-1 flex items-center gap-2">
						<GlobeAltSolid />
						<div class=" line-clamp-1">{$i18n.t('Web Search')}</div>
					</div>

					<Switch state={webSearchEnabled} />
				</button>

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
