<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { page } from '$app/stores';
	import type { Writable, Unsubscriber } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import { 
		chatId as globalChatId,
		chatTitle,
		socket,
		showControls,
		showCallOverlay,
		temporaryChatEnabled,
		showArtifacts,
		user,
		models
	} from '$lib/stores';
	
	// Import components
	import ChatContainer from './components/ChatContainer.svelte';
	import ChatHeader from './components/ChatHeader.svelte';
	import ChatMessagesContainer from './components/ChatMessagesContainer.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import ChatControls from '$lib/components/chat/ChatControls.svelte';
	import EventConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import NotificationToast from '$lib/components/NotificationToast.svelte';
	
	// Import stores and hooks
	import {
		chatHistory,
		selectedModels,
		atSelectedModel,
		selectedToolIds,
		selectedFilterIds,
		imageGenerationEnabled,
		webSearchEnabled,
		codeInterpreterEnabled,
		processing,
		autoScroll,
		showCommands,
		prompt,
		files,
		chatParams,
		chatMetadata,
		chatStore
	} from './stores/chatStore';
	
	import { useChatOperations } from './hooks/useChatOperations';
	import { useFileUpload } from './hooks/useFileUpload';
	
	// Props
	export let chatIdProp = '';
	
	// Context
	const i18n: Writable<i18nType> = getContext('i18n');
	
	// Local state
	let loading = true;
	let messagesContainerElement: HTMLDivElement;
	let messageInput: any;
	let navbarElement: any;
	
	// Event confirmation dialog state
	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventCallback: ((value: any) => void) | null = null;
	
	// Subscriptions
	let chatIdUnsubscriber: Unsubscriber | undefined;
	
	// Initialize hooks
	const chatOps = useChatOperations();
	const fileUpload = useFileUpload();
	
	// Navigation handler
	const navigateHandler = async () => {
		loading = true;
		
		// Reset input state
		prompt.set('');
		messageInput?.setText('');
		files.set([]);
		selectedToolIds.set([]);
		selectedFilterIds.set([]);
		webSearchEnabled.set(false);
		imageGenerationEnabled.set(false);
		codeInterpreterEnabled.set(false);
		
		// Load stored input if available
		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);
		
		if (chatIdProp && (await chatOps.loadChat(chatIdProp))) {
			loading = false;
			scrollToBottom();
			
			// Restore input from session storage
			if (storageChatInput && !$temporaryChatEnabled) {
				try {
					const input = JSON.parse(storageChatInput);
					messageInput?.setText(input.prompt);
					files.set(input.files || []);
					selectedToolIds.set(input.selectedToolIds || []);
					selectedFilterIds.set(input.selectedFilterIds || []);
					webSearchEnabled.set(input.webSearchEnabled || false);
					imageGenerationEnabled.set(input.imageGenerationEnabled || false);
					codeInterpreterEnabled.set(input.codeInterpreterEnabled || false);
				} catch (e) {
					console.error('Failed to restore chat input:', e);
				}
			}
			
			// Focus input
			document.getElementById('chat-input')?.focus();
		} else {
			// Navigate to home if chat not found
			await goto('/');
		}
	};
	
	// Scroll to bottom of messages
	const scrollToBottom = (behavior: 'auto' | 'smooth' = 'auto') => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};
	
	// Handle input submission
	const submitPrompt = async (userPrompt: string, options: any = {}) => {
		if (!userPrompt.trim() && $files.length === 0) return;
		
		processing.set('processing');
		
		try {
			await chatOps.sendPrompt(userPrompt, {
				model: $atSelectedModel?.id || $selectedModels[0],
				files: $files,
				webSearchEnabled: $webSearchEnabled,
				imageGenerationEnabled: $imageGenerationEnabled,
				tools: $selectedToolIds,
				params: $chatParams
			});
			
			// Clear input
			prompt.set('');
			files.set([]);
			messageInput?.setText('');
			
			// Save chat
			if ($chatMetadata.id) {
				await chatOps.updateChatMetadata({
					title: $chatTitle || 'New Chat'
				});
			}
		} catch (error) {
			console.error('Failed to submit prompt:', error);
		} finally {
			processing.set('');
		}
	};
	
	// Handle message actions
	const showMessage = async (message: any) => {
		chatStore.setCurrentId(message.id);
		
		// Update global chat ID if needed
		if ($chatMetadata.id && $globalChatId !== $chatMetadata.id) {
			globalChatId.set($chatMetadata.id);
		}
	};
	
	const submitMessage = async (parentId: string, userPrompt: string) => {
		chatStore.setCurrentId(parentId);
		await submitPrompt(userPrompt);
	};
	
	const regenerateResponse = async (message: any) => {
		processing.set('processing');
		try {
			await chatOps.regenerateResponse(message);
		} finally {
			processing.set('');
		}
	};
	
	const continueResponse = async () => {
		processing.set('processing');
		try {
			await chatOps.continueResponse();
		} finally {
			processing.set('');
		}
	};
	
	const stopResponse = async () => {
		await chatOps.stopResponse();
		processing.set('');
	};
	
	// Placeholder handlers for features not yet refactored
	const mergeResponses = async (messageId: string, responses: any[], chatId: string) => {
		// TODO: Implement merge responses
		console.log('Merge responses not implemented');
	};
	
	const chatActionHandler = async (chatId: string, actionId: string, modelId: string, responseMessageId: string, event?: any) => {
		// TODO: Implement chat action handler
		console.log('Chat action handler not implemented');
	};
	
	const addMessages = async (data: any) => {
		// TODO: Implement add messages
		console.log('Add messages not implemented');
	};
	
	// File upload handlers
	const onFileUpload = async (e: CustomEvent) => {
		const uploadedFiles = await Promise.all(
			e.detail.files.map((file: File) => fileUpload.uploadLocalFile(file))
		);
		
		files.update(f => [...f, ...uploadedFiles.filter(Boolean)]);
	};
	
	const onFileRemove = (fileId: string) => {
		files.update(f => fileUpload.removeFile(f, fileId));
	};
	
	// Event confirmation helper
	const showConfirmation = (title: string, message: string, callback: (value: any) => void, options: any = {}) => {
		eventConfirmationTitle = title;
		eventConfirmationMessage = message;
		eventConfirmationInput = options.input || false;
		eventConfirmationInputPlaceholder = options.placeholder || '';
		eventConfirmationInputValue = options.defaultValue || '';
		eventCallback = callback;
		showEventConfirmation = true;
	};
	
	// Lifecycle
	onMount(() => {
		// Subscribe to chat ID changes
		chatIdUnsubscriber = globalChatId.subscribe(id => {
			if (id && id !== chatIdProp) {
				chatIdProp = id;
			}
		});
		
		// Initial navigation
		if (chatIdProp) {
			navigateHandler();
		}
	});
	
	onDestroy(() => {
		chatIdUnsubscriber?.();
		
		// Save current input state
		if (!$temporaryChatEnabled && $chatMetadata.id) {
			sessionStorage.setItem(
				`chat-input-${$chatMetadata.id}`,
				JSON.stringify({
					prompt: $prompt,
					files: $files,
					selectedToolIds: $selectedToolIds,
					selectedFilterIds: $selectedFilterIds,
					webSearchEnabled: $webSearchEnabled,
					imageGenerationEnabled: $imageGenerationEnabled,
					codeInterpreterEnabled: $codeInterpreterEnabled
				})
			);
		}
	});
	
	// Reactive statements
	$: if (chatIdProp) {
		navigateHandler();
	}
	
	$: if ($chatHistory.currentId && $autoScroll) {
		scrollToBottom('smooth');
	}
</script>

<NotificationToast />

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	on:confirm={(e) => {
		eventCallback?.(e.detail || true);
	}}
	on:cancel={() => {
		eventCallback?.(false);
	}}
/>

<ChatContainer {loading}>
	<div slot="main" class="flex flex-col h-full">
		<ChatHeader
			chatId={$chatMetadata.id}
			title={$chatTitle}
			bind:selectedModels={$selectedModels}
			history={$chatHistory}
			params={$chatParams}
			shareEnabled={!!$chatHistory.currentId}
			showBanners={!$showCommands}
			initNewChat={chatOps.initNewChat}
		/>
		
		<ChatMessagesContainer
			chatId={$chatMetadata.id}
			bind:history={$chatHistory}
			selectedModels={$selectedModels}
			atSelectedModel={$atSelectedModel}
			bind:autoScroll={$autoScroll}
			bind:processing={$processing}
			bind:messagesContainerElement
			bottomPadding={$files.length > 0}
			{sendPrompt}
			{showMessage}
			{submitMessage}
			{continueResponse}
			{regenerateResponse}
			{mergeResponses}
			{chatActionHandler}
			{addMessages}
		/>
		
		<MessageInput
			bind:this={messageInput}
			bind:prompt={$prompt}
			bind:files={$files}
			bind:selectedModels={$selectedModels}
			bind:atSelectedModel={$atSelectedModel}
			bind:selectedToolIds={$selectedToolIds}
			bind:webSearchEnabled={$webSearchEnabled}
			bind:imageGenerationEnabled={$imageGenerationEnabled}
			bind:codeInterpreterEnabled={$codeInterpreterEnabled}
			{submitPrompt}
			{stopResponse}
			on:fileUpload={onFileUpload}
			on:fileRemove={(e) => onFileRemove(e.detail)}
		/>
		
		{#if $showControls}
			<ChatControls />
		{/if}
	</div>
	
	<div slot="artifacts">
		<!-- Artifacts panel content -->
		<div class="h-full bg-gray-50 dark:bg-gray-850 p-4">
			<h3 class="text-lg font-semibold mb-4">{$i18n.t('Artifacts')}</h3>
			<!-- TODO: Implement artifacts display -->
		</div>
	</div>
</ChatContainer>