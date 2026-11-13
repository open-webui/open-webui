export const MAX_HTML_BYTES = 256 * 1024;
const MAX_ARGUMENT_CHARS = 2 * 1024 * 1024;

export type VisualizationArguments = {
	title: string;
	html: string;
	libraries?: Array<'chartjs'>;
};

export function parseVisualizationArguments(raw: unknown): VisualizationArguments | null {
	try {
		const value = typeof raw === 'string' ? JSON.parse(raw) : raw;
		if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
		const { title, html, libraries } = value;
		if (typeof title !== 'string' || !title.trim() || [...title.trim()].length > 160) return null;
		if (
			typeof html !== 'string' ||
			!html.trim() ||
			new TextEncoder().encode(html).length > MAX_HTML_BYTES
		)
			return null;
		if (
			libraries != null &&
			(!Array.isArray(libraries) || libraries.length > 1 || libraries.some((l) => l !== 'chartjs'))
		)
			return null;
		return { title, html, libraries: libraries ?? [] };
	} catch {
		return null;
	}
}

// Only root string values are exposed. Incomplete JSON is never repaired or executed.
export function createStringFieldDecoder(names: readonly string[], partialNames = names) {
	let previous = '',
		cursor = 0,
		key = '',
		value = '';
	let stack: string[] = [];
	let stage: 'key' | 'colon' | 'value' | 'comma' = 'key';
	let stringRole: 'key' | 'value' | 'skip' | null = null;
	let started = false,
		ended = false,
		malformed = false;
	let fields: Record<string, string> = {};
	let keys = new Set<string>();
	const reset = () => {
		previous = '';
		cursor = 0;
		key = '';
		value = '';
		stack = [];
		stage = 'key';
		stringRole = null;
		started = false;
		ended = false;
		malformed = false;
		fields = {};
		keys = new Set();
	};
	return {
		reset,
		update(snapshot: string) {
			if (!snapshot.startsWith(previous)) reset();
			previous = snapshot;
			if (snapshot.length > MAX_ARGUMENT_CHARS) malformed = true;
			while (cursor < snapshot.length && !malformed) {
				const c = snapshot[cursor];
				if (stringRole) {
					if (c === '"') {
						if (stringRole === 'key') {
							key = value;
							if (keys.has(key)) {
								malformed = true;
								break;
							}
							keys.add(key);
							stage = 'colon';
						} else if (stringRole === 'value') {
							if (names.includes(key)) fields[key] = value;
							stage = 'comma';
						}
						stringRole = null;
						cursor++;
						continue;
					}
					if (c.charCodeAt(0) < 32) {
						malformed = true;
						break;
					}
					let decoded = c;
					if (c === '\\') {
						if (cursor + 1 >= snapshot.length) break;
						const escape = snapshot[cursor + 1];
						if (escape === 'u') {
							if (cursor + 6 > snapshot.length) break;
							const hex = snapshot.slice(cursor + 2, cursor + 6);
							if (!/^[\da-f]{4}$/i.test(hex)) {
								malformed = true;
								break;
							}
							decoded = String.fromCharCode(parseInt(hex, 16));
							cursor += 6;
						} else {
							const escapes: Record<string, string> = {
								'"': '"',
								'\\': '\\',
								'/': '/',
								b: '\b',
								f: '\f',
								n: '\n',
								r: '\r',
								t: '\t'
							};
							if (!(escape in escapes)) {
								malformed = true;
								break;
							}
							decoded = escapes[escape];
							cursor += 2;
						}
					} else cursor++;
					if (stringRole !== 'skip') value += decoded;
					continue;
				}
				if (/\s/.test(c)) {
					cursor++;
					continue;
				}
				if (ended) {
					malformed = true;
					break;
				}
				if (!started) {
					if (c !== '{') {
						malformed = true;
						break;
					}
					started = true;
					stack.push(c);
					cursor++;
					continue;
				}
				if (c === '"') {
					stringRole =
						stack.length === 1
							? stage === 'key'
								? 'key'
								: stage === 'value'
									? 'value'
									: null
							: 'skip';
					if (!stringRole) {
						malformed = true;
						break;
					}
					value = '';
					cursor++;
					continue;
				}
				if (stack.length === 1) {
					if (c === ':' && stage === 'colon') {
						stage = 'value';
						cursor++;
						continue;
					}
					if (c === ',' && stage === 'comma') {
						stage = 'key';
						cursor++;
						continue;
					}
					if (c === '}' && (stage === 'comma' || stage === 'key')) {
						stack.pop();
						ended = true;
						cursor++;
						continue;
					}
					if (stage !== 'value' || names.includes(key)) {
						malformed = true;
						break;
					}
					if (c !== '[' && c !== '{') {
						const match = /^(?:true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?=\s*[,}])/.exec(
							snapshot.slice(cursor)
						);
						if (!match) break;
						cursor += match[0].length;
						stage = 'comma';
						continue;
					}
					stage = 'comma';
				}
				if (c === '[' || c === '{') stack.push(c);
				else if (c === ']' || c === '}') {
					if (stack.pop() !== (c === ']' ? '[' : '{')) {
						malformed = true;
						break;
					}
				}
				cursor++;
			}
			const partial =
				stringRole === 'value' && partialNames.includes(key)
					? { [key]: value.replace(/[\uD800-\uDBFF]$/, '') }
					: {};
			const current = { ...fields, ...partial };
			return { values: current, malformed };
		}
	};
}

export function createVisualizationArgumentDecoder() {
	const decoder = createStringFieldDecoder(['title', 'html']);
	return {
		reset: decoder.reset,
		update(snapshot: string) {
			const { values, malformed } = decoder.update(snapshot);
			const html = values.html ?? '';
			const invalid = malformed || new TextEncoder().encode(html).length > MAX_HTML_BYTES;
			return { title: values.title, html: invalid ? '' : html, malformed: invalid };
		}
	};
}
