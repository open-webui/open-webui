<script lang="ts">
	import { goto } from '$app/navigation';

	import { onMount, tick, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';

	import {
		LITELLM_API_BASE_URL,
		OLLAMA_API_BASE_URL,
		OPENAI_API_BASE_URL,
		WEBUI_API_BASE_URL
	} from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { cancelChatCompletion, generateChatCompletion } from '$lib/apis/ollama';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';
	import ChatCompletion from '$lib/components/playground/ChatCompletion.svelte';

	const i18n = getContext('i18n');

	let mode = 'chat';
	let loaded = false;
	let text = '';

	let selectedModelId = '';

	let loading = false;
	let currentRequestId = null;
	let stopResponseFlag = false;

	let messagesContainerElement: HTMLDivElement;
	let textCompletionAreaElement: HTMLTextAreaElement;

	let system = '';
	let messages = [
		{
			role: 'user',
			content: ''
		}
	];

	const scrollToBottom = () => {
		const element = mode === 'chat' ? messagesContainerElement : textCompletionAreaElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	// const cancelHandler = async () => {
	// 	if (currentRequestId) {
	// 		const res = await cancelChatCompletion(localStorage.token, currentRequestId);
	// 		currentRequestId = null;
	// 		loading = false;
	// 	}
	// };

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const textCompletionHandler = async () => {
		const model = $models.find((model) => model.id === selectedModelId);

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{
						role: 'assistant',
						content: text
					}
				]
			},
			model.external
				? model.source === 'litellm'
					? `${LITELLM_API_BASE_URL}/v1`
					: `${OPENAI_API_BASE_URL}`
				: `${OLLAMA_API_BASE_URL}/v1`
		);

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						await cancelChatCompletion(localStorage.token, currentRequestId);
					}

					currentRequestId = null;
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							if (line === 'data: [DONE]') {
								// responseMessage.done = true;
								console.log('done');
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if ('request_id' in data) {
									currentRequestId = data.request_id;
								} else {
									text += data.choices[0].delta.content ?? '';
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				scrollToBottom();
			}
		}
	};

	const chatCompletionHandler = async () => {
		const model = $models.find((model) => model.id === selectedModelId);

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					system
						? {
								role: 'system',
								content: system
						  }
						: undefined,
					...messages
				].filter((message) => message)
			},
			model.external
				? model.source === 'litellm'
					? `${LITELLM_API_BASE_URL}/v1`
					: `${OPENAI_API_BASE_URL}`
				: `${OLLAMA_API_BASE_URL}/v1`
		);

		let responseMessage;
		if (messages.at(-1)?.role === 'assistant') {
			responseMessage = messages.at(-1);
		} else {
			responseMessage = {
				role: 'assistant',
				content: ''
			};
			messages.push(responseMessage);
			messages = messages;
		}

		await tick();
		const textareaElement = document.getElementById(`assistant-${messages.length - 1}-textarea`);

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						await cancelChatCompletion(localStorage.token, currentRequestId);
					}

					currentRequestId = null;
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								// responseMessage.done = true;
								messages = messages;
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if ('request_id' in data) {
									currentRequestId = data.request_id;
								} else {
									if (responseMessage.content == '' && data.choices[0].delta.content == '\n') {
										continue;
									} else {
										textareaElement.style.height = textareaElement.scrollHeight + 'px';

										responseMessage.content += data.choices[0].delta.content ?? '';
										messages = messages;

										textareaElement.style.height = textareaElement.scrollHeight + 'px';

										await tick();
									}
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				scrollToBottom();
			}
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			loading = true;

			if (mode === 'complete') {
				await textCompletionHandler();
			} else if (mode === 'chat') {
				await chatCompletionHandler();
			}

			loading = false;
			stopResponseFlag = false;
			currentRequestId = null;
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Playground')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div class="min-h-screen max-h-[100dvh] w-full flex justify-center dark:text-white">
	<div class=" flex flex-col justify-between w-full overflow-y-auto h-[100dvh]">
		<div class="max-w-2xl mx-auto w-full px-3 md:px-0 my-10 h-full">
			<div class=" flex flex-col h-full">
				<div class="flex flex-col justify-between mb-2.5 gap-1">
					<div class="flex justify-between items-center gap-2">
						<div class=" text-2xl font-semibold self-center flex">
							{$i18n.t('Playground')}
							<span class=" text-xs text-gray-500 self-center ml-1">{$i18n.t('(Beta)')}</span>
						</div>

						<div>
							<button
								class=" flex items-center gap-0.5 text-xs px-2.5 py-0.5 rounded-lg {mode ===
									'chat' && 'text-sky-600 dark:text-sky-200 bg-sky-200/30'} {mode === 'complete' &&
									'text-green-600 dark:text-green-200 bg-green-200/30'} "
								on:click={() => {
									if (mode === 'complete') {
										mode = 'chat';
									} else {
										mode = 'complete';
									}
								}}
							>
								{#if mode === 'complete'}
									{$i18n.t('Text Completion')}
								{:else if mode === 'chat'}
									{$i18n.t('Chat')}
								{/if}

								<div>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-3 h-3"
									>
										<path
											fill-rule="evenodd"
											d="M5.22 10.22a.75.75 0 0 1 1.06 0L8 11.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-2.25 2.25a.75.75 0 0 1-1.06 0l-2.25-2.25a.75.75 0 0 1 0-1.06ZM10.78 5.78a.75.75 0 0 1-1.06 0L8 4.06 6.28 5.78a.75.75 0 0 1-1.06-1.06l2.25-2.25a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
							</button>
						</div>
					</div>

					<div class="  flex gap-1 px-1">
						<select
							id="models"
							class="outline-none bg-transparent text-sm font-medium rounded-lg w-full placeholder-gray-400"
							bind:value={selectedModelId}
						>
							<option class=" text-gray-800" value="" selected disabled
								>{$i18n.t('Select a model')}</option
							>

							{#each $models as model}
								{#if model.name === 'hr'}
									<hr />
								{:else}
									<option value={model.id} class="text-gray-800 text-lg"
										>{model.name +
											`${model.size ? ` (${(model.size / 1024 ** 3).toFixed(1)}GB)` : ''}`}</option
									>
								{/if}
							{/each}
						</select>

						<!-- <button
							class=" self-center dark:hover:text-gray-300"
							id="open-settings-button"
							on:click={async () => {}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
								/>
							</svg>
						</button> -->
					</div>
				</div>

				{#if mode === 'chat'}
					<div class="p-1">
						<div class="p-3 outline outline-1 outline-gray-200 dark:outline-gray-800 rounded-lg">
							<div class=" text-sm font-medium">{$i18n.t('System')}</div>
							<textarea
								id="system-textarea"
								class="w-full h-full bg-transparent resize-none outline-none text-sm"
								bind:value={system}
								placeholder={$i18n.t("You're a helpful assistant.")}
								rows="4"
							/>
						</div>
					</div>
				{/if}

				<div
					class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
					id="messages-container"
					bind:this={messagesContainerElement}
				>
					<div class=" h-full w-full flex flex-col">
						<div class="flex-1 p-1">
							{#if mode === 'complete'}
								<textarea
									id="text-completion-textarea"
									bind:this={textCompletionAreaElement}
									class="w-full h-full p-3 bg-transparent outline outline-1 outline-gray-200 dark:outline-gray-800 resize-none rounded-lg text-sm"
									bind:value={text}
									placeholder={$i18n.t("You're a helpful assistant.")}
								/>
							{:else if mode === 'chat'}
								<ChatCompletion bind:messages />
							{/if}
						</div>
					</div>
				</div>

				<div class="pb-2">
					{#if !loading}
						<button
							class="px-3 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-gray-50 transition rounded-lg"
							on:click={() => {
								submitHandler();
							}}
						>
							{$i18n.t('Submit')}
						</button>
					{:else}
						<button
							class="px-3 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-900 transition rounded-lg"
							on:click={() => {
								stopResponse();
							}}
						>
							{$i18n.t('Cancel')}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
