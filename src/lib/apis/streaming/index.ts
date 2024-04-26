type TextStreamUpdate = {
	done: boolean;
	value: string;
};

// createOpenAITextStream takes a ReadableStreamDefaultReader from an SSE response,
// and returns an async generator that emits delta updates with large deltas chunked into random sized chunks
export async function createOpenAITextStream(
	messageStream: ReadableStreamDefaultReader,
	splitLargeDeltas: boolean
): Promise<AsyncGenerator<TextStreamUpdate>> {
	let iterator = openAIStreamToIterator(messageStream);
	if (splitLargeDeltas) {
		iterator = streamLargeDeltasAsRandomChunks(iterator);
	}
	return iterator;
}

async function* openAIStreamToIterator(
	reader: ReadableStreamDefaultReader
): AsyncGenerator<TextStreamUpdate> {
	while (true) {
		const { value, done } = await reader.read();
		if (done) {
			yield { done: true, value: '' };
			break;
		}
		const lines = value.split('\n');
		for (const line of lines) {
			if (line !== '') {
				console.log(line);
				if (line === 'data: [DONE]') {
					yield { done: true, value: '' };
				} else if (line.startsWith(':')) {
					// Events starting with : are comments https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format
					// OpenRouter sends heartbeats like ": OPENROUTER PROCESSING"
					continue;
				} else {
					try {
						const data = JSON.parse(line.replace(/^data: /, ''));
						console.log(data);

						yield { done: false, value: data.choices?.[0]?.delta?.content ?? '' };
					} catch (e) {
						console.error('Error extracting delta from SSE event:', e);
					}
				}
			}
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
		let content = textStreamUpdate.value;
		if (content.length < 5) {
			yield { done: false, value: content };
			continue;
		}
		while (content != '') {
			const chunkSize = Math.min(Math.floor(Math.random() * 3) + 1, content.length);
			const chunk = content.slice(0, chunkSize);
			yield { done: false, value: chunk };
			await sleep(5);
			content = content.slice(chunkSize);
		}
	}
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
