type LocalStorageCacheEntry<T> = {
	cacheKey: string;
	value: T;
	createdAt: number;
	expiresAt?: number;
};

export const readLocalStorageCache = <T>(storageKey: string, cacheKey: string): T | null => {
	try {
		const cached = JSON.parse(
			localStorage.getItem(storageKey) ?? 'null'
		) as LocalStorageCacheEntry<T> | null;

		if (!cached || cached.cacheKey !== cacheKey) {
			return null;
		}

		if (typeof cached.expiresAt === 'number' && cached.expiresAt < Date.now()) {
			localStorage.removeItem(storageKey);
			return null;
		}

		return cached.value;
	} catch (e) {
		console.error(`Failed to parse ${storageKey} cache`, e);
		localStorage.removeItem(storageKey);
		return null;
	}
};

export const writeLocalStorageCache = <T>(
	storageKey: string,
	cacheKey: string,
	value: T,
	ttlMs?: number
) => {
	try {
		const now = Date.now();
		localStorage.setItem(
			storageKey,
			JSON.stringify({
				cacheKey,
				value,
				createdAt: now,
				...(ttlMs ? { expiresAt: now + ttlMs } : {})
			})
		);
	} catch (e) {
		console.error(`Failed to write ${storageKey} cache`, e);
	}
};

export const clearLocalStorageCache = (storageKey: string) => {
	localStorage.removeItem(storageKey);
};
