import { structuredPatch as diffTexts } from 'diff';

import type { OutputItem } from './structuredOutput';

// Terminal agents (Claude Code, Codex, ACP, Pi) keep each tool's own event in `provider_data`.
export type AgentView =
	| { kind: 'command'; command: string; output: string; exitCode?: number | null }
	| { kind: 'edit'; files: { path: string; diff: string }[] };

// Provider events are untyped JSON; read them through these.
type Data = Record<string, unknown>;
const obj = (value: unknown): Data =>
	value && typeof value === 'object' && !Array.isArray(value) ? (value as Data) : {};
const list = (value: unknown): Data[] => (Array.isArray(value) ? value.map(obj) : []);
const str = (value: unknown) => (value == null ? '' : String(value));
const exitCode = (value: unknown) => (typeof value === 'number' ? value : null);

// Bounds the diff work on large files; past it the edit shows without a preview, like T3.
const MAX_EDIT_LENGTH = 2000;

const header = (path: string) => [`--- a/${path}`, `+++ b/${path}`];

// `@@ -a,b +c,d @@` headers give a diff its line numbers. Unnumbered hunks keep a bare `@@`
// between them so separate changes still read as separate.
const formatHunks = (path: string, hunks: Data[], numbered = true) =>
	[
		...header(path),
		...hunks.flatMap((hunk, index) => [
			...(numbered
				? [
						`@@ -${str(hunk.oldStart)},${str(hunk.oldLines)} +${str(hunk.newStart)},${str(hunk.newLines)} @@`
					]
				: index
					? ['@@']
					: []),
			...(Array.isArray(hunk.lines)
				? hunk.lines.map(str).filter((line) => !line.startsWith('\\'))
				: [])
		])
	].join('\n');

// Diffs two texts into hunks with 3 lines of context. Whole files are numbered from line 1;
// a snippet whose place in the file is unknown is shown without numbers.
const patch = (path: string, oldText: string, newText: string, numbered: boolean) => {
	const result = diffTexts(path, path, oldText, newText, undefined, undefined, {
		context: 3,
		maxEditLength: MAX_EDIT_LENGTH
	});
	return result ? formatHunks(path, list(result.hunks), numbered) : '';
};

const isPatch = (text: string) => /^(diff |--- |@@ )/m.test(text);

// Antigravity replaces bare snippets (one chunk, or a ReplacementChunks list), so its diffs
// have no known place in the file. Its StartLine only starts a search range, not the edit.
const isSnippetEdit = (rawInput: Data) =>
	['TargetContent', 'target_content', 'ReplacementChunks', 'replacement_chunks'].some(
		(key) => key in rawInput
	);

const RESULT_KEYS = ['output', 'stdout', 'content', 'formatted_output'];

// Tool results arrive as text, content blocks or result objects, depending on the agent.
// Only those wrappers are unwrapped, so a command that prints JSON keeps its output as printed.
const plain = (value: unknown): string => {
	if (value == null) return '';
	if (typeof value === 'string') {
		if (!/^\s*[[{"]/.test(value)) return value;
		try {
			const parsed: unknown = JSON.parse(value);
			const wrapped =
				typeof parsed === 'string' ||
				(Array.isArray(parsed) &&
					parsed.every((block) => block && typeof block === 'object' && 'type' in block)) ||
				(parsed &&
					typeof parsed === 'object' &&
					!Array.isArray(parsed) &&
					RESULT_KEYS.some((key) => key in parsed));
			return wrapped ? plain(parsed) : value;
		} catch {
			return value;
		}
	}
	if (Array.isArray(value)) {
		return value
			.map((block) => {
				if (typeof block === 'string') return block;
				const part = (block ?? {}) as Record<string, unknown>;
				const content = (part.content ?? {}) as Record<string, unknown>;
				return String(part.text ?? content.text ?? '');
			})
			.join('\n');
	}
	if (typeof value === 'object') {
		const result = value as Record<string, unknown>;
		const key = RESULT_KEYS.find((name) => result[name] !== undefined);
		return key ? plain(result[key]) : JSON.stringify(value, null, 2);
	}
	return String(value);
};

const codexFile = (change: Data) => {
	const path = str(change.path);
	const diff = str(change.diff);
	if (isPatch(diff)) return { path, diff };
	return {
		path,
		diff:
			obj(change.kind).type === 'delete' ? patch(path, diff, '', true) : patch(path, '', diff, true)
	};
};

const editFile = (path: string, edits: Data[]) => ({
	path,
	diff: edits
		.map((edit) => {
			const oldText = str(edit.old_string ?? edit.oldText);
			return patch(path, oldText, str(edit.new_string ?? edit.newText), !oldText);
		})
		.filter(Boolean)
		.join('\n')
});

export function agentView(item: OutputItem, result: string): AgentView | null {
	const data = obj(item.provider_data ?? item.native);
	if (item.type !== 'function_call' || !Object.keys(data).length || item.name === 'ask_user') {
		return null;
	}
	let args: Data = {};
	try {
		args = obj(JSON.parse(str(item.arguments) || '{}'));
	} catch {
		args = {};
	}

	// Codex app-server items
	if (data.type === 'commandExecution') {
		return {
			kind: 'command',
			command: str(data.command),
			output: data.aggregatedOutput != null ? str(data.aggregatedOutput) : plain(result),
			exitCode: exitCode(data.exitCode)
		};
	}
	if (data.type === 'fileChange') {
		return { kind: 'edit', files: list(data.changes).map(codexFile) };
	}

	// ACP tool calls; permission requests carry the call in params.toolCall.
	// Like T3, oldText/newText are taken as whole files, so lines are numbered from 1,
	// except for agents known to send snippets.
	const requested = obj(obj(data.params).toolCall);
	const call = Object.keys(requested).length ? requested : data;
	const diffs = list(call.content).filter((part) => part.type === 'diff');
	if (diffs.length) {
		const snippets = isSnippetEdit(obj(call.rawInput));
		return {
			kind: 'edit',
			files: diffs.map((part) => ({
				path: str(part.path),
				diff: patch(
					str(part.path),
					str(part.oldText),
					str(part.newText),
					!snippets || part.oldText == null
				)
			}))
		};
	}
	if (call.kind === 'execute') {
		return {
			kind: 'command',
			command: str(obj(call.rawInput).command ?? args.command ?? call.title),
			output: plain(call.rawOutput ?? result)
		};
	}

	// Claude Code and Pi, read from the call's arguments: Claude's result event replaces its call.
	// Once an edit finishes, both report the real patch (Claude: structuredPatch, Pi: details.patch).
	const path = str(args.file_path ?? args.path);
	// Claude's event is its whole `user` message; its tool_use_result belongs to this file only.
	const toolUseResult = obj(data.tool_use_result);
	const hunks =
		!toolUseResult.filePath || toolUseResult.filePath === path
			? list(toolUseResult.structuredPatch)
			: [];
	const piPatch = str(obj(obj(data.result).details).patch);
	const finished = hunks.length
		? { path, diff: formatHunks(path, hunks) }
		: isPatch(piPatch)
			? { path, diff: piPatch }
			: null;
	switch (item.name) {
		case 'Bash':
		case 'bash': {
			const details = obj(data.result);
			return {
				kind: 'command',
				command: str(args.command),
				output: plain(result),
				exitCode: exitCode(obj(details.details).exit_code ?? details.exit_code)
			};
		}
		case 'Edit':
			return { kind: 'edit', files: [finished ?? editFile(path, [args])] };
		case 'MultiEdit':
		case 'edit':
			return { kind: 'edit', files: [finished ?? editFile(path, list(args.edits))] };
		case 'Write':
		case 'write':
			return {
				kind: 'edit',
				files: [finished ?? { path, diff: patch(path, '', str(args.content), true) }]
			};
	}
	return null;
}

export const agentViewName = (view: AgentView) =>
	view.kind === 'command'
		? view.command.split('\n')[0]
		: view.files.map((file) => file.path.split('/').pop() || file.path).join(', ');

export const diffStats = (diff: string) => {
	let additions = 0;
	let deletions = 0;
	for (const line of diff.split('\n')) {
		if (line.startsWith('+') && !line.startsWith('+++ ')) additions++;
		else if (line.startsWith('-') && !line.startsWith('--- ')) deletions++;
	}
	return { additions, deletions };
};
