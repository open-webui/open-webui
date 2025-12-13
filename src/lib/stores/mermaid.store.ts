import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { MERMAID_CONFIG } from '$lib/constants';

/**
 * Cache entry structure
 */
interface CacheEntry {
	svg: string;
	timestamp: number;
	theme: string;
	accessTime: number; // For LRU eviction
}

/**
 * Error entry structure
 */
interface ErrorEntry {
	type: string;
	message: string;
	timestamp: number;
	codePreview?: string;
}

/**
 * Metrics structure
 */
interface Metrics {
	totalRenders: number;
	successfulRenders: number;
	failedRenders: number;
	cacheHits: number;
	cacheMisses: number;
	averageRenderTime: number;
	errorRate: number;
	cacheHitRate: number;
}

/**
 * Store state structure
 */
interface MermaidStoreState {
	initialized: boolean;
	theme: 'dark' | 'light';
	memoryCache: Map<string, CacheEntry>;
	metrics: Metrics;
	errors: ErrorEntry[];
	indexedDBEnabled: boolean;
	broadcastChannelEnabled: boolean;
}

/**
 * Generate cache key from code and theme
 */
function generateCacheKey(code: string, theme: string): string {
	// Normalize code: trim whitespace, normalize line endings
	const normalized = code.trim().replace(/\r\n/g, '\n').replace(/\r/g, '\n');
	
	// Simple hash function (fast, no crypto needed)
	let hash = 0;
	const str = normalized + theme;
	for (let i = 0; i < str.length; i++) {
		const char = str.charCodeAt(i);
		hash = ((hash << 5) - hash) + char;
		hash = hash & hash; // Convert to 32-bit integer
	}
	
	return hash.toString(36);
}

/**
 * Normalize code for consistent caching
 */
function normalizeCode(code: string): string {
	return code.trim().replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

/**
 * Initial store state
 */
const initialState: MermaidStoreState = {
	initialized: false,
	theme: 'light',
	memoryCache: new Map(),
	metrics: {
		totalRenders: 0,
		successfulRenders: 0,
		failedRenders: 0,
		cacheHits: 0,
		cacheMisses: 0,
		averageRenderTime: 0,
		errorRate: 0,
		cacheHitRate: 0
	},
	errors: [],
	indexedDBEnabled: MERMAID_CONFIG.INDEXEDDB_ENABLED && browser,
	broadcastChannelEnabled: MERMAID_CONFIG.BROADCAST_CHANNEL_ENABLED && browser
};

/**
 * IndexedDB cache entry structure
 */
interface IndexedDBCacheEntry {
	key: string;
	svg: string;
	theme: string;
	timestamp: number;
}

/**
 * Mermaid Store - Centralized state and cache management
 */
class MermaidStore {
	private store: Writable<MermaidStoreState>;
	private renderTimeSum = 0; // Sum of all render times for average calculation
	private db: IDBDatabase | null = null;
	private dbInitialized = false;
	private cleanupInterval: ReturnType<typeof setInterval> | null = null;
	private broadcastChannel: BroadcastChannel | null = null;
	private broadcastChannelInitialized = false;
	private metricsLogInterval: ReturnType<typeof setInterval> | null = null;
	private lastMetricsLogCount = 0;

	constructor() {
		this.store = writable(initialState);
		console.log('[Mermaid] Store initialized');
		
		// Initialize IndexedDB if enabled
		if (browser && MERMAID_CONFIG.INDEXEDDB_ENABLED) {
			this.initIndexedDB();
		}

		// Initialize BroadcastChannel if enabled
		if (browser && MERMAID_CONFIG.BROADCAST_CHANNEL_ENABLED) {
			this.initBroadcastChannel();
		}

		// Setup periodic metrics logging if enabled
		if (browser && MERMAID_CONFIG.ENABLE_METRICS) {
			this.setupMetricsLogging();
		}
	}

	/**
	 * Get store value
	 */
	get(): MermaidStoreState {
		let value: MermaidStoreState;
		this.store.subscribe((v) => {
			value = v;
		})();
		return value!;
	}

	/**
	 * Subscribe to store
	 */
	subscribe(callback: (value: MermaidStoreState) => void) {
		return this.store.subscribe(callback);
	}

	/**
	 * Set initialized state
	 */
	setInitialized(initialized: boolean, theme: 'dark' | 'light' = 'light'): void {
		this.store.update((state) => {
			state.initialized = initialized;
			state.theme = theme;
			return state;
		});
	}

	/**
	 * Initialize IndexedDB
	 */
	private async initIndexedDB(): Promise<void> {
		if (!browser || !MERMAID_CONFIG.INDEXEDDB_ENABLED) {
			return;
		}

		try {
			console.log('[Mermaid] IndexedDB: Initializing database');

			return new Promise((resolve, reject) => {
				const request = indexedDB.open('mermaid_cache_db', 1);

				request.onerror = () => {
					const error = request.error;
					console.warn(`[Mermaid] IndexedDB: Unavailable, falling back to memory cache: ${error?.message}`);
					this.dbInitialized = false;
					reject(error);
				};

				request.onsuccess = () => {
					this.db = request.result;
					this.dbInitialized = true;
					console.log('[Mermaid] IndexedDB: Database opened successfully');
					
					// Run cleanup on initialization
					this.cleanupIndexedDB().catch((err) => {
						console.warn('[Mermaid] IndexedDB: Cleanup failed on init:', err);
					});

					// Setup periodic cleanup (every 10 minutes)
					this.cleanupInterval = setInterval(() => {
						this.cleanupIndexedDB().catch((err) => {
							console.warn('[Mermaid] IndexedDB: Periodic cleanup failed:', err);
						});
					}, 10 * 60 * 1000);

					resolve();
				};

				request.onupgradeneeded = (event) => {
					const db = (event.target as IDBOpenDBRequest).result;
					if (!db.objectStoreNames.contains(MERMAID_CONFIG.INDEXEDDB_STORE_NAME)) {
						const store = db.createObjectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME, { keyPath: 'key' });
						store.createIndex('timestamp', 'timestamp', { unique: false });
						store.createIndex('theme', 'theme', { unique: false });
					}
				};
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] IndexedDB: Error initializing, using memory cache: ${errorMessage}`);
			this.dbInitialized = false;
		}
	}

	/**
	 * Get from IndexedDB
	 */
	private async getFromIndexedDB(key: string): Promise<string | null> {
		if (!this.dbInitialized || !this.db) {
			return null;
		}

		try {
			const startTime = performance.now();
			return new Promise((resolve, reject) => {
				const transaction = this.db!.transaction([MERMAID_CONFIG.INDEXEDDB_STORE_NAME], 'readonly');
				const store = transaction.objectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME);
				const request = store.get(key);

				request.onsuccess = () => {
					const duration = performance.now() - startTime;
					const entry = request.result as IndexedDBCacheEntry | undefined;
					
					if (entry) {
						// Check TTL
						const age = Date.now() - entry.timestamp;
						const ttlMs = MERMAID_CONFIG.INDEXEDDB_TTL_DAYS * 24 * 60 * 60 * 1000;
						
						if (age > ttlMs) {
							// Expired, delete it
							this.deleteFromIndexedDB(key).catch(() => {});
							console.log(`[Mermaid] IndexedDB: Cache expired: key=${key}`);
							resolve(null);
						} else {
							console.log(`[Mermaid] IndexedDB: Cache hit: key=${key} (${duration.toFixed(2)}ms)`);
							resolve(entry.svg);
						}
					} else {
						console.log(`[Mermaid] IndexedDB: Cache miss: key=${key}`);
						resolve(null);
					}
				};

				request.onerror = () => {
					const errorMessage = request.error?.message || 'Unknown error';
					console.warn(`[Mermaid] IndexedDB: Error reading: ${errorMessage}, using memory cache`);
					resolve(null);
				};
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] IndexedDB: Error: ${errorMessage}, using memory cache`);
			return null;
		}
	}

	/**
	 * Set in IndexedDB
	 */
	private async setInIndexedDB(key: string, svg: string, theme: string): Promise<void> {
		if (!this.dbInitialized || !this.db) {
			return;
		}

		try {
			const entry: IndexedDBCacheEntry = {
				key,
				svg,
				theme,
				timestamp: Date.now()
			};

			return new Promise((resolve, reject) => {
				const transaction = this.db!.transaction([MERMAID_CONFIG.INDEXEDDB_STORE_NAME], 'readwrite');
				const store = transaction.objectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME);
				const request = store.put(entry);

				request.onsuccess = () => {
					const size = new Blob([svg]).size;
					console.log(`[Mermaid] IndexedDB: Cache saved: key=${key}, size=${size}bytes`);
					resolve();
				};

				request.onerror = () => {
					const error = request.error;
					if (error?.name === 'QuotaExceededError') {
						console.warn('[Mermaid] IndexedDB: Quota exceeded, evicting oldest entries');
						this.evictOldestFromIndexedDB().then(() => {
							// Retry after eviction
							this.setInIndexedDB(key, svg, theme).then(resolve).catch(reject);
						}).catch(reject);
					} else {
						const errorMessage = error?.message || 'Unknown error';
						console.warn(`[Mermaid] IndexedDB: Error saving: ${errorMessage}`);
						resolve(); // Don't fail, just log
					}
				};
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] IndexedDB: Error: ${errorMessage}`);
		}
	}

	/**
	 * Delete from IndexedDB
	 */
	private async deleteFromIndexedDB(key: string): Promise<void> {
		if (!this.dbInitialized || !this.db) {
			return;
		}

		try {
			return new Promise((resolve, reject) => {
				const transaction = this.db!.transaction([MERMAID_CONFIG.INDEXEDDB_STORE_NAME], 'readwrite');
				const store = transaction.objectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME);
				const request = store.delete(key);

				request.onsuccess = () => resolve();
				request.onerror = () => reject(request.error);
			});
		} catch (error) {
			// Ignore delete errors
		}
	}

	/**
	 * Evict oldest entries from IndexedDB
	 */
	private async evictOldestFromIndexedDB(): Promise<void> {
		if (!this.dbInitialized || !this.db) {
			return;
		}

		try {
			return new Promise((resolve, reject) => {
				const transaction = this.db!.transaction([MERMAID_CONFIG.INDEXEDDB_STORE_NAME], 'readwrite');
				const store = transaction.objectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME);
				const index = store.index('timestamp');
				const request = index.openCursor(null, 'next');

				const entriesToDelete: string[] = [];
				let count = 0;
				const maxDelete = 10; // Delete 10 oldest entries

				request.onsuccess = (event) => {
					const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
					if (cursor && count < maxDelete) {
						entriesToDelete.push(cursor.value.key);
						count++;
						cursor.continue();
					} else {
						// Delete entries
						Promise.all(entriesToDelete.map((key) => this.deleteFromIndexedDB(key)))
							.then(() => {
								console.log(`[Mermaid] IndexedDB: Evicted ${entriesToDelete.length} oldest entries`);
								resolve();
							})
							.catch(reject);
					}
				};

				request.onerror = () => reject(request.error);
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] IndexedDB: Error evicting: ${errorMessage}`);
		}
	}

	/**
	 * Cleanup expired entries from IndexedDB
	 */
	private async cleanupIndexedDB(): Promise<void> {
		if (!this.dbInitialized || !this.db) {
			return;
		}

		try {
			const ttlMs = MERMAID_CONFIG.INDEXEDDB_TTL_DAYS * 24 * 60 * 60 * 1000;
			const cutoffTime = Date.now() - ttlMs;

			return new Promise((resolve, reject) => {
				const transaction = this.db!.transaction([MERMAID_CONFIG.INDEXEDDB_STORE_NAME], 'readwrite');
				const store = transaction.objectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME);
				const index = store.index('timestamp');
				const request = index.openCursor(IDBKeyRange.upperBound(cutoffTime));

				const keysToDelete: string[] = [];

				request.onsuccess = (event) => {
					const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
					if (cursor) {
						keysToDelete.push(cursor.value.key);
						cursor.continue();
					} else {
						// Delete expired entries
						Promise.all(keysToDelete.map((key) => this.deleteFromIndexedDB(key)))
							.then(() => {
								if (keysToDelete.length > 0) {
									console.log(`[Mermaid] IndexedDB: Cleanup: Removed ${keysToDelete.length} expired entries`);
								}
								resolve();
							})
							.catch(reject);
					}
				};

				request.onerror = () => reject(request.error);
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] IndexedDB: Cleanup error: ${errorMessage}`);
		}
	}

	/**
	 * Get from memory cache or IndexedDB (two-tier cache)
	 */
	async getFromCache(code: string, theme: string): Promise<string | null> {
		const key = generateCacheKey(code, theme);
		const state = this.get();
		
		// Check memory cache first (<1ms)
		const entry = state.memoryCache.get(key);
		if (entry) {
			// Update access time for LRU
			entry.accessTime = Date.now();
			state.memoryCache.set(key, entry);

			// Update metrics
			this.updateMetrics({ cacheHits: state.metrics.cacheHits + 1 });

			// Broadcast cache hit to other tabs
			if (this.broadcastChannelInitialized) {
				this.broadcastCacheHit(key, entry.svg, entry.theme, entry.timestamp);
			}

			const savedTime = 200; // Estimated saved time (ms)
			console.log(`[Mermaid] Cache hit: key=${key} (saved ${savedTime}ms)`);
			return entry.svg;
		}

		// Check IndexedDB (5-20ms)
		if (this.dbInitialized) {
			const indexedDBSvg = await this.getFromIndexedDB(key);
			if (indexedDBSvg) {
				// Store in memory cache for faster access next time
				this.setInCache(code, indexedDBSvg, theme);
				// Update metrics
				this.updateMetrics({ cacheHits: state.metrics.cacheHits + 1 });
				return indexedDBSvg;
			}
		}

		// Broadcast cache miss to other tabs (they might have it)
		if (this.broadcastChannelInitialized) {
			this.broadcastCacheMiss(key);
		}

		// Update metrics
		this.updateMetrics({ cacheMisses: state.metrics.cacheMisses + 1 });
		console.log(`[Mermaid] Cache miss: key=${key}`);
		return null;
	}

	/**
	 * Set in memory cache and IndexedDB
	 */
	setInCache(code: string, svg: string, theme: string): void {
		const key = generateCacheKey(code, theme);
		const state = this.get();

		// Check if cache is full
		if (state.memoryCache.size >= MERMAID_CONFIG.MEMORY_CACHE_SIZE) {
			// Evict least recently used entry
			let oldestKey: string | null = null;
			let oldestTime = Infinity;

			for (const [k, entry] of state.memoryCache.entries()) {
				if (entry.accessTime < oldestTime) {
					oldestTime = entry.accessTime;
					oldestKey = k;
				}
			}

			if (oldestKey) {
				state.memoryCache.delete(oldestKey);
				console.log(`[Mermaid] Cache evicted: key=${oldestKey} (size limit: ${MERMAID_CONFIG.MEMORY_CACHE_SIZE})`);
			}
		}

		const timestamp = Date.now();
		
		// Add new entry to memory cache
		state.memoryCache.set(key, {
			svg,
			timestamp,
			theme,
			accessTime: Date.now()
		});

		this.store.set(state);

		// Also store in IndexedDB (async, don't wait)
		if (this.dbInitialized) {
			this.setInIndexedDB(key, svg, theme).catch((err) => {
				console.warn(`[Mermaid] IndexedDB: Failed to save cache: ${err}`);
			});
		}

		// Broadcast to other tabs
		if (this.broadcastChannelInitialized) {
			this.broadcastCacheSet(key, svg, theme, timestamp);
		}

		const size = state.memoryCache.size;
		const hits = state.metrics.cacheHits;
		const misses = state.metrics.cacheMisses;
		const hitRate = hits + misses > 0 ? (hits / (hits + misses)) * 100 : 0;
		console.log(`[Mermaid] Cache stats: size=${size}, hits=${hits}, misses=${misses}, hitRate=${hitRate.toFixed(1)}%`);
	}

	/**
	 * Clear memory cache
	 */
	clearCache(): void {
		this.store.update((state) => {
			state.memoryCache.clear();
			return state;
		});
		console.log('[Mermaid] Cache cleared');
	}

	/**
	 * Setup periodic metrics logging
	 */
	private setupMetricsLogging(): void {
		// Log metrics every N renders (from config)
		this.store.subscribe((state) => {
			const totalRenders = state.metrics.totalRenders;
			if (totalRenders > 0 && totalRenders % MERMAID_CONFIG.METRICS_LOG_INTERVAL === 0) {
				if (totalRenders !== this.lastMetricsLogCount) {
					this.logMetrics();
					this.lastMetricsLogCount = totalRenders;
				}
			}
		});
	}

	/**
	 * Log metrics and performance warnings
	 */
	private logMetrics(): void {
		const metrics = this.getMetrics();
		const {
			totalRenders,
			successfulRenders,
			failedRenders,
			cacheHits,
			cacheMisses,
			averageRenderTime,
			errorRate,
			cacheHitRate
		} = metrics;

		console.log(
			`[Mermaid] Metrics: renders=${totalRenders}, successful=${successfulRenders}, failed=${failedRenders}`
		);
		console.log(
			`[Mermaid] Metrics: avgTime=${averageRenderTime.toFixed(2)}ms, cacheHitRate=${(cacheHitRate * 100).toFixed(1)}%, errorRate=${(errorRate * 100).toFixed(1)}%`
		);

		// Performance warnings
		if (averageRenderTime > MERMAID_CONFIG.SLOW_RENDER_WARNING_MS) {
			console.warn(
				`[Mermaid] Performance warning: Average render time ${averageRenderTime.toFixed(2)}ms (threshold: ${MERMAID_CONFIG.SLOW_RENDER_WARNING_MS}ms)`
			);
		}

		if (cacheHitRate < MERMAID_CONFIG.LOW_CACHE_HIT_RATE) {
			console.warn(
				`[Mermaid] Performance warning: Cache hit rate ${(cacheHitRate * 100).toFixed(1)}% (target: >${(MERMAID_CONFIG.LOW_CACHE_HIT_RATE * 100)}%)`
			);
		}

		if (errorRate > MERMAID_CONFIG.HIGH_ERROR_RATE) {
			console.warn(
				`[Mermaid] Performance warning: Error rate ${(errorRate * 100).toFixed(1)}% (threshold: ${(MERMAID_CONFIG.HIGH_ERROR_RATE * 100)}%)`
			);
		}
	}

	/**
	 * Record render metrics
	 */
	recordRender(success: boolean, renderTime: number): void {
		const state = this.get();
		this.renderTimeSum += renderTime;

		this.updateMetrics({
			totalRenders: state.metrics.totalRenders + 1,
			successfulRenders: success
				? state.metrics.successfulRenders + 1
				: state.metrics.successfulRenders,
			failedRenders: success
				? state.metrics.failedRenders
				: state.metrics.failedRenders + 1
		});

		// Update average render time
		const newTotal = this.get().metrics.totalRenders;
		if (newTotal > 0) {
			const avgTime = this.renderTimeSum / newTotal;
			this.updateMetrics({ averageRenderTime: avgTime });

			// Check for performance warnings on individual renders
			if (renderTime > MERMAID_CONFIG.SLOW_RENDER_WARNING_MS) {
				console.warn(
					`[Mermaid] Performance warning: Render took ${renderTime.toFixed(2)}ms (threshold: ${MERMAID_CONFIG.SLOW_RENDER_WARNING_MS}ms)`
				);
			}
		}
	}

	/**
	 * Update metrics
	 */
	private updateMetrics(updates: Partial<Metrics>): void {
		this.store.update((state) => {
			state.metrics = { ...state.metrics, ...updates };

			// Calculate rates
			const total = state.metrics.totalRenders;
			if (total > 0) {
				state.metrics.errorRate = state.metrics.failedRenders / total;
			}

			const cacheTotal = state.metrics.cacheHits + state.metrics.cacheMisses;
			if (cacheTotal > 0) {
				state.metrics.cacheHitRate = state.metrics.cacheHits / cacheTotal;
			}

			return state;
		});
	}

	/**
	 * Get current metrics
	 */
	getMetrics(): Metrics {
		return this.get().metrics;
	}

	/**
	 * Reset metrics
	 */
	resetMetrics(): void {
		this.store.update((state) => {
			state.metrics = { ...initialState.metrics };
			return state;
		});
		this.renderTimeSum = 0;
		console.log('[Mermaid] Metrics reset');
	}

	/**
	 * Add error
	 */
	addError(type: string, message: string, codePreview?: string): void {
		this.store.update((state) => {
			state.errors.push({
				type,
				message,
				timestamp: Date.now(),
				codePreview
			});

			// Keep only last 100 errors
			if (state.errors.length > 100) {
				state.errors.shift();
			}

			return state;
		});
	}

	/**
	 * Get errors
	 */
	getErrors(): ErrorEntry[] {
		return this.get().errors;
	}

	/**
	 * Clear errors
	 */
	clearErrors(): void {
		this.store.update((state) => {
			state.errors = [];
			return state;
		});
	}

	/**
	 * Clear IndexedDB cache
	 */
	async clearIndexedDB(): Promise<void> {
		if (!this.dbInitialized || !this.db) {
			return;
		}

		try {
			return new Promise((resolve, reject) => {
				const transaction = this.db!.transaction([MERMAID_CONFIG.INDEXEDDB_STORE_NAME], 'readwrite');
				const store = transaction.objectStore(MERMAID_CONFIG.INDEXEDDB_STORE_NAME);
				const request = store.clear();

				request.onsuccess = () => {
					console.log('[Mermaid] IndexedDB: Cache cleared');
					resolve();
				};

				request.onerror = () => reject(request.error);
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] IndexedDB: Error clearing: ${errorMessage}`);
		}
	}

	/**
	 * Initialize BroadcastChannel for cross-tab sync
	 */
	private initBroadcastChannel(): void {
		if (!browser || !MERMAID_CONFIG.BROADCAST_CHANNEL_ENABLED) {
			return;
		}

		try {
			this.broadcastChannel = new BroadcastChannel(MERMAID_CONFIG.BROADCAST_CHANNEL_NAME);
			this.broadcastChannelInitialized = true;
			console.log(`[Mermaid] BroadcastChannel: Initialized channel '${MERMAID_CONFIG.BROADCAST_CHANNEL_NAME}'`);

			// Listen for messages from other tabs
			this.broadcastChannel.onmessage = (event) => {
				try {
					const message = event.data;
					this.handleBroadcastMessage(message);
				} catch (error) {
					const errorMessage = error instanceof Error ? error.message : String(error);
					console.warn(`[Mermaid] BroadcastChannel: Message parse error: ${errorMessage}`);
				}
			};

			this.broadcastChannel.onerror = (error) => {
				console.warn('[Mermaid] BroadcastChannel: Error occurred:', error);
			};
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] BroadcastChannel: Unavailable, using local cache only: ${errorMessage}`);
			this.broadcastChannelInitialized = false;
		}
	}

	/**
	 * Handle broadcast messages from other tabs
	 */
	private handleBroadcastMessage(message: any): void {
		if (!message || typeof message !== 'object' || !message.type) {
			return;
		}

		const { type, key, svg, theme, timestamp } = message;

		switch (type) {
			case 'cache-hit':
				if (key && svg && theme) {
					// Check if we don't have this in memory cache
					const state = this.get();
					if (!state.memoryCache.has(key)) {
						// Store in memory cache
						state.memoryCache.set(key, {
							svg,
							timestamp: timestamp || Date.now(),
							theme,
							accessTime: Date.now()
						});
						this.store.set(state);
						console.log(`[Mermaid] BroadcastChannel: Received cache-hit from tab (key: ${key})`);
					}
				}
				break;

			case 'cache-set':
				if (key && svg && theme) {
					// Update local cache if newer
					const state = this.get();
					const existing = state.memoryCache.get(key);
					const messageTimestamp = timestamp || Date.now();
					
					if (!existing || messageTimestamp > existing.timestamp) {
						state.memoryCache.set(key, {
							svg,
							timestamp: messageTimestamp,
							theme,
							accessTime: Date.now()
						});
						this.store.set(state);
						console.log(`[Mermaid] BroadcastChannel: Received cache-set from tab (key: ${key})`);
					}
				}
				break;

			case 'cache-miss':
				// Another tab is looking for this key, we can ignore or respond if we have it
				if (key) {
					const state = this.get();
					const entry = state.memoryCache.get(key);
					if (entry && this.broadcastChannelInitialized && this.broadcastChannel) {
						// Respond with our cached version
						this.broadcastChannel.postMessage({
							type: 'cache-hit',
							key,
							svg: entry.svg,
							theme: entry.theme,
							timestamp: entry.timestamp
						});
					}
				}
				break;

			default:
				// Unknown message type, ignore
				break;
		}
	}

	/**
	 * Broadcast cache hit to other tabs
	 */
	private broadcastCacheHit(key: string, svg: string, theme: string, timestamp: number): void {
		if (!this.broadcastChannelInitialized || !this.broadcastChannel) {
			return;
		}

		try {
			this.broadcastChannel.postMessage({
				type: 'cache-hit',
				key,
				svg,
				theme,
				timestamp
			});
			console.log(`[Mermaid] BroadcastChannel: Sent cache-hit to tabs (key: ${key})`);
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] BroadcastChannel: Error sending message: ${errorMessage}`);
		}
	}

	/**
	 * Broadcast cache set to other tabs
	 */
	private broadcastCacheSet(key: string, svg: string, theme: string, timestamp: number): void {
		if (!this.broadcastChannelInitialized || !this.broadcastChannel) {
			return;
		}

		try {
			this.broadcastChannel.postMessage({
				type: 'cache-set',
				key,
				svg,
				theme,
				timestamp
			});
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] BroadcastChannel: Error sending message: ${errorMessage}`);
		}
	}

	/**
	 * Broadcast cache miss to other tabs (request for cache)
	 */
	private broadcastCacheMiss(key: string): void {
		if (!this.broadcastChannelInitialized || !this.broadcastChannel) {
			return;
		}

		try {
			this.broadcastChannel.postMessage({
				type: 'cache-miss',
				key
			});
			console.log(`[Mermaid] BroadcastChannel: Sent cache-miss to tabs (key: ${key})`);
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.warn(`[Mermaid] BroadcastChannel: Error sending message: ${errorMessage}`);
		}
	}

	/**
	 * Cleanup on destroy
	 */
	destroy(): void {
		if (this.cleanupInterval) {
			clearInterval(this.cleanupInterval);
			this.cleanupInterval = null;
		}
		if (this.metricsLogInterval) {
			clearInterval(this.metricsLogInterval);
			this.metricsLogInterval = null;
		}
		if (this.db) {
			this.db.close();
			this.db = null;
			this.dbInitialized = false;
		}
		if (this.broadcastChannel) {
			this.broadcastChannel.close();
			this.broadcastChannel = null;
			this.broadcastChannelInitialized = false;
		}
	}
}

// Export singleton instance
export const mermaidStore = new MermaidStore();

