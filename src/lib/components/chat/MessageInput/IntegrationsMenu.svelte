<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	import { config, user, tools as _tools, mobile, settings, toolServers } from '$lib/stores';

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
	import ValvesModal from '$lib/components/workspace/common/ValvesModal.svelte';
	import { getOAuthClientAuthorizationUrl } from '$lib/apis/configs';
	import { partition } from 'd3-hierarchy';

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

	let show = false;
	let tab = '';

	let showValvesModal = false;

	let selectedValvesType = 'tool';
	let selectedValvesItemId = null;

	let tools = null;

	$: if (show) {
		init();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const init = async () => {
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		if ($_tools) {
			tools = $_tools.reduce((a, tool, i, arr) => {
				a[tool.id] = {
					name: tool.name,
					description: tool.meta.description,
					enabled: selectedToolIds.includes(tool.id),
					...tool
				};
				return a;
			}, {});
		}

		if ($toolServers) {
			for (const serverIdx in $toolServers) {
				const server = $toolServers[serverIdx];
				if (server.info) {
					tools[`direct_server:${serverIdx}`] = {
						name: server?.info?.title ?? server.url,
						description: server.info.description ?? '',
						enabled: selectedToolIds.includes(`direct_server:${serverIdx}`)
					};
				}
			}
		}

		selectedToolIds = selectedToolIds.filter((id) => Object.keys(tools).includes(id));
	};
</script>

<ValvesModal
	bind:show={showValvesModal}
	userValves={true}
	type={selectedValvesType}
	id={selectedValvesItemId ?? null}
	on:save={async () => {
		await tick();
	}}
/>

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
	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-70 rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
			sideOffset={4}
			alignOffset={-6}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }}>
					{#if tools}
						{#if Object.keys(tools).length > 0}
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									tab = 'tools';
								}}
							>
								<Wrench />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Tools')}
										<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
									</div>

									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>
						{/if}
					{:else}
						<div class="py-4">
							<Spinner />
						</div>
					{/if}

					{#if toggleFilters && toggleFilters.length > 0}
						{#each toggleFilters.sort( (a, b) => a.name.localeCompare( b.name, undefined, { sensitivity: 'base' } ) ) as filter, filterIdx (filter.id)}
							<Tooltip content={filter?.description} placement="top-start">
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
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
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
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
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
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
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
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
				</div>
			{:else if tab === 'tools' && tools}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Tools')}
								<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
							</div>
						</div>
					</button>

					{#each Object.keys(tools) as toolId}
						<button
							class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={(e) => {
								if (!(tools[toolId]?.authenticated ?? true)) {
									e.preventDefault();

									let parts = toolId.split(':');
									let serverId = parts?.at(-1) ?? toolId;

									const authUrl = getOAuthClientAuthorizationUrl(serverId, 'mcp');
									window.open(authUrl, '_blank', 'noopener');
								} else {
									tools[toolId].enabled = !tools[toolId].enabled;
								}
							}}
						>
							{#if !(tools[toolId]?.authenticated ?? true)}
								<!-- make it slighly darker and not clickable -->
								<div class="absolute inset-0 opacity-50 rounded-xl cursor-not-allowed z-10" />
							{/if}
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<Tooltip content={tools[toolId]?.name ?? ''} placement="top">
										<div class="shrink-0">
											<Wrench />
										</div>
									</Tooltip>
									<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
										<div class=" truncate">{tools[toolId].name}</div>
									</Tooltip>
								</div>
							</div>

							{#if tools[toolId]?.has_user_valves}
								<div class=" shrink-0">
									<Tooltip content={$i18n.t('Valves')}>
										<button
											class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
											type="button"
											on:click={(e) => {
												e.stopPropagation();
												e.preventDefault();
												selectedValvesType = 'tool';
												selectedValvesItemId = toolId;
												showValvesModal = true;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
												/>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
												/>
											</svg>
										</button>
									</Tooltip>
								</div>
							{/if}

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
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
