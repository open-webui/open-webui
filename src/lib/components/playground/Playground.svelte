<script lang="ts">
	import { goto } from '$app/navigation';

	import { onMount, tick, getContext } from 'svelte';

	import { toast } from 'svelte-sonner';

	import { OLLAMA_API_BASE_URL, OPENAI_API_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { generateChatCompletion } from '$lib/apis/ollama';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';
	import ChatCompletion from '$lib/components/playground/ChatCompletion.svelte';
	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';

	const i18n = getContext('i18n');

	let mode = 'chat';
	let loaded = false;
	let text = '';

	let selectedModelId = '';

	let loading = false;
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

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const textCompletionHandler = async () => {
		const model = $models.find((model) => model.id === selectedModelId);

		const [res, controller] = await generateOpenAIChatCompletion(
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
			model?.owned_by === 'openai' ? `${OPENAI_API_BASE_URL}` : `${OLLAMA_API_BASE_URL}/v1`
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
						controller.abort('User: Stop Response');
					}
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

								text += data.choices[0].delta.content ?? '';
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

		const [res, controller] = await generateOpenAIChatCompletion(
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
			model?.owned_by === 'openai' ? `${OPENAI_API_BASE_URL}` : `${OLLAMA_API_BASE_URL}/v1`
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
						controller.abort('User: Stop Response');
					}
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

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col h-full">
			<div class="flex flex-col justify-between mb-1 gap-1">
				<div class="flex flex-col gap-1 w-full">
					<div class="flex w-full">
						<div class="overflow-hidden w-full">
							<div class="max-w-full">
								<Selector
									placeholder={$i18n.t('Select a model')}
									items={$models.map((model) => ({
										value: model.id,
										label: model.name,
										model: model
									}))}
									bind:value={selectedModelId}
								/>
							</div>
						</div>

						<div class="flex-shrink-0">
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

			<div class="pb-3 flex justify-end">
				{#if !loading}
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						on:click={() => {
							submitHandler();
						}}
					>
						{$i18n.t('Submit')}
					</button>
				{:else}
					<button
						class="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-full"
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

<style>
	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
