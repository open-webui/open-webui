/**
 * Performance optimization utilities for PII state management
 * Addresses current performance bottlenecks identified in the analysis
 */

import type { ExtendedPiiEntity, PiiModifier } from '$lib/utils/pii';
import type { PositionMapping } from './PiiPositionMapping';

// Performance metrics tracking
export class PiiPerformanceTracker {
	private static instance: PiiPerformanceTracker;
	private enabled = true; // Can be disabled for production

	private metrics = {
		stateUpdates: 0,
		positionRemaps: 0,
		decorationUpdates: 0,
		cacheHits: 0,
		cacheMisses: 0,
		persistTime: 0,
		apiCalls: 0,
		syncOperations: 0,
		lastResetTime: Date.now()
	};

	private constructor() {}

	static getInstance(): PiiPerformanceTracker {
		if (!PiiPerformanceTracker.instance) {
			PiiPerformanceTracker.instance = new PiiPerformanceTracker();
		}
		return PiiPerformanceTracker.instance;
	}

	setEnabled(enabled: boolean): void {
		this.enabled = enabled;
	}

	isEnabled(): boolean {
		return this.enabled;
	}

	recordStateUpdate(): void {
		if (!this.enabled) return;
		this.metrics.stateUpdates++;
	}

	recordPositionRemap(): void {
		if (!this.enabled) return;
		this.metrics.positionRemaps++;
	}

	recordDecorationUpdate(): void {
		if (!this.enabled) return;
		this.metrics.decorationUpdates++;
	}

	recordCacheHit(): void {
		if (!this.enabled) return;
		this.metrics.cacheHits++;
	}

	recordCacheMiss(): void {
		if (!this.enabled) return;
		this.metrics.cacheMisses++;
	}

	recordPersistTime(time: number): void {
		if (!this.enabled) return;
		this.metrics.persistTime += time;
	}

	recordApiCall(): void {
		if (!this.enabled) return;
		this.metrics.apiCalls++;
	}

	recordSyncOperation(): void {
		if (!this.enabled) return;
		this.metrics.syncOperations++;
	}

	// Measure operation timing
	startTiming(): () => number {
		if (!this.enabled) return () => 0;
		const start = performance.now();
		return () => performance.now() - start;
	}

	getMetrics() {
		const elapsed = Date.now() - this.metrics.lastResetTime;
		return {
			...this.metrics,
			elapsedMs: elapsed,
			stateUpdatesPerSecond: (this.metrics.stateUpdates / elapsed) * 1000,
			cacheHitRate: this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses),
			avgPersistTime: this.metrics.persistTime / Math.max(1, this.metrics.stateUpdates)
		};
	}

	reset(): void {
		this.metrics = {
			stateUpdates: 0,
			positionRemaps: 0,
			decorationUpdates: 0,
			cacheHits: 0,
			cacheMisses: 0,
			persistTime: 0,
			apiCalls: 0,
			syncOperations: 0,
			lastResetTime: Date.now()
		};
	}

	// Debug helpers
	logMetrics(): void {
		if (!this.enabled) {
			console.log('PII Performance Tracker: Disabled');
			return;
		}

		const metrics = this.getMetrics();
		console.group('🚀 PII Performance Metrics');
		console.log(
			'📊 State Updates:',
			metrics.stateUpdates,
			`(${metrics.stateUpdatesPerSecond.toFixed(2)}/sec)`
		);
		console.log('🗺️ Position Remaps:', metrics.positionRemaps);
		console.log('🎨 Decoration Updates:', metrics.decorationUpdates);
		console.log('💾 Cache Hit Rate:', `${(metrics.cacheHitRate * 100).toFixed(1)}%`);
		console.log('🔄 Sync Operations:', metrics.syncOperations);
		console.log('🌐 API Calls:', metrics.apiCalls);
		console.log('⏱️ Avg Persist Time:', `${metrics.avgPersistTime.toFixed(2)}ms`);
		console.log('⏰ Runtime:', `${(metrics.elapsedMs / 1000).toFixed(1)}s`);
		console.groupEnd();
	}

	// Global debug access
	static enableGlobalDebug(): void {
		(window as any).piiPerformance = {
			getMetrics: () => PiiPerformanceTracker.getInstance().getMetrics(),
			logMetrics: () => PiiPerformanceTracker.getInstance().logMetrics(),
			reset: () => PiiPerformanceTracker.getInstance().reset(),
			setEnabled: (enabled: boolean) => PiiPerformanceTracker.getInstance().setEnabled(enabled)
		};
		console.log('🔧 PII Performance debugging available via window.piiPerformance');
	}
}

// Intelligent caching for expensive operations
export class PiiStateCache {
	private entityCache = new Map<string, ExtendedPiiEntity[]>();
	private modifierCache = new Map<string, PiiModifier[]>();
	private positionMappingCache = new Map<string, PositionMapping>();
	private decorationCache = new Map<string, any>(); // DecorationSet cache
	private maxCacheSize = 10; // Limit memory usage

	// Cache key generation
	private getCacheKey(conversationId?: string, documentHash?: string): string {
		return `${conversationId || 'temp'}_${documentHash || 'current'}`;
	}

	// Entity caching
	cacheEntities(
		entities: ExtendedPiiEntity[],
		conversationId?: string,
		documentHash?: string
	): void {
		const key = this.getCacheKey(conversationId, documentHash);
		this.entityCache.set(key, [...entities]); // Deep copy to prevent mutations
		this.enforceMaxCacheSize(this.entityCache);
	}

	getCachedEntities(conversationId?: string, documentHash?: string): ExtendedPiiEntity[] | null {
		const key = this.getCacheKey(conversationId, documentHash);
		return this.entityCache.get(key) || null;
	}

	// Position mapping caching
	cachePositionMapping(
		mapping: PositionMapping,
		conversationId?: string,
		documentHash?: string
	): void {
		const key = this.getCacheKey(conversationId, documentHash);
		this.positionMappingCache.set(key, mapping);
		this.enforceMaxCacheSize(this.positionMappingCache);
	}

	getCachedPositionMapping(conversationId?: string, documentHash?: string): PositionMapping | null {
		const key = this.getCacheKey(conversationId, documentHash);
		return this.positionMappingCache.get(key) || null;
	}

	// Decoration caching
	cacheDecorations(decorations: any, conversationId?: string, entityHash?: string): void {
		const key = this.getCacheKey(conversationId, entityHash);
		this.decorationCache.set(key, decorations);
		this.enforceMaxCacheSize(this.decorationCache);
	}

	getCachedDecorations(conversationId?: string, entityHash?: string): any | null {
		const key = this.getCacheKey(conversationId, entityHash);
		return this.decorationCache.get(key) || null;
	}

	// Cache management
	private enforceMaxCacheSize(cache: Map<string, any>): void {
		if (cache.size > this.maxCacheSize) {
			const firstKey = cache.keys().next().value;
			cache.delete(firstKey);
		}
	}

	invalidateConversation(conversationId: string): void {
		const conversationKeys = Array.from(this.entityCache.keys()).filter((key) =>
			key.startsWith(conversationId)
		);

		conversationKeys.forEach((key) => {
			this.entityCache.delete(key);
			this.modifierCache.delete(key);
			this.positionMappingCache.delete(key);
			this.decorationCache.delete(key);
		});
	}

	clear(): void {
		this.entityCache.clear();
		this.modifierCache.clear();
		this.positionMappingCache.clear();
		this.decorationCache.clear();
	}
}

// Batch operation manager to reduce frequent updates
export class PiiBatchManager {
	private pendingUpdates = new Map<
		string,
		{
			entities?: ExtendedPiiEntity[];
			modifiers?: PiiModifier[];
			timestamp: number;
		}
	>();

	private batchTimeout = 50; // ms
	private batchTimer: number | null = null;

	scheduleUpdate(
		conversationId: string,
		entities?: ExtendedPiiEntity[],
		modifiers?: PiiModifier[]
	): Promise<void> {
		// Accumulate updates
		const existing = this.pendingUpdates.get(conversationId);
		this.pendingUpdates.set(conversationId, {
			entities: entities || existing?.entities,
			modifiers: modifiers || existing?.modifiers,
			timestamp: Date.now()
		});

		// Schedule batch execution
		return new Promise((resolve) => {
			if (this.batchTimer) {
				clearTimeout(this.batchTimer);
			}

			this.batchTimer = window.setTimeout(() => {
				this.executeBatch();
				resolve();
			}, this.batchTimeout);
		});
	}

	private executeBatch(): void {
		const updates = Array.from(this.pendingUpdates.entries());
		this.pendingUpdates.clear();

		// Process all accumulated updates
		updates.forEach(([conversationId, update]) => {
			console.log(`PiiBatchManager: Executing batched update for ${conversationId}`, {
				hasEntities: !!update.entities,
				hasModifiers: !!update.modifiers,
				age: Date.now() - update.timestamp
			});

			// Apply the actual state updates here
			// This would integrate with the state manager
		});
	}

	flush(): void {
		if (this.batchTimer) {
			clearTimeout(this.batchTimer);
			this.executeBatch();
		}
	}
}

// Hash generation for cache invalidation
export function generateEntityHash(entities: ExtendedPiiEntity[]): string {
	const essentialData = entities.map((e) => ({
		label: e.label,
		type: e.type,
		shouldMask: e.shouldMask,
		occurrenceCount: e.occurrences?.length || 0
	}));

	return btoa(JSON.stringify(essentialData))
		.replace(/[+/=]/g, '') // Remove special chars
		.substring(0, 16); // Limit length
}

export function generateDocumentHash(text: string): string {
	// Simple hash for document change detection
	let hash = 0;
	if (text.length === 0) return '0';

	for (let i = 0; i < text.length; i++) {
		const char = text.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash; // Convert to 32bit integer
	}

	return Math.abs(hash).toString(16);
}

// Global initialization for debugging
if (typeof window !== 'undefined') {
	PiiPerformanceTracker.enableGlobalDebug();
}
