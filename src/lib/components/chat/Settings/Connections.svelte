<script lang="ts">
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	import { getOllamaAPIUrl, getOllamaVersion, updateOllamaAPIUrl } from '$lib/apis/ollama';
	import { getOpenAIKey, getOpenAIUrl, updateOpenAIKey, updateOpenAIUrl } from '$lib/apis/openai';
	import toast from 'svelte-french-toast';

	export let getModels: Function;

	// External
	let API_BASE_URL = '';

	let OPENAI_API_KEY = '';
	let OPENAI_API_BASE_URL = '';

	let showOpenAI = false;
	let showLiteLLM = false;

	const updateOpenAIHandler = async () => {
		OPENAI_API_BASE_URL = await updateOpenAIUrl(localStorage.token, OPENAI_API_BASE_URL);
		OPENAI_API_KEY = await updateOpenAIKey(localStorage.token, OPENAI_API_KEY);

		await models.set(await getModels());
	};

	const updateOllamaAPIUrlHandler = async () => {
		API_BASE_URL = await updateOllamaAPIUrl(localStorage.token, API_BASE_URL);

		const ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			toast.error(error);
			return null;
		});

		if (ollamaVersion) {
			toast.success('Server connection verified');
			await models.set(await getModels());
		}
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			API_BASE_URL = await getOllamaAPIUrl(localStorage.token);
			OPENAI_API_BASE_URL = await getOpenAIUrl(localStorage.token);
			OPENAI_API_KEY = await getOpenAIKey(localStorage.token);
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateOpenAIHandler();
		dispatch('save');

		// saveSettings({
		// 	OPENAI_API_KEY: OPENAI_API_KEY !== '' ? OPENAI_API_KEY : undefined,
		// 	OPENAI_API_BASE_URL: OPENAI_API_BASE_URL !== '' ? OPENAI_API_BASE_URL : undefined
		// });
	}}
>
	<div class="  pr-1.5 overflow-y-scroll max-h-[20.5rem] space-y-3">
		<div class=" space-y-3">
			<div class="mt-2 space-y-2 pr-1.5">
				<div class="flex justify-between items-center text-sm">
					<div class="  font-medium">OpenAI API</div>
					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							showOpenAI = !showOpenAI;
						}}>{showOpenAI ? 'Hide' : 'Show'}</button
					>
				</div>

				{#if showOpenAI}
					<div>
						<div class=" mb-2.5 text-sm font-medium">API Key</div>
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
						<div class=" mb-2.5 text-sm font-medium">API Base URL</div>
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
							WebUI will make requests to <span class=" text-gray-200"
								>'{OPENAI_API_BASE_URL}/chat'</span
							>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div>
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
