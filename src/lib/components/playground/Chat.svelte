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
	import Download from '../icons/Download.svelte';
	import Export from '../icons/Export.svelte'; // 1. Import the new icon
	import DocumentArrowUp from '../icons/DocumentArrowUp.svelte'; // Import the new upload icon

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	const i18n = getContext('i18n');

	let loaded = false;

	let selectedModelId = '';
	let loading = false;
	let stopResponseFlag = false;

	let systemTextareaElement: HTMLTextAreaElement;
	let messagesContainerElement: HTMLDivElement;
	let fileInput: HTMLInputElement;

	let showSystem = false;
	let showSettings = false;

	let system = '';

	let role = 'user';
	let message = '';

	let messages = [];

	const saveChatHistory = () => {
		if (messages.length === 0 && (!system || system.trim() === '')) {
			toast.error($i18n.t('Chat history is empty.'));
			return;
		}

		const chatData = [];

		if (system && system.trim() !== '') {
			chatData.push({ role: 'system', content: system });
		}
		chatData.push(...messages);

		if (chatData.length === 0) {
			toast.error($i18n.t('Chat history is empty.'));
			return;
		}

		const jsonlContent = chatData.map((msg) => JSON.stringify(msg)).join('\n');
		const blob = new Blob([jsonlContent], { type: 'application/x-jsonlines;charset=utf-8' });

		const date = new Date().toISOString().split('T')[0];
		saveAs(blob, `chat-history-${date}.jsonl`);

		toast.success($i18n.t('Chat history saved as JSONL.'));
	};

	// 2. Add the new function to save in the complex JSON format
	const saveAsComplexJson = () => {
		if (messages.length === 0) {
			toast.error($i18n.t('Chat history is empty.'));
			return;
		}

		// Prompt for a title, with a default value
		const title = prompt($i18n.t('Enter a title for the chat:'), 'Untitled Chat');
		if (title === null) return; // User cancelled

		const now = new Date();
		const timestamp = Math.floor(now.getTime() / 1000);
		const isoTimestamp = now.toISOString();
		const chat_id = crypto.randomUUID();

		// Create a combined list of messages, including system prompt
		const allMessages = [];
		if (system && system.trim() !== '') {
			allMessages.push({ role: 'system', content: system });
		}
		allMessages.push(...messages);

		let lastMessageId = null;
		const processedMessages = allMessages.map((msg, index) => {
			const messageId = crypto.randomUUID();
			const messageObject = {
				id: messageId,
				parentId: index === 0 ? null : lastMessageId,
				childrenIds: [], // We'll populate this in a second pass
				role: msg.role,
				content: msg.content,
				model: msg.role === 'assistant' ? selectedModelId : undefined,
				timestamp: timestamp + index, // Stagger timestamps slightly
				done: msg.role === 'assistant' ? true : undefined
				// 'usage' and other detailed fields are omitted as we don't have them
			};
			lastMessageId = messageId;
			return messageObject;
		});

		// Second pass to link children
		for (let i = 0; i < processedMessages.length - 1; i++) {
			processedMessages[i].childrenIds.push(processedMessages[i + 1].id);
		}

		// Create the history object with message IDs as keys
		const historyMessages = processedMessages.reduce((acc, msg) => {
			acc[msg.id] = msg;
			return acc;
		}, {});

		const chatData = [
			{
				id: crypto.randomUUID(),
				user_id: $user?.id ?? null, // Use the logged-in user's ID if available
				title: title,
				chat: {
					id: chat_id,
					title: title,
					models: selectedModelId ? [selectedModelId] : [],
					params: {}, // Placeholder
					history: {
						messages: historyMessages,
						currentId: processedMessages.length > 0 ? processedMessages.at(-1).id : null
					},
					messages: processedMessages,
					tags: [], // Placeholder
					timestamp: now.getTime(),
					files: [] // Placeholder
				},
				updated_at: isoTimestamp,
				created_at: isoTimestamp,
				share_id: null,
				archived: false,
				pinned: false,
				meta: {},
				folder_id: null
			}
		];

		const jsonContent = JSON.stringify(chatData, null, 2); // Pretty print JSON
		const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8' });

		const sanitizedTitle = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
		saveAs(blob, `chat-${sanitizedTitle}.json`);

		toast.success($i18n.t('Chat history saved as JSON.'));
	};

	const importChatHistory = () => {
		// A simple confirmation before overwriting existing chat
		if (messages.length > 0 || (system && system.trim() !== '')) {
			if (!confirm($i18n.t('This will replace the current chat. Are you sure?'))) {
				return;
			}
		}
		fileInput.click();
	};

	const handleFileSelect = (event: Event) => {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];

		if (!file) {
			return;
		}

		const reader = new FileReader();

		reader.onload = (e) => {
			try {
				const content = e.target?.result as string;
				const lines = content.split('\n').filter((line) => line.trim() !== '');
				const importedMessages = lines.map((line) => JSON.parse(line));

				if (importedMessages.length === 0) {
					toast.error($i18n.t('The selected file is empty or invalid.'));
					return;
				}

				// Check for a system message at the beginning
				if (importedMessages[0].role === 'system') {
					system = importedMessages[0].content;
					messages = importedMessages.slice(1);
				} else {
					system = ''; // Reset system prompt if not present in the file
					messages = importedMessages;
				}

				toast.success($i18n.t('Chat history imported successfully.'));

				// Scroll to bottom to see the new content
				tick().then(scrollToBottom);
			} catch (error) {
				console.error('Failed to parse JSONL file:', error);
				toast.error(
					$i18n.t('Failed to import chat. The file may be corrupted or not in JSONL format.')
				);
			} finally {
				// Reset file input to allow re-uploading the same file
				target.value = '';
			}
		};

		reader.onerror = () => {
			toast.error($i18n.t('Failed to read the file.'));
			target.value = '';
		};

		reader.readAsText(file);
	};

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
		<Sidebar bind:show={showSettings} className=" bg-white dark:bg-gray-900" width="300px">
			<div class="flex flex-col px-5 py-3 text-sm">
				<div class="flex justify-between items-center mb-2">
					<div class=" font-medium text-base">Settings</div>

					<div class=" translate-x-1.5">
						<button
							class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
							on:click={() => {
								showSettings = !showSettings;
							}}
						>
							<ArrowRight className="size-3" strokeWidth="2.5" />
						</button>
					</div>
				</div>

				<div class="mt-1">
					<div>
						<div class=" text-xs font-medium mb-1">Model</div>

						<div class="w-full">
							<select
								class="w-full bg-transparent border border-gray-100 dark:border-gray-850 rounded-lg py-1 px-2 -mx-0.5 text-sm outline-hidden"
								bind:value={selectedModelId}
							>
								{#each $models as model}
									<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
								{/each}
							</select>
						</div>
					</div>
				</div>
			</div>
		</Sidebar>

		<div class=" flex flex-col h-full px-3.5">
			<div class="flex w-full items-start gap-1.5">
				<Collapsible
					className="w-full flex-1"
					bind:open={showSystem}
					buttonClassName="w-full rounded-lg text-sm border border-gray-100 dark:border-gray-850 w-full py-1 px-1.5"
					grow={true}
				>
					<div class="flex gap-2 justify-between items-center">
						<div class=" shrink-0 font-medium ml-1.5">
							{$i18n.t('System Instructions')}
						</div>

						{#if !showSystem}
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

				<div class="translate-y-1 flex items-center">
					<button
						class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
						on:click={importChatHistory}
						title={$i18n.t('Import Chat from JSONL')}
					>
						<DocumentArrowUp />
					</button>

					<button
						class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
						on:click={saveAsComplexJson}
						title={$i18n.t('Export Chat as JSON')}
					>
						<Export />
					</button>

					<button
						class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
						on:click={saveChatHistory}
						title={$i18n.t('Download Chat as JSONL')}
					>
						<Download />
					</button>

					<button
						class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
						on:click={() => {
							showSettings = !showSettings;
						}}
					>
						<Cog6 />
					</button>
				</div>
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
				<div class="text-xs font-medium text-gray-500 px-2 py-1">
					{selectedModelId}
				</div>
				<div class="border border-gray-100 dark:border-gray-850 w-full px-3 py-2.5 rounded-xl">
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

					<div class="flex justify-between">
						<div>
							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg"
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

						<div>
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

	<input
		bind:this={fileInput}
		type="file"
		accept=".jsonl"
		class="hidden"
		on:change={handleFileSelect}
	/>
</div>
