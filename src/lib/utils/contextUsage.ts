type ContextMessage = {
	content?: unknown;
	output?: unknown[];
	tool_calls?: unknown;
	files?: unknown[];
	usage?: Record<string, unknown>;
	info?: { usage?: Record<string, unknown> };
};

export const estimateTokens = (value: unknown): number => {
	if (value === null || value === undefined || value === '') return 0;
	if (typeof value !== 'string') {
		try {
			value = JSON.stringify(value);
		} catch {
			value = String(value);
		}
	}
	return Math.max(1, Math.floor(String(value).length / 4));
};

export const estimateMessagesTokens = (messages: ContextMessage[]): number =>
	messages.reduce((total, message) => {
		// Structured output already includes the assistant text and tool calls.
		let next = total + 4;
		next += message.output?.length
			? estimateTokens(message.output)
			: estimateTokens(message.content) + estimateTokens(message.tool_calls);
		if (message.files?.length) {
			next += estimateTokens(
				JSON.stringify(message.files).replace(/data:[\w/+.;=%-]*;base64,[A-Za-z0-9+/=]*/g, '')
			);
		}
		return next;
	}, 0);

// Usage objects survive message copies between streaming events. Weak keys let old
// checkpoints disappear when a new usage snapshot or chat replaces them.
const usageCheckpoints = new WeakMap<object, number>();

export const captureUsageCheckpoint = (message: ContextMessage): void => {
	const usage = message.usage ?? message.info?.usage;
	if (usage) usageCheckpoints.set(usage, estimateMessagesTokens([message]));
};

export const estimateUsageGrowth = (message: ContextMessage): number => {
	const usage = message.usage ?? message.info?.usage;
	if (!usage) return 0;
	const tokens = estimateMessagesTokens([message]);
	if (!usageCheckpoints.has(usage)) {
		// shortcut: loaded chats anchor here; persist checkpoints if reloads must retain in-flight estimates.
		usageCheckpoints.set(usage, tokens);
	}
	return Math.max(0, tokens - usageCheckpoints.get(usage)!);
};
