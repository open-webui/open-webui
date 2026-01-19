<script lang="ts">
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getGeminiConfig, updateGeminiConfig } from '$lib/apis/gemini';
	import { getModels as _getModels, getBackendConfig } from '$lib/apis';
	import { getConnectionsConfig, setConnectionsConfig } from '$lib/apis/configs';

	import { config, models, settings, user, ollamaConfigCache, openaiConfigCache, geminiConfigCache, connectionsConfigCache } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import GeminiConnection from './Connections/GeminiConnection.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';

	const i18n: Writable<any> = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections &&
				(($settings?.directConnections ?? null) as any),
			false,
			true
		);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS: any = {};

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_CONFIGS: any = {};

	let GEMINI_API_KEYS = [''];
	let GEMINI_API_BASE_URLS = [''];
	let GEMINI_API_CONFIGS: any = {};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;
	let ENABLE_GEMINI_API: null | boolean = null;

	let connectionsConfig: any = null;

	let showAddOpenAIConnectionModal = false;
	let showAddGeminiConnectionModal = false;
	let showAddOllamaConnectionModal = false;

	const updateOpenAIHandler = async (refreshModels = true) => {
		if (ENABLE_OPENAI_API !== null) {
			// Remove trailing slashes
			OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			// Check if API KEYS length is same than API URLS length
			if (OPENAI_API_KEYS.length !== OPENAI_API_BASE_URLS.length) {
				// if there are more keys than urls, remove the extra keys
				if (OPENAI_API_KEYS.length > OPENAI_API_BASE_URLS.length) {
					OPENAI_API_KEYS = OPENAI_API_KEYS.slice(0, OPENAI_API_BASE_URLS.length);
				}

				// if there are more urls than keys, add empty keys
				if (OPENAI_API_KEYS.length < OPENAI_API_BASE_URLS.length) {
					const diff = OPENAI_API_BASE_URLS.length - OPENAI_API_KEYS.length;
					for (let i = 0; i < diff; i++) {
						OPENAI_API_KEYS.push('');
					}
				}
			}

			const res = await updateOpenAIConfig(localStorage.token, {
				ENABLE_OPENAI_API: ENABLE_OPENAI_API,
				OPENAI_API_BASE_URLS: OPENAI_API_BASE_URLS,
				OPENAI_API_KEYS: OPENAI_API_KEYS,
				OPENAI_API_CONFIGS: OPENAI_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				// Update cache with new config
				openaiConfigCache.set({
					ENABLE_OPENAI_API,
					OPENAI_API_BASE_URLS,
					OPENAI_API_KEYS,
					OPENAI_API_CONFIGS
				});
				toast.success($i18n.t('OpenAI API settings updated'));
				if (refreshModels) {
					await models.set(await getModels());
				}
			}
		}
	};

	const updateOllamaHandler = async (refreshModels = true) => {
		if (ENABLE_OLLAMA_API !== null) {
			// Remove trailing slashes
			OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			const res = await updateOllamaConfig(localStorage.token, {
				ENABLE_OLLAMA_API: ENABLE_OLLAMA_API,
				OLLAMA_BASE_URLS: OLLAMA_BASE_URLS,
				OLLAMA_API_CONFIGS: OLLAMA_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				// Update cache with new config
				ollamaConfigCache.set({
					ENABLE_OLLAMA_API,
					OLLAMA_BASE_URLS,
					OLLAMA_API_CONFIGS
				});
				toast.success($i18n.t('Ollama API settings updated'));
				if (refreshModels) {
					await models.set(await getModels());
				}
			}
		}
	};

	const updateConnectionsHandler = async () => {
		const res = await setConnectionsConfig(localStorage.token, connectionsConfig).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			connectionsConfigCache.set(null);
			toast.success($i18n.t('Connections settings updated'));
			await models.set(await getModels());
			await config.set(await getBackendConfig());
		}
	};

	const addOpenAIConnectionHandler = async (connection: any) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection: any) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[OLLAMA_BASE_URLS.length - 1] = {
			...connection.config,
			key: connection.key
		};

		await updateOllamaHandler();
	};

	const updateGeminiHandler = async (refreshModels = true) => {
		if (ENABLE_GEMINI_API !== null) {
			// Remove trailing slashes
			GEMINI_API_BASE_URLS = GEMINI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			// Check if API KEYS length is same than API URLS length
			if (GEMINI_API_KEYS.length !== GEMINI_API_BASE_URLS.length) {
				if (GEMINI_API_KEYS.length > GEMINI_API_BASE_URLS.length) {
					GEMINI_API_KEYS = GEMINI_API_KEYS.slice(0, GEMINI_API_BASE_URLS.length);
				}
				if (GEMINI_API_KEYS.length < GEMINI_API_BASE_URLS.length) {
					const diff = GEMINI_API_BASE_URLS.length - GEMINI_API_KEYS.length;
					for (let i = 0; i < diff; i++) {
						GEMINI_API_KEYS.push('');
					}
				}
			}

			const res = await updateGeminiConfig(localStorage.token, {
				ENABLE_GEMINI_API: ENABLE_GEMINI_API,
				GEMINI_API_BASE_URLS: GEMINI_API_BASE_URLS,
				GEMINI_API_KEYS: GEMINI_API_KEYS,
				GEMINI_API_CONFIGS: GEMINI_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				// Update cache with new config
				geminiConfigCache.set({
					ENABLE_GEMINI_API,
					GEMINI_API_BASE_URLS,
					GEMINI_API_KEYS,
					GEMINI_API_CONFIGS
				});
				toast.success($i18n.t('Gemini API settings updated'));
				if (refreshModels) {
					await models.set(await getModels());
				}
			}
		}
	};

	const addGeminiConnectionHandler = async (connection: any) => {
		GEMINI_API_BASE_URLS = [...GEMINI_API_BASE_URLS, connection.url];
		GEMINI_API_KEYS = [...GEMINI_API_KEYS, connection.key];
		GEMINI_API_CONFIGS[GEMINI_API_BASE_URLS.length - 1] = connection.config;

		await updateGeminiHandler();
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			let ollamaConfig: any = {};
			let openaiConfig: any = {};
			let geminiConfig: any = {};

			await Promise.all([
				(async () => {
					// Use cached config if available
					if ($ollamaConfigCache) {
						ollamaConfig = $ollamaConfigCache;
					} else {
						ollamaConfig = await getOllamaConfig(localStorage.token);
						ollamaConfigCache.set(ollamaConfig);
					}
				})(),
				(async () => {
					// Use cached config if available
					if ($openaiConfigCache) {
						openaiConfig = $openaiConfigCache;
					} else {
						openaiConfig = await getOpenAIConfig(localStorage.token);
						openaiConfigCache.set(openaiConfig);
					}
				})(),
				(async () => {
					// Use cached config if available
					if ($geminiConfigCache) {
						geminiConfig = $geminiConfigCache;
					} else {
						geminiConfig = await getGeminiConfig(localStorage.token);
						geminiConfigCache.set(geminiConfig);
					}
				})(),
				(async () => {
					// Use cached config if available
					if ($connectionsConfigCache) {
						connectionsConfig = JSON.parse(JSON.stringify($connectionsConfigCache));
					} else {
						connectionsConfig = await getConnectionsConfig(localStorage.token);
						connectionsConfigCache.set(JSON.parse(JSON.stringify(connectionsConfig)));
					}
				})()
			]);

			ENABLE_OPENAI_API = openaiConfig.ENABLE_OPENAI_API;
			ENABLE_OLLAMA_API = ollamaConfig.ENABLE_OLLAMA_API;

			OPENAI_API_BASE_URLS = openaiConfig.OPENAI_API_BASE_URLS;
			OPENAI_API_KEYS = openaiConfig.OPENAI_API_KEYS;
			OPENAI_API_CONFIGS = openaiConfig.OPENAI_API_CONFIGS;

			OLLAMA_BASE_URLS = ollamaConfig.OLLAMA_BASE_URLS;
			OLLAMA_API_CONFIGS = ollamaConfig.OLLAMA_API_CONFIGS;

			if (ENABLE_OPENAI_API) {
				// get url and idx
				for (const [idx, url] of OPENAI_API_BASE_URLS.entries()) {
					if (!OPENAI_API_CONFIGS[idx]) {
						// Legacy support, url as key
						OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[url] || {};
					}
				}
			}

			if (ENABLE_OLLAMA_API) {
				for (const [idx, url] of OLLAMA_BASE_URLS.entries()) {
					if (!OLLAMA_API_CONFIGS[idx]) {
						OLLAMA_API_CONFIGS[idx] = OLLAMA_API_CONFIGS[url] || {};
					}
				}
			}

			ENABLE_GEMINI_API = geminiConfig.ENABLE_GEMINI_API;
			GEMINI_API_BASE_URLS = geminiConfig.GEMINI_API_BASE_URLS ?? [];
			GEMINI_API_KEYS = geminiConfig.GEMINI_API_KEYS ?? [];
			GEMINI_API_CONFIGS = geminiConfig.GEMINI_API_CONFIGS ?? {};

			for (const [idx, url] of GEMINI_API_BASE_URLS.entries()) {
				if (!GEMINI_API_CONFIGS[idx]) {
					GEMINI_API_CONFIGS[idx] = {};
				}
			}
		}
	});

	const submitHandler = async () => {
		// Don't refresh models on form submit - only save configs
		updateOpenAIHandler(false);
		updateOllamaHandler(false);

		dispatch('save');

		await config.set(await getBackendConfig());
	};
</script>

<AddConnectionModal
	bind:show={showAddOpenAIConnectionModal}
	onSubmit={addOpenAIConnectionHandler}
/>

<AddConnectionModal
	ollama
	bind:show={showAddOllamaConnectionModal}
	onSubmit={addOllamaConnectionHandler}
/>

<AddConnectionModal
	gemini
	bind:show={showAddGeminiConnectionModal}
	onSubmit={addGeminiConnectionHandler}
/>

<form class="flex flex-col h-full justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && connectionsConfig !== null}
			<div class="max-w-5xl mx-auto mb-3.5">
				<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

				<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2 mb-4">
							<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								{$i18n.t('OpenAI API')}
							</div>
							<Switch
								bind:state={ENABLE_OPENAI_API}
								on:change={async () => {
									updateOpenAIHandler(false);
								}}
							/>
						</div>

						{#if ENABLE_OPENAI_API}
							<hr class="border-gray-100 dark:border-gray-800 my-2.5" />
							<div class="flex flex-col gap-2">
								<div class="flex items-center gap-2">
									<div class="text-sm font-medium">{$i18n.t('Manage OpenAI API Connections')}</div>

									<Tooltip content={$i18n.t(`Add Connection`)}>
										<button
											class="p-1 bg-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-full transition"
											on:click={() => {
												showAddOpenAIConnectionModal = true;
											}}
											type="button"
										>
											<Plus className="size-3.5" />
										</button>
									</Tooltip>
								</div>

								<div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-1">
									{#each OPENAI_API_BASE_URLS as url, idx}
										<OpenAIConnection
											bind:url={OPENAI_API_BASE_URLS[idx]}
											bind:key={OPENAI_API_KEYS[idx]}
											bind:config={OPENAI_API_CONFIGS[idx]}
											onSubmit={() => {
												updateOpenAIHandler();
											}}
											onDelete={() => {
												OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
													(url, urlIdx) => idx !== urlIdx
												);
												OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);

												let newConfig = {};
												OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OPENAI_API_CONFIGS = newConfig;
												updateOpenAIHandler();
											}}
										/>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<!-- Gemini API Section -->
				<!-- Gemini API Section -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2 mb-4">
							<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								{$i18n.t('Gemini API')}
							</div>
							<Switch
								bind:state={ENABLE_GEMINI_API}
								on:change={async () => {
									updateGeminiHandler(false);
								}}
							/>
						</div>

						{#if ENABLE_GEMINI_API}
							<hr class="border-gray-100 dark:border-gray-800 my-2.5" />
							<div class="flex flex-col gap-2">
								<div class="flex items-center gap-2">
									<div class="text-sm font-medium">{$i18n.t('Manage Gemini API Connections')}</div>

									<Tooltip content={$i18n.t(`Add Connection`)}>
										<button
											class="p-1 bg-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-full transition"
											on:click={() => {
												showAddGeminiConnectionModal = true;
											}}
											type="button"
										>
											<Plus className="size-3.5" />
										</button>
									</Tooltip>
								</div>

								<div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-1">
									{#each GEMINI_API_BASE_URLS as url, idx}
										<GeminiConnection
											bind:url={GEMINI_API_BASE_URLS[idx]}
											bind:key={GEMINI_API_KEYS[idx]}
											bind:config={GEMINI_API_CONFIGS[idx]}
											onSubmit={() => {
												updateGeminiHandler();
											}}
											onDelete={() => {
												GEMINI_API_BASE_URLS = GEMINI_API_BASE_URLS.filter(
													(url, urlIdx) => idx !== urlIdx
												);
												GEMINI_API_KEYS = GEMINI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);

												let newConfig = {};
												GEMINI_API_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														GEMINI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												GEMINI_API_CONFIGS = newConfig;
												updateGeminiHandler();
											}}
										/>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<!-- Ollama API Section -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2 mb-4">
							<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
								{$i18n.t('Ollama API')}
							</div>
							<Switch
								bind:state={ENABLE_OLLAMA_API}
								on:change={async () => {
									updateOllamaHandler(false);
								}}
							/>
						</div>

						{#if ENABLE_OLLAMA_API}
							<hr class="border-gray-100 dark:border-gray-800 my-2.5" />
							<div class="flex flex-col gap-2">
								<div class="flex items-center gap-2">
									<div class="text-sm font-medium">{$i18n.t('Manage Ollama API Connections')}</div>

									<Tooltip content={$i18n.t(`Add Connection`)}>
										<button
											class="p-1 bg-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-full transition"
											on:click={() => {
												showAddOllamaConnectionModal = true;
											}}
											type="button"
										>
											<Plus className="size-3.5" />
										</button>
									</Tooltip>
								</div>

								<div class="flex w-full gap-2">
									<div class="flex-1 flex flex-col gap-2 mt-1">
										{#each OLLAMA_BASE_URLS as url, idx}
											<OllamaConnection
												bind:url={OLLAMA_BASE_URLS[idx]}
												bind:config={OLLAMA_API_CONFIGS[idx]}
												{idx}
												onSubmit={() => {
													updateOllamaHandler();
												}}
												onDelete={() => {
													OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter(
														(url, urlIdx) => idx !== urlIdx
													);

													let newConfig = {};
													OLLAMA_BASE_URLS.forEach((url, newIdx) => {
														newConfig[newIdx] =
															OLLAMA_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
													});
													OLLAMA_API_CONFIGS = newConfig;
													updateOllamaHandler();
												}}
											/>
										{/each}
									</div>
								</div>

								<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('Trouble accessing Ollama?')}
									<a
										class=" text-gray-300 font-medium underline"
										href="https://github.com/open-webui/open-webui#troubleshooting"
										target="_blank"
									>
										{$i18n.t('Click here for help.')}
									</a>
								</div>
							</div>
						{/if}
					</div>
				</div>

				<!-- Advanced Settings -->
				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
							{$i18n.t('Advanced Settings')}
						</div>

						<hr class="border-gray-100 dark:border-gray-800 my-2.5" />

						<div class="flex flex-col gap-4">
							<div>
								<div class="flex justify-between items-center text-sm">
									<div class="font-medium">{$i18n.t('Direct Connections')}</div>
									<Switch
										bind:state={connectionsConfig.ENABLE_DIRECT_CONNECTIONS}
										on:change={async () => {
											updateConnectionsHandler();
										}}
									/>
								</div>
								<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t(
										'Direct Connections allow users to connect to their own OpenAI compatible API endpoints.'
									)}
								</div>
							</div>

							<hr class="border-gray-100 dark:border-gray-800" />

							<div>
								<div class="flex justify-between items-center text-sm">
									<div class="font-medium">{$i18n.t('Cache Base Model List')}</div>
									<Switch
										bind:state={connectionsConfig.ENABLE_BASE_MODELS_CACHE}
										on:change={async () => {
											updateConnectionsHandler();
										}}
									/>
								</div>
								<div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t(
										'Base Model List Cache speeds up access by fetching base models only at startup or on settings save—faster, but may not show recent base model changes.'
									)}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
