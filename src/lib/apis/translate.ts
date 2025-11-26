import { WEBUI_BASE_URL } from '$lib/constants';

export interface TranslationRequest {
	content: string;
	targetLanguage: string;
	modelId?: string;
}

export interface TranslationResponse {
	translatedContent: string;
	success: boolean;
	error?: string;
}

export const translateMessage = async (
	token: string,
	request: TranslationRequest
): Promise<TranslationResponse> => {
	try {
		const response = await fetch(`${WEBUI_BASE_URL}/api/translate`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(request)
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ error: 'Translation failed' }));
			throw new Error(errorData.error || 'Translation failed');
		}

		const result = await response.json();
		return {
			translatedContent: result.translatedContent || result.content || '',
			success: true
		};
	} catch (error) {
		console.error('Translation error:', error);
		return {
			translatedContent: '',
			success: false,
			error: error.message || 'Translation failed'
		};
	}
};

export const translateMessageWithModel = async (
	token: string,
	content: string,
	targetLanguage: string,
	modelId: string
): Promise<TranslationResponse> => {
	try {
		// 构建翻译提示
		const languageNames = {
			zh: '中文',
			ja: '日语',
			ko: '韩语',
			en: '英语'
		};

		const targetLangName = languageNames[targetLanguage] || targetLanguage;
		
		const translationPrompt = `请将以下文本翻译成${targetLangName}，只返回翻译后的文本，不要添加任何解释或注释：

${content}`;

		const response = await fetch(`${WEBUI_BASE_URL}/api/chat/completions`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				model: modelId,
				messages: [
					{
						role: 'user',
						content: translationPrompt
					}
				],
				stream: false
			})
		});

		if (!response.ok) {
			throw new Error('Translation request failed');
		}

		const result = await response.json();
		const translatedContent = result.choices?.[0]?.message?.content || '';
		
		return {
			translatedContent: translatedContent.trim(),
			success: true
		};
	} catch (error) {
		console.error('Translation with model error:', error);
		return {
			translatedContent: '',
			success: false,
			error: error.message || 'Translation failed'
		};
	}
};