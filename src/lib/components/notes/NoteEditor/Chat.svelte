<script lang="ts">
	export let show = false;
	export let selectedModelId = '';

	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import {
		OLLAMA_API_BASE_URL,
		OPENAI_API_BASE_URL,
		WEBUI_API_BASE_URL,
		WEBUI_BASE_URL
	} from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';

	import Messages from '$lib/components/notes/NoteEditor/Chat/Messages.svelte';
	import MessageInput from '$lib/components/channel/MessageInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let loading = false;
	let stopResponseFlag = false;

	let systemTextareaElement: HTMLTextAreaElement;
	let messagesContainerElement: HTMLDivElement;

	let system = '';
	let content = '';

	let messages = [];
	let chatInputElement = null;

	const scrollToBottom = () => {
		const element = messagesContainerElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopHandler = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const chatCompletionHandler = async () => {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models.find((model) => model.id === selectedModelId);
		if (!model) {
			selectedModelId = '';
			return;
		}

		const [res, controller] = await chatCompletion(
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
			`${WEBUI_BASE_URL}/api`
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

	const submitHandler = async (e) => {
		const { content, data } = e;
		if (selectedModelId && content) {
			messages.push({
				role: 'user',
				content: content
			});
			messages = messages;

			await tick();
			scrollToBottom();

			loading = true;
			await chatCompletionHandler();

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

<div class="flex items-center mb-2">
	<div class=" -translate-x-1.5">
		<button
			class="p-1.5 bg-transparent transition rounded-lg"
			on:click={() => {
				show = !show;
			}}
		>
			<XMark className="size-5" strokeWidth="2.5" />
		</button>
	</div>

	<div class=" font-medium text-base flex items-center gap-1">
		<div>
			{$i18n.t('Chat')}
		</div>

		<div>
			<Tooltip
				content={$i18n.t(
					'This feature is experimental and may be modified or discontinued without notice.'
				)}
				position="top"
				className="inline-block"
			>
				<span class="text-gray-500 text-sm">({$i18n.t('Experimental')})</span>
			</Tooltip>
		</div>
	</div>
</div>

<div class="flex flex-col items-center mb-2 flex-1">
	<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
		<div class="mx-auto w-full md:px-0 h-full relative">
			<div class=" flex flex-col h-full">
				<div
					class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
					id="messages-container"
					bind:this={messagesContainerElement}
				>
					<div class=" h-full w-full flex flex-col">
						<div class="flex-1 p-1">
							<Messages bind:messages />
						</div>
					</div>
				</div>

				<div class=" pb-2">
					<MessageInput
						bind:chatInputElement
						acceptFiles={false}
						inputLoading={loading}
						onSubmit={submitHandler}
						onStop={stopHandler}
					>
						<div slot="menu">
							<select
								class=" bg-transparent rounded-lg py-1 px-2 -mx-0.5 text-sm outline-hidden w-50"
								bind:value={selectedModelId}
							>
								{#each $models as model}
									<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
								{/each}
							</select>
						</div>
					</MessageInput>
				</div>
			</div>
		</div>
	</div>
</div>
