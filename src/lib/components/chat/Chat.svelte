<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { i18n } from '$lib/i18n';
	import { settings } from '$lib/stores';
	import favicon from '$lib/assets/icons/favicon.png';
	import { generateCiceroChatCompletion } from '$lib/apis/ciceroapi';

	export let chatId: string;
	export let history: any = { messages: {}, currentId: null };
	let userPrompt: string = '';

	interface ChatEvent {
		type: string;
		data: {
			chatId: string;
			messageId: string;
			content?: string;
			done?: boolean;
			error?: boolean;
		};
	}

	const chatEventHandler = async (event: ChatEvent) => {
		if (event.data.chatId !== chatId) return;
		
		const messageId = event.data.messageId;
		const message = history.messages[messageId];
		if (!message) return;

		if (event.data.content) {
			message.content += event.data.content;
		}
		
		if (event.data.done !== undefined) {
			message.done = event.data.done;
		}
		
		if (event.data.error) {
			message.error = true;
			toast.error($i18n.t('Error generating response'));
		}
		
		history = { ...history };
		await tick();
	};

	onMount(async () => {
		// Initialize welcome message
		const welcomeMessageId = uuidv4();
		history.messages[welcomeMessageId] = {
			id: welcomeMessageId,
			role: 'assistant',
			content: $i18n.t('welcome.message'),
			done: true,
			timestamp: new Date().getTime(),
			parentId: null,
			childrenIds: [],
			model: 'arthrod/cicerollamatry8',
			isWelcomeMessage: true
		};
		history.currentId = welcomeMessageId;
	});

	const sendPrompt = async (userPrompt: string) => {
		if (!userPrompt.trim()) {
			toast.error($i18n.t('Please enter a message'));
			return;
		}

		const userMessageId = uuidv4();
		const responseMessageId = uuidv4();
		const parentMessage = history.messages[history.currentId];
		const isFirstMessage = parentMessage && parentMessage.isWelcomeMessage;

		const userMessage = {
			id: userMessageId,
			parentId: isFirstMessage ? null : (parentMessage ? parentMessage.id : null),
			childrenIds: [responseMessageId],
			role: 'user',
			content: userPrompt,
			timestamp: new Date().getTime()
		};

		const responseMessage = {
			id: responseMessageId,
			parentId: userMessageId,
			childrenIds: [],
			role: 'assistant',
			content: '',
			done: false,
			error: false,
			timestamp: new Date().getTime()
		};

		history.messages[userMessageId] = userMessage;
		history.messages[responseMessageId] = responseMessage;
		history.currentId = responseMessageId;
		history = { ...history };

		// Clear input after sending
		userPrompt = '';

		try {
			const [res, controller] = await generateCiceroChatCompletion(
				localStorage.token,
				{
					messages: [
						...Object.values(history.messages)
							.filter(m => !m.isWelcomeMessage)
							.map(m => ({
								role: m.role,
								content: m.content
							})),
						{ role: 'user', content: userPrompt }
					],
					model: 'arthrod/cicerollamatry8',
					stream: true
				}
			);

			if (!res?.ok) {
				const errorData = await res.json().catch(() => null);
				throw new Error(errorData?.error || `HTTP error! status: ${res.status}`);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error('No reader available');

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = new TextDecoder().decode(value);
				const lines = chunk.split('\n').filter(line => line.trim() !== '');

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						const jsonData = line.slice(6);
						if (jsonData === '[DONE]') {
							chatEventHandler({
								type: 'chat',
								data: {
									chatId,
									messageId: responseMessageId,
									done: true
								}
							});
							continue;
						}

						try {
							const data = JSON.parse(jsonData);
							const content = data.choices[0]?.delta?.content;
							if (content) {
								chatEventHandler({
									type: 'chat',
									data: {
										chatId,
										messageId: responseMessageId,
										content
									}
								});
							}
						} catch (e) {
							console.error('Error parsing SSE data:', e);
						}
					}
				}
			}

			// Handle notifications and auto-copy if enabled
			if ($settings.notificationEnabled && !document.hasFocus()) {
				new Notification('Cicero-Pt-BR', {
					body: responseMessage.content,
					icon: favicon
				});
			}

			if ($settings?.responseAutoCopy ?? false) {
				await navigator.clipboard.writeText(responseMessage.content);
			}

		} catch (error) {
			console.error('Error in chat completion:', error);
			chatEventHandler({
				type: 'chat',
				data: {
					chatId,
					messageId: responseMessageId,
					error: true,
					done: true
				}
			});
		}
	};
</script>

<div class="flex flex-col h-full">
	<div class="flex-1 overflow-y-auto p-4">
		{#each Object.values(history.messages) as message}
			<div class="mb-4 {message.role === 'assistant' ? 'bg-gray-100 dark:bg-gray-800 rounded p-3' : 'p-3'}">
				<div class="font-bold mb-2">{message.role === 'assistant' ? 'Cicero' : 'You'}</div>
				<div class="whitespace-pre-wrap">{message.content}</div>
			</div>
		{/each}
	</div>
	
	<div class="p-4 border-t dark:border-gray-700">
		<form on:submit|preventDefault={() => sendPrompt(userPrompt)}>
			<input
				type="text"
				bind:value={userPrompt}
				placeholder={$i18n.t('Type your message...')}
				class="w-full p-3 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
			/>
		</form>
	</div>
</div>
