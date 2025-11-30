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

	import { chatCompletion } from '$lib/apis/openai';

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

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full relative">
		<div class=" flex flex-col h-full px-3.5">
			<div class="flex w-full items-start gap-1.5">
				<Collapsible
					className="w-full flex-1"
					bind:open={showSystem}
					buttonClassName="w-full rounded-lg text-sm border border-gray-100/30 dark:border-gray-850/30 w-full py-1 px-1.5"
					grow={true}
				>
					<div class="flex gap-2 justify-between items-center">
						<div class=" shrink-0 font-medium ml-1.5">
							{$i18n.t('System Instructions')}
						</div>

						{#if !showSystem && system.trim()}
							<div class=" flex-1 text-gray-500 line-clamp-1">
								{system}
							</div>
						{/if}

						<div class="shrink-0">
							<button class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg">
								{#if showSystem}
									<ChevronUp className="size-3.5" />
								{:else}
									<Pencil className="size-3.5" />
								{/if}
							</button>
						</div>
					</div>

					<div slot="content">
						<div class="pt-1 px-1.5">
							<textarea
								bind:this={systemTextareaElement}
								class="w-full h-full bg-transparent resize-none outline-hidden text-sm"
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
			</div>

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

			<div class="pb-3">
				<div
					class="border border-gray-100/30 dark:border-gray-850/30 w-full px-3 py-2.5 rounded-xl"
				>
					<div class="py-0.5">
						<!-- $i18n.t('a user') -->
						<!-- $i18n.t('an assistant') -->
						<textarea
							bind:value={message}
							class=" w-full h-full bg-transparent resize-none outline-hidden text-sm"
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

					<div
						class="flex justify-between flex-col sm:flex-row items-start sm:items-center gap-2 mt-2"
					>
						<div class="shrink-0">
							<button
								type="button"
								class="px-3.5 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg shrink-0 {($settings?.highContrastMode ??
								false)
									? ''
									: 'outline-hidden'}"
								aria-pressed={role === 'assistant'}
								aria-label={$i18n.t(
									role === 'user' ? 'Switch to Assistant role' : 'Switch to User role'
								)}
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

						<div class="flex items-center justify-between gap-2 w-full sm:w-auto">
							<div class="flex-1">
								<select
									class=" bg-transparent border border-gray-100/30 dark:border-gray-850/30 rounded-lg py-1 px-2 -mx-0.5 text-sm outline-hidden w-full"
									bind:value={selectedModelId}
								>
									{#each $models as model}
										<option value={model.id} class="bg-gray-50 dark:bg-gray-700"
											>{model.name}</option
										>
									{/each}
								</select>
							</div>

							<div class="flex gap-2 shrink-0">
								{#if !loading}
									<button
										disabled={message === ''}
										class="px-3.5 py-1.5 text-sm font-medium disabled:bg-gray-50 dark:disabled:hover:bg-gray-850 disabled:cursor-not-allowed bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg"
										on:click={() => {
											addHandler();
											role = role === 'user' ? 'assistant' : 'user';
										}}
									>
										{$i18n.t('Add')}
									</button>

									<button
										class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg"
										on:click={() => {
											submitHandler();
										}}
									>
										{$i18n.t('Run')}
									</button>
								{:else}
									<button
										class="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-lg"
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
</div>
