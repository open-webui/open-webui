<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	import { config, user, tools as _tools, mobile, settings, toolServers } from '$lib/stores';

	import { getOAuthClientAuthorizationUrl } from '$lib/apis/configs';
	import { getTools } from '$lib/apis/tools';
	import { getVoices, getVoiceStatus, type VoiceStatus } from '$lib/apis/audio';
	import { getMusicStatus, type MusicStatus } from '$lib/apis/music';
	import { getVideoStatus, type VideoStatus } from '$lib/apis/video';

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
	import Download from '$lib/components/icons/Download.svelte';
	import SoundHigh from '$lib/components/icons/SoundHigh.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Video from '$lib/components/icons/Video.svelte';
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

	export let downloadVoiceEnabled = false;
	export let downloadVoiceVoice = '';
	export let downloadVoiceUnavailableMessage = '';

	export let musicEnabled = false;
	export let musicUnavailableMessage = '';

	export let pyPhotoEnabled = false;

	export let videoEnabled = false;
	export let videoUnavailableMessage = '';

	export let onShowValves: Function;
	export let onClose: Function;
	export let closeOnOutsideClick = true;

	let show = false;
	let tab = '';

	let tools = null;

	let mounted = false;
	let voiceStatus: VoiceStatus | null = null;
	let musicStatus: MusicStatus | null = null;
	let videoStatus: VideoStatus | null = null;
	let downloadVoiceVoices: { id: string; name: string }[] = [];
	let downloadVoiceLoadingVoices = false;
	let downloadVoiceLoadingStatus = false;
	let musicLoadingStatus = false;
	let videoLoadingStatus = false;

	$: if (show) {
		init();
	}

	$: if (mounted && show) {
		void refreshVoiceStatus();
		void refreshMusicStatus();
		void refreshVideoStatus();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const canUseDownloadVoice = () => $user?.role === 'admin' || ($user?.permissions?.chat?.tts ?? true);

	const refreshVoiceStatus = async () => {
		if (!mounted || downloadVoiceLoadingStatus) return;
		downloadVoiceLoadingStatus = true;
		try {
			voiceStatus = await getVoiceStatus(localStorage.token);

			if (!downloadVoiceVoice) {
				downloadVoiceVoice = voiceStatus?.default_voice ?? '';
			}

			if (!voiceStatus?.available) {
				downloadVoiceEnabled = false;
				downloadVoiceUnavailableMessage = $i18n.t('Voice generation temporarily unavailable');
			} else {
				downloadVoiceUnavailableMessage = '';
			}
		} catch (e) {
			voiceStatus = null;
			downloadVoiceEnabled = false;
			downloadVoiceUnavailableMessage = $i18n.t('Voice generation temporarily unavailable');
		} finally {
			downloadVoiceLoadingStatus = false;
		}
	};

	const refreshMusicStatus = async () => {
		if (!mounted || musicLoadingStatus) return;
		musicLoadingStatus = true;
		try {
			musicStatus = await getMusicStatus(localStorage.token);

			if (!musicStatus?.available) {
				musicEnabled = false;
				musicUnavailableMessage = $i18n.t('Music generation temporarily unavailable');
			} else {
				musicUnavailableMessage = '';
			}
		} catch (e) {
			musicStatus = null;
			musicEnabled = false;
			musicUnavailableMessage = $i18n.t('Music generation temporarily unavailable');
		} finally {
			musicLoadingStatus = false;
		}
	};

	const refreshVideoStatus = async () => {
		if (!mounted || videoLoadingStatus) return;
		videoLoadingStatus = true;
		try {
			videoStatus = await getVideoStatus(localStorage.token);

			if (!videoStatus?.available) {
				videoEnabled = false;
				videoUnavailableMessage = $i18n.t('Video generation temporarily unavailable');
			} else {
				videoUnavailableMessage = '';
			}
		} catch (e) {
			videoStatus = null;
			videoEnabled = false;
			videoUnavailableMessage = $i18n.t('Video generation temporarily unavailable');
		} finally {
			videoLoadingStatus = false;
		}
	};

	const loadDownloadVoiceVoices = async () => {
		if (!mounted || downloadVoiceLoadingVoices) return;
		downloadVoiceLoadingVoices = true;
		try {
			const res = await getVoices(localStorage.token);
			downloadVoiceVoices = (res?.voices ?? []).slice();
			downloadVoiceVoices.sort((a, b) =>
				(a.name ?? '').localeCompare(b.name ?? '', $i18n.resolvedLanguage)
			);

			if (
				!downloadVoiceVoice ||
				(downloadVoiceVoices.length > 0 &&
					!downloadVoiceVoices.some((v) => v.id === downloadVoiceVoice))
			) {
				downloadVoiceVoice = voiceStatus?.default_voice ?? downloadVoiceVoices?.[0]?.id ?? '';
			}
		} catch (e) {
			downloadVoiceVoices = [];
		} finally {
			downloadVoiceLoadingVoices = false;
		}
	};

	$: if (mounted && downloadVoiceEnabled && voiceStatus?.available) {
		void loadDownloadVoiceVoices();
	}

	$: if (mounted && !canUseDownloadVoice() && downloadVoiceEnabled) {
		downloadVoiceEnabled = false;
	}

	onMount(() => {
		mounted = true;
		void refreshVoiceStatus();
		void refreshMusicStatus();
		void refreshVideoStatus();
	});

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

									{#if filter?.has_user_valves}
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

					{#if canUseDownloadVoice()}
						<div>
							<Tooltip content={$i18n.t('Generate and download a voice version')} placement="top-start">
								<button
									class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
									aria-pressed={downloadVoiceEnabled}
									aria-label={$i18n.t('Download Voice')}
									on:click={async () => {
										if (downloadVoiceEnabled) {
											downloadVoiceEnabled = false;
											downloadVoiceUnavailableMessage = '';
											return;
										}

										await refreshVoiceStatus();
										if (!voiceStatus?.available) {
											downloadVoiceEnabled = false;
											if (!downloadVoiceUnavailableMessage) {
												downloadVoiceUnavailableMessage = $i18n.t(
													'Voice generation temporarily unavailable'
												);
											}
											return;
										}

										downloadVoiceUnavailableMessage = '';
										downloadVoiceEnabled = true;
									}}
								>
									<div class="flex-1 truncate">
										<div class="flex flex-1 gap-2 items-center">
											<div class="shrink-0">
												<Download className="size-4" strokeWidth="1.5" />
											</div>
											<div class=" truncate">{$i18n.t('Download Voice')}</div>
										</div>
									</div>

									<div class=" shrink-0 flex items-center gap-2">
										{#if downloadVoiceEnabled}
											<select
												class="h-8 max-w-[12rem] rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-2 text-xs text-gray-800 dark:text-gray-200 outline-hidden"
												bind:value={downloadVoiceVoice}
												disabled={downloadVoiceLoadingVoices || downloadVoiceVoices.length === 0}
												on:click|stopPropagation
												on:mousedown|stopPropagation
												on:keydown|stopPropagation
											>
												{#if downloadVoiceLoadingVoices}
													<option value="" selected>Loading voices...</option>
												{:else}
													{#each downloadVoiceVoices as voice}
														<option value={voice.id}>{voice.name}</option>
													{/each}
												{/if}
											</select>
										{/if}

										<Switch
											state={downloadVoiceEnabled}
											on:change={async (e) => {
												const state = e.detail;
												await tick();
											}}
										/>
									</div>
								</button>
							</Tooltip>

							{#if downloadVoiceUnavailableMessage}
								<div class="px-3 pb-1 text-xs text-amber-600 dark:text-amber-400">
									{downloadVoiceUnavailableMessage}
								</div>
							{/if}
						</div>
					{/if}

					<div>
						<Tooltip content={$i18n.t('Generate music from your prompt')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								aria-pressed={musicEnabled}
								aria-label={$i18n.t('Music')}
								on:click={async () => {
									if (musicEnabled) {
										musicEnabled = false;
										musicUnavailableMessage = '';
										return;
									}

									await refreshMusicStatus();
									if (!musicStatus?.available) {
										musicEnabled = false;
										if (!musicUnavailableMessage) {
											musicUnavailableMessage = $i18n.t('Music generation temporarily unavailable');
										}
										return;
									}

									musicUnavailableMessage = '';
									musicEnabled = true;
									videoEnabled = false;
									videoUnavailableMessage = '';
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<SoundHigh className="size-4" strokeWidth="1.5" />
										</div>
										<div class=" truncate">{$i18n.t('Music')}</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={musicEnabled}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>

						{#if musicUnavailableMessage}
							<div class="px-3 pb-1 text-xs text-amber-600 dark:text-amber-400">
								{musicUnavailableMessage}
							</div>
						{/if}
					</div>

					<div>
						<Tooltip content={$i18n.t('Generate a 1:1 PNG from assistant text')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								aria-pressed={pyPhotoEnabled}
								aria-label={$i18n.t('PY Photo')}
								on:click={() => {
									pyPhotoEnabled = !pyPhotoEnabled;
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Camera className="size-4" strokeWidth="1.5" />
										</div>
										<div class=" truncate">PY ფოტო</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={pyPhotoEnabled}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>
					</div>

					<div>
						<Tooltip content={$i18n.t('Generate video from your prompt')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								aria-pressed={videoEnabled}
								aria-label={$i18n.t('Video')}
								on:click={async () => {
									if (videoEnabled) {
										videoEnabled = false;
										videoUnavailableMessage = '';
										return;
									}

									await refreshVideoStatus();
									if (!videoStatus?.available) {
										videoEnabled = false;
										if (!videoUnavailableMessage) {
											videoUnavailableMessage = $i18n.t('Video generation temporarily unavailable');
										}
										return;
									}

									videoUnavailableMessage = '';
									videoEnabled = true;
									musicEnabled = false;
									musicUnavailableMessage = '';
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<Video className="size-4" strokeWidth="1.5" />
										</div>
										<div class=" truncate">ვიდეო</div>
									</div>
								</div>

								<div class=" shrink-0">
									<Switch
										state={videoEnabled}
										on:change={async (e) => {
											const state = e.detail;
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>

						{#if videoUnavailableMessage}
							<div class="px-3 pb-1 text-xs text-amber-600 dark:text-amber-400">
								{videoUnavailableMessage}
							</div>
						{/if}
					</div>
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
								<!-- make it slighly darker and not clickable -->
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

							<div class=" shrink-0">
								<Switch state={tools[toolId].enabled} />
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
