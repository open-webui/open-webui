import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

type DbLike = {
	get(storeName: string, key: string): Promise<unknown>;
	put(storeName: string, value: unknown, key: string): Promise<void>;
	delete(storeName: string, key: string): Promise<void>;
};

const kv = new Map<string, unknown>();

vi.mock('idb', () => {
	const openDB = async (
		_dbName: string,
		_version: number,
		options: { upgrade(db: { objectStoreNames: { contains(name: string): boolean }; createObjectStore(name: string): void }): void }
	): Promise<DbLike> => {
		const createdStores = new Set<string>();
		options.upgrade({
			objectStoreNames: { contains: (name: string) => createdStores.has(name) },
			createObjectStore: (name: string) => {
				createdStores.add(name);
			}
		});

		return {
			get: async (_storeName: string, key: string) => kv.get(key),
			put: async (_storeName: string, value: unknown, key: string) => {
				kv.set(key, value);
			},
			delete: async (_storeName: string, key: string) => {
				kv.delete(key);
			}
		};
	};

	return { openDB };
});

describe('crypto idb storage', () => {
	const originalIndexedDB = (globalThis as any).indexedDB;

	beforeEach(() => {
		kv.clear();
	});

	afterEach(() => {
		(globalThis as any).indexedDB = originalIndexedDB;
	});

	it('throws when IndexedDB is unavailable', async () => {
		(globalThis as any).indexedDB = undefined;

		const { getStoredUMK } = await import('./idb');
		await expect(getStoredUMK()).rejects.toThrow('IndexedDB is not available');
	});

	it('stores, reads, and deletes UMK record', async () => {
		(globalThis as any).indexedDB = {};

		const { deleteStoredUMK, getStoredUMK, setStoredUMK } = await import('./idb');

		expect(await getStoredUMK()).toBeNull();

		await setStoredUMK({
			v: 1,
			jwk: { kty: 'oct', k: 'AA', alg: 'A256GCM', ext: true, key_ops: ['encrypt', 'decrypt'] },
			fingerprint: 'fp'
		});

		expect(await getStoredUMK()).toEqual({
			v: 1,
			jwk: { kty: 'oct', k: 'AA', alg: 'A256GCM', ext: true, key_ops: ['encrypt', 'decrypt'] },
			fingerprint: 'fp'
		});

		await deleteStoredUMK();
		expect(await getStoredUMK()).toBeNull();
	});
});
