import type { OutputItem } from './structuredOutput';

// Terminal agents (Claude Code, Codex, ACP, Pi) keep each tool's own event in `provider_data`.
export type AgentView =
	| { kind: 'command'; command: string; output: string; exitCode?: number | null }
	| { kind: 'edit'; files: { path: string; diff: string }[] };

const lines = (text = '') => (text ? text.replace(/\n$/, '').split('\n') : []);

// Line diff of two snippets, so unchanged lines show as context instead of removed and re-added.
const lineDiff = (before: string[], after: string[]): string[] => {
	if (before.length * after.length > 250_000) {
		return [...before.map((line) => `-${line}`), ...after.map((line) => `+${line}`)];
	}
	const common = before.map(() => new Uint32Array(after.length + 1));
	common.push(new Uint32Array(after.length + 1));
	for (let i = before.length - 1; i >= 0; i--) {
		for (let j = after.length - 1; j >= 0; j--) {
			common[i][j] =
				before[i] === after[j]
					? common[i + 1][j + 1] + 1
					: Math.max(common[i + 1][j], common[i][j + 1]);
		}
	}
	const out: string[] = [];
	let i = 0;
	let j = 0;
	while (i < before.length && j < after.length) {
		if (before[i] === after[j]) {
			out.push(` ${before[i]}`);
			i++;
			j++;
		} else if (common[i + 1][j] >= common[i][j + 1]) out.push(`-${before[i++]}`);
		else out.push(`+${after[j++]}`);
	}
	while (i < before.length) out.push(`-${before[i++]}`);
	while (j < after.length) out.push(`+${after[j++]}`);
	return out;
};

const header = (path: string) => [`--- a/${path}`, `+++ b/${path}`];

// A hunk header gives the diff its line numbers; without a known start line there is none.
const patch = (path: string, oldText = '', newText = '', start?: number) => {
	const before = lines(oldText);
	const after = lines(newText);
	const at = start ?? (before.length ? undefined : 1);
	return [
		...header(path),
		...(at !== undefined
			? [
					`@@ -${before.length ? at : 0},${before.length} +${after.length ? at : 0},${after.length} @@`
				]
			: []),
		...lineDiff(before, after)
	].join('\n');
};

const isPatch = (text: string) => /^(diff |--- |@@ )/m.test(text);

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

// Provider events are untyped JSON; read them through these.
type Data = Record<string, unknown>;
const obj = (value: unknown): Data =>
	value && typeof value === 'object' && !Array.isArray(value) ? (value as Data) : {};
const list = (value: unknown): Data[] => (Array.isArray(value) ? value.map(obj) : []);
const str = (value: unknown) => (value == null ? '' : String(value));
const exitCode = (value: unknown) => (typeof value === 'number' ? value : null);

// Claude Code's structuredPatch: hunks with their real start lines.
const structuredPatch = (path: string, hunks: Data[]) =>
	[
		...header(path),
		...hunks.flatMap((hunk) => [
			`@@ -${str(hunk.oldStart)},${str(hunk.oldLines)} +${str(hunk.newStart)},${str(hunk.newLines)} @@`,
			...(Array.isArray(hunk.lines) ? hunk.lines.map(str) : [])
		])
	].join('\n');

const codexFile = (change: Data) => {
	const path = str(change.path);
	const diff = str(change.diff);
	if (isPatch(diff)) return { path, diff };
	return {
		path,
		diff: obj(change.kind).type === 'delete' ? patch(path, diff, '', 1) : patch(path, '', diff, 1)
	};
};

const editFile = (path: string, edits: Data[]) => ({
	path,
	diff: edits
		.map((edit) =>
			patch(path, str(edit.old_string ?? edit.oldText), str(edit.new_string ?? edit.newText))
		)
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

	// ACP tool calls
	const diffs = list(data.content).filter((part) => part.type === 'diff');
	if (diffs.length) {
		return {
			kind: 'edit',
			files: diffs.map((part) => ({
				path: str(part.path),
				diff: patch(str(part.path), str(part.oldText), str(part.newText))
			}))
		};
	}
	if (data.kind === 'execute') {
		return {
			kind: 'command',
			command: str(args.command ?? data.title),
			output: plain(data.rawOutput ?? result)
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
		? { path, diff: structuredPatch(path, hunks) }
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
				files: [finished ?? { path, diff: patch(path, '', str(args.content)) }]
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
