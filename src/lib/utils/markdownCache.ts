/**
 * LRU Cache for Markdown parsing results
 * Helps avoid re-parsing the same content multiple times
 */

interface CacheEntry<T> {
	value: T;
	timestamp: number;
}

class LRUCache<K, V> {
	private cache: Map<K, CacheEntry<V>>;
	private maxSize: number;
	private maxAge: number; // in milliseconds

	constructor(maxSize: number = 100, maxAge: number = 5 * 60 * 1000) {
		this.cache = new Map();
		this.maxSize = maxSize;
		this.maxAge = maxAge;
	}

	get(key: K): V | undefined {
		const entry = this.cache.get(key);
		if (!entry) return undefined;

		// Check if entry has expired
		if (Date.now() - entry.timestamp > this.maxAge) {
			this.cache.delete(key);
			return undefined;
		}

		// Move to end (most recently used)
		this.cache.delete(key);
		this.cache.set(key, entry);
		return entry.value;
	}

	set(key: K, value: V): void {
		// Delete existing entry if present
		if (this.cache.has(key)) {
			this.cache.delete(key);
		}

		// Evict oldest entries if at capacity
		while (this.cache.size >= this.maxSize) {
			const firstKey = this.cache.keys().next().value;
			if (firstKey !== undefined) {
				this.cache.delete(firstKey);
			}
		}

		this.cache.set(key, {
			value,
			timestamp: Date.now()
		});
	}

	has(key: K): boolean {
		const entry = this.cache.get(key);
		if (!entry) return false;

		if (Date.now() - entry.timestamp > this.maxAge) {
			this.cache.delete(key);
			return false;
		}

		return true;
	}

	clear(): void {
		this.cache.clear();
	}

	get size(): number {
		return this.cache.size;
	}
}

// Create a singleton cache for markdown tokens
// Key: content hash, Value: parsed tokens
const markdownCache = new LRUCache<string, unknown[]>(200, 10 * 60 * 1000);

/**
 * Generate a simple hash for content
 * Using a fast hash for performance
 */
function hashContent(content: string, modelName?: string, userName?: string): string {
	const combined = `${content}|${modelName ?? ''}|${userName ?? ''}`;
	let hash = 0;
	for (let i = 0; i < combined.length; i++) {
		const char = combined.charCodeAt(i);
		hash = ((hash << 5) - hash) + char;
		hash = hash & hash; // Convert to 32bit integer
	}
	return hash.toString(36);
}

/**
 * Get cached tokens or parse and cache new ones
 */
export function getCachedTokens(
	content: string,
	modelName: string | undefined,
	userName: string | undefined,
	parser: (content: string) => unknown[]
): unknown[] {
	const key = hashContent(content, modelName, userName);

	const cached = markdownCache.get(key);
	if (cached) {
		return cached;
	}

	const tokens = parser(content);
	markdownCache.set(key, tokens);
	return tokens;
}

/**
 * Clear the markdown cache
 * Useful when settings change that affect parsing
 */
export function clearMarkdownCache(): void {
	markdownCache.clear();
}

/**
 * Get cache statistics for debugging
 */
export function getMarkdownCacheStats(): { size: number } {
	return {
		size: markdownCache.size
	};
}

export { LRUCache };
