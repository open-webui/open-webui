/**
 * OpenAI-compatible inference was removed from Open WebUI.
 * OpenDevin/OpenHands will provide the replacement engine later.
 */

const ENGINE_REMOVED_MESSAGE =
	'Le moteur d’inférence OpenWebUI a été supprimé. Le moteur OpenDevin/OpenHands sera branché ultérieurement.';

const unavailable = async (..._: unknown[]): Promise<any> => {
	throw new Error(ENGINE_REMOVED_MESSAGE);
};

export const getOpenAIConfig = async (token = '') => unavailable(token);
export const updateOpenAIConfig = async (token = '', config: unknown) => unavailable(token, config);
export const getOpenAIModelsDirect = async (url: string, key: string) => unavailable(url, key);
export const getOpenAIModels = async (token: string, urlIdx?: number) => unavailable(token, urlIdx);
export const verifyOpenAIConnection = async (
	token = '',
	connection: Record<string, unknown> = {},
	direct = false
) => unavailable(token, connection, direct);
export const chatCompletion = async (token = '', body: unknown, url = '') => unavailable(token, body, url);
export const generateOpenAIChatCompletion = async (token = '', body: unknown, url = '') =>
	unavailable(token, body, url);
export const synthesizeOpenAISpeech = async (
	token = '',
	speaker = 'alloy',
	text = '',
	model = 'tts-1'
) => unavailable(token, speaker, text, model);
