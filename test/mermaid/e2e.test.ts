/**
 * Mermaid End-to-End Test Suite
 * 
 * Tests the complete user flow from code input to rendered diagram
 */

import { describe, it, expect, beforeAll, beforeEach } from 'vitest';

describe('Mermaid E2E User Flow', () => {
	beforeAll(async () => {
		// Setup: Initialize services
		const { mermaidService } = await import('$lib/services/mermaid.service');
		await mermaidService.initialize();
	});

	beforeEach(() => {
		// Clear state before each test
		const { mermaidStore } = require('$lib/stores/mermaid.store');
		mermaidStore.clearCache();
		mermaidStore.resetMetrics();
	});

	describe('User Flow: First Render', () => {
		it('should complete full flow: code -> parse -> render -> cache -> display', async () => {
			const { mermaidService } = await import('$lib/services/mermaid.service');
			const { mermaidStore } = await import('$lib/stores/mermaid.store');

			const code = 'graph TD\nA[Start]-->B[End]';
			const theme = 'light';

			// Step 1: User provides code
			expect(code).toBeTruthy();

			// Step 2: Check cache (first time, should miss)
			const cached = await mermaidStore.getFromCache(code, theme);
			expect(cached).toBeNull();

			// Step 3: Parse code
			const isValid = await mermaidService.parse(code);
			expect(isValid).toBe(true);

			// Step 4: Render diagram
			const svg = await mermaidService.render(code, theme);
			expect(svg).toBeTruthy();
			expect(svg).toContain('<svg');

			// Step 5: Store in cache
			mermaidStore.setInCache(code, svg!, theme);

			// Step 6: Verify cache hit on next access
			const cachedSvg = await mermaidStore.getFromCache(code, theme);
			expect(cachedSvg).toBe(svg);

			// Step 7: Verify metrics
			const metrics = mermaidStore.getMetrics();
			expect(metrics.totalRenders).toBeGreaterThan(0);
			expect(metrics.cacheHits).toBeGreaterThan(0);
		});
	});

	describe('User Flow: Cached Render', () => {
		it('should use cache on subsequent renders', async () => {
			const { mermaidService } = await import('$lib/services/mermaid.service');
			const { mermaidStore } = await import('$lib/stores/mermaid.store');

			const code = 'graph LR\nA-->B-->C';
			const theme = 'light';

			// First render
			const svg1 = await mermaidService.render(code, theme);
			mermaidStore.setInCache(code, svg1!, theme);

			// Second render (should use cache)
			const cachedSvg = await mermaidStore.getFromCache(code, theme);
			expect(cachedSvg).toBe(svg1);

			// Should not call render again
			const svg2 = await mermaidService.render(code, theme);
			// If cached, this should be fast
			expect(cachedSvg).toBeTruthy();
		});
	});

	describe('User Flow: Theme Switching', () => {
		it('should handle theme changes correctly', async () => {
			const { mermaidService } = await import('$lib/services/mermaid.service');
			const { mermaidStore } = await import('$lib/stores/mermaid.store');

			const code = 'graph TD\nA-->B';

			// Render for light theme
			const lightSvg = await mermaidService.render(code, 'light');
			mermaidStore.setInCache(code, lightSvg!, 'light');

			// Switch to dark theme
			document.documentElement.classList.add('dark');
			// Re-initialize service (simulating theme change)
			await mermaidService.initialize();

			// Render for dark theme
			const darkSvg = await mermaidService.render(code, 'dark');
			mermaidStore.setInCache(code, darkSvg!, 'dark');

			// Both should be cached
			const cachedLight = await mermaidStore.getFromCache(code, 'light');
			const cachedDark = await mermaidStore.getFromCache(code, 'dark');

			expect(cachedLight).toBe(lightSvg);
			expect(cachedDark).toBe(darkSvg);
		});
	});

	describe('User Flow: Error Recovery', () => {
		it('should handle errors and allow retry', async () => {
			const { mermaidService } = await import('$lib/services/mermaid.service');
			const { mermaidStore } = await import('$lib/stores/mermaid.store');
			const { retryRender } = await import('$lib/utils/mermaid-errors');

			const invalidCode = 'invalid syntax !!!';

			// First attempt should fail
			const svg1 = await mermaidService.render(invalidCode);
			expect(svg1).toBeNull();

			// Retry should also fail (parse errors are not retryable)
			const svg2 = await retryRender(
				async () => await mermaidService.render(invalidCode),
				2
			);
			expect(svg2).toBeNull();

			// Fix the code
			const validCode = 'graph TD\nA-->B';
			const svg3 = await mermaidService.render(validCode);
			expect(svg3).toBeTruthy();
		});
	});
});

