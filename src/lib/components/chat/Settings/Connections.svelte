<script lang="ts">
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	import {
		getOpenAIConfig,
		getOpenAIKeys,
		getOpenAIUrls,
		updateOpenAIConfig,
		updateOpenAIKeys,
		updateOpenAIUrls
	} from '$lib/apis/openai';
	import Switch from '$lib/components/common/Switch.svelte';
	import AdvancedParams from './Advanced/AdvancedParams.svelte';

	const i18n = getContext('i18n');

	export let getModels: Function;
	export let saveSettings: Function;


	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];

	let ENABLE_OPENAI_API = false;

	// Advanced
	let showAdvanced: boolean = false;
	let requestFormat = '';
	let keepAlive: any = null;

	let options = {
		// Advanced
		seed: 0,
		temperature: '',
		repeat_penalty: '',
		repeat_last_n: '',
		mirostat: '',
		mirostat_eta: '',
		mirostat_tau: '',
		top_k: '',
		top_p: '',
		stop: '',
		tfs_z: '',
		num_ctx: '',
		num_predict: ''
	};

	const updateOpenAIHandler = async () => {
		OPENAI_API_BASE_URLS = await updateOpenAIUrls(localStorage.token, OPENAI_API_BASE_URLS);
		OPENAI_API_KEYS = await updateOpenAIKeys(localStorage.token, OPENAI_API_KEYS);

		await models.set(await getModels());
	};

	const toggleRequestFormat = async () => {
		if (requestFormat === '') {
			requestFormat = 'json';
		} else {
			requestFormat = '';
		}

		saveSettings({ requestFormat: requestFormat !== '' ? requestFormat : undefined });
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			const config = await getOpenAIConfig(localStorage.token);
			ENABLE_OPENAI_API = config.ENABLE_OPENAI_API;

			OPENAI_API_BASE_URLS = await getOpenAIUrls(localStorage.token);
			OPENAI_API_KEYS = await getOpenAIKeys(localStorage.token);
		}

		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		requestFormat = settings.requestFormat ?? '';
		keepAlive = settings.keepAlive ?? null;

		options.seed = settings.seed ?? 0;
		options.temperature = settings.temperature ?? '';
		options.repeat_penalty = settings.repeat_penalty ?? '';
		options.top_k = settings.top_k ?? '';
		options.top_p = settings.top_p ?? '';
		options.num_ctx = settings.num_ctx ?? '';
		options = { ...options, ...settings.options };
		options.stop = (settings?.options?.stop ?? []).join(',');

	});
</script>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateOpenAIHandler();
		dispatch('save');
	}}
>
	<div class="  pr-1.5 overflow-y-scroll max-h-[25rem] space-y-3">
		<div class=" space-y-3">
			<div class="mt-2 space-y-2 pr-1.5">
				<div class="flex justify-between items-center text-sm">
					<div class="  font-medium">{$i18n.t('OpenAI API')}</div>

					<div class="mt-1">
						<Switch
							bind:state={ENABLE_OPENAI_API}
							on:change={async () => {
								updateOpenAIConfig(localStorage.token, ENABLE_OPENAI_API);
							}}
						/>
					</div>
				</div>

				{#if ENABLE_OPENAI_API}
					<div class="flex flex-col gap-1">
						{#each OPENAI_API_BASE_URLS as url, idx}
							<div class="flex w-full gap-2">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
										placeholder={$i18n.t('API Base URL')}
										bind:value={url}
										autocomplete="off"
									/>
								</div>

								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
										placeholder={$i18n.t('API Key')}
										bind:value={OPENAI_API_KEYS[idx]}
										autocomplete="off"
									/>
								</div>
								<div class="self-center flex items-center">
									{#if idx === 0}
										<button
											class="px-1"
											on:click={() => {
												OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, ''];
												OPENAI_API_KEYS = [...OPENAI_API_KEYS, ''];
											}}
											type="button"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
												/>
											</svg>
										</button>
									{:else}
										<button
											class="px-1"
											on:click={() => {
												OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
													(url, urlIdx) => idx !== urlIdx
												);
												OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);
											}}
											type="button"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path d="M3.75 7.25a.75.75 0 0 0 0 1.5h8.5a.75.75 0 0 0 0-1.5h-8.5Z" />
											</svg>
										</button>
									{/if}
								</div>
							</div>
							<div class=" mb-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('WebUI will make requests to')}
								<span class=" text-gray-200">'{url}/models'</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div class="mt-2 space-y-3 pr-1.5">
			<div class="flex justify-between items-center text-sm">
				<div class="  font-medium">{$i18n.t('Advanced Parameters')}</div>
				<button
					class=" text-xs font-medium text-gray-500"
					type="button"
					on:click={() => {
						showAdvanced = !showAdvanced;
					}}>{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}</button
				>
			</div>

			{#if showAdvanced}
				<AdvancedParams bind:options />
				<hr class=" dark:border-gray-700" />

				<div class=" py-1 w-full justify-between">
					<div class="flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Keep Alive')}</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							type="button"
							on:click={() => {
								keepAlive = keepAlive === null ? '5m' : null;
							}}
						>
							{#if keepAlive === null}
								<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
							{:else}
								<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
							{/if}
						</button>
					</div>

					{#if keepAlive !== null}
						<div class="flex mt-1 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="text"
								placeholder={$i18n.t("e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.")}
								bind:value={keepAlive}
							/>
						</div>
					{/if}
				</div>

				<div>
					<div class=" py-1 flex w-full justify-between">
						<div class=" self-center text-sm font-medium">{$i18n.t('Request Mode')}</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								toggleRequestFormat();
							}}
						>
							{#if requestFormat === ''}
								<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
							{:else if requestFormat === 'json'}
								<!-- <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            class="w-4 h-4 self-center"
                        >
                            <path
                                d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM10 7a3 3 0 100 6 3 3 0 000-6zM15.657 5.404a.75.75 0 10-1.06-1.06l-1.061 1.06a.75.75 0 001.06 1.06l1.06-1.06zM6.464 14.596a.75.75 0 10-1.06-1.06l-1.06 1.06a.75.75 0 001.06 1.06l1.06-1.06zM18 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 0118 10zM5 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 015 10zM14.596 15.657a.75.75 0 001.06-1.06l-1.06-1.061a.75.75 0 10-1.06 1.06l1.06 1.06zM5.404 6.464a.75.75 0 001.06-1.06l-1.06-1.06a.75.75 0 10-1.061 1.06l1.06 1.06z"
                            />
                        </svg> -->
								<span class="ml-2 self-center"> {$i18n.t('JSON')} </span>
							{/if}
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="  px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			on:click={() => {
				saveSettings({
					options: {
						seed: (options.seed !== 0 ? options.seed : undefined) ?? undefined,
						stop: options.stop !== '' ? options.stop.split(',').filter((e) => e) : undefined,
						temperature: options.temperature !== '' ? options.temperature : undefined,
						repeat_penalty: options.repeat_penalty !== '' ? options.repeat_penalty : undefined,
						repeat_last_n: options.repeat_last_n !== '' ? options.repeat_last_n : undefined,
						mirostat: options.mirostat !== '' ? options.mirostat : undefined,
						mirostat_eta: options.mirostat_eta !== '' ? options.mirostat_eta : undefined,
						mirostat_tau: options.mirostat_tau !== '' ? options.mirostat_tau : undefined,
						top_k: options.top_k !== '' ? options.top_k : undefined,
						top_p: options.top_p !== '' ? options.top_p : undefined,
						tfs_z: options.tfs_z !== '' ? options.tfs_z : undefined,
						num_ctx: options.num_ctx !== '' ? options.num_ctx : undefined,
						num_predict: options.num_predict !== '' ? options.num_predict : undefined
					},
					keepAlive: keepAlive ? (isNaN(keepAlive) ? keepAlive : parseInt(keepAlive)) : undefined
				});
				dispatch('save');
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
