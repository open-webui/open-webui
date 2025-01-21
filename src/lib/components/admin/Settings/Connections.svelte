<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getModels as _getModels } from '$lib/apis';

	import { models, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from './Connections/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(localStorage.token);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS = {};

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_CONFIGS = {};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;

	let pipelineUrls = {};
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

	const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[OPENAI_API_BASE_URLS.length] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[OLLAMA_BASE_URLS.length] = connection.config;

		await updateOllamaHandler();
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			let ollamaConfig = {};
			let openaiConfig = {};

			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
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

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateOpenAIHandler();
		updateOllamaHandler();

		dispatch('save');
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null}
			<div class="my-2">
				<div class="mt-2 space-y-2 pr-1.5">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('OpenAI API')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={ENABLE_OPENAI_API}
									on:change={async () => {
										updateOpenAIHandler();
									}}
								/>
							</div>
						</div>
					</div>

					{#if ENABLE_OPENAI_API}
						<hr class=" border-gray-50 dark:border-gray-850" />

						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium">{$i18n.t('Manage OpenAI API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="px-1"
										on:click={() => {
											showAddOpenAIConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex flex-col gap-1.5 mt-1.5">
								{#each OPENAI_API_BASE_URLS as url, idx}
									<OpenAIConnection
										pipeline={pipelineUrls[url] ? true : false}
										bind:url
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

											delete OPENAI_API_CONFIGS[idx];
										}}
									/>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<hr class=" border-gray-50 dark:border-gray-850" />

			<div class="pr-1.5 my-2">
				<div class="flex justify-between items-center text-sm mb-2">
					<div class="  font-medium">{$i18n.t('Ollama API')}</div>

					<div class="mt-1">
						<Switch
							bind:state={ENABLE_OLLAMA_API}
							on:change={async () => {
								updateOllamaHandler();
							}}
						/>
					</div>
				</div>

				{#if ENABLE_OLLAMA_API}
					<hr class=" border-gray-50 dark:border-gray-850 my-2" />

					<div class="">
						<div class="flex justify-between items-center">
							<div class="font-medium">{$i18n.t('Manage Ollama API Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showAddOllamaConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex w-full gap-1.5">
							<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
								{#each OLLAMA_BASE_URLS as url, idx}
									<OllamaConnection
										bind:url
										bind:config={OLLAMA_API_CONFIGS[idx]}
										{idx}
										onSubmit={() => {
											updateOllamaHandler();
										}}
										onDelete={() => {
											OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);
											delete OLLAMA_API_CONFIGS[idx];
										}}
									/>
								{/each}
							</div>
						</div>

						<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
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
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
