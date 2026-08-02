/**
 * Iteratively unwrap nested JSON-encoded strings.
 *
 * The naive recursive form (`return parse(JSON.parse(str))`) recurses forever
 * on scalar values such as `JSON.parse('5') -> 5`, because `JSON.parse(5)` is
 * `JSON.parse('5')` again. Unwrapping in a `while` loop avoids that
 * stack-overflow-and-recover path.
 */
export function parseToolResult(value: string | unknown): unknown {
	let current: unknown = value;
	while (typeof current === 'string') {
		try {
			current = JSON.parse(current);
		} catch {
			break;
		}
	}
	return current;
}

/**
 * A tool call result is considered an error when the (possibly JSON-encoded)
 * payload is an object that carries a non-empty `error` string — the shape the
 * Open WebUI backend uses for tool failures such as
 * `{"error": "403 Client Error: Forbidden for url: ..."}`.
 *
 * Empty/null/non-string `error` fields are ignored so that normal results that
 * happen to include an `error: null` or `error: 0` field are not misreported.
 */
export function isToolResultError(value: string | unknown): boolean {
	const parsed = parseToolResult(value);
	if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
		return false;
	}
	const error = (parsed as Record<string, unknown>).error;
	return typeof error === 'string' && error.trim().length > 0;
}
