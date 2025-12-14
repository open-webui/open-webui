export type StoredUMKRecordV1 = {
	v: 1;
	jwk: JsonWebKey;
	fingerprint: string;
};

const DB_NAME = 'owui.crypto';
const DB_VERSION = 1;
const STORE_NAME = 'keys';

export const UMK_STORAGE_KEY = 'owui.umk.v1';

async function getDb() {
	if (typeof indexedDB === 'undefined') {
		throw new Error('IndexedDB is not available');
	}

	const { openDB } = await import('idb');
	return openDB(DB_NAME, DB_VERSION, {
		upgrade(db) {
			if (!db.objectStoreNames.contains(STORE_NAME)) {
				db.createObjectStore(STORE_NAME);
			}
		}
	});
}

export async function getStoredUMK(): Promise<StoredUMKRecordV1 | null> {
	const db = await getDb();
	const value = (await db.get(STORE_NAME, UMK_STORAGE_KEY)) as StoredUMKRecordV1 | undefined;
	return value ?? null;
}

export async function setStoredUMK(record: StoredUMKRecordV1): Promise<void> {
	const db = await getDb();
	await db.put(STORE_NAME, record, UMK_STORAGE_KEY);
}

export async function deleteStoredUMK(): Promise<void> {
	const db = await getDb();
	await db.delete(STORE_NAME, UMK_STORAGE_KEY);
}
