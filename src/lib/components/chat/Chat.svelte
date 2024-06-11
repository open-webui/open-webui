<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import mermaid from 'mermaid';

	import { getContext, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { OLLAMA_API_BASE_URL, OPENAI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import {
		chatId,
		chats,
		config,
		type Model,
		models,
		settings,
		showSidebar,
		tags as _tags,
		WEBUI_NAME,
		banners,
		user,
		socket,
		showCallOverlay,
		tools
	} from '$lib/stores';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		promptTemplate,
		splitStream
	} from '$lib/utils';

	import { generateChatCompletion } from '$lib/apis/ollama';
	import {
		addTagById,
		createNewChat,
		deleteTagById,
		getAllChatTags,
		getChatById,
		getChatList,
		getTagsById,
		updateChatById
	} from '$lib/apis/chats';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { runWebSearch } from '$lib/apis/rag';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { queryMemory } from '$lib/apis/memories';
	import { getUserSettings } from '$lib/apis/users';
	import { chatCompleted, generateTitle, generateSearchQuery } from '$lib/apis';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import { error } from '@sveltejs/kit';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let chatIdProp = '';
	let loaded = false;

	let stopResponseFlag = false;
	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	let showModelSelector = true;

	let selectedModels = [''];
	let atSelectedModel: Model | undefined;

	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	let selectedToolIds = [];
	let webSearchEnabled = false;

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

	$: if (chatIdProp) {
		(async () => {
			if (await loadChat()) {
				await tick();
				loaded = true;

				window.setTimeout(() => scrollToBottom(), 0);
				const chatInput = document.getElementById('chat-textarea');
				chatInput?.focus();
			} else {
				await goto('/');
			}
		})();
	}

	onMount(async () => {
		if (!$chatId) {
			await initNewChat();
		} else {
			if (!($settings.saveChatHistory ?? true)) {
				await goto('/');
			}
		}
	});

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
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
			console.log($config?.default_models.split(',') ?? '');
			selectedModels = $config?.default_models.split(',');
		} else {
			selectedModels = [''];
		}

		if ($page.url.searchParams.get('q')) {
			prompt = $page.url.searchParams.get('q') ?? '';

			if (prompt) {
				await tick();
				submitPrompt(prompt);
			}
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		const userSettings = await getUserSettings(localStorage.token);

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
		}

		const chatInput = document.getElementById('chat-textarea');
		setTimeout(() => chatInput?.focus(), 0);
	};

	const loadChat = async () => {
		chatId.set(chatIdProp);
		chat = await getChatById(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			tags = await getTags();
			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];
				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);
				title = chatContent.title;

				const userSettings = await getUserSettings(localStorage.token);

				if (userSettings) {
					await settings.set(userSettings.ui);
				} else {
					await settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
				}

				await settings.set({
					...$settings,
					system: chatContent.system ?? $settings.system,
					params: chatContent.options ?? $settings.params
				});

				autoScroll = true;
				await tick();

				if (messages.length > 0) {
					history.messages[messages.at(-1).id].done = true;
				}
				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const scrollToBottom = async () => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	const createMessagesList = (responseMessageId) => {
		const message = history.messages[responseMessageId];
		if (message.parentId) {
			return [...createMessagesList(message.parentId), message];
		} else {
			return [message];
		}
	};

	const chatCompletedHandler = async (modelId, messages) => {
		await mermaid.run({
			querySelector: '.mermaid'
		});

		const res = await chatCompleted(localStorage.token, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: m.content,
				timestamp: m.timestamp
			})),
			chat_id: $chatId
		}).catch((error) => {
			console.error(error);
			return null;
		});

		if (res !== null) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				history.messages[message.id] = {
					...history.messages[message.id],
					...(history.messages[message.id].content !== message.content
						? { originalContent: history.messages[message.id].content }
						: {}),
					...message
				};
			}
		}
	};

	const getChatEventEmitter = async (modelId: string, chatId: string = '') => {
		return setInterval(() => {
			$socket?.emit('usage', {
				action: 'chat',
				model: modelId,
				chat_id: chatId
			});
		}, 1000);
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt, _user = null) => {
		let _responses = [];
		console.log('submitPrompt', $chatId);

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		if (selectedModels.includes('')) {
			toast.error($i18n.t('Model not selected'));
		} else if (messages.length != 0 && messages.at(-1).done != true) {
			// Response not done
			console.log('wait');
		} else if (
			files.length > 0 &&
			files.filter((file) => file.upload_status === false).length > 0
		) {
			// Upload not done
			toast.error(
				$i18n.t(
					`Oops! Hold tight! Your files are still in the processing oven. We're cooking them up to perfection. Please be patient and we'll let you know once they're ready.`
				)
			);
		} else {
			// Reset chat input textarea
			const chatTextAreaElement = document.getElementById('chat-textarea');

			if (chatTextAreaElement) {
				chatTextAreaElement.value = '';
				chatTextAreaElement.style.height = '';
			}

			const _files = JSON.parse(JSON.stringify(files));
			files = [];

			prompt = '';

			// Create user message
			let userMessageId = uuidv4();
			let userMessage = {
				id: userMessageId,
				parentId: messages.length !== 0 ? messages.at(-1).id : null,
				childrenIds: [],
				role: 'user',
				user: _user ?? undefined,
				content: userPrompt,
				files: _files.length > 0 ? _files : undefined,
				timestamp: Math.floor(Date.now() / 1000), // Unix epoch
				models: selectedModels.filter((m, mIdx) => selectedModels.indexOf(m) === mIdx)
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

			// Send prompt
			_responses = await sendPrompt(userPrompt, userMessageId);
		}

		return _responses;
	};

	const sendPrompt = async (prompt, parentId, modelId = null, newChat = true) => {
		let _responses = [];

		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
			? [atSelectedModel.id]
			: selectedModels;

		// Create response messages for each selected model
		const responseMessageIds = {};
		for (const modelId of selectedModelIds) {
			const model = $models.filter((m) => m.id === modelId).at(0);

			if (model) {
				let responseMessageId = uuidv4();
				let responseMessage = {
					parentId: parentId,
					id: responseMessageId,
					childrenIds: [],
					role: 'assistant',
					content: '',
					model: model.id,
					modelName: model.name ?? model.id,
					userContext: null,
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

				responseMessageIds[modelId] = responseMessageId;
			}
		}
		await tick();

		// Create new chat if only one message in messages
		if (newChat && messages.length == 2) {
			if ($settings.saveChatHistory ?? true) {
				chat = await createNewChat(localStorage.token, {
					id: $chatId,
					title: $i18n.t('New Chat'),
					models: selectedModels,
					system: $settings.system ?? undefined,
					options: {
						...($settings.params ?? {})
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

		const _chatId = JSON.parse(JSON.stringify($chatId));

		await Promise.all(
			selectedModelIds.map(async (modelId) => {
				console.log('modelId', modelId);
				const model = $models.filter((m) => m.id === modelId).at(0);

				if (model) {
					// If there are image files, check if model is vision capable
					const hasImages = messages.some((message) =>
						message.files?.some((file) => file.type === 'image')
					);

					if (hasImages && !(model.info?.meta?.capabilities?.vision ?? true)) {
						toast.error(
							$i18n.t('Model {{modelName}} is not vision capable', {
								modelName: model.name ?? model.id
							})
						);
					}

					let responseMessageId = responseMessageIds[modelId];
					let responseMessage = history.messages[responseMessageId];

					let userContext = null;
					if ($settings?.memory ?? false) {
						if (userContext === null) {
							const res = await queryMemory(localStorage.token, prompt).catch((error) => {
								toast.error(error);
								return null;
							});
							if (res) {
								if (res.documents[0].length > 0) {
									userContext = res.documents.reduce((acc, doc, index) => {
										const createdAtTimestamp = res.metadatas[index][0].created_at;
										const createdAtDate = new Date(createdAtTimestamp * 1000)
											.toISOString()
											.split('T')[0];
										acc.push(`${index + 1}. [${createdAtDate}]. ${doc[0]}`);
										return acc;
									}, []);
								}

								console.log(userContext);
							}
						}
					}
					responseMessage.userContext = userContext;

					const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);

					if (webSearchEnabled) {
						await getWebSearchResults(model.id, parentId, responseMessageId);
					}

					let _response = null;
					if (model?.owned_by === 'openai') {
						_response = await sendPromptOpenAI(model, prompt, responseMessageId, _chatId);
					} else if (model) {
						_response = await sendPromptOllama(model, prompt, responseMessageId, _chatId);
					}
					_responses.push(_response);

					console.log('chatEventEmitter', chatEventEmitter);

					if (chatEventEmitter) clearInterval(chatEventEmitter);
				} else {
					toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
				}
			})
		);

		await chats.set(await getChatList(localStorage.token));

		return _responses;
	};

	const getWebSearchResults = async (model: string, parentId: string, responseId: string) => {
		const responseMessage = history.messages[responseId];

		responseMessage.statusHistory = [
			{
				done: false,
				action: 'web_search',
				description: $i18n.t('Generating search query')
			}
		];
		messages = messages;

		const prompt = history.messages[parentId].content;
		let searchQuery = await generateSearchQuery(localStorage.token, model, messages, prompt).catch(
			(error) => {
				console.log(error);
				return prompt;
			}
		);

		if (!searchQuery) {
			toast.warning($i18n.t('No search query generated'));
			responseMessage.statusHistory.push({
				done: true,
				error: true,
				action: 'web_search',
				description: 'No search query generated'
			});

			messages = messages;
		}

		responseMessage.statusHistory.push({
			done: false,
			action: 'web_search',
			description: $i18n.t(`Searching "{{searchQuery}}"`, { searchQuery })
		});
		messages = messages;

		const results = await runWebSearch(localStorage.token, searchQuery).catch((error) => {
			console.log(error);
			toast.error(error);

			return null;
		});

		if (results) {
			responseMessage.statusHistory.push({
				done: true,
				action: 'web_search',
				description: $i18n.t('Searched {{count}} sites', { count: results.filenames.length }),
				query: searchQuery,
				urls: results.filenames
			});

			if (responseMessage?.files ?? undefined === undefined) {
				responseMessage.files = [];
			}

			responseMessage.files.push({
				collection_name: results.collection_name,
				name: searchQuery,
				type: 'web_search_results',
				urls: results.filenames
			});

			messages = messages;
		} else {
			responseMessage.statusHistory.push({
				done: true,
				error: true,
				action: 'web_search',
				description: 'No search results found'
			});
			messages = messages;
		}
	};

	const sendPromptOllama = async (model, userPrompt, responseMessageId, _chatId) => {
		let _response = null;

		const responseMessage = history.messages[responseMessageId];

		// Wait until history/message have been updated
		await tick();

		// Scroll down
		scrollToBottom();

		const messagesBody = [
			$settings.system || (responseMessage?.userContext ?? null)
				? {
						role: 'system',
						content: `${promptTemplate($settings?.system ?? '', $user.name)}${
							responseMessage?.userContext ?? null
								? `\n\nUser Context:\n${(responseMessage?.userContext ?? []).join('\n')}`
								: ''
						}`
				  }
				: undefined,
			...messages
		]
			.filter((message) => message?.content?.trim())
			.map((message, idx, arr) => {
				// Prepare the base message object
				const baseMessage = {
					role: message.role,
					content: message.content
				};

				// Extract and format image URLs if any exist
				const imageUrls = message.files
					?.filter((file) => file.type === 'image')
					.map((file) => file.url.slice(file.url.indexOf(',') + 1));

				// Add images array only if it contains elements
				if (imageUrls && imageUrls.length > 0 && message.role === 'user') {
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

		let docs = [];

		if (model?.info?.meta?.knowledge ?? false) {
			docs = model.info.meta.knowledge;
		}

		docs = [
			...docs,
			...messages
				.filter((message) => message?.files ?? null)
				.map((message) =>
					message.files.filter((item) =>
						['doc', 'collection', 'web_search_results'].includes(item.type)
					)
				)
				.flat(1)
		].filter(
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		const [res, controller] = await generateChatCompletion(localStorage.token, {
			model: model.id,
			messages: messagesBody,
			options: {
				...($settings.params ?? {}),
				stop:
					$settings?.params?.stop ?? undefined
						? $settings.params.stop.map((str) =>
								decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
						  )
						: undefined,
				num_predict: $settings?.params?.max_tokens ?? undefined,
				repeat_penalty: $settings?.params?.frequency_penalty ?? undefined
			},
			format: $settings.requestFormat ?? undefined,
			keep_alive: $settings.keepAlive ?? undefined,
			tool_ids: selectedToolIds.length > 0 ? selectedToolIds : undefined,
			docs: docs.length > 0 ? docs : undefined,
			citations: docs.length > 0,
			chat_id: $chatId
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
					} else {
						const messages = createMessagesList(responseMessageId);
						await chatCompletedHandler(model.id, messages);
					}

					_response = responseMessage.content;
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							let data = JSON.parse(line);

							if ('citations' in data) {
								responseMessage.citations = data.citations;
								continue;
							}

							if ('detail' in data) {
								throw data;
							}

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
									responseMessage.error = {
										code: 400,
										content: `Oops! No text generated from Ollama, Please try again.`
									};
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
											: `${model.id}`,
										{
											body: responseMessage.content,
											icon: selectedModelfile?.imageUrl ?? `${WEBUI_BASE_URL}/static/favicon.png`
										}
									);
								}

								if ($settings.responseAutoCopy) {
									copyToClipboard(responseMessage.content);
								}

								if ($settings.responseAutoPlayback && !$showCallOverlay) {
									await tick();
									document.getElementById(`speak-button-${responseMessage.id}`)?.click();
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
						history: history,
						models: selectedModels
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
					responseMessage.error = { content: error.detail };
				} else {
					toast.error(error.error);
					responseMessage.error = { content: error.error };
				}
			} else {
				toast.error(
					$i18n.t(`Uh-oh! There was an issue connecting to {{provider}}.`, { provider: 'Ollama' })
				);
				responseMessage.error = {
					content: $i18n.t(`Uh-oh! There was an issue connecting to {{provider}}.`, {
						provider: 'Ollama'
					})
				};
			}
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
			const _title = await generateChatTitle(userPrompt);
			await setChatTitle(_chatId, _title);
		}

		return _response;
	};

	const sendPromptOpenAI = async (model, userPrompt, responseMessageId, _chatId) => {
		let _response = null;
		const responseMessage = history.messages[responseMessageId];

		let docs = [];

		if (model?.info?.meta?.knowledge ?? false) {
			docs = model.info.meta.knowledge;
		}

		docs = [
			...docs,
			...messages
				.filter((message) => message?.files ?? null)
				.map((message) =>
					message.files.filter((item) =>
						['doc', 'collection', 'web_search_results'].includes(item.type)
					)
				)
				.flat(1)
		].filter(
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		scrollToBottom();

		try {
			const [res, controller] = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: model.id,
					stream: true,
					stream_options:
						model.info?.meta?.capabilities?.usage ?? false
							? {
									include_usage: true
							  }
							: undefined,
					messages: [
						$settings.system || (responseMessage?.userContext ?? null)
							? {
									role: 'system',
									content: `${promptTemplate($settings?.system ?? '', $user.name)}${
										responseMessage?.userContext ?? null
											? `\n\nUser Context:\n${(responseMessage?.userContext ?? []).join('\n')}`
											: ''
									}`
							  }
							: undefined,
						...messages
					]
						.filter((message) => message?.content?.trim())
						.map((message, idx, arr) => ({
							role: message.role,
							...((message.files?.filter((file) => file.type === 'image').length > 0 ?? false) &&
							message.role === 'user'
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
											arr.length - 1 !== idx
												? message.content
												: message?.raContent ?? message.content
								  })
						})),
					seed: $settings?.params?.seed ?? undefined,
					stop:
						$settings?.params?.stop ?? undefined
							? $settings.params.stop.map((str) =>
									decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
							  )
							: undefined,
					temperature: $settings?.params?.temperature ?? undefined,
					top_p: $settings?.params?.top_p ?? undefined,
					frequency_penalty: $settings?.params?.frequency_penalty ?? undefined,
					max_tokens: $settings?.params?.max_tokens ?? undefined,
					tool_ids: selectedToolIds.length > 0 ? selectedToolIds : undefined,
					docs: docs.length > 0 ? docs : undefined,
					citations: docs.length > 0,
					chat_id: $chatId
				},
				`${OPENAI_API_BASE_URL}`
			);

			// Wait until history/message have been updated
			await tick();

			scrollToBottom();

			if (res && res.ok && res.body) {
				const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
				let lastUsage = null;

				for await (const update of textStream) {
					const { value, done, citations, error, usage } = update;
					if (error) {
						await handleOpenAIError(error, null, model, responseMessage);
						break;
					}
					if (done || stopResponseFlag || _chatId !== $chatId) {
						responseMessage.done = true;
						messages = messages;

						if (stopResponseFlag) {
							controller.abort('User: Stop Response');
						} else {
							const messages = createMessagesList(responseMessageId);

							await chatCompletedHandler(model.id, messages);
						}

						_response = responseMessage.content;

						break;
					}

					if (usage) {
						lastUsage = usage;
					}

					if (citations) {
						responseMessage.citations = citations;
						continue;
					}

					if (responseMessage.content == '' && value == '\n') {
						continue;
					} else {
						responseMessage.content += value;
						messages = messages;
					}

					if (autoScroll) {
						scrollToBottom();
					}
				}

				if ($settings.notificationEnabled && !document.hasFocus()) {
					const notification = new Notification(`${model.id}`, {
						body: responseMessage.content,
						icon: `${WEBUI_BASE_URL}/static/favicon.png`
					});
				}

				if ($settings.responseAutoCopy) {
					copyToClipboard(responseMessage.content);
				}

				if ($settings.responseAutoPlayback && !$showCallOverlay) {
					await tick();

					document.getElementById(`speak-button-${responseMessage.id}`)?.click();
				}

				if (lastUsage) {
					responseMessage.info = { ...lastUsage, openai: true };
				}

				if ($chatId == _chatId) {
					if ($settings.saveChatHistory ?? true) {
						chat = await updateChatById(localStorage.token, _chatId, {
							models: selectedModels,
							messages: messages,
							history: history
						});
						await chats.set(await getChatList(localStorage.token));
					}
				}
			} else {
				await handleOpenAIError(null, res, model, responseMessage);
			}
		} catch (error) {
			await handleOpenAIError(error, null, model, responseMessage);
		}
		messages = messages;

		stopResponseFlag = false;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length == 2) {
			window.history.replaceState(history.state, '', `/c/${_chatId}`);

			const _title = await generateChatTitle(userPrompt);
			await setChatTitle(_chatId, _title);
		}

		return _response;
	};

	const handleOpenAIError = async (error, res: Response | null, model, responseMessage) => {
		let errorMessage = '';
		let innerError;

		if (error) {
			innerError = error;
		} else if (res !== null) {
			innerError = await res.json();
		}
		console.error(innerError);
		if ('detail' in innerError) {
			toast.error(innerError.detail);
			errorMessage = innerError.detail;
		} else if ('error' in innerError) {
			if ('message' in innerError.error) {
				toast.error(innerError.error.message);
				errorMessage = innerError.error.message;
			} else {
				toast.error(innerError.error);
				errorMessage = innerError.error;
			}
		} else if ('message' in innerError) {
			toast.error(innerError.message);
			errorMessage = innerError.message;
		}

		responseMessage.error = {
			content:
				$i18n.t(`Uh-oh! There was an issue connecting to {{provider}}.`, {
					provider: model.name ?? model.id
				}) +
				'\n' +
				errorMessage
		};
		responseMessage.done = true;

		messages = messages;
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const regenerateResponse = async (message) => {
		console.log('regenerateResponse');

		if (messages.length != 0) {
			let userMessage = history.messages[message.parentId];
			let userPrompt = userMessage.content;

			if ((userMessage?.models ?? [...selectedModels]).length == 1) {
				await sendPrompt(userPrompt, userMessage.id, undefined, false);
			} else {
				await sendPrompt(userPrompt, userMessage.id, message.model, false);
			}
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
				if (model?.owned_by === 'openai') {
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
			toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
		}
	};

	const generateChatTitle = async (userPrompt) => {
		if ($settings?.title?.auto ?? true) {
			const title = await generateTitle(
				localStorage.token,
				selectedModels[0],
				userPrompt,
				$chatId
			).catch((error) => {
				console.error(error);
				return 'New Chat';
			});

			return title;
		} else {
			return `${userPrompt}`;
		}
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

	const getTags = async () => {
		return await getTagsById(localStorage.token, $chatId).catch(async (error) => {
			return [];
		});
	};
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} | ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<CallOverlay {submitPrompt} bind:files />

{#if !chatIdProp || (loaded && chatIdProp)}
	<div
		class="h-screen max-h-[100dvh] {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} w-full max-w-full flex flex-col"
	>
		<Navbar
			{title}
			bind:selectedModels
			bind:showModelSelector
			shareEnabled={messages.length > 0}
			{chat}
			{initNewChat}
		/>

		{#if $banners.length > 0 && messages.length === 0 && !$chatId && selectedModels.length <= 1}
			<div
				class="absolute top-[4.25rem] w-full {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''}"
			>
				<div class=" flex flex-col gap-1 w-full">
					{#each $banners.filter( (b) => (b.dismissible ? !JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]').includes(b.id) : true) ) as banner}
						<Banner
							{banner}
							on:dismiss={(e) => {
								const bannerId = e.detail;

								localStorage.setItem(
									'dismissedBannerIds',
									JSON.stringify(
										[
											bannerId,
											...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]')
										].filter((id) => $banners.find((b) => b.id === id))
									)
								);
							}}
						/>
					{/each}
				</div>
			</div>
		{/if}

		<div class="flex flex-col flex-auto">
			<div
				class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full"
				id="messages-container"
				bind:this={messagesContainerElement}
				on:scroll={(e) => {
					autoScroll =
						messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
						messagesContainerElement.clientHeight + 5;
				}}
			>
				<div class=" h-full w-full flex flex-col {chatIdProp ? 'py-4' : 'pt-2 pb-4'}">
					<Messages
						chatId={$chatId}
						{selectedModels}
						{processing}
						bind:history
						bind:messages
						bind:autoScroll
						bind:prompt
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
				bind:selectedToolIds
				bind:webSearchEnabled
				bind:atSelectedModel
				availableToolIds={selectedModelIds.reduce((a, e, i, arr) => {
					const model = $models.find((m) => m.id === e);
					if (model?.info?.meta?.toolIds ?? false) {
						return [...new Set([...a, ...model.info.meta.toolIds])];
					}
					return a;
				}, [])}
				{selectedModels}
				{messages}
				{submitPrompt}
				{stopResponse}
			/>
		</div>
	</div>
{/if}
