<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import {
		models,
		modelfiles,
		user,
		settings,
		chats,
		chatId,
		config,
		WEBUI_NAME,
		tags as _tags
	} from '$lib/stores';
	import { copyToClipboard, splitStream } from '$lib/utils';

	import { generateChatCompletion, cancelChatCompletion, generateTitle } from '$lib/apis/ollama';
	import {
		addTagById,
		createNewChat,
		deleteTagById,
		getAllChatTags,
		getChatList,
		getTagsById,
		updateChatById
	} from '$lib/apis/chats';
	import { queryCollection, queryDoc } from '$lib/apis/rag';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';

	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import ModelSelector from '$lib/components/chat/ModelSelector.svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import { RAGTemplate } from '$lib/utils/rag';
	import { LITELLM_API_BASE_URL, OPENAI_API_BASE_URL } from '$lib/constants';
	import { WEBUI_BASE_URL } from '$lib/constants';
	let stopResponseFlag = false;
	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;
	let currentRequestId = null;

	let selectedModels = [''];

	let selectedModelfile = null;
	$: selectedModelfile =
		selectedModels.length === 1 &&
		$modelfiles.filter((modelfile) => modelfile.tagName === selectedModels[0]).length > 0
			? $modelfiles.filter((modelfile) => modelfile.tagName === selectedModels[0])[0]
			: null;

	let selectedModelfiles = {};
	$: selectedModelfiles = selectedModels.reduce((a, tagName, i, arr) => {
		const modelfile =
			$modelfiles.filter((modelfile) => modelfile.tagName === tagName)?.at(0) ?? undefined;

		return {
			...a,
			...(modelfile && { [tagName]: modelfile })
		};
	}, {});

	let chat = null;
	let tags = [];

	let title = '';
	let prompt = '';
	let files = [];
	let messages = [];
	let history = {
		messages: {},
		currentId: null
	};

	$: if (history.currentId !== null) {
		let _messages = [];

		let currentMessage = history.messages[history.currentId];
		while (currentMessage !== null) {
			_messages.unshift({ ...currentMessage });
			currentMessage =
				currentMessage.parentId !== null ? history.messages[currentMessage.parentId] : null;
		}
		messages = _messages;
	} else {
		messages = [];
	}

	onMount(async () => {
		await initNewChat();
	});

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
		if (currentRequestId !== null) {
			await cancelChatCompletion(localStorage.token, currentRequestId);
			currentRequestId = null;
		}
		window.history.replaceState(history.state, '', `/`);
		await chatId.set('');

		autoScroll = true;

		title = '';
		messages = [];
		history = {
			messages: {},
			currentId: null
		};

		if ($page.url.searchParams.get('models')) {
			selectedModels = $page.url.searchParams.get('models')?.split(',');
		} else if ($settings?.models) {
			selectedModels = $settings?.models;
		} else if ($config?.default_models) {
			selectedModels = $config?.default_models.split(',');
		} else {
			selectedModels = [''];
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		let _settings = JSON.parse(localStorage.getItem('settings') ?? '{}');
		settings.set({
			..._settings
		});

		const chatInput = document.getElementById('chat-textarea');
		setTimeout(() => chatInput?.focus(), 0);
	};

	const scrollToBottom = () => {
		messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
	};

	//////////////////////////
	// Ollama functions
	//////////////////////////

	const submitPrompt = async (userPrompt, _user = null) => {
		console.log('submitPrompt', $chatId);

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		if (selectedModels.includes('')) {
			toast.error('Model not selected');
		} else if (messages.length != 0 && messages.at(-1).done != true) {
			// Response not done
			console.log('wait');
		} else if (
			files.length > 0 &&
			files.filter((file) => file.upload_status === false).length > 0
		) {
			// Upload not done
			toast.error(
				`Oops! Hold tight! Your files are still in the processing oven. We're cooking them up to perfection. Please be patient and we'll let you know once they're ready.`
			);
		} else {
			// Reset chat message textarea height
			document.getElementById('chat-textarea').style.height = '';

			// Create user message
			let userMessageId = uuidv4();
			let userMessage = {
				id: userMessageId,
				parentId: messages.length !== 0 ? messages.at(-1).id : null,
				childrenIds: [],
				role: 'user',
				user: _user ?? undefined,
				content: userPrompt,
				files: files.length > 0 ? files : undefined,
				timestamp: Math.floor(Date.now() / 1000) // Unix epoch
			};

			// Add message to history and Set currentId to messageId
			history.messages[userMessageId] = userMessage;
			history.currentId = userMessageId;

			// Append messageId to childrenIds of parent message
			if (messages.length !== 0) {
				history.messages[messages.at(-1).id].childrenIds.push(userMessageId);
			}

			// Wait until history/message have been updated
			await tick();

			// Create new chat if only one message in messages
			if (messages.length == 1) {
				if ($settings.saveChatHistory ?? true) {
					chat = await createNewChat(localStorage.token, {
						id: $chatId,
						title: 'New Chat',
						models: selectedModels,
						system: $settings.system ?? undefined,
						options: {
							...($settings.options ?? {})
						},
						messages: messages,
						history: history,
						tags: [],
						timestamp: Date.now()
					});
					await chats.set(await getChatList(localStorage.token));
					await chatId.set(chat.id);
				} else {
					await chatId.set('local');
				}
				await tick();
			}

			// Reset chat input textarea
			prompt = '';
			files = [];

			// Send prompt
			await sendPrompt(userPrompt, userMessageId);
		}
	};

	const sendPrompt = async (prompt, parentId) => {
		const _chatId = JSON.parse(JSON.stringify($chatId));

		await Promise.all(
			selectedModels.map(async (modelId) => {
				const model = $models.filter((m) => m.id === modelId).at(0);

				if (model) {
					// Create response message
					let responseMessageId = uuidv4();
					let responseMessage = {
						parentId: parentId,
						id: responseMessageId,
						childrenIds: [],
						role: 'assistant',
						content: '',
						model: model.id,
						timestamp: Math.floor(Date.now() / 1000) // Unix epoch
					};

					// Add message to history and Set currentId to messageId
					history.messages[responseMessageId] = responseMessage;
					history.currentId = responseMessageId;

					// Append messageId to childrenIds of parent message
					if (parentId !== null) {
						history.messages[parentId].childrenIds = [
							...history.messages[parentId].childrenIds,
							responseMessageId
						];
					}

					if (model?.external) {
						await sendPromptOpenAI(model, prompt, responseMessageId, _chatId);
					} else if (model) {
						await sendPromptOllama(model, prompt, responseMessageId, _chatId);
					}
				} else {
					toast.error(`Model ${modelId} not found`);
				}
			})
		);

		await chats.set(await getChatList(localStorage.token));
	};

	const sendPromptOllama = async (model, userPrompt, responseMessageId, _chatId) => {
		model = model.id;
		const responseMessage = history.messages[responseMessageId];

		// Wait until history/message have been updated
		await tick();

		// Scroll down
		scrollToBottom();

		const messagesBody = [
			$settings.system
				? {
						role: 'system',
						content: $settings.system
				  }
				: undefined,
			...messages
		]
			.filter((message) => message)
			.map((message, idx, arr) => {
				// Prepare the base message object
				const baseMessage = {
					role: message.role,
					content: arr.length - 2 !== idx ? message.content : message?.raContent ?? message.content
				};

				// Extract and format image URLs if any exist
				const imageUrls = message.files
					?.filter((file) => file.type === 'image')
					.map((file) => file.url.slice(file.url.indexOf(',') + 1));

				// Add images array only if it contains elements
				if (imageUrls && imageUrls.length > 0) {
					baseMessage.images = imageUrls;
				}

				return baseMessage;
			});

		let lastImageIndex = -1;

		// Find the index of the last object with images
		messagesBody.forEach((item, index) => {
			if (item.images) {
				lastImageIndex = index;
			}
		});

		// Remove images from all but the last one
		messagesBody.forEach((item, index) => {
			if (index !== lastImageIndex) {
				delete item.images;
			}
		});

		const docs = messages
			.filter((message) => message?.files ?? null)
			.map((message) =>
				message.files.filter((item) => item.type === 'doc' || item.type === 'collection')
			)
			.flat(1);

		const [res, controller] = await generateChatCompletion(localStorage.token, {
			model: model,
			messages: messagesBody,
			options: {
				...($settings.options ?? {})
			},
			format: $settings.requestFormat ?? undefined,
			keep_alive: $settings.keepAlive ?? undefined,
			docs: docs.length > 0 ? docs : undefined
		});

		if (res && res.ok) {
			console.log('controller', controller);

			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag || _chatId !== $chatId) {
					responseMessage.done = true;
					messages = messages;

					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
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
							let data = JSON.parse(line);

							if ('detail' in data) {
								throw data;
							}

							if ('id' in data) {
								console.log(data);
								currentRequestId = data.id;
							} else {
								if (data.done == false) {
									if (responseMessage.content == '' && data.message.content == '\n') {
										continue;
									} else {
										responseMessage.content += data.message.content;
										messages = messages;
									}
								} else {
									responseMessage.done = true;

									if (responseMessage.content == '') {
										responseMessage.error = true;
										responseMessage.content =
											'Oops! No text generated from Ollama, Please try again.';
									}

									responseMessage.context = data.context ?? null;
									responseMessage.info = {
										total_duration: data.total_duration,
										load_duration: data.load_duration,
										sample_count: data.sample_count,
										sample_duration: data.sample_duration,
										prompt_eval_count: data.prompt_eval_count,
										prompt_eval_duration: data.prompt_eval_duration,
										eval_count: data.eval_count,
										eval_duration: data.eval_duration
									};
									messages = messages;

									if ($settings.notificationEnabled && !document.hasFocus()) {
										const notification = new Notification(
											selectedModelfile
												? `${
														selectedModelfile.title.charAt(0).toUpperCase() +
														selectedModelfile.title.slice(1)
												  }`
												: `${model}`,
											{
												body: responseMessage.content,
												icon: selectedModelfile?.imageUrl ?? `${WEBUI_BASE_URL}/static/favicon.png`
											}
										);
									}

									if ($settings.responseAutoCopy) {
										copyToClipboard(responseMessage.content);
									}

									if ($settings.responseAutoPlayback) {
										await tick();
										document.getElementById(`speak-button-${responseMessage.id}`)?.click();
									}
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
					if ('detail' in error) {
						toast.error(error.detail);
					}
					break;
				}

				if (autoScroll) {
					scrollToBottom();
				}
			}

			if ($chatId == _chatId) {
				if ($settings.saveChatHistory ?? true) {
					chat = await updateChatById(localStorage.token, _chatId, {
						messages: messages,
						history: history
					});
					await chats.set(await getChatList(localStorage.token));
				}
			}
		} else {
			if (res !== null) {
				const error = await res.json();
				console.log(error);
				if ('detail' in error) {
					toast.error(error.detail);
					responseMessage.content = error.detail;
				} else {
					toast.error(error.error);
					responseMessage.content = error.error;
				}
			} else {
				toast.error(`Uh-oh! There was an issue connecting to Ollama.`);
				responseMessage.content = `Uh-oh! There was an issue connecting to Ollama.`;
			}

			responseMessage.error = true;
			responseMessage.content = `Uh-oh! There was an issue connecting to Ollama.`;
			responseMessage.done = true;
			messages = messages;
		}

		stopResponseFlag = false;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length == 2 && messages.at(1).content !== '') {
			window.history.replaceState(history.state, '', `/c/${_chatId}`);
			await generateChatTitle(_chatId, userPrompt);
		}
	};

	const sendPromptOpenAI = async (model, userPrompt, responseMessageId, _chatId) => {
		const responseMessage = history.messages[responseMessageId];
		scrollToBottom();

		const docs = messages
			.filter((message) => message?.files ?? null)
			.map((message) =>
				message.files.filter((item) => item.type === 'doc' || item.type === 'collection')
			)
			.flat(1);

		console.log(docs);

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					$settings.system
						? {
								role: 'system',
								content: $settings.system
						  }
						: undefined,
					...messages
				]
					.filter((message) => message)
					.map((message, idx, arr) => ({
						role: message.role,
						...(message.files?.filter((file) => file.type === 'image').length > 0 ?? false
							? {
									content: [
										{
											type: 'text',
											text:
												arr.length - 1 !== idx
													? message.content
													: message?.raContent ?? message.content
										},
										...message.files
											.filter((file) => file.type === 'image')
											.map((file) => ({
												type: 'image_url',
												image_url: {
													url: file.url
												}
											}))
									]
							  }
							: {
									content:
										arr.length - 1 !== idx ? message.content : message?.raContent ?? message.content
							  })
					})),
				seed: $settings?.options?.seed ?? undefined,
				stop: $settings?.options?.stop ?? undefined,
				temperature: $settings?.options?.temperature ?? undefined,
				top_p: $settings?.options?.top_p ?? undefined,
				num_ctx: $settings?.options?.num_ctx ?? undefined,
				frequency_penalty: $settings?.options?.repeat_penalty ?? undefined,
				max_tokens: $settings?.options?.num_predict ?? undefined,
				docs: docs.length > 0 ? docs : undefined
			},
			model.source === 'litellm' ? `${LITELLM_API_BASE_URL}/v1` : `${OPENAI_API_BASE_URL}`
		);

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag || _chatId !== $chatId) {
					responseMessage.done = true;
					messages = messages;
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								responseMessage.done = true;
								messages = messages;
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (responseMessage.content == '' && data.choices[0].delta.content == '\n') {
									continue;
								} else {
									responseMessage.content += data.choices[0].delta.content ?? '';
									messages = messages;
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				if ($settings.notificationEnabled && !document.hasFocus()) {
					const notification = new Notification(`OpenAI ${model}`, {
						body: responseMessage.content,
						icon: `${WEBUI_BASE_URL}/static/favicon.png`
					});
				}

				if ($settings.responseAutoCopy) {
					copyToClipboard(responseMessage.content);
				}

				if ($settings.responseAutoPlayback) {
					await tick();
					document.getElementById(`speak-button-${responseMessage.id}`)?.click();
				}

				if (autoScroll) {
					scrollToBottom();
				}
			}

			if ($chatId == _chatId) {
				if ($settings.saveChatHistory ?? true) {
					chat = await updateChatById(localStorage.token, _chatId, {
						messages: messages,
						history: history
					});
					await chats.set(await getChatList(localStorage.token));
				}
			}
		} else {
			if (res !== null) {
				const error = await res.json();
				console.log(error);
				if ('detail' in error) {
					toast.error(error.detail);
					responseMessage.content = error.detail;
				} else {
					if ('message' in error.error) {
						toast.error(error.error.message);
						responseMessage.content = error.error.message;
					} else {
						toast.error(error.error);
						responseMessage.content = error.error;
					}
				}
			} else {
				toast.error(`Uh-oh! There was an issue connecting to ${model}.`);
				responseMessage.content = `Uh-oh! There was an issue connecting to ${model}.`;
			}

			responseMessage.error = true;
			responseMessage.content = `Uh-oh! There was an issue connecting to ${model}.`;
			responseMessage.done = true;
			messages = messages;
		}

		stopResponseFlag = false;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length == 2) {
			window.history.replaceState(history.state, '', `/c/${_chatId}`);

			if ($settings?.titleAutoGenerateModel) {
				await generateChatTitle(_chatId, userPrompt);
			} else {
				await setChatTitle(_chatId, userPrompt);
			}
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const regenerateResponse = async () => {
		console.log('regenerateResponse');
		if (messages.length != 0 && messages.at(-1).done == true) {
			messages.splice(messages.length - 1, 1);
			messages = messages;

			let userMessage = messages.at(-1);
			let userPrompt = userMessage.content;

			await sendPrompt(userPrompt, userMessage.id);
		}
	};

	const continueGeneration = async () => {
		console.log('continueGeneration');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (messages.length != 0 && messages.at(-1).done == true) {
			const responseMessage = history.messages[history.currentId];
			responseMessage.done = false;
			await tick();

			const model = $models.filter((m) => m.id === responseMessage.model).at(0);

			if (model) {
				if (model?.external) {
					await sendPromptOpenAI(
						model,
						history.messages[responseMessage.parentId].content,
						responseMessage.id,
						_chatId
					);
				} else
					await sendPromptOllama(
						model,
						history.messages[responseMessage.parentId].content,
						responseMessage.id,
						_chatId
					);
			}
		} else {
			toast.error(`Model ${modelId} not found`);
		}
	};

	const generateChatTitle = async (_chatId, userPrompt) => {
		if ($settings.titleAutoGenerate ?? true) {
			const title = await generateTitle(
				localStorage.token,
				$settings?.titleGenerationPrompt ??
					"Create a concise, 3-5 word phrase as a header for the following query, strictly adhering to the 3-5 word limit and avoiding the use of the word 'title': {{prompt}}",
				$settings?.titleAutoGenerateModel ?? selectedModels[0],
				userPrompt
			);

			if (title) {
				await setChatTitle(_chatId, title);
			}
		} else {
			await setChatTitle(_chatId, `${userPrompt}`);
		}
	};

	const getTags = async () => {
		return await getTagsById(localStorage.token, $chatId).catch(async (error) => {
			return [];
		});
	};

	const addTag = async (tagName) => {
		const res = await addTagById(localStorage.token, $chatId, tagName);
		tags = await getTags();

		chat = await updateChatById(localStorage.token, $chatId, {
			tags: tags
		});

		_tags.set(await getAllChatTags(localStorage.token));
	};

	const deleteTag = async (tagName) => {
		const res = await deleteTagById(localStorage.token, $chatId, tagName);
		tags = await getTags();

		chat = await updateChatById(localStorage.token, $chatId, {
			tags: tags
		});

		_tags.set(await getAllChatTags(localStorage.token));
	};

	const setChatTitle = async (_chatId, _title) => {
		if (_chatId === $chatId) {
			title = _title;
		}

		if ($settings.saveChatHistory ?? true) {
			chat = await updateChatById(localStorage.token, _chatId, { title: _title });
			await chats.set(await getChatList(localStorage.token));
		}
	};
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} | ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<div class="h-screen max-h-[100dvh] w-full flex flex-col">
	<Navbar {title} shareEnabled={messages.length > 0} {initNewChat} {tags} {addTag} {deleteTag} />
	<div class="flex flex-col flex-auto">
		<div
			class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0"
			id="messages-container"
			bind:this={messagesContainerElement}
			on:scroll={(e) => {
				autoScroll =
					messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
					messagesContainerElement.clientHeight + 50;
			}}
		>
			<div
				class="{$settings?.fullScreenMode ?? null
					? 'max-w-full'
					: 'max-w-2xl md:px-0'} mx-auto w-full px-4"
			>
				<ModelSelector bind:selectedModels />
			</div>

			<div class=" h-full w-full flex flex-col py-8">
				<Messages
					chatId={$chatId}
					{selectedModels}
					{selectedModelfiles}
					{processing}
					bind:history
					bind:messages
					bind:autoScroll
					bottomPadding={files.length > 0}
					{sendPrompt}
					{continueGeneration}
					{regenerateResponse}
				/>
			</div>
		</div>

		<MessageInput
			bind:files
			bind:prompt
			bind:autoScroll
			suggestionPrompts={selectedModelfile?.suggestionPrompts ?? $config.default_prompt_suggestions}
			{messages}
			{submitPrompt}
			{stopResponse}
		/>
	</div>
</div>
