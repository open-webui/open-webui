import type { Model } from '$lib/stores';

export interface MessageInputProps {
	transparentBackground?: boolean;
	placeholder?: string;
	prompt: string;
	files: FileItem[];
	selectedModels: string[];
	atSelectedModel?: Model;
	selectedToolIds: string[];
	selectedFilterIds: string[];
	imageGenerationEnabled: boolean;
	webSearchEnabled: boolean;
	codeInterpreterEnabled: boolean;
	showCommands: boolean;
	autoScroll: boolean;
	history: any;
	taskIds: string[] | null;
	toolServers: any[];
}

export interface FileItem {
	id: string;
	name: string;
	type: string;
	size?: number;
	url?: string;
	base64?: string;
	collection_name?: string;
	file?: File;
	context?: string;
	error?: string;
	status?: 'uploading' | 'uploaded' | 'error';
	progress?: number;
}

export interface InputVariable {
	id: string;
	name: string;
	type: 'text' | 'select' | 'date' | 'number';
	label: string;
	value?: string;
	options?: string[];
	required?: boolean;
}

export interface CloudStorageFile {
	id: string;
	name: string;
	mimeType: string;
	data: ArrayBuffer | Blob;
	size: number;
}

export interface AutoCompletionOptions {
	prompt: string;
	model?: string;
	context?: string;
}

export interface VoiceRecordingState {
	recording: boolean;
	processing: boolean;
	duration: number;
	audioBlob?: Blob;
}

export interface CommandItem {
	name: string;
	value: string;
	description?: string;
	action?: () => void;
}

export interface ToolItem {
	id: string;
	name: string;
	description?: string;
	icon?: string;
	enabled: boolean;
}

export interface MessageInputCallbacks {
	onChange?: (text: string) => void;
	onSubmit: (prompt: string, options?: any) => Promise<void>;
	createMessagePair: (prompt: string, files?: FileItem[]) => Promise<any>;
	stopResponse: () => void;
}

export interface FileUploadOptions {
	fullContext?: boolean;
	compress?: boolean;
	maxSize?: number;
	acceptedTypes?: string[];
}

export interface TextProcessingOptions {
	variables?: Record<string, string>;
	extractVariables?: boolean;
	processMarkdown?: boolean;
}