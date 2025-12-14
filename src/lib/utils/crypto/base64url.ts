function toBase64(bytes: Uint8Array): string {
	if (typeof btoa === 'function') {
		let binary = '';
		for (let index = 0; index < bytes.length; index += 1) {
			binary += String.fromCharCode(bytes[index]);
		}
		return btoa(binary);
	}

	const bufferCtor = (globalThis as { Buffer?: unknown }).Buffer as
		| { from(data: Uint8Array): { toString(encoding: 'base64'): string } }
		| undefined;
	if (bufferCtor) {
		return bufferCtor.from(bytes).toString('base64');
	}

	throw new Error('No base64 encoder available');
}

function fromBase64(base64: string): Uint8Array {
	if (typeof atob === 'function') {
		const binary = atob(base64);
		const bytes = new Uint8Array(binary.length);
		for (let index = 0; index < binary.length; index += 1) {
			bytes[index] = binary.charCodeAt(index);
		}
		return bytes;
	}

	const bufferCtor = (globalThis as { Buffer?: unknown }).Buffer as
		| { from(data: string, encoding: 'base64'): Uint8Array }
		| undefined;
	if (bufferCtor) {
		return new Uint8Array(bufferCtor.from(base64, 'base64'));
	}

	throw new Error('No base64 decoder available');
}

export function toB64Url(bytes: Uint8Array): string {
	return toBase64(bytes).replaceAll('+', '-').replaceAll('/', '_').replaceAll(/=+$/g, '');
}

export function fromB64Url(b64url: string): Uint8Array {
	const base64 = b64url.replaceAll('-', '+').replaceAll('_', '/');
	const padding = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4));
	return fromBase64(base64 + padding);
}
