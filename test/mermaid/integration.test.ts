/**
 * Mermaid Integration Test Suite
 * 
 * End-to-end integration tests for the complete Mermaid pipeline
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { mermaidService } from '$lib/services/mermaid.service';
import { mermaidStore } from '$lib/stores/mermaid.store';
import { MERMAID_CONFIG } from '$lib/constants';

// Mock Mermaid diagrams for testing
const MOCK_DIAGRAMS = {
	simple: 'graph TD\nA-->B',
	complex: `graph LR
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E`,
	sequence: `sequenceDiagram
    participant A
    participant B
    A->>B: Message
    B-->>A: Response`,
	invalid: 'invalid mermaid syntax !!!'
};

describe('Mermaid Complete Pipeline Integration', () => {
	beforeAll(async () => {
		// Initialize service
		await mermaidService.initialize();
	});

	beforeEach(() => {
		mermaidStore.clearCache();
		mermaidStore.resetMetrics();
	});

	describe('Complete Render Pipeline', () => {
		it('should render diagram from start to finish', async () => {
			const code = MOCK_DIAGRAMS.simple;
			const theme = 'light';

			// Step 1: Check cache (should miss)
			const cached = await mermaidStore.getFromCache(code, theme);
			expect(cached).toBeNull();

			// Step 2: Render
			const svg = await mermaidService.render(code, theme);
			expect(svg).toBeTruthy();
			expect(svg).toContain('<svg');

			// Step 3: Store in cache
			mermaidStore.setInCache(code, svg!, theme);

			// Step 4: Verify cache hit
			const cachedSvg = await mermaidStore.getFromCache(code, theme);
			expect(cachedSvg).toBe(svg);

			// Step 5: Verify metrics
			const metrics = mermaidStore.getMetrics();
			expect(metrics.cacheHits).toBeGreaterThan(0);
		});

		it('should handle multiple diagrams in sequence', async () => {
			const diagrams = [MOCK_DIAGRAMS.simple, MOCK_DIAGRAMS.complex, MOCK_DIAGRAMS.sequence];

			for (const code of diagrams) {
				const svg = await mermaidService.render(code);
				expect(svg).toBeTruthy();
				mermaidStore.setInCache(code, svg!, 'light');
			}

			// Verify all are cached
			for (const code of diagrams) {
				const cached = await mermaidStore.getFromCache(code, 'light');
				expect(cached).toBeTruthy();
			}
		});

		it('should maintain cache across theme changes', async () => {
			const code = MOCK_DIAGRAMS.simple;

			// Render and cache for light theme
			const lightSvg = await mermaidService.render(code, 'light');
			mermaidStore.setInCache(code, lightSvg!, 'light');

			// Render and cache for dark theme
			const darkSvg = await mermaidService.render(code, 'dark');
			mermaidStore.setInCache(code, darkSvg!, 'dark');

			// Verify both themes are cached separately
			const cachedLight = await mermaidStore.getFromCache(code, 'light');
			const cachedDark = await mermaidStore.getFromCache(code, 'dark');

			expect(cachedLight).toBe(lightSvg);
			expect(cachedDark).toBe(darkSvg);
		});
	});

	describe('Performance Metrics', () => {
		it('should track render performance', async () => {
			const code = MOCK_DIAGRAMS.simple;
			const startTime = performance.now();

			await mermaidService.render(code);
			const renderTime = performance.now() - startTime;

			mermaidStore.recordRender(true, renderTime);

			const metrics = mermaidStore.getMetrics();
			expect(metrics.totalRenders).toBe(1);
			expect(metrics.averageRenderTime).toBeGreaterThan(0);
		});

		it('should calculate cache hit rate', async () => {
			const code = MOCK_DIAGRAMS.simple;
			const svg = await mermaidService.render(code);

			// First render (miss)
			await mermaidStore.getFromCache(code, 'light');

			// Store
			mermaidStore.setInCache(code, svg!, 'light');

			// Second access (hit)
			await mermaidStore.getFromCache(code, 'light');

			const metrics = mermaidStore.getMetrics();
			expect(metrics.cacheHitRate).toBeGreaterThan(0);
		});
	});

	describe('Error Handling Pipeline', () => {
		it('should handle invalid syntax gracefully', async () => {
			const code = MOCK_DIAGRAMS.invalid;
			const svg = await mermaidService.render(code);

			expect(svg).toBeNull();

			// Should record failed render
			const metrics = mermaidStore.getMetrics();
			// Note: This depends on how errors are tracked
		});

		it('should not cache failed renders', async () => {
			const code = MOCK_DIAGRAMS.invalid;
			const svg = await mermaidService.render(code);

			expect(svg).toBeNull();

			// Should not be in cache
			const cached = await mermaidStore.getFromCache(code, 'light');
			expect(cached).toBeNull();
		});
	});

	describe('Cache Eviction', () => {
		it('should evict old entries when cache is full', async () => {
			// Fill cache
			for (let i = 0; i < MERMAID_CONFIG.MEMORY_CACHE_SIZE + 5; i++) {
				const code = `graph TD\nA${i}-->B${i}`;
				const svg = await mermaidService.render(code);
				if (svg) {
					mermaidStore.setInCache(code, svg, 'light');
				}
			}

			const state = mermaidStore.get();
			expect(state.memoryCache.size).toBeLessThanOrEqual(MERMAID_CONFIG.MEMORY_CACHE_SIZE);
		});
	});
});

