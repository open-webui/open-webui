// Editor JSON can contain ProseMirror's null-prototype attributes, which fast-deep-equal
// cannot compare. Keep this scoped to JSON data, with reference checks and early exits.
export function equalEditorJSON(a: unknown, b: unknown): boolean {
	if (a === b) return true;
	if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;

	if (Array.isArray(a)) {
		if (!Array.isArray(b) || a.length !== b.length) return false;
		for (let i = 0; i < a.length; i++) {
			if (!equalEditorJSON(a[i], b[i])) return false;
		}
		return true;
	}

	if (Array.isArray(b)) return false;

	const left = a as Record<string, unknown>;
	const right = b as Record<string, unknown>;
	const keys = Object.keys(left);
	if (keys.length !== Object.keys(right).length) return false;

	for (const key of keys) {
		if (
			!Object.prototype.hasOwnProperty.call(right, key) ||
			!equalEditorJSON(left[key], right[key])
		) {
			return false;
		}
	}
	return true;
}
