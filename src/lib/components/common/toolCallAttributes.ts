import { decode } from 'html-entities';

export function decodeToolCallAttribute(value: string, htmlEncoded = true): string {
	return htmlEncoded ? decode(value) : value;
}

export function parseJSONString(value: string) {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let parsed: any = value;
	while (typeof parsed === 'string') {
		try {
			parsed = JSON.parse(parsed);
		} catch {
			break;
		}
	}
	return parsed;
}

export function parseToolCallAttribute(value: string, htmlEncoded = true) {
	return parseJSONString(decodeToolCallAttribute(value, htmlEncoded));
}
