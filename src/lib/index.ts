// place files you want to import through the `$lib` alias in this folder.
import { getOpenAIConfig, updateOpenAIConfig } from '$lib/apis/openai';

export async function initFoundryConnection() {
	const res = await fetch('/port.txt');
	if (!res.ok) return;
	const port = (await res.text()).trim();
	const foundryURL = `http://localhost:${port}/v1`;

	const openaiConfig = await getOpenAIConfig(localStorage.token);
	if (!openaiConfig.OPENAI_API_BASE_URLS.includes(foundryURL)) {
		await updateOpenAIConfig(localStorage.token, {
			ENABLE_OPENAI_API: true,
			OPENAI_API_BASE_URLS: [...openaiConfig.OPENAI_API_BASE_URLS, foundryURL],
			OPENAI_API_KEYS: [...openaiConfig.OPENAI_API_KEYS, ''],
			OPENAI_API_CONFIGS: openaiConfig.OPENAI_API_CONFIGS
		});
		console.log(`✅ Foundry connection added automatically: ${foundryURL}`);
	}
}