<script lang="ts">
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	import { getOllamaUrls, getOllamaVersion, updateOllamaUrls } from '$lib/apis/ollama';
	import {
		getOpenAIKeys,
		getOpenAIUrls,
		updateOpenAIKeys,
		updateOpenAIUrls
	} from '$lib/apis/openai';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let getModels: Function;

	// External
	let OLLAMA_BASE_URL = '';
	let OLLAMA_BASE_URLS = [''];

	let OPENAI_API_KEY = '';
	let OPENAI_API_BASE_URL = '';

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];

	let showOpenAI = false;

	const updateOpenAIHandler = async () => {
		OPENAI_API_BASE_URLS = await updateOpenAIUrls(localStorage.token, OPENAI_API_BASE_URLS);
		OPENAI_API_KEYS = await updateOpenAIKeys(localStorage.token, OPENAI_API_KEYS);

		await models.set(await getModels());
	};

	const updateOllamaUrlsHandler = async () => {
		OLLAMA_BASE_URLS = await updateOllamaUrls(localStorage.token, OLLAMA_BASE_URLS);

		const ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			toast.error(error);
			return null;
		});

		if (ollamaVersion) {
			toast.success($i18n.t('Server connection verified'));
			await models.set(await getModels());
		}
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			OLLAMA_BASE_URLS = await getOllamaUrls(localStorage.token);
			OPENAI_API_BASE_URLS = await getOpenAIUrls(localStorage.token);
			OPENAI_API_KEYS = await getOpenAIKeys(localStorage.token);
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
	<div class="  pr-1.5 overflow-y-scroll max-h-[22rem] space-y-3">
		<div class=" space-y-3">
			<div class="mt-2 space-y-2 pr-1.5">
				<div class="flex justify-between items-center text-sm">
					<div class="  font-medium">{$i18n.t('OpenAI API')}</div>
					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							showOpenAI = !showOpenAI;
						}}>{showOpenAI ? $i18n.t('Hide') : $i18n.t('Show')}</button
					>
				</div>

				{#if showOpenAI}
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

		<div>
			<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Ollama Base URL')}</div>
			<div class="flex w-full gap-1.5">
				<div class="flex-1 flex flex-col gap-2">
					{#each OLLAMA_BASE_URLS as url, idx}
						<div class="flex gap-1.5">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder="Enter URL (e.g. http://localhost:11434)"
								bind:value={url}
							/>

							<div class="self-center flex items-center">
								{#if idx === 0}
									<button
										class="px-1"
										on:click={() => {
											OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, ''];
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
											OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);
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
					{/each}
				</div>

				<div class="">
					<button
						class="p-2.5 bg-gray-200 hover:bg-gray-300 dark:bg-gray-850 dark:hover:bg-gray-800 rounded-lg transition"
						on:click={() => {
							updateOllamaUrlsHandler();
						}}
						type="button"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
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
