<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getModels as _getModels, getBackendConfig } from '$lib/apis';
	import { getConnectionsConfig, setConnectionsConfig } from '$lib/apis/configs';

	import { config, models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	const i18n: any = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null,
			false,
			true
		);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS: string[] = [''];
	let OLLAMA_API_CONFIGS: any = {};

	let OPENAI_API_KEYS: string[] = [''];
	let OPENAI_API_BASE_URLS: string[] = [''];
	let OPENAI_API_CONFIGS: any = {};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;

	let connectionsConfig: any = null;

	let pipelineUrls: Record<string, boolean> = {};
	let showAddOpenAIConnectionModal = false;
	let showAddOllamaConnectionModal = false;

	const updateOpenAIHandler = async () => {
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
				toast.success($i18n.t('OpenAI API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateOllamaHandler = async () => {
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
				toast.success($i18n.t('Ollama API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateConnectionsHandler = async () => {
		const res = await setConnectionsConfig(localStorage.token, connectionsConfig).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
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

	onMount(async () => {
		if ($user?.role === 'admin') {
			let ollamaConfig: any = {};
			let openaiConfig: any = {};

			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
				})(),
				(async () => {
					connectionsConfig = await getConnectionsConfig(localStorage.token);
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

				OPENAI_API_BASE_URLS.forEach(async (url, idx) => {
					OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[idx] || {};
					if (!(OPENAI_API_CONFIGS[idx]?.enable ?? true)) {
						return;
					}
					const res = await getOpenAIModels(localStorage.token, idx);
					if (res.pipelines) {
						pipelineUrls[url] = true;
					}
				});
			}

			if (ENABLE_OLLAMA_API) {
				for (const [idx, url] of OLLAMA_BASE_URLS.entries()) {
					if (!OLLAMA_API_CONFIGS[idx]) {
						OLLAMA_API_CONFIGS[idx] = OLLAMA_API_CONFIGS[url] || {};
					}
				}
			}
		}
	});

	const submitHandler = async () => {
		updateOpenAIHandler();
		updateOllamaHandler();

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

<form class="flex h-full flex-col justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Connections')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && connectionsConfig !== null}
			<AdminSettingSection first>
				<AdminSettingRow label={$i18n.t('OpenAI API')}>
					<Switch
						bind:state={ENABLE_OPENAI_API}
						on:change={async () => {
							updateOpenAIHandler();
						}}
					/>
				</AdminSettingRow>

				{#if ENABLE_OPENAI_API}
					<div>
						<div class="mb-2 flex items-center justify-between gap-4">
							<div class="text-xs text-gray-600 dark:text-gray-400">
								{$i18n.t('Manage OpenAI API Connections')}
							</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-700 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-gray-300"
									on:click={() => {
										showAddOpenAIConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1.5">
							{#each OPENAI_API_BASE_URLS as url, idx}
								<OpenAIConnection
									bind:url={OPENAI_API_BASE_URLS[idx]}
									bind:key={OPENAI_API_KEYS[idx]}
									bind:config={OPENAI_API_CONFIGS[idx]}
									pipeline={pipelineUrls[url] ? true : false}
									onSubmit={() => {
										updateOpenAIHandler();
									}}
									onDelete={() => {
										OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
											(url, urlIdx) => idx !== urlIdx
										);
										OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);

										let newConfig: any = {};
										OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
											newConfig[newIdx] = OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
										});
										OPENAI_API_CONFIGS = newConfig;
										updateOpenAIHandler();
									}}
								/>
							{/each}
						</div>
					</div>
				{/if}

				<AdminSettingRow label={$i18n.t('Ollama API')}>
					<Switch
						bind:state={ENABLE_OLLAMA_API}
						on:change={async () => {
							updateOllamaHandler();
						}}
					/>
				</AdminSettingRow>

				{#if ENABLE_OLLAMA_API}
					<div>
						<div class="mb-2 flex items-center justify-between gap-4">
							<div class="text-xs text-gray-600 dark:text-gray-400">
								{$i18n.t('Manage Ollama API Connections')}
							</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-700 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-gray-300"
									on:click={() => {
										showAddOllamaConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1.5">
							{#each OLLAMA_BASE_URLS as url, idx}
								<OllamaConnection
									bind:url={OLLAMA_BASE_URLS[idx]}
									bind:config={OLLAMA_API_CONFIGS[idx]}
									{idx}
									onSubmit={() => {
										updateOllamaHandler();
									}}
									onDelete={() => {
										OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);

										let newConfig: any = {};
										OLLAMA_BASE_URLS.forEach((url, newIdx) => {
											newConfig[newIdx] = OLLAMA_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
										});
										OLLAMA_API_CONFIGS = newConfig;
									}}
								/>
							{/each}
						</div>

						<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t('Trouble accessing Ollama?')}
							<a
								class="font-normal underline hover:text-gray-700 dark:hover:text-gray-300"
								href="https://github.com/open-webui/open-webui#troubleshooting"
								target="_blank"
							>
								{$i18n.t('Click here for help.')}
							</a>
						</div>
					</div>
				{/if}
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('User Connections')}>
				<AdminSettingRow
					label={$i18n.t('Direct Connections')}
					description={$i18n.t(
						'Direct Connections allow users to connect to their own OpenAI compatible API endpoints.'
					)}
				>
					<Switch
						bind:state={connectionsConfig.ENABLE_DIRECT_CONNECTIONS}
						on:change={async () => {
							updateConnectionsHandler();
						}}
					/>
				</AdminSettingRow>

				<AdminSettingRow
					label={$i18n.t('Cache Base Model List')}
					description={$i18n.t(
						'Base Model List Cache speeds up access by fetching base models only at startup or on settings save—faster, but may not show recent base model changes.'
					)}
				>
					<Switch
						bind:state={connectionsConfig.ENABLE_BASE_MODELS_CACHE}
						on:change={async () => {
							updateConnectionsHandler();
						}}
					/>
				</AdminSettingRow>
			</AdminSettingSection>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
