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
	<div class=" overflow-y-auto scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && connectionsConfig !== null}
			<div class="max-w-5xl mx-auto mb-3.5">
				<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

				<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="mb-4">
					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="flex items-center gap-2.5 mb-4">
							<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-gray-800 dark:text-gray-200">
									<path d="M21.55 10.004a5.416 5.416 0 00-.478-4.501c-1.217-2.09-3.662-3.166-6.05-2.66A5.59 5.59 0 0010.831 1C8.39.995 6.224 2.546 5.473 4.838A5.553 5.553 0 001.76 7.496a5.487 5.487 0 00.691 6.5 5.416 5.416 0 00.477 4.502c1.217 2.09 3.662 3.165 6.05 2.66A5.586 5.586 0 0013.168 23c2.443.006 4.61-1.546 5.361-3.84a5.553 5.553 0 003.715-2.66 5.488 5.488 0 00-.693-6.497v.001zm-8.381 11.558a4.199 4.199 0 01-2.675-.954c.034-.018.093-.05.132-.074l4.44-2.53a.71.71 0 00.364-.623v-6.176l1.877 1.069c.02.01.033.029.036.05v5.115c-.003 2.274-1.87 4.118-4.174 4.123zM4.192 17.78a4.059 4.059 0 01-.498-2.763c.032.02.09.055.131.078l4.44 2.53c.225.13.504.13.73 0l5.42-3.088v2.138a.068.068 0 01-.027.057L9.9 19.288c-1.999 1.136-4.552.46-5.707-1.51h-.001zM3.023 8.216A4.15 4.15 0 015.198 6.41l-.002.151v5.06a.711.711 0 00.364.624l5.42 3.087-1.876 1.07a.067.067 0 01-.063.005l-4.489-2.559c-1.995-1.14-2.679-3.658-1.53-5.63h.001zm15.417 3.54l-5.42-3.088L14.896 7.6a.067.067 0 01.063-.006l4.489 2.557c1.998 1.14 2.683 3.662 1.529 5.633a4.163 4.163 0 01-2.174 1.807V12.38a.71.71 0 00-.363-.623zm1.867-2.773a6.04 6.04 0 00-.132-.078l-4.44-2.53a.731.731 0 00-.729 0l-5.42 3.088V7.325a.068.068 0 01.027-.057L14.1 4.713c2-1.137 4.555-.46 5.707 1.513.487.833.664 1.809.499 2.757h.001zm-11.741 3.81l-1.877-1.068a.065.065 0 01-.036-.051V6.559c.001-2.277 1.873-4.122 4.181-4.12.976 0 1.92.338 2.671.954-.034.018-.092.05-.131.073l-4.44 2.53a.71.71 0 00-.365.623l-.003 6.173v.002zm1.02-2.168L12 9.25l2.414 1.375v2.75L12 14.75l-2.415-1.375v-2.75z"/>
								</svg>
							</div>
							<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
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
						<div class="flex items-center gap-2.5 mb-4">
							<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-4 h-4">
									<path d="M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z" fill="#3186FF"/>
									<path d="M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z" fill="url(#gemini-grad-0)"/>
									<path d="M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z" fill="url(#gemini-grad-1)"/>
									<path d="M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z" fill="url(#gemini-grad-2)"/>
									<defs>
										<linearGradient gradientUnits="userSpaceOnUse" id="gemini-grad-0" x1="7" x2="11" y1="15.5" y2="12"><stop stop-color="#08B962"/><stop offset="1" stop-color="#08B962" stop-opacity="0"/></linearGradient>
										<linearGradient gradientUnits="userSpaceOnUse" id="gemini-grad-1" x1="8" x2="11.5" y1="5.5" y2="11"><stop stop-color="#F94543"/><stop offset="1" stop-color="#F94543" stop-opacity="0"/></linearGradient>
										<linearGradient gradientUnits="userSpaceOnUse" id="gemini-grad-2" x1="3.5" x2="17.5" y1="13.5" y2="12"><stop stop-color="#FABC12"/><stop offset=".46" stop-color="#FABC12" stop-opacity="0"/></linearGradient>
									</defs>
								</svg>
							</div>
							<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
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
						<div class="flex items-center gap-2.5 mb-4">
							<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-gray-800 dark:text-gray-200">
									<path d="M7.905 1.09c.216.085.411.225.588.41.295.306.544.744.734 1.263.191.522.315 1.1.362 1.68a5.054 5.054 0 012.049-.636l.051-.004c.87-.07 1.73.087 2.48.474.101.053.2.11.297.17.05-.569.172-1.134.36-1.644.19-.52.439-.957.733-1.264a1.67 1.67 0 01.589-.41c.257-.1.53-.118.796-.042.401.114.745.368 1.016.737.248.337.434.769.561 1.287.23.934.27 2.163.115 3.645l.053.04.026.019c.757.576 1.284 1.397 1.563 2.35.435 1.487.216 3.155-.534 4.088l-.018.021.002.003c.417.762.67 1.567.724 2.4l.002.03c.064 1.065-.2 2.137-.814 3.19l-.007.01.01.024c.472 1.157.62 2.322.438 3.486l-.006.039a.651.651 0 01-.747.536.648.648 0 01-.54-.742c.167-1.033.01-2.069-.48-3.123a.643.643 0 01.04-.617l.004-.006c.604-.924.854-1.83.8-2.72-.046-.779-.325-1.544-.8-2.273a.644.644 0 01.18-.886l.009-.006c.243-.159.467-.565.58-1.12a4.229 4.229 0 00-.095-1.974c-.205-.7-.58-1.284-1.105-1.683-.595-.454-1.383-.673-2.38-.61a.653.653 0 01-.632-.371c-.314-.665-.772-1.141-1.343-1.436a3.288 3.288 0 00-1.772-.332c-1.245.099-2.343.801-2.67 1.686a.652.652 0 01-.61.425c-1.067.002-1.893.252-2.497.703-.522.39-.878.935-1.066 1.588a4.07 4.07 0 00-.068 1.886c.112.558.331 1.02.582 1.269l.008.007c.212.207.257.53.109.785-.36.622-.629 1.549-.673 2.44-.05 1.018.186 1.902.719 2.536l.016.019a.643.643 0 01.095.69c-.576 1.236-.753 2.252-.562 3.052a.652.652 0 01-1.269.298c-.243-1.018-.078-2.184.473-3.498l.014-.035-.008-.012a4.339 4.339 0 01-.598-1.309l-.005-.019a5.764 5.764 0 01-.177-1.785c.044-.91.278-1.842.622-2.59l.012-.026-.002-.002c-.293-.418-.51-.953-.63-1.545l-.005-.024a5.352 5.352 0 01.093-2.49c.262-.915.777-1.701 1.536-2.269.06-.045.123-.09.186-.132-.159-1.493-.119-2.73.112-3.67.127-.518.314-.95.562-1.287.27-.368.614-.622 1.015-.737.266-.076.54-.059.797.042zm4.116 9.09c.936 0 1.8.313 2.446.855.63.527 1.005 1.235 1.005 1.94 0 .888-.406 1.58-1.133 2.022-.62.375-1.451.557-2.403.557-1.009 0-1.871-.259-2.493-.734-.617-.47-.963-1.13-.963-1.845 0-.707.398-1.417 1.056-1.946.668-.537 1.55-.849 2.485-.849zm0 .896a3.07 3.07 0 00-1.916.65c-.461.37-.722.835-.722 1.25 0 .428.21.829.61 1.134.455.347 1.124.548 1.943.548.799 0 1.473-.147 1.932-.426.463-.28.7-.686.7-1.257 0-.423-.246-.89-.683-1.256-.484-.405-1.14-.643-1.864-.643zm.662 1.21l.004.004c.12.151.095.37-.056.49l-.292.23v.446a.375.375 0 01-.376.373.375.375 0 01-.376-.373v-.46l-.271-.218a.347.347 0 01-.052-.49.353.353 0 01.494-.051l.215.172.22-.174a.353.353 0 01.49.051zm-5.04-1.919c.478 0 .867.39.867.871a.87.87 0 01-.868.871.87.87 0 01-.867-.87.87.87 0 01.867-.872zm8.706 0c.48 0 .868.39.868.871a.87.87 0 01-.868.871.87.87 0 01-.867-.87.87.87 0 01.867-.872zM7.44 2.3l-.003.002a.659.659 0 00-.285.238l-.005.006c-.138.189-.258.467-.348.832-.17.692-.216 1.631-.124 2.782.43-.128.899-.208 1.404-.237l.01-.001.019-.034c.046-.082.095-.161.148-.239.123-.771.022-1.692-.253-2.444-.134-.364-.297-.65-.453-.813a.628.628 0 00-.107-.09L7.44 2.3zm9.174.04l-.002.001a.628.628 0 00-.107.09c-.156.163-.32.45-.453.814-.29.794-.387 1.776-.23 2.572l.058.097.008.014h.03a5.184 5.184 0 011.466.212c.086-1.124.038-2.043-.128-2.722-.09-.365-.21-.643-.349-.832l-.004-.006a.659.659 0 00-.285-.239h-.004z"/>
								</svg>
							</div>
							<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
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

								<div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-1">
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
						<div class="flex items-center gap-2.5 mb-4">
							<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-purple-600 dark:text-purple-400">
									<path fill-rule="evenodd" d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 00-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 00-2.282.819l-.922 1.597a1.875 1.875 0 00.432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 000 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 00-.432 2.385l.922 1.597a1.875 1.875 0 002.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 002.28-.819l.923-1.597a1.875 1.875 0 00-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 000-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 00-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 00-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 00-1.85-1.567h-1.843zM12 15.75a3.75 3.75 0 100-7.5 3.75 3.75 0 000 7.5z" clip-rule="evenodd" />
								</svg>
							</div>
							<div class="text-base font-semibold text-gray-800 dark:text-gray-100">
								{$i18n.t('Advanced Settings')}
							</div>
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
