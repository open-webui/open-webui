import { createStringFieldDecoder } from './arguments';
import type { OutputItem } from '$lib/components/chat/Messages/structuredOutput';

// Slice complete or still-streaming members without interpreting braces inside JSON strings.
function* callEntries(source: string): Generator<string> {
	const batch = /^\s*\{\s*"calls"\s*:\s*\[/.exec(source);
	if (!batch) {
		yield source; // Original single-call dispatcher format.
		return;
	}
	let start = -1,
		depth = 0,
		quoted = false;
	for (let index = batch[0].length; index < source.length; index++) {
		const char = source[index];
		if (quoted) {
			if (char === '\\') index++;
			else if (char === '"') quoted = false;
			continue;
		}
		if (char === '"') quoted = true;
		else if (char === '{') {
			if (depth++ === 0) start = index;
		} else if (char === '}') {
			if (--depth === 0) {
				yield source.slice(start, index + 1);
				start = -1;
			}
			if (depth < 0) return;
		} else if (depth === 0 && !/[\s,]/.test(char)) return;
	}
	if (start !== -1) yield source.slice(start);
}

export function getDispatchedVisualizationPreviews(item: OutputItem): OutputItem[] {
	const callId = item.call_id ?? item.id;
	if (
		item.type !== 'function_call' ||
		item.tool_type !== 'builtin' ||
		item.tool_id !== 'builtin:call_tool' ||
		!callId ||
		!item.tool_targets
	)
		return [];
	const source =
		typeof item.arguments === 'string' ? item.arguments : JSON.stringify(item.arguments ?? {});
	const previews: OutputItem[] = [];
	let index = 0;
	for (const entry of callEntries(source)) {
		const { values, malformed } = createStringFieldDecoder(
			['tool_name', 'params'],
			['params']
		).update(entry);
		const id = index === 0 ? callId : `${callId}:${index}`;
		index++;
		const target = item.tool_targets[values.tool_name];
		if (
			malformed ||
			target?.tool_type !== 'builtin' ||
			target.tool_id !== 'builtin:render_visualization' ||
			typeof values.params !== 'string'
		)
			continue;
		previews.push({
			type: 'function_call',
			id,
			call_id: id,
			name: values.tool_name,
			...target,
			arguments: values.params,
			status: item.status === 'completed' ? 'in_progress' : item.status
		});
	}
	return previews;
}
