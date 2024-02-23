<script lang="ts">
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount } from 'svelte';
	import { getOllamaAPIUrl, getOllamaEnablement, updateOllamaAPIUrl, updateOllamaEnablement } from '$lib/apis/ollama';
	import {
		getOpenAIEnablement,
		getOpenAIKey,
		getOpenAIUrl,
		updateOpenAIEnablement,
		updateOpenAIKey,
		updateOpenAIUrl
	} from '$lib/apis/openai';
	import {
		getVertexAIEnablement,
		getVertexAIKey,
		getVertexAIUrl,
		updateVertexAIEnablement,
		updateVertexAIKey,
		updateVertexAIUrl
	} from '$lib/apis/vertexai';
	import toast from 'svelte-french-toast';

	const dispatch = createEventDispatcher();

	export let getModels: Function;

	// External
	let ENABLE_OLLAMA = true;
	let API_BASE_URL = '';

	let ENABLE_OPENAI = false;
	let OPENAI_API_KEY = '';
	let OPENAI_API_BASE_URL = '';

	let ENABLE_VERTEXAI = false;
	let VERTEXAI_API_KEY = '';
	let VERTEXAI_API_BASE_URL = '';

	const updateOpenAIHandler = async () => {
		ENABLE_OPENAI = await updateOpenAIEnablement(localStorage.token, ENABLE_OPENAI);
		OPENAI_API_BASE_URL = await updateOpenAIUrl(localStorage.token, OPENAI_API_BASE_URL);
		OPENAI_API_KEY = await updateOpenAIKey(localStorage.token, OPENAI_API_KEY);

		if (ENABLE_OPENAI) {
			await models.set(await getModels());
		}
	};

	const updateVertexAIHandler = async () => {
		ENABLE_VERTEXAI = await updateVertexAIEnablement(localStorage.token, ENABLE_VERTEXAI);
		VERTEXAI_API_BASE_URL = await updateVertexAIUrl(localStorage.token, VERTEXAI_API_BASE_URL);
		VERTEXAI_API_KEY = await updateVertexAIKey(localStorage.token, VERTEXAI_API_KEY);

		if (ENABLE_VERTEXAI) {
			await models.set(await getModels());
		}
	};

	const updateOllamaAPIUrlHandler = async () => {
		ENABLE_OLLAMA = await updateOllamaEnablement(localStorage.token, ENABLE_OLLAMA);
		API_BASE_URL = await updateOllamaAPIUrl(localStorage.token, API_BASE_URL);
		if (ENABLE_OLLAMA) {
			const _models = await getModels('ollama');

			if (_models.length > 0) {
				toast.success('Server connection verified');
				await models.set(_models);
			}
		}
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			API_BASE_URL = await getOllamaAPIUrl(localStorage.token);
			ENABLE_OLLAMA = await getOllamaEnablement(localStorage.token);
			ENABLE_OPENAI = await getOpenAIEnablement(localStorage.token);
			OPENAI_API_BASE_URL = await getOpenAIUrl(localStorage.token);
			OPENAI_API_KEY = await getOpenAIKey(localStorage.token);
			ENABLE_VERTEXAI = await getVertexAIEnablement(localStorage.token);
			VERTEXAI_API_BASE_URL = await getVertexAIUrl(localStorage.token);
			VERTEXAI_API_KEY = await getVertexAIKey(localStorage.token);
		}
	});
</script>

<form
	class="flex flex-col h-full space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateOllamaAPIUrlHandler();
		updateOpenAIHandler();
		updateVertexAIHandler();
		dispatch('save');

		// saveSettings({
		// 	OPENAI_API_KEY: OPENAI_API_KEY !== '' ? OPENAI_API_KEY : undefined,
		// 	OPENAI_API_BASE_URL: OPENAI_API_BASE_URL !== '' ? OPENAI_API_BASE_URL : undefined
		// });
	}}
>
	<div>
		<div>
			<div class=" mb-2.5 text-sm font-medium">Enable Ollama</div>
			<div class="flex w-full">
				<div class="flex-1">
					<label class="switch">
						<input type="checkbox" bind:checked={ENABLE_OLLAMA}>
						<span class="slider round"></span>
					</label>
				</div>
			</div>
		</div>
		<div class=" mb-2.5 text-sm font-medium">Ollama API URL</div>
		<div class="flex w-full">
			<div class="flex-1 mr-2">
				<input
					class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
					placeholder="Enter URL (e.g. http://localhost:11434/api)"
					bind:value={API_BASE_URL}
				/>
			</div>
			<button
				class="px-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 rounded transition"
				on:click={() => {
					updateOllamaAPIUrlHandler();
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

		<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			Trouble accessing Ollama?
			<a
				class=" text-gray-300 font-medium"
				href="https://github.com/open-webui/open-webui#troubleshooting"
				target="_blank"
			>
				Click here for help.
			</a>
		</div>
	</div>

	<hr class=" dark:border-gray-700" />

	<div class=" space-y-3">
		<div>
			<div class=" mb-2.5 text-sm font-medium">Enable OpenAI</div>
			<div class="flex w-full">
				<div class="flex-1">
					<label class="switch">
						<input type="checkbox" bind:checked={ENABLE_OPENAI}>
						<span class="slider round"></span>
					</label>
				</div>
			</div>
		</div>

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
		</div>

		<div>
			<div class=" mb-2.5 text-sm font-medium">OpenAI API Base URL</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter OpenAI API Base URL"
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


	<hr class=" dark:border-gray-700" />

	<div class=" space-y-3">
		<div>
			<div class=" mb-2.5 text-sm font-medium">Enable VertexAI</div>
			<div class="flex w-full">
				<div class="flex-1">
					<label class="switch">
						<input type="checkbox" bind:checked={ENABLE_VERTEXAI}>
						<span class="slider round"></span>
					</label>
				</div>
			</div>
		</div>

		<div>
			<div class=" mb-2.5 text-sm font-medium">VertexAI API Key</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter VertexAI API Key"
						bind:value={VERTEXAI_API_KEY}
						autocomplete="off"
					/>
				</div>
			</div>
		</div>

		<div>
			<div class=" mb-2.5 text-sm font-medium">VertexAI API Base URL</div>
			<div class="flex w-full">
				<div class="flex-1">
					<input
						class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
						placeholder="Enter VertexAI API Base URL"
						bind:value={VERTEXAI_API_BASE_URL}
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				WebUI will make requests to <span class=" text-gray-200">'{VERTEXAI_API_BASE_URL}/chat'</span>
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
