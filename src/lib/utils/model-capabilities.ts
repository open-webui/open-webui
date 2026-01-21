/**
 * 模型能力推断工具
 * 根据模型名称自动推断其支持的能力
 */

export interface ModelCapabilities {
	vision: boolean;      // 视觉/图像理解
	reasoning: boolean;   // 推理/思考链
	tools: boolean;       // 工具调用/函数调用
	webSearch: boolean;   // 联网搜索
	free: boolean;        // 免费模型
	imageGen: boolean;    // 图像生成
	embedding: boolean;   // 嵌入模型
	rerank: boolean;      // 重排模型
}

/**
 * 根据模型ID推断其能力
 */
export function inferModelCapabilities(modelId: string): ModelCapabilities {
	const id = modelId.toLowerCase();

	return {
		vision: inferVision(id),
		reasoning: inferReasoning(id),
		tools: inferTools(id),
		webSearch: inferWebSearch(id),
		free: inferFree(id),
		imageGen: inferImageGen(id),
		embedding: inferEmbedding(id),
		rerank: inferRerank(id)
	};
}

// 视觉能力推断
function inferVision(id: string): boolean {
	// 明确不支持视觉的模型（优先排除）
	const noVisionPatterns = [
		'gpt-3.5',
		'gpt-4-0314',
		'gpt-4-0613',
		'text-',
		'davinci',
		'curie',
		'babbage',
		'ada'
	];

	if (noVisionPatterns.some(p => id.includes(p))) {
		return false;
	}

	// 正则匹配：以 v 结尾（如 glm-4.6v, glm-4v, yi-1.5v）
	if (/[\d.]v$/.test(id) || /[\d.]v[(-]/.test(id)) {
		return true;
	}

	// 正则匹配：包含 vl（如 qwen3-vl-xxx, llava, cogvlm, internvl）
	if (/vl/.test(id)) {
		return true;
	}

	// 明确支持视觉的模型
	const visionPatterns = [
		'vision',
		'4o',           // gpt-4o 系列
		'gpt-4-turbo',
		'gpt-4-1',      // gpt-4.1
		'gpt-5',
		'claude-3',     // claude-3 全系列支持视觉
		'claude-4',
		'gemini',       // gemini 全系列
		'minicpm-v',
		'yi-vision',
		'pixtral'
	];

	return visionPatterns.some(p => id.includes(p));
}

// 推理/思考能力推断
function inferReasoning(id: string): boolean {
	const reasoningPatterns = [
		'o1',           // OpenAI o1 系列
		'o3',           // OpenAI o3 系列
		'o4',           // OpenAI o4 系列
		'deepseek-r1',  // DeepSeek R1
		'deepseek-reasoner',
		'thinking',     // 带 thinking 的模型
		'reasoner',
		'qwq',          // Qwen QwQ
		'marco-o1',
		'skywork-o1'
	];

	return reasoningPatterns.some(p => id.includes(p));
}

// 工具调用能力推断
function inferTools(id: string): boolean {
	// 大多数现代模型都支持工具调用
	const toolsPatterns = [
		'gpt-4',
		'gpt-3.5-turbo',
		'gpt-5',
		'claude-3',
		'claude-4',
		'gemini',
		'glm-4',
		'qwen',
		'deepseek',
		'mistral',
		'mixtral',
		'llama-3',
		'llama3',
		'yi-',
		'command-r'
	];

	// 明确不支持工具的模型
	const noToolsPatterns = [
		'o1-preview',   // o1 系列暂不支持工具
		'o1-mini',
		'deepseek-r1',  // R1 推理模型不支持工具
		'text-',
		'instruct',
		'davinci',
		'curie',
		'babbage',
		'ada',
		'base'
	];

	if (noToolsPatterns.some(p => id.includes(p))) {
		return false;
	}

	return toolsPatterns.some(p => id.includes(p));
}

// 联网搜索能力推断 - 大多数现代聊天模型都可以配合联网搜索
function inferWebSearch(id: string): boolean {
	// 排除嵌入和重排模型
	if (inferEmbedding(id) || inferRerank(id)) {
		return false;
	}
	return true;
}

// 免费模型推断
function inferFree(id: string): boolean {
	return id.includes('free');
}

// 图像生成模型推断
function inferImageGen(id: string): boolean {
	const imageGenPatterns = [
		'dall-e',
		'dalle',
		'stable-diffusion',
		'sd-',
		'sdxl',
		'flux',
		'midjourney',
		'imagen',
		'cogview',
		'wanx',        // 通义万相
		'kolors',
		'playground',
		'ideogram',
		'recraft'
	];
	// 匹配包含 image 但排除 vision/理解类
	if (id.includes('image') && !id.includes('vision')) {
		return true;
	}
	return imageGenPatterns.some(p => id.includes(p));
}

// 嵌入模型推断
function inferEmbedding(id: string): boolean {
	const embeddingPatterns = [
		'embed',
		'embedding',
		'text-embedding',
		'bge-',
		'e5-',
		'gte-',
		'jina-embed',
		'nomic-embed',
		'mxbai-embed'
	];
	return embeddingPatterns.some(p => id.includes(p));
}

// 重排模型推断
function inferRerank(id: string): boolean {
	const rerankPatterns = [
		'rerank',
		'reranker',
		'bge-reranker',
		'jina-reranker'
	];
	return rerankPatterns.some(p => id.includes(p));
}

/**
 * 获取能力的显示信息
 */
export const capabilityInfo = {
	vision: {
		label: 'Vision',
		labelZh: '视觉'
	},
	reasoning: {
		label: 'Reasoning',
		labelZh: '推理'
	},
	tools: {
		label: 'Tools',
		labelZh: '工具'
	},
	webSearch: {
		label: 'Web Search',
		labelZh: '联网'
	},
	free: {
		label: 'Free',
		labelZh: '免费'
	},
	imageGen: {
		label: 'Image Generation',
		labelZh: '生图'
	},
	embedding: {
		label: 'Embedding',
		labelZh: '嵌入'
	},
	rerank: {
		label: 'Rerank',
		labelZh: '重排'
	}
} as const;

/**
 * 根据模型ID推断其所属分组（按品牌/厂商）
 */
export function getModelGroup(modelId: string): string {
	let id = modelId.toLowerCase();

	// 处理 provider/model 格式
	if (id.includes('/')) {
		id = id.split('/').pop() || id;
	}

	// 按品牌分组
	if (/^(gpt|o1|o3|o4|dall-?e|chatgpt)/.test(id)) return 'OpenAI';
	if (/^(gemini|palm|bard)/.test(id)) return 'Google';
	if (/^claude/.test(id)) return 'Anthropic';
	if (/^(qwen|qwq)/.test(id)) return 'Qwen';
	if (/^deepseek/.test(id)) return 'DeepSeek';
	if (/^(glm|chatglm)/.test(id)) return 'GLM';
	if (/^(llama|codellama)/.test(id)) return 'Llama';
	if (/^(mistral|mixtral|codestral)/.test(id)) return 'Mistral';
	if (/^yi-/.test(id)) return 'Yi';
	if (/^(kimi|moonshot)/.test(id)) return 'Kimi';
	if (/^(hunyuan|混元)/.test(id)) return 'Hunyuan';
	if (/^(ernie|文心)/.test(id)) return 'ERNIE';
	if (/^(spark|星火)/.test(id)) return 'Spark';
	if (/^doubao/.test(id)) return 'Doubao';
	if (/^(flux|sd|stable|sdxl)/.test(id)) return 'StableDiffusion';
	if (/^(midjourney|mj)/.test(id)) return 'Midjourney';
	if (/^ideogram/.test(id)) return 'Ideogram';
	if (/^(embed|bge-|e5-|gte-)/.test(id)) return 'Embedding';
	if (/^rerank/.test(id)) return 'Rerank';

	// 默认取第一个 - 之前的部分，首字母大写
	const name = id.split('-')[0];
	return name.charAt(0).toUpperCase() + name.slice(1);
}
