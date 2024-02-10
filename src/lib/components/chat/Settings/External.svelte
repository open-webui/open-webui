<script lang="ts">
	import { getOpenAIKey, getOpenAIUrl, updateOpenAIKey, updateOpenAIUrl } from '$lib/apis/openai';
	import { getOpenAICompatKeyList, getOpenAICompatUrlList, getOpenAICompatModelLabelList, updateOpenAICompatKeyList, updateOpenAICompatUrlList, updateOpenAICompatModelLabelList } from '$lib/apis/openai_compat';
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	export let getModels: Function;

	// External
	let OPENAI_API_KEY = '';
	let OPENAI_API_BASE_URL = '';

	let OPENAI_COMPAT_API_KEY_LIST = '';
	let OPENAI_COMPAT_API_BASE_URL_LIST = '';
	let OPENAI_COMPAT_MODEL_LABEL_LIST = '';
	const updateHandler = async () => {
		OPENAI_API_BASE_URL = await updateOpenAIUrl(localStorage.token, OPENAI_API_BASE_URL);
		OPENAI_API_KEY = await updateOpenAIKey(localStorage.token, OPENAI_API_KEY);

		OPENAI_COMPAT_API_KEY_LIST = APIs.map((api) => api.apiKey).join(';');
		OPENAI_COMPAT_API_BASE_URL_LIST = APIs.map((api) => api.url).join(';');
		OPENAI_COMPAT_MODEL_LABEL_LIST = APIs.map((api) => api.label).join(';');

		// trim trailing semi-colons
		OPENAI_COMPAT_API_KEY_LIST = OPENAI_COMPAT_API_KEY_LIST.replace(/;+$/, '');
		OPENAI_COMPAT_API_BASE_URL_LIST = OPENAI_COMPAT_API_BASE_URL_LIST.replace(/;+$/, '');
		OPENAI_COMPAT_MODEL_LABEL_LIST = OPENAI_COMPAT_MODEL_LABEL_LIST.replace(/;+$/, '');

		OPENAI_COMPAT_API_KEY_LIST = await updateOpenAICompatKeyList(localStorage.token, OPENAI_COMPAT_API_KEY_LIST);
		OPENAI_COMPAT_API_BASE_URL_LIST = await updateOpenAICompatUrlList(localStorage.token, OPENAI_COMPAT_API_BASE_URL_LIST);
		OPENAI_COMPAT_MODEL_LABEL_LIST = await updateOpenAICompatModelLabelList(localStorage.token, OPENAI_COMPAT_MODEL_LABEL_LIST);

		await models.set(await getModels());
	};

	let APIs: {
		index: number;
		label: string;
		url: string;
		apiKey: string;
	}[] = []
	function addNewApi() {
		const newApi = { label: '', url: '', apiKey: '', index: APIs.length};
		APIs = [...APIs, newApi];
	}

	onMount(async () => {
		if ($user.role === 'admin') {
			OPENAI_API_BASE_URL = await getOpenAIUrl(localStorage.token);
			OPENAI_API_KEY = await getOpenAIKey(localStorage.token);
		}

		OPENAI_COMPAT_API_KEY_LIST = await getOpenAICompatKeyList(localStorage.token);
		OPENAI_COMPAT_API_BASE_URL_LIST = await getOpenAICompatUrlList(localStorage.token);
		OPENAI_COMPAT_MODEL_LABEL_LIST = await getOpenAICompatModelLabelList(localStorage.token);
		const keys = OPENAI_COMPAT_API_KEY_LIST?.split(';') ?? [];
		const baseUrls = OPENAI_COMPAT_API_BASE_URL_LIST?.split(';') ?? [];
		const labels = OPENAI_COMPAT_MODEL_LABEL_LIST?.split(';') ?? [];
		for (let i = 0; i < keys.length; i++) {
			APIs.push({ index: i, label: labels[i], url: baseUrls[i], apiKey: keys[i] });
		}
		if (APIs.length === 0) {
			addNewApi();
		}
		APIs = [...APIs];
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
		dispatch('save');

		// saveSettings({
		// 	OPENAI_API_KEY: OPENAI_API_KEY !== '' ? OPENAI_API_KEY : undefined,
		// 	OPENAI_API_BASE_URL: OPENAI_API_BASE_URL !== '' ? OPENAI_API_BASE_URL : undefined
		// });
	}}
>
	<div class=" space-y-3">
		<div>
			<div class=" mb-2.5 text-sm font-medium">OpenAI API Key</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter OpenAI API Key"
						bind:value={OPENAI_API_KEY}
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				Adds optional support for online models.
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div>
			<div class=" mb-2.5 text-sm font-medium">OpenAI API Base URL</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter OpenAI API Key"
						bind:value={OPENAI_API_BASE_URL}
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				WebUI will make requests to <span class=" text-gray-200">'{OPENAI_API_BASE_URL}/chat'</span>
			</div>
		</div>
	</div>

	<div class=" space-y-3">
		<h1>External API</h1>
		<div>
			<div class=" mb-2.5 text-sm font-medium">OpenAI API Key</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter OpenAI API Key"
						bind:value={OPENAI_API_KEY}
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				Adds optional support for online models.
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div>
			<div class=" mb-2.5 text-sm font-medium">OpenAI API Base URL</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter OpenAI API Key"
						bind:value={OPENAI_API_BASE_URL}
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				WebUI will make requests to <span class=" text-gray-200">'{OPENAI_API_BASE_URL}/chat'</span>
			</div>
		</div>
	</div>

	<h1>Add New Open AI Compatible API</h1>
	{#each APIs as api, index (api.index)}
		<div class="flex justify-between space-x-2">
			<input type="text" placeholder="Label" bind:value={api.label} />
			<input type="text" placeholder="API URL" bind:value={api.url} />
			<input type="text" placeholder="API Key" bind:value={api.apiKey} />
		</div>
	{/each}
	
	<button on:click|preventDefault={addNewApi}>
		Add new row
	</button>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
