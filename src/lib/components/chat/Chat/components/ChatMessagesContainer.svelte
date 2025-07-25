<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import { settings, selectedFolder } from '$lib/stores';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Placeholder from '$lib/components/chat/Placeholder.svelte';
	import type { ChatHistory, ChatMessage } from '../types';
	import type { Model } from '$lib/stores';
	import { createMessagesList } from '../utils/messageUtils';
	
	export let chatId: string;
	export let history: ChatHistory;
	export let selectedModels: string[];
	export let atSelectedModel: Model | undefined;
	export let autoScroll = true;
	export let processing = '';
	export let messagesContainerElement: HTMLDivElement;
	export let bottomPadding = false;
	
	// Message action handlers
	export let sendPrompt: (prompt: string, options?: any) => Promise<void>;
	export let showMessage: (message: ChatMessage) => Promise<void>;
	export let submitMessage: (parentId: string, prompt: string) => Promise<void>;
	export let continueResponse: () => Promise<void>;
	export let regenerateResponse: (message: ChatMessage) => Promise<void>;
	export let mergeResponses: (messageId: string, responses: any[], chatId: string) => Promise<void>;
	export let chatActionHandler: (chatId: string, actionId: string, modelId: string, responseMessageId: string, event?: any) => Promise<void>;
	export let addMessages: (data: any) => Promise<void>;
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	$: messages = createMessagesList(history, history.currentId);
	$: showPlaceholder = ($settings?.landingPageMode === 'chat' && !$selectedFolder) || messages.length === 0;
	
	function handleScroll(e: Event) {
		const container = e.target as HTMLDivElement;
		const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 5;
		autoScroll = isAtBottom;
		dispatch('scroll', { autoScroll });
	}
	
	function setInputText(text: string) {
		dispatch('setInputText', { text });
	}
</script>

<div class="flex flex-col flex-auto z-10 w-full @container overflow-auto">
	{#if showPlaceholder}
		<Placeholder 
			{selectedModels} 
			{showMessage}
		/>
	{:else}
		<div
			class="pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden 
				{$settings?.backgroundPattern !== 'none' && $settings?.backgroundPattern 
					? `background-pattern-${$settings.backgroundPattern}` 
					: ''}"
			id="messages-container"
			bind:this={messagesContainerElement}
			style={$settings?.backgroundPattern !== 'none' && $settings?.backgroundOpacity !== undefined 
				? `--background-pattern-opacity: ${$settings.backgroundOpacity / 100};` 
				: ''}
			on:scroll={handleScroll}
		>
			<div class="h-full w-full flex flex-col">
				<Messages
					{chatId}
					bind:history
					bind:autoScroll
					bind:prompt
					{setInputText}
					{selectedModels}
					{atSelectedModel}
					{sendPrompt}
					{showMessage}
					{submitMessage}
					{continueResponse}
					{regenerateResponse}
					{mergeResponses}
					{chatActionHandler}
					{addMessages}
					{bottomPadding}
					{processing}
				/>
			</div>
		</div>
	{/if}
</div>