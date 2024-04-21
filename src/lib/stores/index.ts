import { APP_NAME } from '$lib/constants';
import { type Writable, writable } from 'svelte/store';

// Backend
export const WEBUI_NAME = writable(APP_NAME);
export const config = writable(undefined);
export const user = writable(undefined);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable({});

export const theme = writable('system');
export const chatId = writable('');

export const chats = writable([]);
export const tags = writable([]);
export const models: Writable<Model[]> = writable([]);

export const modelfiles = writable([]);
export const prompts = writable([]);
export const documents = writable([
	{
		collection_name: 'collection_name',
		filename: 'filename',
		name: 'name',
		title: 'title'
	},
	{
		collection_name: 'collection_name1',
		filename: 'filename1',
		name: 'name1',
		title: 'title1'
	}
]);

export const settings = writable({});
export const showSettings = writable(false);
export const showChangelog = writable(false);

type Model = OpenAIModel | OllamaModel;

type OpenAIModel = {
	id: string;
	name: string;
	external: boolean;
	source?: string;
}

type OllamaModel = {
	id: string;
	name: string;

	// Ollama specific fields
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
}

type OllamaModelDetails = {
  parent_model: string;
  format: string;
  family: string;
  families: string[] | null;
  parameter_size: string;
  quantization_level: string;
};
