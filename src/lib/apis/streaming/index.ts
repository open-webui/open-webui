import { EventSourceParserStream } from 'eventsource-parser/stream';
import type { ParsedEvent } from 'eventsource-parser';

type TextStreamUpdate = {
	done: boolean;
	value: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	sources?: any;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	selectedModelId?: any;
	error?: any;
	usage?: ResponseUsage;
	paramFallback?: boolean;
	reasoningContent?: string;
};

type ResponseUsage = {
	/** Including images and tools if any */
	prompt_tokens: number;
	/** The tokens generated */
	completion_tokens: number;
	/** Sum of the above two fields */
	total_tokens: number;
	/** Any other fields that aren't part of the base OpenAI spec */
	[other: string]: unknown;
};

// createOpenAITextStream takes a responseBody with a SSE response,
// and returns an async generator that emits delta updates with large deltas chunked into random sized chunks
export async function createOpenAITextStream(
	responseBody: ReadableStream<Uint8Array>,
	splitLargeDeltas: boolean
): Promise<AsyncGenerator<TextStreamUpdate>> {
	const eventStream = responseBody
		.pipeThrough(new TextDecoderStream() as unknown as TransformStream<Uint8Array, string>)
		.pipeThrough(new EventSourceParserStream())
		.getReader();
	let iterator = openAIStreamToIterator(eventStream);
	if (splitLargeDeltas) {
		iterator = streamLargeDeltasAsRandomChunks(iterator);
	}
	return iterator;
}

async function* openAIStreamToIterator(
	reader: ReadableStreamDefaultReader<ParsedEvent>
): AsyncGenerator<TextStreamUpdate> {
	while (true) {
		const { value, done } = await reader.read();
		if (done) {
			yield { done: true, value: '' };
			break;
		}
		if (!value) {
			continue;
		}
		const data = value.data;
		if (data.startsWith('[DONE]')) {
			yield { done: true, value: '' };
			break;
		}

		try {
			const parsedData = JSON.parse(data);
			console.log(parsedData);

			if (parsedData.error) {
				yield { done: true, value: '', error: parsedData.error };
				break;
			}

			if (parsedData.sources) {
				yield { done: false, value: '', sources: parsedData.sources };
				continue;
			}

			if (parsedData.selected_model_id) {
				yield { done: false, value: '', selectedModelId: parsedData.selected_model_id };
				continue;
			}

			if (parsedData.usage) {
				yield { done: false, value: '', usage: parsedData.usage };
				continue;
			}

			// Handle param fallback notification (model doesn't support some parameters)
			if (parsedData.__param_fallback) {
				console.log('⚠️ Param fallback - model does not support some parameters');
				yield { done: false, value: '', paramFallback: true };
				continue;
			}

			// Handle heartbeat events (model is still thinking)
			if (parsedData.type === 'heartbeat') {
				console.log('💭 心跳信号 - 模型正在思考中...', parsedData.status);
				continue; // Skip heartbeat, just keep connection alive
			}

			// Extract content and reasoning from either streaming (delta) or non-streaming (message) format
			const choice = parsedData.choices?.[0];
			const delta = choice?.delta;
			const message = choice?.message;

			// Get content: prefer delta.content (streaming) over message.content (non-streaming)
			const content = delta?.content ?? message?.content ?? '';

			// Get reasoning content from various possible field names
			// Support: reasoning_content, reasoning, thinking, thinking_content, thought, thought_content
			const reasoningContent =
				delta?.reasoning_content ??
				delta?.reasoning ??
				delta?.thinking ??
				delta?.thinking_content ??
				delta?.thought ??
				delta?.thought_content ??
				message?.reasoning_content ??
				message?.reasoning ??
				message?.thinking ??
				message?.thinking_content ??
				message?.thought ??
				message?.thought_content ??
				'';

			yield {
				done: false,
				value: content,
				reasoningContent: reasoningContent || undefined
			};
		} catch (e) {
			console.error('Error extracting delta from SSE event:', e);
		}
	}
}

// streamLargeDeltasAsRandomChunks will chunk large deltas (length > 5) into random sized chunks between 1-3 characters
// This is to simulate a more fluid streaming, even though some providers may send large chunks of text at once
async function* streamLargeDeltasAsRandomChunks(
	iterator: AsyncGenerator<TextStreamUpdate>
): AsyncGenerator<TextStreamUpdate> {
	for await (const textStreamUpdate of iterator) {
		if (textStreamUpdate.done) {
			yield textStreamUpdate;
			return;
		}

		if (textStreamUpdate.error) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.sources) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.selectedModelId) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.usage) {
			yield textStreamUpdate;
			continue;
		}
		if (textStreamUpdate.paramFallback) {
			yield textStreamUpdate;
			continue;
		}

		// If there's reasoning content, yield it first (only on first chunk)
		const reasoningContent = textStreamUpdate.reasoningContent;

		let content = textStreamUpdate.value;
		if (content.length < 5) {
			yield { done: false, value: content, reasoningContent };
			continue;
		}
		let isFirstChunk = true;
		while (content != '') {
			const chunkSize = Math.min(Math.floor(Math.random() * 3) + 1, content.length);
			const chunk = content.slice(0, chunkSize);
			// Only include reasoningContent in the first chunk
			yield { done: false, value: chunk, reasoningContent: isFirstChunk ? reasoningContent : undefined };
			isFirstChunk = false;
			// Do not sleep if the tab is hidden
			// Timers are throttled to 1s in hidden tabs
			if (document?.visibilityState !== 'hidden') {
				await sleep(5);
			}
			content = content.slice(chunkSize);
		}
	}
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
