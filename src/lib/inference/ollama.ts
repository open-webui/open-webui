/**
 * Ollama inference was removed from Open WebUI.
 * OpenDevin/OpenHands will provide the replacement engine later.
 */

const ENGINE_REMOVED_MESSAGE =
	'Le moteur d’inférence OpenWebUI a été supprimé. Le moteur OpenDevin/OpenHands sera branché ultérieurement.';

const unavailable = async (..._: unknown[]): Promise<any> => {
	throw new Error(ENGINE_REMOVED_MESSAGE);
};

export const verifyOllamaConnection = async (
	token = '',
	connection: Record<string, unknown> = {}
) => unavailable(token, connection);
export const getOllamaConfig = async (token = '') => unavailable(token);
export const updateOllamaConfig = async (token = '', config: unknown) => unavailable(token, config);
export const getOllamaUrls = async (token = '') => unavailable(token);
export const getOllamaVersion = async (token: string, urlIdx?: number) => unavailable(token, urlIdx);
export const getOllamaModels = async (token = '', urlIdx: number | null = null) =>
	unavailable(token, urlIdx);
export const generatePrompt = async (token = '', model: string, conversation: string) =>
	unavailable(token, model, conversation);
export const generateEmbeddings = async (token = '', model: string, text: string) =>
	unavailable(token, model, text);
export const generateTextCompletion = async (token = '', model: string, text: string) =>
	unavailable(token, model, text);
export const generateChatCompletion = async (token = '', body: unknown) => unavailable(token, body);
export const unloadModel = async (token: string, tagName: string) => unavailable(token, tagName);
export const createModel = async (token: string, payload: unknown, urlIdx: string | null = null) =>
	unavailable(token, payload, urlIdx);
export const deleteModel = async (token: string, tagName: string, urlIdx: string | null = null) =>
	unavailable(token, tagName, urlIdx);
export const pullModel = async (token: string, tagName: string, urlIdx: number | null = null) =>
	unavailable(token, tagName, urlIdx);
export const downloadModel = async (...args: unknown[]) => unavailable(...args);
export const uploadModel = async (token: string, file: File, urlIdx: string | null = null) =>
	unavailable(token, file, urlIdx);
