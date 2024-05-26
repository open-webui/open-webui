<script lang="ts">
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	import {
		getOpenAIConfig,
		getOpenAIKeys, getOpenAIParams,
		getOpenAIUrls,
		updateOpenAIConfig,
		updateOpenAIKeys, updateOpenAIParams,
		updateOpenAIUrls
	} from '$lib/apis/openai';
	import Switch from '$lib/components/common/Switch.svelte';
	import DefaultParams from './DefaultParams/DefaultParams.svelte';

	const i18n = getContext('i18n');

	export let getModels: Function;

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_PARAMS = [{
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
	}];

	let ENABLE_OPENAI_API = false;

	const updateOpenAIHandler = async () => {
		OPENAI_API_BASE_URLS = await updateOpenAIUrls(localStorage.token, OPENAI_API_BASE_URLS);
		OPENAI_API_KEYS = await updateOpenAIKeys(localStorage.token, OPENAI_API_KEYS);
		OPENAI_API_PARAMS = await updateOpenAIParams(localStorage.token, OPENAI_API_PARAMS);

		await models.set(await getModels());
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			const config = await getOpenAIConfig(localStorage.token);
			ENABLE_OPENAI_API = config.ENABLE_OPENAI_API;

			OPENAI_API_BASE_URLS = await getOpenAIUrls(localStorage.token);
			OPENAI_API_KEYS = await getOpenAIKeys(localStorage.token);
			OPENAI_API_PARAMS = await getOpenAIParams(localStorage.token);
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
								await updateOpenAIConfig(localStorage.token, ENABLE_OPENAI_API);
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
												OPENAI_API_PARAMS = [...OPENAI_API_PARAMS, {
													seed: 0,
													temperature: '',
													repetition_penalty: '',
													top_k: '',
													top_p: '',
													num_predict: ''
												}]
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
												OPENAI_API_PARAMS = OPENAI_API_PARAMS.filter((_, paramIdx) => idx !== paramIdx)
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
								bind:options={OPENAI_API_PARAMS[idx]}
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
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
