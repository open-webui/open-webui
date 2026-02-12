<script lang="ts">
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
	import Collapsible from '../common/Collapsible.svelte';

	import Messages from '$lib/components/playground/Chat/Messages.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Pencil from '../icons/Pencil.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import Sidebar from '../common/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let selectedModelId = '';
	let loading = false;
	let stopResponseFlag = false;

	let systemTextareaElement: HTMLTextAreaElement;
	let messagesContainerElement: HTMLDivElement;

	let showSystem = false;
	let showSettings = false;

	let system = '';

	let role = 'user';
	let message = '';

	let messages = [];

	const scrollToBottom = () => {
		const element = messagesContainerElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const resizeSystemTextarea = async () => {
		await tick();
		if (systemTextareaElement) {
			systemTextareaElement.style.height = '';
			systemTextareaElement.style.height = Math.min(systemTextareaElement.scrollHeight, 555) + 'px';
		}
	};

	$: if (showSystem) {
		resizeSystemTextarea();
	}

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

	const addHandler = async () => {
		if (message) {
			messages.push({
				role: role,
				content: message
			});
			messages = messages;
			message = '';
			await tick();
			scrollToBottom();
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			await addHandler();

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

<div class="flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full relative">
		<Sidebar bind:show={showSettings} className="bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800" width="320px">
			<div class="flex flex-col h-full">
				<div class="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-800">
					<div class="font-semibold text-base text-gray-900 dark:text-white">Settings</div>

					<button
						class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors rounded-lg"
						on:click={() => {
							showSettings = !showSettings;
						}}
					>
						<ArrowRight className="size-4" strokeWidth="2.5" />
					</button>
				</div>

				<div class="flex-1 px-5 py-4 overflow-y-auto">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Model
						</label>

						<select
							class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg py-2.5 px-3 text-sm outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-100 focus:border-transparent transition-shadow"
							bind:value={selectedModelId}
						>
							{#each $models as model}
								<option value={model.id} class="bg-white dark:bg-gray-800">{model.name}</option>
							{/each}
						</select>
					</div>
				</div>
			</div>
		</Sidebar>

		<div class="flex flex-col h-full px-4 py-3">
			<div class="flex w-full items-start gap-2 mb-3">
				<Collapsible
					className="w-full flex-1"
					bind:open={showSystem}
					buttonClassName="w-full rounded-lg text-sm border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 transition-colors w-full py-2.5 px-3"
					grow={true}
				>
					<div class="flex gap-2 justify-between items-center">
						<div class="shrink-0 font-medium text-gray-900 dark:text-white">
							{$i18n.t('System Instructions')}
						</div>

						{#if !showSystem}
							<div class="flex-1 text-gray-500 dark:text-gray-400 line-clamp-1 text-sm">
								{system || $i18n.t("You're a helpful assistant.")}
							</div>
						{/if}

						<div class="shrink-0">
							<div class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors rounded">
								{#if showSystem}
									<ChevronUp className="size-4" />
								{:else}
									<Pencil className="size-4" />
								{/if}
							</div>
						</div>
					</div>

					<div slot="content">
						<div class="pt-3 pb-2 px-1">
							<textarea
								bind:this={systemTextareaElement}
								class="w-full h-full bg-transparent resize-none outline-none text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
								bind:value={system}
								placeholder={$i18n.t("You're a helpful assistant.")}
								on:input={() => {
									resizeSystemTextarea();
								}}
								rows="4"
							/>
						</div>
					</div>
				</Collapsible>

				<button
					class="p-2.5 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 border border-gray-200 dark:border-gray-800 transition-colors rounded-lg"
					on:click={() => {
						showSettings = !showSettings;
					}}
				>
					<Cog6 className="size-5" />
				</button>
			</div>

			<div
				class="pb-3 flex flex-col justify-between w-full flex-auto overflow-auto h-0 bg-gray-50/50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-800"
				id="messages-container"
				bind:this={messagesContainerElement}
			>
				<div class="h-full w-full flex flex-col">
					<div class="flex-1 p-3">
						<Messages bind:messages />
					</div>
				</div>
			</div>

			<div class="pt-3">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400 px-1 pb-2">
					{selectedModelId || 'No model selected'}
				</div>
				<div class="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 w-full rounded-xl shadow-sm">
					<div class="px-4 py-3">
						<textarea
							bind:value={message}
							class="w-full h-full bg-transparent resize-none outline-none text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
							placeholder={$i18n.t(`Enter {{role}} message here`, {
								role: role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
							})}
							on:input={(e) => {
								e.target.style.height = '';
								e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
							}}
							on:focus={(e) => {
								e.target.style.height = '';
								e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
							}}
							rows="2"
						/>
					</div>

					<div class="flex justify-between items-center px-4 pb-3 pt-2 border-t border-gray-100 dark:border-gray-800">
						<div>
							<button
								class="px-4 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-900 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-100 transition-colors rounded-lg"
								on:click={() => {
									role = role === 'user' ? 'assistant' : 'user';
								}}
							>
								{#if role === 'user'}
									{$i18n.t('User')}
								{:else}
									{$i18n.t('Assistant')}
								{/if}
							</button>
						</div>

						<div class="flex gap-2">
							{#if !loading}
								<button
									disabled={message === ''}
									class="px-4 py-2 text-sm font-medium disabled:bg-gray-100 disabled:text-gray-400 dark:disabled:bg-gray-800 dark:disabled:text-gray-600 disabled:cursor-not-allowed bg-gray-100 hover:bg-gray-200 text-gray-900 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-100 transition-colors rounded-lg"
									on:click={() => {
										addHandler();
										role = role === 'user' ? 'assistant' : 'user';
									}}
								>
									{$i18n.t('Add')}
								</button>

								<button
									class="px-4 py-2 text-sm font-medium bg-gray-900 hover:bg-gray-800 text-white dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-gray-200 transition-colors rounded-lg shadow-sm"
									on:click={() => {
										submitHandler();
									}}
								>
									{$i18n.t('Run')}
								</button>
							{:else}
								<button
									class="px-4 py-2 text-sm font-medium bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-400 transition-colors rounded-lg"
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
	</div>
</div>