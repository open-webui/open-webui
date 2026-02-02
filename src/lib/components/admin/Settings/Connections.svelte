<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getModels as _getModels } from '$lib/apis';
	import { getDirectConnectionsConfig, setDirectConnectionsConfig } from '$lib/apis/configs';

	import { config, models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
		);
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

	let directConnectionsConfig = null;

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

	const updateDirectConnectionsHandler = async () => {
		const res = await setDirectConnectionsConfig(localStorage.token, directConnectionsConfig).catch(
			(error) => {
				toast.error(`${error}`);
			}
		);

		if (res) {
			toast.success($i18n.t('Direct Connections settings updated'));
			await models.set(await getModels());
		}
	};

	const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[OLLAMA_BASE_URLS.length - 1] = {
			...connection.config,
			key: connection.key
		};

		await updateOllamaHandler();
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			let ollamaConfig = {};
			let openaiConfig = {};

			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
				})(),
				(async () => {
					directConnectionsConfig = await getDirectConnectionsConfig(localStorage.token);
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
		updateDirectConnectionsHandler();

		dispatch('save');
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

<form class="flex flex-col h-full justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<div class="overflow-y-scroll scrollbar-hidden h-full" style="padding-right: 4px;">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && directConnectionsConfig !== null}
			<!-- OpenAI API Section -->
			<div class="my-2" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="mt-2 space-y-2 pr-1.5">
					<div class="flex justify-between items-center text-sm" style="margin-bottom: 12px;">
						<div class="flex items-center" style="gap: 8px;">
							<div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #10b981, #06b6d4); border-radius: 2px;"></div>
							<div class="font-medium" style="color: #1f2937; letter-spacing: -0.01em; font-size: 15px;">{$i18n.t('OpenAI API')}</div>
						</div>

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
						<div class="" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06); margin-top: 12px;">
							<div class="flex justify-between items-center" style="margin-bottom: 12px;">
								<div class="font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Manage OpenAI API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="px-1"
										on:click={() => {
											showAddOpenAIConnectionModal = true;
										}}
										type="button"
										style="background: linear-gradient(135deg, #10b981, #06b6d4); color: white; border-radius: 8px; padding: 6px 10px; transition: all 0.2s; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.25); border: none; display: flex; align-items: center; justify-content: center;"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex flex-col gap-1.5 mt-1.5" style="gap: 10px;">
								{#each OPENAI_API_BASE_URLS as url, idx}
									<div style="background: #f9fafb; border-radius: 8px; padding: 12px; border: 1px solid rgba(0,0,0,0.08); transition: all 0.2s;">
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

												let newConfig = {};
												OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] = OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OPENAI_API_CONFIGS = newConfig;
												updateOpenAIHandler();
											}}
										/>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Ollama API Section -->
			<div class="pr-1.5 my-2" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="flex justify-between items-center text-sm mb-2" style="margin-bottom: 12px;">
					<div class="flex items-center" style="gap: 8px;">
						<div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #3b82f6, #8b5cf6); border-radius: 2px;"></div>
						<div class="font-medium" style="color: #1f2937; letter-spacing: -0.01em; font-size: 15px;">{$i18n.t('Ollama API')}</div>
					</div>

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
					<div class="" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06); margin-top: 12px;">
						<div class="flex justify-between items-center" style="margin-bottom: 12px;">
							<div class="font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Manage Ollama API Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showAddOllamaConnectionModal = true;
									}}
									type="button"
									style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; border-radius: 8px; padding: 6px 10px; transition: all 0.2s; box-shadow: 0 2px 6px rgba(59, 130, 246, 0.25); border: none; display: flex; align-items: center; justify-content: center;"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex w-full gap-1.5">
							<div class="flex-1 flex flex-col gap-1.5 mt-1.5" style="gap: 10px;">
								{#each OLLAMA_BASE_URLS as url, idx}
									<div style="background: #f9fafb; border-radius: 8px; padding: 12px; border: 1px solid rgba(0,0,0,0.08); transition: all 0.2s;">
										<OllamaConnection
											bind:url
											bind:config={OLLAMA_API_CONFIGS[idx]}
											{idx}
											onSubmit={() => {
												updateOllamaHandler();
											}}
											onDelete={() => {
												OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);

												let newConfig = {};
												OLLAMA_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] = OLLAMA_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OLLAMA_API_CONFIGS = newConfig;
											}}
										/>
									</div>
								{/each}
							</div>
						</div>

						<div class="mt-1 text-xs text-gray-400 dark:text-gray-500" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.06); line-height: 1.5;">
							{$i18n.t('Trouble accessing Ollama?')}
							<a
								class="text-gray-300 font-medium underline"
								href="https://github.com/open-webui/open-webui#troubleshooting"
								target="_blank"
								style="color: #3b82f6; font-weight: 600; transition: color 0.2s;"
							>
								{$i18n.t('Click here for help.')}
							</a>
						</div>
					</div>
				{/if}
			</div>

			<!-- Direct Connections Section -->
			<div class="pr-1.5 my-2" style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="flex justify-between items-center text-sm">
					<div class="flex items-center" style="gap: 8px;">
						<div style="width: 4px; height: 24px; background: linear-gradient(to bottom, #f59e0b, #ef4444); border-radius: 2px;"></div>
						<div class="font-medium" style="color: #1f2937; letter-spacing: -0.01em; font-size: 15px;">{$i18n.t('Direct Connections')}</div>
					</div>

					<div class="flex items-center">
						<div class="">
							<Switch
								bind:state={directConnectionsConfig.ENABLE_DIRECT_CONNECTIONS}
								on:change={async () => {
									updateDirectConnectionsHandler();
								}}
							/>
						</div>
					</div>
				</div>

				<div class="mt-1.5" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06); margin-top: 12px;">
					<div class="text-xs text-gray-500" style="line-height: 1.6; color: #6b7280;">
						{$i18n.t(
							'Direct Connections allow users to connect to their own OpenAI compatible API endpoints.'
						)}
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto" style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
					<Spinner className="size-6" />
					<div style="color: #6b7280; font-size: 13px; font-weight: 500;">Loading connections...</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium" style="border-top: 1px solid rgba(0,0,0,0.08); margin-top: 8px; padding-top: 16px;">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
			style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); padding: 10px 24px; font-weight: 600; transition: all 0.3s; border: none;"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>