<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';

	import { config, user, tools as _tools, mobile, settings, toolServers } from '$lib/stores';

	import { getOAuthClientAuthorizationUrl } from '$lib/apis/configs';
	import { getTools } from '$lib/apis/tools';

	import Knobs from '$lib/components/icons/Knobs.svelte';
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
	import Cog6 from '$lib/components/icons/Cog6.svelte';

	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let nativeWebSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onShowValves: Function;
	export let onClose: Function;
	export let closeOnOutsideClick = true;

	// Clear Context props
	export let history: any = null;
	export let onToggleContextBreak: () => void = () => {};

	let show = false;
	let tab = '';

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
			class="w-60 md:w-64 max-w-[85vw] md:max-w-64 rounded-2xl px-1.5 py-1.5 border border-gray-300/40 dark:border-gray-700/60 z-50 bg-white dark:bg-gray-900 dark:text-white shadow-lg shadow-gray-300/30 dark:shadow-gray-950/50 max-h-80 overflow-y-auto overflow-x-hidden scrollbar-thin"
			sideOffset={4}
			alignOffset={-6}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }} class="space-y-0.5">
					{#if tools}
						{#if Object.keys(tools).length > 0}
							<button
								class="group flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									tab = 'tools';
								}}
							>
								<div
									class={selectedToolIds.length > 0
										? 'text-blue-500 dark:text-blue-400'
										: 'text-gray-500 dark:text-gray-400'}
								>
									<Wrench className="size-[18px]" strokeWidth="2" />
								</div>

								<div class="flex items-center w-full justify-between">
									<div class="flex items-center gap-2">
										<span class="font-medium text-gray-700 dark:text-gray-200"
											>{$i18n.t('Tools')}</span
										>
										{#if selectedToolIds.length > 0}
											<span
												class="px-1.5 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400"
												>{selectedToolIds.length}</span
											>
										{/if}
									</div>

									<div
										class="text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors"
									>
										<ChevronRight className="size-4" />
									</div>
								</div>
							</button>
						{/if}
					{:else}
						<div class="py-6 flex justify-center">
							<Spinner />
						</div>
					{/if}

					{#if toggleFilters && toggleFilters.length > 0}
						{#each toggleFilters.sort( (a, b) => a.name.localeCompare( b.name, undefined, { sensitivity: 'base' } ) ) as filter, filterIdx (filter.id)}
							<Tooltip content={filter?.description} placement="top-start">
								<button
									class="group flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 {selectedFilterIds.includes(
										filter.id
									)
										? 'bg-violet-50 dark:bg-violet-950/40'
										: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
									on:click={() => {
										if (selectedFilterIds.includes(filter.id)) {
											selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
										} else {
											selectedFilterIds = [...selectedFilterIds, filter.id];
										}
									}}
								>
									<div
										class={selectedFilterIds.includes(filter.id)
											? 'text-violet-500 dark:text-violet-400'
											: 'text-gray-500 dark:text-gray-400'}
									>
										{#if filter?.icon}
											<img
												src={filter.icon}
												class="size-[18px] {filter.icon.includes('svg') ? 'dark:invert-[80%]' : ''}"
												style="fill: currentColor;"
												alt={filter.name}
											/>
										{:else}
											<Sparkles className="size-[18px]" strokeWidth="2" />
										{/if}
									</div>

									<div class="flex-1 flex items-center justify-between min-w-0">
										<span class="font-medium text-gray-700 dark:text-gray-200 truncate"
											>{filter?.name}</span
										>

										<div class="flex items-center gap-2 ml-2">
											{#if filter?.has_user_valves}
												<Tooltip content={$i18n.t('Valves')}>
													<button
														class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
														type="button"
														on:click={(e) => {
															e.stopPropagation();
															e.preventDefault();
															onShowValves({
																type: 'function',
																id: filter.id
															});
														}}
													>
														<Knobs className="size-3.5" />
													</button>
												</Tooltip>
											{/if}

											<Switch
												state={selectedFilterIds.includes(filter.id)}
												on:change={async (e) => {
													const state = e.detail;
													await tick();
												}}
											/>
										</div>
									</div>
								</button>
							</Tooltip>
						{/each}
					{/if}

					{#if showWebSearchButton || showImageGenerationButton || showCodeInterpreterButton}
						{#if tools && Object.keys(tools).length > 0}
							<div class="mx-3 my-1 h-px bg-gray-200 dark:bg-gray-700/70" />
						{/if}
					{/if}

					{#if showWebSearchButton}
						<Tooltip content={$i18n.t('Search the internet')} placement="top-start">
							<button
								class="group flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 {webSearchEnabled
									? 'bg-cyan-50 dark:bg-cyan-950/40'
									: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
								on:click={() => {
									webSearchEnabled = !webSearchEnabled;
									if (webSearchEnabled) {
										nativeWebSearchEnabled = false;
									}
								}}
							>
								<div
									class={webSearchEnabled
										? 'text-cyan-500 dark:text-cyan-400'
										: 'text-gray-500 dark:text-gray-400'}
								>
									<GlobeAlt className="size-[18px]" strokeWidth="2" />
								</div>

								<div class="flex-1 flex items-center justify-between">
									<span class="font-medium text-gray-700 dark:text-gray-200"
										>{$i18n.t('Web Search')}</span
									>

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

					<Tooltip content={$i18n.t('Use model built-in web search')} placement="top-start">
						<button
							class="group flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 {nativeWebSearchEnabled
								? 'bg-emerald-50 dark:bg-emerald-950/40'
								: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
							on:click={() => {
								nativeWebSearchEnabled = !nativeWebSearchEnabled;
								if (nativeWebSearchEnabled) {
									webSearchEnabled = false;
								}
							}}
						>
							<div
								class={nativeWebSearchEnabled
									? 'text-emerald-500 dark:text-emerald-400'
									: 'text-gray-500 dark:text-gray-400'}
							>
								<GlobeAlt className="size-[18px]" strokeWidth="2" />
							</div>

							<div class="flex-1 flex items-center justify-between">
								<span class="font-medium text-gray-700 dark:text-gray-200"
									>{$i18n.t('Native Web Search')}</span
								>

								<Switch
									state={nativeWebSearchEnabled}
									on:change={async (e) => {
										await tick();
									}}
								/>
							</div>
						</button>
					</Tooltip>

					{#if showImageGenerationButton}
						<Tooltip content={$i18n.t('Generate an image')} placement="top-start">
							<button
								class="group flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 {imageGenerationEnabled
									? 'bg-pink-50 dark:bg-pink-950/40'
									: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
								on:click={() => {
									imageGenerationEnabled = !imageGenerationEnabled;
								}}
							>
								<div
									class={imageGenerationEnabled
										? 'text-pink-500 dark:text-pink-400'
										: 'text-gray-500 dark:text-gray-400'}
								>
									<Photo className="size-[18px]" strokeWidth="2" />
								</div>

								<div class="flex-1 flex items-center justify-between">
									<span class="font-medium text-gray-700 dark:text-gray-200"
										>{$i18n.t('Image')}</span
									>

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
								class="group flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 {codeInterpreterEnabled
									? 'bg-amber-50 dark:bg-amber-950/40'
									: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
								aria-pressed={codeInterpreterEnabled}
								aria-label={codeInterpreterEnabled
									? $i18n.t('Disable Code Interpreter')
									: $i18n.t('Enable Code Interpreter')}
								on:click={() => {
									codeInterpreterEnabled = !codeInterpreterEnabled;
								}}
							>
								<div
									class={codeInterpreterEnabled
										? 'text-amber-500 dark:text-amber-400'
										: 'text-gray-500 dark:text-gray-400'}
								>
									<Terminal className="size-[18px]" strokeWidth="2" />
								</div>

								<div class="flex-1 flex items-center justify-between">
									<span class="font-medium text-gray-700 dark:text-gray-200"
										>{$i18n.t('Code Interpreter')}</span
									>

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

					<!-- Clear Context Button - Last Item -->
					{#if history?.currentId}
						<div class="mx-3 my-1 h-px bg-gray-200 dark:bg-gray-700/70" />
						<Tooltip content={$i18n.t('Clear Context')} placement="top-start">
							<button
								class="group flex w-full gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 hover:bg-red-50 dark:hover:bg-red-950/40"
								on:click={() => {
									onToggleContextBreak();
									show = false;
								}}
							>
								<div
									class="text-gray-500 dark:text-gray-400 group-hover:text-red-500 dark:group-hover:text-red-400 transition-colors"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-[18px]"
									>
										<path
											fill-rule="evenodd"
											d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 3.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>

								<span
									class="font-medium text-gray-700 dark:text-gray-200 group-hover:text-red-600 dark:group-hover:text-red-400 transition-colors"
									>{$i18n.t('Clear Context')}</span
								>
							</button>
						</Tooltip>
					{/if}
				</div>
			{:else if tab === 'tools' && tools}
				<div in:fly={{ x: 20, duration: 150 }} class="space-y-0.5">
					<div class="flex items-center justify-between gap-2">
						<button
							class="group flex flex-1 gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-800/50"
							on:click={() => {
								tab = '';
							}}
						>
							<div class="text-gray-500 dark:text-gray-400">
								<ChevronLeft className="size-[18px]" strokeWidth="2" />
							</div>

							<div class="flex items-center gap-2">
								<span class="font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Tools')}</span>
								<span
									class="px-1.5 py-0.5 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
									>{Object.keys(tools).length}</span
								>
							</div>
						</button>

						<Tooltip content={$i18n.t('Manage Tools')} placement="top">
							<button
								class="group p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl transition-all duration-200"
								on:click={() => {
									goto('/workspace/tools');
									show = false;
								}}
							>
								<Cog6 className="size-[18px]" strokeWidth="2" />
							</button>
						</Tooltip>
					</div>

					<div class="mx-3 my-1 h-px bg-gray-200 dark:bg-gray-700/70" />

					{#each Object.keys(tools) as toolId}
						<button
							class="group relative flex w-full justify-between gap-2.5 items-center px-3 py-2 text-sm cursor-pointer rounded-xl transition-all duration-200 {tools[
								toolId
							].enabled
								? 'bg-blue-50 dark:bg-blue-950/40'
								: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
							on:click={async (e) => {
								if (!(tools[toolId]?.authenticated ?? true)) {
									e.preventDefault();

									let parts = toolId.split(':');
									let serverId = parts?.at(-1) ?? toolId;

									const authUrl = getOAuthClientAuthorizationUrl(serverId, 'mcp');
									window.open(authUrl, '_self', 'noopener');
								} else {
									tools[toolId].enabled = !tools[toolId].enabled;

									const state = tools[toolId].enabled;
									await tick();

									if (state) {
										selectedToolIds = [...selectedToolIds, toolId];
									} else {
										selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
									}
								}
							}}
						>
							{#if !(tools[toolId]?.authenticated ?? true)}
								<div
									class="absolute inset-0 bg-gray-100/50 dark:bg-gray-800/50 rounded-xl cursor-pointer z-10"
								/>
							{/if}

							<div class="flex items-center gap-2.5 min-w-0 flex-1">
								<div
									class="shrink-0 {tools[toolId].enabled
										? 'text-blue-500 dark:text-blue-400'
										: 'text-gray-500 dark:text-gray-400'}"
								>
									<Wrench className="size-[18px]" strokeWidth="2" />
								</div>

								<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
									<span class="font-medium text-gray-700 dark:text-gray-200 truncate"
										>{tools[toolId].name}</span
									>
								</Tooltip>
							</div>

							<div class="flex items-center gap-2 shrink-0">
								{#if tools[toolId]?.has_user_valves}
									<Tooltip content={$i18n.t('Valves')}>
										<button
											class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
											type="button"
											on:click={(e) => {
												e.stopPropagation();
												e.preventDefault();
												onShowValves({
													type: 'tool',
													id: toolId
												});
											}}
										>
											<Knobs className="size-3.5" />
										</button>
									</Tooltip>
								{/if}

								<Switch state={tools[toolId].enabled} />
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
