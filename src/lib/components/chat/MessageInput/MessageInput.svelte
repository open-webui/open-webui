<script lang="ts">
	import { createEventDispatcher, getContext, onMount, onDestroy } from 'svelte';
	import { get } from 'svelte/store';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import { 
		settings, 
		config, 
		models as modelsStore,
		showCallOverlay,
		showControls,
		temporaryChatEnabled,
		mobile
	} from '$lib/stores';
	
	// Import components
	import TextInput from './components/TextInput.svelte';
	import FileUploadArea from './components/FileUploadArea.svelte';
	import ModelSelector from './components/ModelSelector.svelte';
	import FeatureToggles from './components/FeatureToggles.svelte';
	import VoiceInput from './components/VoiceInput.svelte';
	import InputMenu from './InputMenu.svelte';
	import Commands from './Commands.svelte';
	import InputVariablesModal from './InputVariablesModal.svelte';
	import ToolServersModal from '../ToolServersModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	
	// Import stores and utilities
	import {
		inputText,
		inputFiles,
		inputVariables,
		selectedVariableValues,
		showCommands,
		showToolServers,
		showInputVariables,
		isRecording,
		isDragging,
		isProcessing,
		activeFeatures,
		messageInputStore
	} from './stores/messageInputStore';
	
	import type { FileItem, MessageInputProps, MessageInputCallbacks } from './types';
	
	// Props
	export let transparentBackground = false;
	export let placeholder = '';
	export let prompt = '';
	export let files: FileItem[] = [];
	export let selectedModels: string[] = [''];
	export let atSelectedModel = undefined;
	export let selectedToolIds: string[] = [];
	export let selectedFilterIds: string[] = [];
	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;
	export let codeInterpreterEnabled = false;
	export let autoScroll = false;
	export let history: any = {};
	export let taskIds: string[] | null = null;
	export let toolServers: any[] = [];
	
	// Callbacks
	export let onChange: (text: string) => void = () => {};
	export let createMessagePair: MessageInputCallbacks['createMessagePair'];
	export let stopResponse: MessageInputCallbacks['stopResponse'];
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	let textInputComponent: TextInput;
	let fileUploadArea: FileUploadArea;
	
	// Sync props with stores
	$: messageInputStore.setText(prompt);
	$: inputFiles.set(files);
	$: messageInputStore.selectedModels.set(selectedModels);
	$: messageInputStore.atSelectedModel.set(atSelectedModel);
	$: messageInputStore.selectedToolIds.set(selectedToolIds);
	$: messageInputStore.selectedFilterIds.set(selectedFilterIds);
	$: messageInputStore.imageGenerationEnabled.set(imageGenerationEnabled);
	$: messageInputStore.webSearchEnabled.set(webSearchEnabled);
	$: messageInputStore.codeInterpreterEnabled.set(codeInterpreterEnabled);
	
	// Sync stores with props (two-way binding)
	$: prompt = $inputText;
	$: files = $inputFiles;
	$: selectedToolIds = get(messageInputStore.selectedToolIds);
	$: selectedFilterIds = get(messageInputStore.selectedFilterIds);
	$: imageGenerationEnabled = get(messageInputStore.imageGenerationEnabled);
	$: webSearchEnabled = get(messageInputStore.webSearchEnabled);
	$: codeInterpreterEnabled = get(messageInputStore.codeInterpreterEnabled);
	
	// Computed
	$: sttEnabled = $settings?.voice?.stt?.enabled ?? $config?.audio?.stt?.enabled ?? false;
	
	// Handle text input changes
	function handleTextInput(event: CustomEvent) {
		const text = event.detail;
		messageInputStore.setText(text);
		onChange(text);
	}
	
	// Handle submit
	async function handleSubmit(event?: CustomEvent) {
		const text = event?.detail || $inputText;
		if (!text.trim() && $inputFiles.length === 0) return;
		
		// Process variables
		const processedText = text.replace(/\{\{(\w+)\}\}/g, (match, variable) => {
			return $selectedVariableValues[variable] || match;
		});
		
		// Call the submit handler
		const submitFn = get(messageInputStore.submitPrompt);
		if (submitFn) {
			await submitFn(processedText, {
				files: $inputFiles,
				selectedToolIds: $selectedToolIds,
				selectedFilterIds: $selectedFilterIds,
				imageGenerationEnabled: $imageGenerationEnabled,
				webSearchEnabled: $webSearchEnabled,
				codeInterpreterEnabled: $codeInterpreterEnabled
			});
		}
		
		// Reset input
		messageInputStore.reset();
	}
	
	// Handle file operations
	function handleFileAdd(event: CustomEvent) {
		messageInputStore.addFile(event.detail);
	}
	
	function handleFileRemove(event: CustomEvent) {
		messageInputStore.removeFile(event.detail);
	}
	
	// Handle feature toggles
	function handleFeatureToggle(event: CustomEvent) {
		const { feature, enabled } = event.detail;
		
		switch (feature) {
			case 'webSearch':
				messageInputStore.webSearchEnabled.set(enabled);
				break;
			case 'imageGeneration':
				messageInputStore.imageGenerationEnabled.set(enabled);
				break;
			case 'codeInterpreter':
				messageInputStore.codeInterpreterEnabled.set(enabled);
				break;
		}
	}
	
	// Handle model change
	function handleModelChange(event: CustomEvent) {
		const { models, atModel } = event.detail;
		selectedModels = models;
		atSelectedModel = atModel;
	}
	
	// Handle voice recording
	function handleRecordingComplete(event: CustomEvent) {
		const { blob, duration } = event.detail;
		// TODO: Process voice recording
		console.log('Recording complete:', { blob, duration });
	}
	
	// Public methods
	export function setText(text: string) {
		textInputComponent?.setText(text);
	}
	
	export function insertText(text: string) {
		textInputComponent?.insertText(text);
	}
	
	export function focus() {
		textInputComponent?.focus();
	}
	
	// Save/restore state
	onMount(() => {
		// Load saved state if available
		if (!$temporaryChatEnabled) {
			const savedState = sessionStorage.getItem('messageInputState');
			if (savedState) {
				try {
					const state = JSON.parse(savedState);
					messageInputStore.setText(state.text || '');
					inputFiles.set(state.files || []);
					// ... restore other state
				} catch (e) {
					console.error('Failed to restore message input state:', e);
				}
			}
		}
	});
	
	onDestroy(() => {
		// Save state
		if (!$temporaryChatEnabled) {
			const state = messageInputStore.getState();
			sessionStorage.setItem('messageInputState', JSON.stringify(state));
		}
	});
</script>

<div class="w-full relative">
	{#if $showCommands}
		<Commands
			bind:show={$showCommands}
			{selectedModels}
			on:select={(e) => {
				insertText(e.detail);
				showCommands.set(false);
			}}
		/>
	{/if}
	
	{#if $showInputVariables}
		<InputVariablesModal
			bind:show={$showInputVariables}
			variables={$inputVariables}
			bind:values={$selectedVariableValues}
		/>
	{/if}
	
	{#if $showToolServers}
		<ToolServersModal
			bind:show={$showToolServers}
			{toolServers}
		/>
	{/if}
	
	<FileUploadArea
		bind:this={fileUploadArea}
		files={$inputFiles}
		isDragging={$isDragging}
		on:fileAdd={handleFileAdd}
		on:fileRemove={handleFileRemove}
	>
		<div 
			class="flex flex-col w-full {transparentBackground 
				? '' 
				: 'bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm'}"
		>
			<!-- Input area -->
			<div class="flex items-end gap-2 p-2">
				<!-- Menu button -->
				<InputMenu
					on:command={(e) => showCommands.set(!$showCommands)}
					on:googleDrive={(e) => fileUploadArea?.handleGoogleDrive()}
					on:oneDrive={(e) => fileUploadArea?.handleOneDrive()}
				/>
				
				<!-- Text input -->
				<div class="flex-1">
					<TextInput
						bind:this={textInputComponent}
						value={$inputText}
						{placeholder}
						{transparentBackground}
						{selectedModels}
						variables={$selectedVariableValues}
						on:input={handleTextInput}
						on:submit={handleSubmit}
						on:variablesFound={(e) => inputVariables.set(e.detail)}
					/>
				</div>
				
				<!-- Voice input -->
				<VoiceInput
					recording={$isRecording}
					{sttEnabled}
					on:recordingComplete={handleRecordingComplete}
				/>
				
				<!-- Submit button -->
				{#if $inputText.trim() || $inputFiles.length > 0}
					<button
						type="button"
						class="p-2 rounded-lg bg-black dark:bg-white text-white dark:text-black 
							   hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
						on:click={() => handleSubmit()}
						disabled={$isProcessing}
					>
						{#if $isProcessing}
							<div class="animate-spin w-5 h-5 border-2 border-white dark:border-black border-t-transparent rounded-full" />
						{:else}
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
							</svg>
						{/if}
					</button>
				{:else if taskIds && taskIds.length > 0}
					<button
						type="button"
						class="p-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors"
						on:click={() => stopResponse()}
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				{/if}
			</div>
			
			<!-- Bottom toolbar -->
			<div class="flex items-center justify-between px-3 pb-2">
				<div class="flex items-center gap-2">
					<!-- Model selector -->
					<ModelSelector
						{selectedModels}
						{atSelectedModel}
						on:modelChange={handleModelChange}
					/>
					
					<!-- Feature toggles -->
					<FeatureToggles
						webSearchEnabled={$webSearchEnabled}
						imageGenerationEnabled={$imageGenerationEnabled}
						codeInterpreterEnabled={$codeInterpreterEnabled}
						toolsEnabled={$activeFeatures.count > 0}
						toolsCount={$activeFeatures.tools.length + $activeFeatures.filters.length}
						on:toggle={handleFeatureToggle}
						on:openTools={() => showToolServers.set(true)}
					/>
				</div>
				
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{#if $activeFeatures.count > 0}
						{$activeFeatures.count} {$i18n.t('features active')}
					{/if}
				</div>
			</div>
		</div>
	</FileUploadArea>
</div>