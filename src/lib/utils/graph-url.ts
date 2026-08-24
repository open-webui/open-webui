/**
 * Pulls the URL string out of a `get_record_graph_url` tool result, and
 * matches the tool by name.
 *
 * Ported from `ichirouganaim_frontend`'s `lib/graph-url.ts` (the reference
 * repo's own `extractGraphUrl`, built up over three real, live-verified
 * shape bugs across different providers -- see that file's docstring and
 * this project's decisions.md). Only the shapes relevant to this Pipe are
 * kept as primary; the others are cheap defensive fallbacks in case
 * `claude_cli.py`'s own emission ever changes shape.
 *
 * **Live-verified for this fork specifically** (decisions.md, 2026-08-22):
 * `claude_cli.py`'s `_append_tool_result` stores the `tool_result` block's
 * `content` field verbatim into `function_call_output.output[0].text` --
 * for a real `get_record_graph_url` call that's the string
 * `'{"result":"http://127.0.0.1:1246/records/<id>/graph-view/"}'`. That's
 * also exactly what the reference repo's own docstring documents for the
 * `claude-cli` provider (its Phase 7 finding), so the `result.result`
 * branch below is the one that actually fires for this integration; the
 * `structuredContent`/`content[]` branches are unreachable *today* because
 * `claude_cli.py` never forwards that richer envelope, kept only in case
 * that changes.
 */

// claude_cli.py's MCP_SERVER_KEY constant names every tool
// `mcp__<that key>__<tool>` (currently `mcp__ichirouganaim_mcp__<tool>`) --
// the CLI's own namespacing convention, not this fork's native
// middleware.py one (which uses a different, single-underscore scheme and
// isn't reachable via this Pipe at all). Matched here on a `__`-prefixed
// suffix rather than the full name, so a rename of that key on the Python
// side (like `mcp` -> `ichirouganaim_mcp`, decisions.md 2026-08-22) doesn't
// need a matching change here.
const BARE_NAME = 'get_record_graph_url';

export function isGraphUrlTool(toolName: string): boolean {
	return toolName === BARE_NAME || toolName.endsWith(`__${BARE_NAME}`);
}

export function extractGraphUrl(output: unknown): string | null {
	if (typeof output === 'string') {
		try {
			return extractGraphUrl(JSON.parse(output));
		} catch {
			// Not JSON -- e.g. a plain error string from a failed call.
			return null;
		}
	}

	if (typeof output !== 'object' || output === null) return null;
	const result = output as Record<string, unknown>;

	const structured = result.structuredContent;
	if (
		typeof structured === 'object' &&
		structured !== null &&
		typeof (structured as Record<string, unknown>).result === 'string'
	) {
		return (structured as Record<string, unknown>).result as string;
	}

	const content = result.content;
	if (Array.isArray(content)) {
		const textPart = content.find(
			(part): part is { type: 'text'; text: string } =>
				typeof part === 'object' &&
				part !== null &&
				(part as Record<string, unknown>).type === 'text' &&
				typeof (part as Record<string, unknown>).text === 'string'
		);
		if (textPart) return textPart.text;
	}

	// The claude-cli Pipe's own shape: { result: "<url>" }.
	if (typeof result.result === 'string') return result.result;

	return null;
}
