import { writable, derived, get } from 'svelte/store';
import type { FileItem, InputVariable, VoiceRecordingState } from '../types';
import type { Model } from '$lib/stores';

// Core input state
export const inputText = writable('');
export const inputFiles = writable<FileItem[]>([]);
export const inputVariables = writable<InputVariable[]>([]);
export const selectedVariableValues = writable<Record<string, string>>({});

// Model selection
export const selectedModels = writable<string[]>(['']);
export const atSelectedModel = writable<Model | undefined>(undefined);

// Feature toggles
export const selectedToolIds = writable<string[]>([]);
export const selectedFilterIds = writable<string[]>([]);
export const imageGenerationEnabled = writable(false);
export const webSearchEnabled = writable(false);
export const codeInterpreterEnabled = writable(false);

// UI state
export const showCommands = writable(false);
export const showToolServers = writable(false);
export const showInputVariables = writable(false);
export const isRecording = writable(false);
export const isDragging = writable(false);
export const isProcessing = writable(false);

// Voice recording state
export const voiceRecordingState = writable<VoiceRecordingState>({
	recording: false,
	processing: false,
	duration: 0
});

// Auto-completion
export const autoCompletionEnabled = writable(false);
export const autoCompletionContext = writable('');

// Derived stores
export const hasContent = derived(
	[inputText, inputFiles],
	([$text, $files]) => $text.trim().length > 0 || $files.length > 0
);

export const selectedModelIds = derived(
	[atSelectedModel, selectedModels],
	([$atSelectedModel, $selectedModels]) => 
		$atSelectedModel ? [$atSelectedModel.id] : $selectedModels
);

export const activeFeatures = derived(
	[selectedToolIds, selectedFilterIds, imageGenerationEnabled, webSearchEnabled, codeInterpreterEnabled],
	([$tools, $filters, $image, $web, $code]) => ({
		tools: $tools,
		filters: $filters,
		imageGeneration: $image,
		webSearch: $web,
		codeInterpreter: $code,
		count: $tools.length + $filters.length + ($image ? 1 : 0) + ($web ? 1 : 0) + ($code ? 1 : 0)
	})
);

// Store actions
export const messageInputStore = {
	// Reset all input state
	reset() {
		inputText.set('');
		inputFiles.set([]);
		inputVariables.set([]);
		selectedVariableValues.set({});
		selectedToolIds.set([]);
		selectedFilterIds.set([]);
		imageGenerationEnabled.set(false);
		webSearchEnabled.set(false);
		codeInterpreterEnabled.set(false);
		showCommands.set(false);
		showToolServers.set(false);
		showInputVariables.set(false);
	},
	
	// Add a file
	addFile(file: FileItem) {
		inputFiles.update(files => [...files, file]);
	},
	
	// Remove a file
	removeFile(fileId: string) {
		inputFiles.update(files => files.filter(f => f.id !== fileId));
	},
	
	// Update file status
	updateFileStatus(fileId: string, updates: Partial<FileItem>) {
		inputFiles.update(files => 
			files.map(f => f.id === fileId ? { ...f, ...updates } : f)
		);
	},
	
	// Set input text
	setText(text: string) {
		inputText.set(text);
	},
	
	// Append to input text
	appendText(text: string) {
		inputText.update(current => current + text);
	},
	
	// Toggle tool
	toggleTool(toolId: string) {
		selectedToolIds.update(ids => {
			const index = ids.indexOf(toolId);
			if (index >= 0) {
				return ids.filter(id => id !== toolId);
			} else {
				return [...ids, toolId];
			}
		});
	},
	
	// Toggle filter
	toggleFilter(filterId: string) {
		selectedFilterIds.update(ids => {
			const index = ids.indexOf(filterId);
			if (index >= 0) {
				return ids.filter(id => id !== filterId);
			} else {
				return [...ids, filterId];
			}
		});
	},
	
	// Set variable value
	setVariableValue(variableName: string, value: string) {
		selectedVariableValues.update(values => ({
			...values,
			[variableName]: value
		}));
	},
	
	// Get current state
	getState() {
		return {
			text: get(inputText),
			files: get(inputFiles),
			models: get(selectedModels),
			atModel: get(atSelectedModel),
			tools: get(selectedToolIds),
			filters: get(selectedFilterIds),
			imageGeneration: get(imageGenerationEnabled),
			webSearch: get(webSearchEnabled),
			codeInterpreter: get(codeInterpreterEnabled),
			variables: get(selectedVariableValues)
		};
	}
};