export type OllamaModel = {
	id: string;
	name: string;
	model: string;
};

export type LiteLLMModel = {
	id: string;
	name: string;
	external: boolean;
	source: string;
};

export type OpenAIModel = {
	id: string;
	name: string;
	external: boolean;
};

export type Model = OllamaModel | LiteLLMModel | OpenAIModel;
