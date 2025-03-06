<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings, showSidebar } from '$lib/stores';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { generateChatCompletion } from '$lib/apis/ollama';

	import { splitStream } from '$lib/utils';
	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import { Result } from 'postcss';

	const i18n = getContext('i18n');

	let loaded = false;
	let text = '';
	let newText = '';
	let oldText = '';
	let start = 0;
	let end = 0;
	let selectedText = '';
	let startSegment = '';
	let endSegment = '';
	let customUserMessage = '';

	let selectedModelId = '';

	let loading = false;
	let stopResponseFlag = false;
	let cursorPosition = 0;

	let textCompletionAreaElement: HTMLTextAreaElement;

	const scrollToBottom = () => {
		const element = textCompletionAreaElement;

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
		console.log("sendin' a message", text)
		if (!model) {
			return;
		}

		let messages = []
		startSegment = ''
		endSegment = ''
		if (selectedText) {
			startSegment = text.slice(0, start)
			endSegment = text.slice(start + selectedText.length)
			messages.push({
				role: 'system',
				content: `You are a text rewriter. Improve clarity and ease of reading.`
			})
			messages.push({
				role: 'user',
				content: `${customUserMessage}. Only rewrite the text <selected>${selectedText}</selected> text to match the existing context. DO NOT ADD NEW SECTIONS TO THE TEXT. SERIOUSLY.`
			})
			messages.push({
				role: 'assistant',
				content: startSegment
			})
		} else if (start != 0 && start == end) {
			startSegment = text.slice(0, start)
			endSegment = text.slice(start)
			messages.push({
				role: 'system',
				content: `You are a text expander.`
			})
			messages.push({
				role: 'user',
				content: `${customUserMessage}. Add additional detail and text to <start>${startSegment}</start>. Do not rewrite content related to the following: ${endSegment}`
			})
			messages.push({
				role: 'assistant',
				content: startSegment
			})

		} else {
			messages.push({
				role: 'user',
				content: customUserMessage
			})
			messages.push({
				role: 'assistant',
				content: text
			})
		}
		customUserMessage = ''
		console.log("Messages", messages)

		const [res, controller] = await generateChatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: messages
			},
			`${WEBUI_BASE_URL}/api`
		);

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();
			newText = '';
			oldText = text;

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}
					break;
				}
				if (value.done) {
					break;
				}

				try {
					let result = JSON.parse(value);
					newText += result?.message?.content;
					if (selectedText || (start !=0 && start == end)) {
						text = startSegment + newText + endSegment;
					} else {
						text = oldText + newText;
					}
				} catch (error) {
					console.log(error);
					stopResponseFlag = true
				}

				scrollToBottom();
				start = text.length;
				end = text.length;
			}

			selectedText = '';
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			loading = true;
			await textCompletionHandler();

			loading = false;
			stopResponseFlag = false;
		}
	};
	const recordLocation = (event) => {
		console.log("Current location stats:")
		console.log(`Start: ${start}, End: ${end}, SelectedText: ${selectedText}`)
		const target = event.target;
		if (!textCompletionAreaElement.contains(target)) {
			return;
		}

		start = textCompletionAreaElement.selectionStart;
		end = textCompletionAreaElement.selectionEnd;
		selectedText = '';
		if (start == end) {
			console.log("No selection, caret position", start);
		} else {
			selectedText = textCompletionAreaElement.value.slice(start, end)
		}
		console.log("Updated location stats:")
		console.log(`Start: ${start}, End: ${end}, SelectedText: ${selectedText}`)
	}
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

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col h-full px-4">
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
					</div>
				</div>
			</div>

			<div class="flex justify-between items-center mb-4 max-w-[500px]">
			<input
				type="text"
				bind:value={customUserMessage}
				placeholder={$i18n.t('Enter a custom instruction')}
				class="w-[350px] px-5 py-2 text-sm font-medium border border-gray-300 rounded-md dark:text-black focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-300 ease-out"
			/>
			<button
				class="px-5 py-3 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full ml-1"
				on:click={() => {
				submitHandler();
				}}
			>
				{$i18n.t('Generate')}
			</button>
			</div>

			<div class='text-xs text-blue-900'>
				Marker Stats: (Start {start}, End {end}, Selected Text: {selectedText})
			</div>


			<div
				class=" pt-0.5 pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
				id="messages-container"
			>
				<div class=" h-full w-full flex flex-col">
					<div class="flex-1">
						<textarea
							id="text-completion-textarea"
							bind:this={textCompletionAreaElement}
							class="w-full h-full p-3 bg-transparent border border-gray-50 dark:border-gray-850 outline-none resize-none rounded-lg text-sm"
							bind:value={text}
							placeholder={$i18n.t("You're a helpful assistant.")}
		
  							on:mouseup={recordLocation}
						/>
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
						{$i18n.t('Run')}
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
