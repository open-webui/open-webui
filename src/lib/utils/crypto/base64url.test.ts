import { describe, expect, it } from 'vitest';

import { fromB64Url, toB64Url } from './base64url';

describe('base64url helpers', () => {
	it('round-trips bytes', () => {
		const input = new Uint8Array([0, 1, 2, 3, 250, 251, 252, 253, 254, 255]);
		const encoded = toB64Url(input);
		const decoded = fromB64Url(encoded);

		expect(decoded).toEqual(input);
		expect(encoded).not.toMatch(/[+/=]/);
	});

	it('uses btoa/atob when available', () => {
		const originalBtoa = (globalThis as any).btoa;
		const originalAtob = (globalThis as any).atob;

		let btoaCalled = false;
		let atobCalled = false;

		(globalThis as any).btoa = (binary: string) => {
			btoaCalled = true;
			return Buffer.from(binary, 'binary').toString('base64');
		};
		(globalThis as any).atob = (base64: string) => {
			atobCalled = true;
			return Buffer.from(base64, 'base64').toString('binary');
		};

		try {
			const input = new Uint8Array([9, 8, 7, 6, 5, 4, 3, 2, 1]);
			const encoded = toB64Url(input);
			const decoded = fromB64Url(encoded);

			expect(decoded).toEqual(input);
			expect(btoaCalled).toBe(true);
			expect(atobCalled).toBe(true);
		} finally {
			(globalThis as any).btoa = originalBtoa;
			(globalThis as any).atob = originalAtob;
		}
	});

	it('throws when no base64 primitives exist', () => {
		const originalBtoa = (globalThis as any).btoa;
		const originalAtob = (globalThis as any).atob;
		const originalBuffer = (globalThis as any).Buffer;

		(globalThis as any).btoa = undefined;
		(globalThis as any).atob = undefined;
		(globalThis as any).Buffer = undefined;

		try {
			expect(() => toB64Url(new Uint8Array([1, 2, 3]))).toThrow('No base64 encoder available');
			expect(() => fromB64Url('AQID')).toThrow('No base64 decoder available');
		} finally {
			(globalThis as any).btoa = originalBtoa;
			(globalThis as any).atob = originalAtob;
			(globalThis as any).Buffer = originalBuffer;
		}
	});
});

