import { get, writable } from 'svelte/store';

import i18n from '$lib/i18n';
import { generateToolCallSummary } from '$lib/apis';
import { config, models } from '$lib/stores';

export type ToolCallInfo = { id: string; name: string; arguments: string; error: boolean };

const CALLS_PER_REQUEST = 5;
const MAX_CONCURRENT_REQUESTS = 2;

// Fresh labels by tool call id; the chat copies them onto the saved message
export const toolCallSummaries = writable<Record<string, string>>({});

const requested = new Set<string>();
const waiting: (() => Promise<void>)[] = [];
let running = 0;

const runNext = async () => {
	if (running >= MAX_CONCURRENT_REQUESTS) return;
	const task = waiting.shift();
	if (!task) return;

	running += 1;
	try {
		await task();
	} finally {
		running -= 1;
		runNext();
	}
};

const languageName = () =>
	new Intl.DisplayNames(['en'], { type: 'language' }).of(i18n.language || 'en') ?? i18n.language;

const fetchSummaries = async (calls: ToolCallInfo[], modelId: string, chatId: string) => {
	const steps = await generateToolCallSummary(
		localStorage.token,
		modelId,
		calls.map(({ name, arguments: args, error }) => ({ name, arguments: args, error })),
		languageName(),
		chatId || undefined
	);
	if (steps?.length !== calls.length) return;

	const fresh: Record<string, string> = {};
	calls.forEach((call, index) => {
		if (steps[index]) fresh[call.id] = steps[index];
	});
	toolCallSummaries.update((summaries) => ({ ...summaries, ...fresh }));
};

export const requestToolCallSummaries = (
	calls: ToolCallInfo[],
	modelId: string,
	chatId: string
) => {
	if (!get(config)?.features?.enable_tool_call_summary_generation || !localStorage.token) return;

	const resolvedModelId = modelId || get(models)[0]?.id;
	if (!resolvedModelId) return;

	const missing = calls.filter((call) => call.id && !requested.has(call.id));
	for (let start = 0; start < missing.length; start += CALLS_PER_REQUEST) {
		const chunk = missing.slice(start, start + CALLS_PER_REQUEST);
		chunk.forEach((call) => requested.add(call.id));
		waiting.push(() => fetchSummaries(chunk, resolvedModelId, chatId));
		runNext();
	}
};
