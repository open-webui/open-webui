<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { fly } from 'svelte/transition';

	import { user, tools as _tools, skills as _skills, toolServers } from '$lib/stores';

	import { deleteOAuthSession } from '$lib/apis/auths';
	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';

	import { toast } from 'svelte-sonner';

	import Knobs from '$lib/components/icons/Knobs.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SearchInput from './InputMenu/SearchInput.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LinkSlash from '$lib/components/icons/LinkSlash.svelte';

	const i18n = getContext('i18n') as any;

	type IntegrationItem = {
		id: string;
		name: string;
		description?: string;
		meta?: { description?: string };
		is_active?: boolean;
		authenticated?: boolean;
		has_user_valves?: boolean;
		[key: string]: any;
	};

	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];
	export let oauthRedirectHandler: Function = () => {};

	export let toggleFilters: {
		id: string;
		name: string;
		description?: string;
		icon?: string;
		has_user_valves?: boolean;
	}[] = [];
	export let selectedFilterIds: string[] = [];

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onShowValves: Function;
	export let onClose: Function;
	export let onWebSearchToggle: Function = () => {};
	export let closeOnOutsideClick = true;

	let show = false;
	let tab = '';

	let tools: Record<string, IntegrationItem> | null = null;
	let skills: Record<string, IntegrationItem> | null = null;
	let toolQuery = '';
	let skillQuery = '';
	let searchedToolQuery = '';
	let searchedSkillQuery = '';
	let toolSearchDebounceTimer: ReturnType<typeof setTimeout>;
	let skillSearchDebounceTimer: ReturnType<typeof setTimeout>;
	let toolRequestId = 0;
	let skillRequestId = 0;

	$: toolIds = Object.keys(tools ?? {});
	$: skillIds = Object.keys(skills ?? {});

	$: if (show && toolQuery !== searchedToolQuery) {
		scheduleToolSearch();
	}

	$: if (show && skillQuery !== searchedSkillQuery) {
		scheduleSkillSearch();
	}

	$: if (show) {
		init();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const init = async () => {
		await Promise.all([loadTools(), loadSkills()]);
	};

	const setTools = (toolItems: IntegrationItem[] | null, query = '') => {
		const q = query.trim().toLowerCase();
		const items = (toolItems ?? []).reduce<Record<string, IntegrationItem>>((a, tool) => {
			a[tool.id] = {
				...tool,
				name: tool.name,
				description: tool.meta?.description
			};
			return a;
		}, {});

		for (const serverIdx in ($toolServers ?? []) as any[]) {
			const server = (($toolServers ?? []) as any[])[serverIdx];
			if (server.info) {
				const name = server?.info?.title ?? server.url;
				if (q && !name.toLowerCase().includes(q)) {
					continue;
				}

				items[`direct_server:${serverIdx}`] = {
					id: `direct_server:${serverIdx}`,
					name,
					description: server.info.description ?? ''
				};
			}
		}

		tools = items;

		if (!q) {
			selectedToolIds = selectedToolIds.filter((id) => Object.keys(tools ?? {}).includes(id));
		}
	};

	const setSkills = (skillItems: IntegrationItem[] | null, query = '') => {
		skills = (skillItems ?? [])
			.filter((skill) => skill.is_active)
			.reduce<Record<string, IntegrationItem>>((a, skill) => {
				a[skill.id] = {
					...skill,
					name: skill.name,
					description: skill.description
				};
				return a;
			}, {});

		if (!query.trim()) {
			selectedSkillIds = selectedSkillIds.filter((id) => Object.keys(skills ?? {}).includes(id));
		}
	};

	const loadTools = async (query = toolQuery) => {
		const requestId = ++toolRequestId;
		const q = query.trim();
		searchedToolQuery = query;

		if (q) {
			const toolItems = await getTools(localStorage.token, q).catch(() => []);
			if (requestId !== toolRequestId) return;
			setTools(toolItems, q);
			return;
		}

		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}
		if (requestId !== toolRequestId) return;
		setTools($_tools, q);
	};

	const loadSkills = async (query = skillQuery) => {
		const requestId = ++skillRequestId;
		const q = query.trim();
		searchedSkillQuery = query;

		if (q) {
			const skillItems = await getSkills(localStorage.token, q).catch(() => []);
			if (requestId !== skillRequestId) return;
			setSkills(skillItems, q);
			return;
		}

		if ($_skills === null) {
			await _skills.set(await getSkills(localStorage.token));
		}
		if (requestId !== skillRequestId) return;
		setSkills($_skills, q);
	};

	const scheduleToolSearch = () => {
		clearTimeout(toolSearchDebounceTimer);
		toolSearchDebounceTimer = setTimeout(() => {
			loadTools();
		}, 200);
	};

	const scheduleSkillSearch = () => {
		clearTimeout(skillSearchDebounceTimer);
		skillSearchDebounceTimer = setTimeout(() => {
			loadSkills();
		}, 200);
	};

	const toggleTool = async (toolId: string, e: MouseEvent) => {
		const tool = tools?.[toolId];
		if (!tool) return;

		if (!(tool.authenticated ?? true)) {
			e.preventDefault();

			const parts = toolId.split(':');
			oauthRedirectHandler({
				id: toolId,
				serverId: parts.at(-1) ?? toolId,
				authType: parts.length > 1 ? (parts[0] === 'server' ? parts[1] : parts[0]) : null
			});
			return;
		}

		const state = !selectedToolIds.includes(toolId);
		await tick();

		if (state) {
			selectedToolIds = [...selectedToolIds, toolId];
		} else {
			selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
		}
	};

	const toggleSkill = async (skillId: string) => {
		const skill = skills?.[skillId];
		if (!skill) return;

		const state = !selectedSkillIds.includes(skillId);
		await tick();

		if (state) {
			selectedSkillIds = [...selectedSkillIds, skillId];
		} else {
			selectedSkillIds = selectedSkillIds.filter((id) => id !== skillId);
		}
	};

	onDestroy(() => {
		clearTimeout(toolSearchDebounceTimer);
		clearTimeout(skillSearchDebounceTimer);
	});
</script>

<Dropdown
	bind:show
	{closeOnOutsideClick}
	onOpenChange={(state) => {
		if (state === false) {
			toolQuery = '';
			skillQuery = '';
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Integrations')} placement="top">
		<slot />
	</Tooltip>
	<div slot="content">
		<DropdownMenu className="min-w-70 max-w-70 max-h-72 overflow-hidden">
			{#if tab === ''}
				<div
					class="max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
					in:fly={{ x: -20, duration: 150 }}
				>
					{#if tools}
						{#if Object.keys(tools).length > 0}
							<button
								class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
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

						{#if skills && Object.keys(skills).length > 0}
							<button
								class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
								on:click={() => {
									tab = 'skills';
								}}
							>
								<Cube className="size-3.5" strokeWidth="1.75" />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Skills')}
										<span class="ml-0.5 text-gray-500">{Object.keys(skills).length}</span>
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
									class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
									aria-pressed={selectedFilterIds.includes(filter.id)}
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
													<div class="size-3.5 items-center flex justify-center">
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
													<Sparkles className="size-3.5" strokeWidth="1.75" />
												{/if}
											</div>

											<div class=" truncate">{filter?.name}</div>
										</div>
									</div>

									{#if filter?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
										<div class=" shrink-0">
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

									<div class=" shrink-0" inert>
										<Switch state={selectedFilterIds.includes(filter.id)} />
									</div>
								</button>
							</Tooltip>
						{/each}
					{/if}

					{#if showWebSearchButton}
						<Tooltip content={$i18n.t('Search the internet')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
								aria-pressed={webSearchEnabled}
								on:click={() => {
									webSearchEnabled = !webSearchEnabled;
									onWebSearchToggle(webSearchEnabled);
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

								<div class=" shrink-0" inert>
									<Switch state={webSearchEnabled} />
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if showImageGenerationButton}
						<Tooltip content={$i18n.t('Generate an image')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
								aria-pressed={imageGenerationEnabled}
								on:click={() => {
									imageGenerationEnabled = !imageGenerationEnabled;
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Photo className="size-3.5" strokeWidth="1.5" />
										</div>

										<div class=" truncate">{$i18n.t('Image')}</div>
									</div>
								</div>

								<div class=" shrink-0" inert>
									<Switch state={imageGenerationEnabled} />
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if showCodeInterpreterButton}
						<Tooltip content={$i18n.t('Execute code for analysis')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
								aria-pressed={codeInterpreterEnabled}
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

								<div class=" shrink-0" inert>
									<Switch state={codeInterpreterEnabled} />
								</div>
							</button>
						</Tooltip>
					{/if}
				</div>
			{:else if tab === 'tools' && tools}
				<div class="flex max-h-72 min-h-0 flex-col gap-0.5" in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							toolQuery = '';
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Tools')}
								<span class="ml-0.5 text-gray-500">{toolIds.length}</span>
							</div>
						</div>
					</button>

					<SearchInput bind:value={toolQuery} placeholder={$i18n.t('Search tools')} />

					<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
						{#if toolIds.length === 0}
							<div class="text-center text-xs text-gray-500 py-3">{$i18n.t('No tools found')}</div>
						{:else}
							<div class="flex flex-col gap-0.5">
								{#each toolIds as toolId}
									<button
										class="relative flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
										aria-pressed={(tools?.[toolId]?.authenticated ?? true)
											? selectedToolIds.includes(toolId)
											: undefined}
										on:click={async (e) => {
											await toggleTool(toolId, e);
										}}
									>
										{#if !(tools?.[toolId]?.authenticated ?? true)}
											<!-- make it slighly darker and not clickable -->
											<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10"></div>
										{/if}
										<div class="flex-1 truncate">
											<div class="flex flex-1 gap-2 items-center">
												<Tooltip content={tools?.[toolId]?.name ?? ''} placement="top">
													<div class="shrink-0">
														<Wrench />
													</div>
												</Tooltip>
												<Tooltip content={tools?.[toolId]?.description ?? ''} placement="top-start">
													<div class=" truncate">{tools?.[toolId]?.name}</div>
												</Tooltip>
											</div>
										</div>

										{#if (tools?.[toolId]?.authenticated ?? true) && toolId.startsWith('server:mcp:')}
											<div class="shrink-0">
												<Tooltip content={$i18n.t('Disconnect OAuth')}>
													<button
														class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
														type="button"
														on:click={async (e) => {
															e.stopPropagation();
															e.preventDefault();

															const parts = toolId.split(':');
															const serverId = parts.at(-1) ?? toolId;
															const provider = `mcp:${serverId}`;

															try {
																await deleteOAuthSession(localStorage.token, provider);
																toast.success($i18n.t('OAuth session disconnected'));

																// Refresh tools to update authenticated state
																_tools.set(await getTools(localStorage.token));
																selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
																await init();
															} catch (err) {
																toast.error(err ?? $i18n.t('Failed to disconnect'));
															}
														}}
													>
														<LinkSlash className="size-3.5" />
													</button>
												</Tooltip>
											</div>
										{/if}

										{#if tools?.[toolId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
											<div class=" shrink-0">
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

										<div class=" shrink-0" inert>
											<Switch state={selectedToolIds.includes(toolId)} />
										</div>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{:else if tab === 'skills' && skills}
				<div class="flex max-h-72 min-h-0 flex-col gap-0.5" in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							skillQuery = '';
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Skills')}
								<span class="ml-0.5 text-gray-500">{skillIds.length}</span>
							</div>
						</div>
					</button>

					<SearchInput bind:value={skillQuery} placeholder={$i18n.t('Search skills')} />

					<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
						{#if skillIds.length === 0}
							<div class="text-center text-xs text-gray-500 py-3">{$i18n.t('No skills found')}</div>
						{:else}
							<div class="flex flex-col gap-0.5">
								{#each skillIds as skillId}
									<button
										class="relative flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[0.8125rem] font-normal cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
										aria-pressed={selectedSkillIds.includes(skillId)}
										on:click={async () => {
											await toggleSkill(skillId);
										}}
									>
										<div class="flex-1 truncate">
											<div class="flex flex-1 gap-2 items-center">
												<Tooltip content={skills?.[skillId]?.name ?? ''} placement="top">
													<div class="shrink-0">
														<Cube className="size-3.5" strokeWidth="1.75" />
													</div>
												</Tooltip>
												<Tooltip
													content={skills?.[skillId]?.description ?? ''}
													placement="top-start"
												>
													<div class=" truncate">{skills?.[skillId]?.name}</div>
												</Tooltip>
											</div>
										</div>

										<div class=" shrink-0" inert>
											<Switch state={selectedSkillIds.includes(skillId)} />
										</div>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
