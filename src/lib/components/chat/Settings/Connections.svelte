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
	import DefaultParams from './DefaultParams/DefaultParams.svelte';

	const i18n = getContext('i18n');

	export let getModels: Function;
	export let saveSettings: Function;


	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];

	let ENABLE_OPENAI_API = false;

	let options = {
		api_url: '',
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
		num_predict: '',
		keep_alive: null,
		request_format: '',
	};

	let modelParamsList: any[] = [];

	const updateOpenAIHandler = async () => {
		OPENAI_API_BASE_URLS = await updateOpenAIUrls(localStorage.token, OPENAI_API_BASE_URLS);
		OPENAI_API_KEYS = await updateOpenAIKeys(localStorage.token, OPENAI_API_KEYS);

		await models.set(await getModels());
	};

	const handleSaveModelParams = () => {
		let submitData = modelParamsList.map(m => (
			{
				api_url: m.api_url,
				seed: (m.seed !== 0 ? m.seed : undefined) ?? undefined,
				stop: m.stop !== '' ? m.stop.split(',').filter((e) => e) : undefined,
				temperature: m.temperature !== '' ? m.temperature : undefined,
				mirostat: m.mirostat !== '' ? m.mirostat : undefined,
				mirostat_eta: m.mirostat_eta !== '' ? m.mirostat_eta : undefined,
				mirostat_tau: m.mirostat_tau !== '' ? m.mirostat_tau : undefined,
				top_k: m.top_k !== '' ? m.top_k : undefined,
				top_p: m.top_p !== '' ? m.top_p : undefined,
				repeat_penalty: m.repeat_penalty !== '' ? m.repeat_penalty : undefined,
				repeat_last_n: m.repeat_last_n !== '' ? m.repeat_last_n : undefined,
				tfs_z: m.tfs_z !== '' ? m.tfs_z : undefined,
				num_ctx: m.num_ctx !== '' ? m.num_ctx : undefined,
				num_predict: m.num_predict !== '' ? m.num_predict : undefined,
				keep_alive: m.keep_alive !== null ? m.keep_alive : undefined,
				request_format: m.request_format !== '' ? m.request_format : undefined,
			}))
		localStorage.setItem('models_params', JSON.stringify(submitData));
	}

	onMount(async () => {
		if ($user.role === 'admin') {
			const config = await getOpenAIConfig(localStorage.token);
			ENABLE_OPENAI_API = config.ENABLE_OPENAI_API;

			OPENAI_API_BASE_URLS = await getOpenAIUrls(localStorage.token);
			OPENAI_API_KEYS = await getOpenAIKeys(localStorage.token);

			let modelsParams = JSON.parse(localStorage.getItem('models_params') ?? '{}');

			OPENAI_API_BASE_URLS.forEach(url => {
				let foundOptions = modelsParams.find(m => m.api_url === url);
			
				if(foundOptions) {
					modelParamsList= [...modelParamsList, 
					{
						api_url: url,
						seed: foundOptions.seed ?? 0,
						stop: (foundOptions?.stop ?? []).join(','),
						temperature: foundOptions.temperature ?? '',
						mirostat: foundOptions.mirostat ?? '',
						mirostat_eta: foundOptions.mirostat_eta ?? '',
						mirostat_tau: foundOptions.mirostat_tau ?? '',
						top_k: foundOptions.top_k ?? '',
						top_p: foundOptions.top_p ?? '',
						repeat_penalty: foundOptions.repeat_penalty ?? '',
						repeat_last_n: foundOptions.repeat_last_n ?? '',
						tfs_z: foundOptions.tfs_z ?? '',
						num_ctx: foundOptions.num_ctx ?? '',
						num_predict: foundOptions.num_predict ?? '',
						keep_alive: foundOptions.keep_alive ?? null,
						request_format: foundOptions.request_format ?? '',
					}]

					return;
				}
					modelParamsList= [...modelParamsList, {...options, api_url: url}]
				})
		}
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
										on:input={(e)=> {modelParamsList[idx].api_url = e.target.value}}
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
												modelParamsList = [...modelParamsList, options];
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
												modelParamsList = modelParamsList.filter((_, keyIdx) => idx !== keyIdx)
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
							<DefaultParams 
								options={modelParamsList[idx]} 
							/>
							<hr class=" dark:border-gray-700 mx-2 my-4" />
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="  px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			on:click={() => handleSaveModelParams()}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
