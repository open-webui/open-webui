export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}

// This enum corresponds to the available workspace permissions from the backend.
export enum WORKSPACE_VISIBILITY_TYPES {
	MODEL = "make_models_public",
	KNOWLEDGE = "make_knowledge_public",
	PROMPT = "make_prompts_public",
	TOOL = "make_tools_public",
}