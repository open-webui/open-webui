import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

let stored: unknown = null;

const getStoredUMK = vi.fn(async () => stored);
const setStoredUMK = vi.fn(async (record: unknown) => {
	stored = record;
});
const deleteStoredUMK = vi.fn(async () => {
	stored = null;
});

vi.mock('./idb', () => ({
	UMK_STORAGE_KEY: 'owui.umk.v1',
	getStoredUMK,
	setStoredUMK,
	deleteStoredUMK
}));

beforeAll(async () => {
	if (!globalThis.crypto?.subtle) {
		const { webcrypto } = await import('crypto');
		(globalThis as any).crypto = webcrypto;
	}
});

describe('UMK lifecycle', () => {
	beforeEach(() => {
		stored = null;
		getStoredUMK.mockClear();
		setStoredUMK.mockClear();
		deleteStoredUMK.mockClear();
	});

	it('creates and persists a UMK', async () => {
		const { getOrCreateUMK } = await import('./envelope');

		const first = await getOrCreateUMK();
		expect(first.fingerprint).toMatch(/\S+/);
		expect(setStoredUMK).toHaveBeenCalledTimes(1);

		const second = await getOrCreateUMK();
		expect(second.fingerprint).toBe(first.fingerprint);
		expect(setStoredUMK).toHaveBeenCalledTimes(1);
	});

	it('repairs a stored fingerprint mismatch', async () => {
		const { getOrCreateUMK } = await import('./envelope');

		const first = await getOrCreateUMK();

		stored = { ...(stored as any), fingerprint: 'wrong' };
		setStoredUMK.mockClear();

		const second = await getOrCreateUMK();
		expect(second.fingerprint).toBe(first.fingerprint);
		expect((stored as any).fingerprint).toBe(first.fingerprint);
		expect(setStoredUMK).toHaveBeenCalledTimes(1);
	});

	it('recreates the UMK when the stored record is invalid', async () => {
		stored = { v: 1, jwk: {}, fingerprint: 'fp' };
		const { getOrCreateUMK } = await import('./envelope');

		const result = await getOrCreateUMK();
		expect(result.fingerprint).toMatch(/\S+/);
		expect((stored as any).jwk?.k).toBeTruthy();
	});

	it('exports and imports recovery keys', async () => {
		const { exportRecoveryKey, getOrCreateUMK, importRecoveryKey } = await import('./envelope');

		const exported = await exportRecoveryKey();
		expect(exported).toMatch(/\S+/);

		stored = null;
		const { fingerprint } = await importRecoveryKey(`  ${exported}  `);
		expect((stored as any).fingerprint).toBe(fingerprint);

		const umk = await getOrCreateUMK();
		expect(umk.fingerprint).toBe(fingerprint);
	});
});

