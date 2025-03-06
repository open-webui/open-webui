<script>
	import Markdown from '../chat/Messages/Markdown.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';
	export let history;
	import { v4 as uuidv4 } from 'uuid';
	let messages = [];
	let messagesLoading = false;

	$: messages = Object.keys(history.messages)
		.filter((key) => history.messages[key].role === 'assistant')
		.map((key) => history.messages[key].content);
	const loadMoreMessages = async () => {
		messagesLoading = true;
		await tick();
		messagesLoading = false;
	};

	let selectedModels = [''];
	console.log(history)

	import { onDestroy, onMount } from 'svelte';
	import { selectedText, selectionRange } from './store.js';

	let showMenu = false;
	let menuRef;
	let x = 0;
	$: x = 0;
	let y = 0;
	$: y = 0;

	let containerRef;

	let menuStyle = '';
	let promptt = '';



	// onMount(() => {
	// 	const handleSelectionChange = () => {
	// 		const selection = window.getSelection();
	// 		const text = selection.toString();
	// 		selectedText.set(text);

	// 		if (text) {
	// 			const range = selection.getRangeAt(0);
	// 			selectionRange.set(range);
	// 			const rect = range.getBoundingClientRect();
	// 			showMenu = true;
	// 			menuStyle = `absolute z-10 top: ${rect.bottom + window.scrollY}px; left: ${rect.left + window.scrollX}px;`;
	// 			console.log('Selection detected:', text);
	// 			console.log('Show Menu' , showMenu)
	// 			console.log('Menu style:', menuStyle);
	// 		} else {
	// 			showMenu = false;
	// 			console.log('No selection');
	// 		}
	// 	};

	// 	document.addEventListener('selectionchange', handleSelectionChange);

	// 	return () => {
	// 		document.removeEventListener('selectionchange', handleSelectionChange);
	// 	};
	// });

	const applyStyle = (style) => {
		// const range = selection?.getRangeAt(0);
		// if (range) {
		// 	const span = document.createElement('span');
		// 	span.style.fontWeight = style === 'bold' ? 'bold' : 'normal';
		// 	span.style.fontStyle = style === 'italic' ? 'italic' : 'normal';
		// 	range.surroundContents(span);
		// 	selectedText.set('');
		// 	showMenu = false;
		// }
		document.execCommand('bold', false, null);
		showMenu = false;
	};

	// const removeText = () => {
	// 	const range = get(selectionRange);
	// 	if (range) {
	// 		range.deleteContents();
	// 		selectedText.set('');
	// 		showMenu = false;
	// 	}
	// };

	// const handleMouseOver = () => {
	// 	if (get(selectedText)) {
	// 		showMenu = true;
	// 	}
	// };

	onMount(() => {
		document.addEventListener('click', handleMouseOut);
	});

	onDestroy(() => {
		document.removeEventListener('click', handleMouseOut);
	});

	const handleMouseOut = (event) => {
		if (menuRef && !menuRef.contains(event.target)) {
			showMenu = false;
		}
	};
	console.log(' the whole content', messages[messages.length - 1]);
	console.log('############################################');

	function handleTextSelect(event) {
		const selection = window.getSelection();
		if (selection?.toString().trim() !== '') {
			const range = selection?.getRangeAt(0);
			const rect = range.getBoundingClientRect();

			const containerRect = containerRef.getBoundingClientRect();

			x = Math.round(rect?.left) - containerRect.left + containerRef.scrollLeft;
			y = Math.round(rect.top) - containerRect.top + containerRef.scrollTop - 70;

			const menuWidth = 100;
			const menuHeight = 120;

			if (x + menuWidth > containerRect.width) {
				x = containerRect.width - menuWidth;
			}

			if (y < 0) {
				y = rect.bottom - containerRect.top + containerRef.scrollTop;
			}

			if (y + menuHeight > containerRect.height) {
				y = containerRect.height - menuHeight;
			}

			showMenu = true;
			console.log(showMenu);
		} else {
			showMenu = false;
		}
	}
	// const submitPrompt = async (userPrompt, { _raw = false } = {}) => {
	// 	console.log('submitPrompt', userPrompt);
	// 	// console.log(' karan is here now')

	// 	const messages = createMessagesList(history.currentId);
	// 	const _selectedModels = selectedModels.map((modelId) =>
	// 		$models.map((m) => m.id).includes(modelId) ? modelId : ''
	// 	);
	// 	if (JSON.stringify(selectedModels) !== JSON.stringify(_selectedModels)) {
	// 		selectedModels = _selectedModels;
	// 	}

	// 	if (userPrompt === '') {
	// 		toast.error($i18n.t('Please enter a prompt'));
	// 		return;
	// 	}
	// 	if (selectedModels.includes('')) {
	// 		toast.error($i18n.t('Model not selected'));
	// 		return;
	// 	}

	// 	if (messages.length != 0 && messages.at(-1).done != true) {
	// 		// Response not done
	// 		return;
	// 	}
	// 	if (messages.length != 0 && messages.at(-1).error) {
	// 		// Error in response
	// 		toast.error($i18n.t(`Oops! There was an error in the previous response.`));
	// 		return;
	// 	}	

	// 	prompt = '';
	// 	await tick();

	// 	// Reset chat input textarea
	// 	const chatInputElement = document.getElementById('chat-input');

	// 	if (chatInputElement) {
	// 		chatInputElement.style.height = '';
	// 	}
	// 	prompt = '';
	// 	_files = []
	// 	// Create user message
	// 	let userMessageId = uuidv4();
	// 	let userMessage = {
	// 		id: userMessageId,
	// 		parentId: messages.length !== 0 ? messages.at(-1).id : null,
	// 		childrenIds: [],
	// 		role: 'user',
	// 		content: userPrompt,
	// 		files: _files.length > 0 ? _files : undefined,
	// 		timestamp: Math.floor(Date.now() / 1000), // Unix epoch
	// 		models: selectedModels
	// 	};

	// 	// Add message to history and Set currentId to messageId
	// 	history.messages[userMessageId] = userMessage;
	// 	history.currentId = userMessageId;

	// 	// Append messageId to childrenIds of parent message
	// 	if (messages.length !== 0) {
	// 		history.messages[messages.at(-1).id].childrenIds.push(userMessageId);
	// 	}

	// 	// Wait until history/message have been updated
	// 	await tick();

	// 	// focus on chat input
	// 	const chatInput = document.getElementById('chat-input');
	// 	chatInput?.focus();

	// 	saveSessionSelectedModels();

	// 	await sendPrompt(userPrompt, userMessageId, { newChat: true });
	// };
	
	// const initChatHandler = async () => {
	// 	if (!$temporaryChatEnabled) {
	// 		chat = await createNewChat(localStorage.token, {
	// 			id: $chatId,
	// 			title: $i18n.t('New Chat'),
	// 			models: selectedModels,
	// 			system: $settings.system ?? undefined,
	// 			params: params,
	// 			history: history,
	// 			messages: createMessagesList(history.currentId),
	// 			tags: [],
	// 			timestamp: Date.now()
	// 		});

	// 		currentChatPage.set(1);
	// 		await chats.set(await getChatList(localStorage.token, $currentChatPage));
	// 		await chatId.set(chat.id);

	// 		window.history.replaceState(history.state, '', `/c/${chat.id}`);
	// 	} else {
	// 		await chatId.set('local');
	// 	}
	// 	await tick();
	// };

	// const saveChatHandler = async (_chatId) => {
	// 	if ($chatId == _chatId) {
	// 		if (!$temporaryChatEnabled) {
	// 			chat = await updateChatById(localStorage.token, _chatId, {
	// 				models: selectedModels,
	// 				history: history,
	// 				messages: createMessagesList(history.currentId),
	// 				params: params,
	// 				files: chatFiles
	// 			});

	// 			currentChatPage.set(1);
	// 			await chats.set(await getChatList(localStorage.token, $currentChatPage));
	// 		}
	// 	}
	// };
	
	// const saveSessionSelectedModels = () => {
	// 	if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
	// 		return;
	// 	}
	// 	sessionStorage.selectedModels = JSON.stringify(selectedModels);
	// 	console.log('saveSessionSelectedModels', selectedModels, sessionStorage.selectedModels);
	// };

	// const sendPrompt = async (
	// 	prompt: string,
	// 	parentId: string,
	// 	{ modelId = null, modelIdx = null, newChat = false } = {}
	// ) => {
	// 	// Create new chat if newChat is true and first user message
	// 	if (
	// 		newChat &&
	// 		history.messages[history.currentId].parentId === null &&
	// 		history.messages[history.currentId].role === 'user'
	// 	) {
	// 		await initChatHandler();
	// 	} else {
	// 		await saveChatHandler($chatId);
	// 	}

	// 	// If modelId is provided, use it, else use selected model
	// 	let selectedModelIds = modelId
	// 		? [modelId]
	// 		: atSelectedModel !== undefined
	// 			? [atSelectedModel.id]
	// 			: selectedModels;

	// 	// Create response messages for each selected model
	// 	const responseMessageIds: Record<PropertyKey, string> = {};
	// 	for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
	// 		const model = $models.filter((m) => m.id === modelId).at(0);

	// 		if (model) {
	// 			let responseMessageId = uuidv4();
	// 			let responseMessage = {
	// 				parentId: parentId,
	// 				id: responseMessageId,
	// 				childrenIds: [],
	// 				role: 'assistant',
	// 				content: '',
	// 				model: model.id,
	// 				modelName: model.name ?? model.id,
	// 				modelIdx: modelIdx ? modelIdx : _modelIdx,
	// 				userContext: null,
	// 				timestamp: Math.floor(Date.now() / 1000) // Unix epoch
	// 			};

	// 			// Add message to history and Set currentId to messageId
	// 			history.messages[responseMessageId] = responseMessage;
	// 			history.currentId = responseMessageId;

	// 			// Append messageId to childrenIds of parent message
	// 			if (parentId !== null) {
	// 				history.messages[parentId].childrenIds = [
	// 					...history.messages[parentId].childrenIds,
	// 					responseMessageId
	// 				];
	// 			}

	// 			responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
	// 		}
	// 	}
	// 	await tick();

	// 	// Save chat after all messages have been created
	// 	await saveChatHandler($chatId);

	// 	const _chatId = JSON.parse(JSON.stringify($chatId));
	// 	await Promise.all(
	// 		selectedModelIds.map(async (modelId, _modelIdx) => {
	// 			console.log('modelId', modelId);
	// 			const model = $models.filter((m) => m.id === modelId).at(0);

	// 			if (model) {
	// 				const messages = createMessagesList(parentId);
	// 				// If there are image files, check if model is vision capable
	// 				const hasImages = messages.some((message) =>
	// 					message.files?.some((file) => file.type === 'image')
	// 				);

	// 				if (hasImages && !(model.info?.meta?.capabilities?.vision ?? true)) {
	// 					toast.error(
	// 						$i18n.t('Model {{modelName}} is not vision capable', {
	// 							modelName: model.name ?? model.id
	// 						})
	// 					);
	// 				}

	// 				let responseMessageId =
	// 					responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`];
	// 				let responseMessage = history.messages[responseMessageId];

	// 				let userContext = null;
	// 				if ($settings?.memory ?? false) {
	// 					if (userContext === null) {
	// 						const res = await queryMemory(localStorage.token, prompt).catch((error) => {
	// 							toast.error(error);
	// 							return null;
	// 						});
	// 						if (res) {
	// 							if (res.documents[0].length > 0) {
	// 								userContext = res.documents[0].reduce((acc, doc, index) => {
	// 									const createdAtTimestamp = res.metadatas[0][index].created_at;
	// 									const createdAtDate = new Date(createdAtTimestamp * 1000)
	// 										.toISOString()
	// 										.split('T')[0];
	// 									return `${acc}${index + 1}. [${createdAtDate}]. ${doc}\n`;
	// 								}, '');
	// 							}

	// 							console.log(userContext);
	// 						}
	// 					}
	// 				}
	// 				responseMessage.userContext = userContext;

	// 				const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);

	// 				scrollToBottom();
	// 				await sendPromptSocket(model, responseMessageId, _chatId);

	// 				if (chatEventEmitter) clearInterval(chatEventEmitter);
	// 			} else {
	// 				toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
	// 			}
	// 		})
	// 	);

	// 	currentChatPage.set(1);
	// 	chats.set(await getChatList(localStorage.token, $currentChatPage));
	// };
</script>

<div class="mt-16 right-pane space-y-3 overflow-y-scroll overflow-x-none relative">
	<div
		bind:this={containerRef}
		on:mouseup={handleTextSelect}
		class="w-full textSelectionBox border-2 overflow-none"
	>
		<Markdown content={messages[messages.length - 1]} />
	</div>
	<hr />

	<!-- {#if showMenu} -->
	<div
		class={'bg-white shadow-lg rounded-lg px-4 py-2 space-x-4'}
		style={`position : absolute ; left : ${x}px ; top : ${y}px ; z-index : 1`}
		bind:this={menuRef}
	>
		<button class="rounded-md bg-neutral-200 px-4 py-2" on:click={() => applyStyle('bold')}
			><svg
				xmlns="http://www.w3.org/2000/svg"
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="lucide lucide-bold"
				><path d="M6 12h9a4 4 0 0 1 0 8H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h7a4 4 0 0 1 0 8" /></svg
			></button
		>
		<button on:click={() => applyStyle('italic')}>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="lucide lucide-italic"
				><line x1="19" x2="10" y1="4" y2="4" /><line x1="14" x2="5" y1="20" y2="20" /><line
					x1="15"
					x2="9"
					y1="4"
					y2="20"
				/></svg
			>
		</button>
		
		<input placeholder="Enter something" bind:value={promptt}/>
	</div>

	<!-- {/if -->
	<p>{$selectedText}</p>
</div>
