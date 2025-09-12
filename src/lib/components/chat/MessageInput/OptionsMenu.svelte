<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, onMount, tick } from 'svelte';

	import { config, user, tools as _tools, mobile, settings } from '$lib/stores';

	import { getTools } from '$lib/apis/tools';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onClose: Function;

	let tools = null;
	let show = false;
	let showAllTools = false;

	$: if (show) {
		init();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const init = async () => {
		await _tools.set(await getTools(localStorage.token));
		if ($_tools) {
			tools = $_tools.reduce((a, tool, i, arr) => {
				a[tool.id] = {
					name: tool.name,
					description: tool.meta.description,
					enabled: selectedToolIds.includes(tool.id)
				};
				return a;
			}, {});
			selectedToolIds = selectedToolIds.filter((id) => $_tools?.some((tool) => tool.id === id));
		}
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
	<Tooltip content={$i18n.t('Integrations')} placement="top">
		<slot />
	</Tooltip>

	<!-- class="w-full max-w-[240px] rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-850 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg transition max-h-96 overflow-y-auto scrollbar-thin" -->

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[240px] rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-850 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto scrollbar-thin"
			sideOffset={4}
			alignOffset={-6}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if tools}
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800"
					on:click={() => {
						showAllTools = !showAllTools;
					}}
				>
					{#if !showAllTools}
						<Wrench />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Tools')}
								<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
							</div>

							<div class="text-gray-500">
								<ChevronRight />
							</div>
						</div>
					{:else}
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Tools')}
								<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
							</div>
						</div>
					{/if}
				</button>
			{:else}
				<div class="py-4">
					<Spinner />
				</div>
			{/if}

			{#if showAllTools}
				{#each Object.keys(tools) as toolId}
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800"
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
								<div class="shrink-0">
									<Wrench />
								</div>

								<div class=" truncate">{tools[toolId].name}</div>
							</Tooltip>
						</div>

						<div class=" shrink-0">
							<Switch
								state={tools[toolId].enabled}
								on:change={async (e) => {
									const state = e.detail;
									await tick();
									if (state) {
										selectedToolIds = [...selectedToolIds, toolId];
									} else {
										selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
									}
								}}
							/>
						</div>
					</button>
				{/each}
			{:else}
				{#if toggleFilters && toggleFilters.length > 0}
					{#each toggleFilters.sort( (a, b) => a.name.localeCompare( b.name, undefined, { sensitivity: 'base' } ) ) as filter, filterIdx (filter.id)}
						<Tooltip content={filter?.description} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800"
								on:click={() => {
									if (selectedFilterIds.includes(filter.id)) {
										selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
									} else {
										selectedFilterIds = [...selectedFilterIds, filter.id];
									}
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											{#if filter?.icon}
												<div class="size-4 items-center flex justify-center">
													<img
														src={filter.icon}
														class="size-3.5 {filter.icon.includes('svg')
															? 'dark:invert-[80%]'
															: ''}"
														style="fill: currentColor;"
														alt={filter.name}
													/>
												</div>
											{:else}
												<Sparkles className="size-4" strokeWidth="1.75" />
											{/if}
										</div>

										<div class=" truncate">{filter?.name}</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={selectedFilterIds.includes(filter.id)}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>
					{/each}
				{/if}

				{#if showWebSearchButton}
					<Tooltip content={$i18n.t('Search the internet')} placement="top-start">
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800"
							on:click={() => {
								webSearchEnabled = !webSearchEnabled;
							}}
						>
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<div class="shrink-0">
										<GlobeAlt />
									</div>

									<div class=" truncate">{$i18n.t('Web Search')}</div>
								</div>
							</div>

							<div class=" shrink-0">
								<Switch
									state={webSearchEnabled}
									on:change={async (e) => {
										const state = e.detail;
										await tick();
									}}
								/>
							</div>
						</button>
					</Tooltip>
				{/if}

				{#if showImageGenerationButton}
					<Tooltip content={$i18n.t('Generate an image')} placement="top-start">
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800"
							on:click={() => {
								imageGenerationEnabled = !imageGenerationEnabled;
							}}
						>
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<div class="shrink-0">
										<Photo className="size-4" strokeWidth="1.5" />
									</div>

									<div class=" truncate">{$i18n.t('Image')}</div>
								</div>
							</div>

							<div class=" shrink-0">
								<Switch
									state={imageGenerationEnabled}
									on:change={async (e) => {
										const state = e.detail;
										await tick();
									}}
								/>
							</div>
						</button>
					</Tooltip>
				{/if}

				{#if showCodeInterpreterButton}
					<Tooltip content={$i18n.t('Execute code for analysis')} placement="top-start">
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800"
							aria-pressed={codeInterpreterEnabled}
							aria-label={codeInterpreterEnabled
								? $i18n.t('Disable Code Interpreter')
								: $i18n.t('Enable Code Interpreter')}
							on:click={() => {
								codeInterpreterEnabled = !codeInterpreterEnabled;
							}}
						>
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<div class="shrink-0">
										<Terminal className="size-3.5" strokeWidth="1.75" />
									</div>

									<div class=" truncate">{$i18n.t('Code Interpreter')}</div>
								</div>
							</div>

							<div class=" shrink-0">
								<Switch
									state={codeInterpreterEnabled}
									on:change={async (e) => {
										const state = e.detail;
										await tick();
									}}
								/>
							</div>
						</button>
					</Tooltip>
				{/if}
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
