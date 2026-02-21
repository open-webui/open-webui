<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	import { config, user, tools as _tools, mobile, settings, toolServers } from '$lib/stores';

	import { getOAuthClientAuthorizationUrl } from '$lib/apis/configs';
	import { getTools, getBuiltinToolCategories } from '$lib/apis/tools';

	import {
		getAlwaysApproved,
		removeAlwaysApproved,
		clearAllAlwaysApproved,
		getYoloStatus,
		setYolo,
		clearYolo,
		pendingYolo,
		setPendingYolo,
		getPendingYoloAsStatus,
		type AlwaysApprovedMap,
		type YoloStatus
	} from '$lib/stores/toolApproval';

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
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Note from '$lib/components/icons/Note.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	const i18n = getContext('i18n');

	export let chatId = '';

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

	export let onShowValves: Function;
	export let onClose: Function;
	export let closeOnOutsideClick = true;

	let show = false;
	let tab = '';

	let tools: Record<string, any> | null = null;

	// YOLO and Always Approved state
	let alwaysApproved: AlwaysApprovedMap = {};
	let yoloStatus: YoloStatus = { yolo_all: false, yolo_functions: {} };

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

		if (featureTools.length === 0 && builtinTools.length === 0) {
			await loadBuiltinTools();
		}

		if ($_tools) {
			tools = $_tools.reduce((a: Record<string, any>, tool: any) => {
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
					tools = tools || {};
					tools[`direct_server:${serverIdx}`] = {
						name: server?.info?.title ?? server.url,
						description: server.info.description ?? '',
						enabled: selectedToolIds.includes(`direct_server:${serverIdx}`)
					};
				}
			}
		}

		if (tools) {
			selectedToolIds = selectedToolIds.filter((id) => Object.keys(tools!).includes(id));
		}
	};

	const loadAlwaysApproved = async () => {
		if (chatId) {
			alwaysApproved = await getAlwaysApproved(chatId);
		}
	};

	const loadYoloStatus = async () => {
		if (chatId) {
			yoloStatus = await getYoloStatus(chatId);
		} else {
			yoloStatus = getPendingYoloAsStatus();
		}
	};

	// Builtin tools for YOLO menu, fetched from backend.
	// "Feature tools" (web search, image gen, code interpreter) are shown conditionally
	// via existing show* flags. "Builtin tools" (the rest) are shown dynamically.
	interface BuiltinTool {
		id: string;
		name: string;
		parentIds: string[];
	}

	let featureTools: BuiltinTool[] = [];
	let builtinTools: BuiltinTool[] = [];

	async function loadBuiltinTools() {
		try {
			const categories = await getBuiltinToolCategories(localStorage.token);
			if (categories) {
				const features: BuiltinTool[] = [];
				const builtin: BuiltinTool[] = [];
				for (const [id, cat] of Object.entries(categories)) {
					const entry: BuiltinTool = {
						id,
						name: cat.name,
						parentIds: cat.functions.map((fn: string) => `builtin:${fn}`)
					};
					if (cat.feature) {
						features.push(entry);
					} else {
						builtin.push(entry);
					}
				}
				featureTools = features;
				builtinTools = builtin;
			}
		} catch (e) {
			console.error('Failed to load builtin tool categories:', e);
		}
	}

	// Feature tools are gated by their existing show* flags
	$: visibleFeatureTools = featureTools.filter(
		(t) =>
			(t.id === 'web_search' && showWebSearchButton) ||
			(t.id === 'image_generation' && showImageGenerationButton) ||
			(t.id === 'code_interpreter' && showCodeInterpreterButton)
	);

	function isBuiltinToolYolo(tool: BuiltinTool): boolean {
		return tool.parentIds.every((pid) => {
			const funcs = yoloStatus.yolo_functions[pid];
			return funcs && (funcs.includes('*') || funcs.length > 0);
		});
	}

	async function toggleBuiltinToolYolo(tool: BuiltinTool) {
		const isOn = isBuiltinToolYolo(tool);
		if (chatId) {
			let result: YoloStatus | null = null;
			for (const pid of tool.parentIds) {
				result = await setYolo(chatId, 'parent', !isOn, pid);
			}
			if (result) yoloStatus = result;
		} else {
			for (const pid of tool.parentIds) {
				setPendingYolo('parent', !isOn, pid);
			}
			yoloStatus = getPendingYoloAsStatus();
		}
	}

	async function toggleYoloAll() {
		const newState = !yoloStatus.yolo_all;
		if (chatId) {
			const result = await setYolo(chatId, 'all', newState);
			if (result) yoloStatus = result;
		} else {
			setPendingYolo('all', newState);
			yoloStatus = getPendingYoloAsStatus();
		}
	}

	async function toggleToolYolo(toolId: string) {
		const parentFuncs = yoloStatus.yolo_functions[toolId];
		const isOn = parentFuncs && (parentFuncs.includes('*') || parentFuncs.length > 0);
		if (chatId) {
			const result = await setYolo(chatId, 'parent', !isOn, toolId);
			if (result) yoloStatus = result;
		} else {
			setPendingYolo('parent', !isOn, toolId);
			yoloStatus = getPendingYoloAsStatus();
		}
	}

	// Helper: check if a function is in YOLO
	function isFunctionYolo(parentId: string, funcName: string): boolean {
		const parentFuncs = yoloStatus.yolo_functions[parentId];
		if (!parentFuncs) return false;
		return parentFuncs.includes('*') || parentFuncs.includes(funcName);
	}

	// Helper: count always-approved entries
	$: alwaysApprovedCount = Object.values(alwaysApproved).reduce(
		(sum, children) => sum + children.length,
		0
	);
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			tab = '';
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Integrations')} placement="top">
		<slot />
	</Tooltip>
	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
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
							<!-- Tools -->
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => {
									tab = 'tools';
								}}
							>
								<Wrench />
								<div class="flex items-center w-full justify-between">
									<div class="line-clamp-1">
										{$i18n.t('Tools')}
										<span class="ml-0.5 text-gray-500">{Object.keys(tools).length}</span>
									</div>
									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>

							<!-- YOLO Mode -->
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={async () => {
									await loadYoloStatus();
									tab = 'yolo';
								}}
							>
								<svg
									class="size-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
								</svg>
								<div class="flex items-center w-full justify-between">
									<div class="line-clamp-1">
										{$i18n.t('YOLO Mode')}
										{#if yoloStatus.yolo_all}
											<span class="ml-0.5 text-amber-500 text-xs font-medium">ON</span>
										{/if}
									</div>
									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>

							<!-- Always Allowed -->
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={async () => {
									if (chatId) await loadAlwaysApproved();
									tab = 'always-allowed';
								}}
							>
								<svg
									class="size-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
								</svg>
								<div class="flex items-center w-full justify-between">
									<div class="line-clamp-1">
										{$i18n.t('Always Allowed')}
										{#if alwaysApprovedCount > 0}
											<span class="ml-0.5 text-gray-500">{alwaysApprovedCount}</span>
										{/if}
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
															class="size-3.5 {filter.icon.includes('data:image/svg')
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

											<div class="truncate">{filter?.name}</div>
										</div>
									</div>

									{#if filter?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
										<div class="shrink-0">
											<Tooltip content={$i18n.t('Valves')}>
												<button
													class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
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
													<Knobs />
												</button>
											</Tooltip>
										</div>
									{/if}

									<div class="shrink-0">
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
										<div class="truncate">{$i18n.t('Web Search')}</div>
									</div>
								</div>

								<div class="shrink-0">
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
										<div class="truncate">{$i18n.t('Image')}</div>
									</div>
								</div>

								<div class="shrink-0">
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
										<div class="truncate">{$i18n.t('Code Interpreter')}</div>
									</div>
								</div>

								<div class="shrink-0">
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
				<!-- Tools sub-menu (existing) -->
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
								<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10" />
							{/if}
							<div class="flex-1 truncate">
								<div class="flex flex-1 gap-2 items-center">
									<Tooltip content={tools[toolId]?.name ?? ''} placement="top">
										<div class="shrink-0">
											<Wrench />
										</div>
									</Tooltip>
									<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
										<div class="truncate">{tools[toolId].name}</div>
									</Tooltip>
								</div>
							</div>

							{#if tools[toolId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
								<div class="shrink-0">
									<Tooltip content={$i18n.t('Valves')}>
										<button
											class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
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
											<Knobs />
										</button>
									</Tooltip>
								</div>
							{/if}

							<div class="shrink-0">
								<Switch state={tools[toolId].enabled} />
							</div>
						</button>
					{/each}
				</div>
			{:else if tab === 'yolo' && tools}
				<!-- YOLO Mode sub-menu -->
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<div class="flex items-center w-full justify-between">
							<div>{$i18n.t('YOLO Mode')}</div>
						</div>
					</button>

					<!-- YOLO All toggle -->
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={toggleYoloAll}
					>
						<div class="flex-1 truncate">
							<div class="flex flex-1 gap-2 items-center">
								<svg
									class="size-4 text-amber-500"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
								</svg>
								<div class="truncate font-medium">{$i18n.t('YOLO All Tools')}</div>
							</div>
						</div>
						<div class="shrink-0">
							<Switch state={yoloStatus.yolo_all} />
						</div>
					</button>

					{#if !yoloStatus.yolo_all}
						<!-- Default Features YOLO toggles (gated by existing show* flags) -->
						{#if visibleFeatureTools.length > 0}
							<div class="border-t border-gray-100 dark:border-gray-800 my-1" />
							<div class="px-3 py-1 text-xs font-medium text-gray-400 dark:text-gray-500">
								{$i18n.t('Default Features')}
							</div>
							{#each visibleFeatureTools as featureTool (featureTool.id)}
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									on:click={() => toggleBuiltinToolYolo(featureTool)}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												{#if featureTool.id === 'web_search'}
													<GlobeAlt />
												{:else if featureTool.id === 'image_generation'}
													<Photo className="size-4" strokeWidth="1.5" />
												{:else if featureTool.id === 'code_interpreter'}
													<Terminal className="size-3.5" strokeWidth="1.75" />
												{/if}
											</div>
											<div class="truncate">{$i18n.t(featureTool.name)}</div>
										</div>
									</div>
									<div class="shrink-0">
										<Switch state={isBuiltinToolYolo(featureTool)} />
									</div>
								</button>
							{/each}
						{/if}

						<!-- Builtin Tools YOLO toggles (loaded dynamically from backend) -->
						{#if builtinTools.length > 0}
							<div class="border-t border-gray-100 dark:border-gray-800 my-1" />
							<div class="px-3 py-1 text-xs font-medium text-gray-400 dark:text-gray-500">
								{$i18n.t('Builtin Tools')}
							</div>
							{#each builtinTools as builtinTool (builtinTool.id)}
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									on:click={() => toggleBuiltinToolYolo(builtinTool)}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												{#if builtinTool.id === 'time'}
													<Calendar className="size-4" strokeWidth="1.5" />
												{:else if builtinTool.id === 'memory'}
													<Database className="size-4" strokeWidth="1.5" />
												{:else if builtinTool.id === 'chats'}
													<ChatBubble className="size-4" strokeWidth="1.5" />
												{:else if builtinTool.id === 'notes'}
													<Note className="size-4" strokeWidth="1.5" />
												{:else if builtinTool.id === 'knowledge'}
													<BookOpen className="size-4" strokeWidth="1.5" />
												{:else if builtinTool.id === 'channels'}
													<Hashtag className="size-4" strokeWidth="1.5" />
												{:else}
													<Wrench />
												{/if}
											</div>
											<div class="truncate">{$i18n.t(builtinTool.name)}</div>
										</div>
									</div>
									<div class="shrink-0">
										<Switch state={isBuiltinToolYolo(builtinTool)} />
									</div>
								</button>
							{/each}
						{/if}

						{#if (visibleFeatureTools.length > 0 || builtinTools.length > 0) && Object.keys(tools).length > 0}
							<div class="border-t border-gray-100 dark:border-gray-800 my-1" />
							<div class="px-3 py-1 text-xs font-medium text-gray-400 dark:text-gray-500">
								{$i18n.t('Workspace Tools')}
							</div>
						{/if}

						<!-- Per-tool YOLO toggles -->
						{#each Object.keys(tools) as toolId}
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								on:click={() => toggleToolYolo(toolId)}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Wrench />
										</div>
										<div class="truncate">{tools[toolId].name}</div>
									</div>
								</div>
								<div class="shrink-0">
									<Switch
										state={(() => {
											const parentFuncs = yoloStatus.yolo_functions[toolId];
											return !!(
												parentFuncs &&
												(parentFuncs.includes('*') || parentFuncs.length > 0)
											);
										})()}
									/>
								</div>
							</button>
						{/each}
					{/if}
				</div>
			{:else if tab === 'always-allowed'}
				<!-- Always Allowed sub-menu -->
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<div class="flex items-center w-full justify-between">
							<div>{$i18n.t('Always Allowed')}</div>
						</div>
					</button>

					{#if alwaysApprovedCount > 0}
						<!-- Revoke All -->
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
							on:click={async () => {
								await clearAllAlwaysApproved(chatId);
								alwaysApproved = {};
							}}
						>
							<div class="flex flex-1 gap-2 items-center">
								<svg
									class="size-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<line x1="18" y1="6" x2="6" y2="18" />
									<line x1="6" y1="6" x2="18" y2="18" />
								</svg>
								<div class="truncate">{$i18n.t('Revoke All')}</div>
							</div>
						</button>

						<div class="border-t border-gray-100 dark:border-gray-800 my-1" />

						<!-- Tree of always-approved entries grouped by parent -->
						{#each Object.entries(alwaysApproved) as [parentId, children], idx}
							{#if idx > 0}
								<div class="border-t border-gray-100 dark:border-gray-800 my-1" />
							{/if}

							<!-- Parent header row -->
							<div
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Wrench />
										</div>
										<div class="truncate font-medium">{parentId}</div>
									</div>
								</div>
								<button
									class="shrink-0 text-red-500 hover:text-red-700 dark:hover:text-red-300 transition p-0.5"
									title={$i18n.t('Revoke tool')}
									on:click={async () => {
										await removeAlwaysApproved(chatId, parentId, '', 'parent');
										alwaysApproved = await getAlwaysApproved(chatId);
									}}
								>
									<svg
										class="size-4"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<line x1="18" y1="6" x2="6" y2="18" />
										<line x1="6" y1="6" x2="18" y2="18" />
									</svg>
								</button>
							</div>

							<!-- Children -->
							{#if children.includes('*')}
								<div
									class="flex w-full items-center pl-9 pr-3 py-1 text-xs text-gray-500 dark:text-gray-400 italic"
								>
									{$i18n.t('All functions approved')}
								</div>
							{:else}
								{#each children as funcName}
									<div
										class="flex w-full justify-between gap-2 items-center pl-9 pr-3 py-1 text-sm rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									>
										<div class="flex-1 truncate text-gray-700 dark:text-gray-300">
											{funcName}
										</div>
										<button
											class="shrink-0 text-red-500 hover:text-red-700 dark:hover:text-red-300 transition p-0.5"
											title={$i18n.t('Revoke function')}
											on:click={async () => {
												await removeAlwaysApproved(chatId, parentId, funcName, 'function');
												alwaysApproved = await getAlwaysApproved(chatId);
											}}
										>
											<svg
												class="size-3.5"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<line x1="18" y1="6" x2="6" y2="18" />
												<line x1="6" y1="6" x2="18" y2="18" />
											</svg>
										</button>
									</div>
								{/each}
							{/if}
						{/each}
					{:else}
						<div class="px-3 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
							{$i18n.t('No tools are always allowed')}
						</div>
					{/if}
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
