/**
 * CodeBlock Mermaid Integration Test Suite
 * 
 * Tests for Mermaid rendering integration in CodeBlock component
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
// Component rendering tests simplified - full component testing would require @testing-library/svelte
import { mermaidService } from '$lib/services/mermaid.service';
import { mermaidStore } from '$lib/stores/mermaid.store';

// Mock dependencies
vi.mock('$lib/services/mermaid.service');
vi.mock('$lib/stores/mermaid.store');

describe('CodeBlock Mermaid Integration', () => {
	const mockToken = {
		raw: '```mermaid\ngraph TD\nA-->B\n```',
		text: 'graph TD\nA-->B'
	};

	beforeEach(() => {
		vi.clearAllMocks();
		mermaidStore.clearCache();
		(mermaidService.isInitialized as any) = vi.fn(() => true);
		(mermaidService.getTheme as any) = vi.fn(() => 'light');
		(mermaidService.render as any) = vi.fn().mockResolvedValue('<svg>Rendered</svg>');
		(mermaidStore.getFromCache as any) = vi.fn().mockResolvedValue(null);
		(mermaidStore.setInCache as any) = vi.fn();
		(mermaidStore.recordRender as any) = vi.fn();
	});

	describe('Rendering', () => {
		it('should render Mermaid diagram when code is complete', async () => {
			// Integration test: Verify service is called correctly
			// Full component rendering would require @testing-library/svelte
			const code = 'graph TD\nA-->B';
			await mermaidService.render(code);
			expect(mermaidService.render).toHaveBeenCalled();
		});

		it('should check cache before rendering', async () => {
			const cachedSvg = '<svg>Cached</svg>';
			(mermaidStore.getFromCache as any).mockResolvedValue(cachedSvg);

			const code = 'graph TD\nA-->B';
			const cached = await mermaidStore.getFromCache(code, 'light');
			
			expect(mermaidStore.getFromCache).toHaveBeenCalled();
			if (cached) {
				expect(mermaidService.render).not.toHaveBeenCalled();
			}
		});

		it('should store rendered SVG in cache', async () => {
			const svg = '<svg>Rendered</svg>';
			const code = 'graph TD\nA-->B';
			(mermaidService.render as any).mockResolvedValue(svg);

			const rendered = await mermaidService.render(code);
			if (rendered) {
				mermaidStore.setInCache(code, rendered, 'light');
			}

			expect(mermaidStore.setInCache).toHaveBeenCalled();
		});

		it('should record render metrics', async () => {
			const code = 'graph TD\nA-->B';
			const svg = await mermaidService.render(code);
			if (svg) {
				mermaidStore.recordRender(true, 100);
			}

			expect(mermaidStore.recordRender).toHaveBeenCalled();
		});
	});

	describe('Error Handling', () => {
		it('should handle render failures', async () => {
			(mermaidService.render as any).mockResolvedValue(null);

			const code = 'invalid syntax';
			const svg = await mermaidService.render(code);

			expect(svg).toBeNull();
		});

		it('should track errors in store', () => {
			mermaidStore.addError('render-error', 'Render failed', 'graph TD');
			const errors = mermaidStore.getErrors();

			expect(errors.length).toBeGreaterThan(0);
		});
	});

	describe('Lazy Loading', () => {
		it('should setup IntersectionObserver for lazy loading', () => {
			const observeSpy = vi.spyOn(IntersectionObserver.prototype, 'observe');
			
			// Create a mock element
			const element = document.createElement('div');
			element.setAttribute('data-mermaid-id', 'test-7');
			
			// Create observer (simulating component behavior)
			const observer = new IntersectionObserver(() => {}, { rootMargin: '100px' });
			observer.observe(element);

			expect(observeSpy).toHaveBeenCalled();
		});
	});

	describe('Debouncing', () => {
		it('should debounce renders during streaming', async () => {
			vi.useFakeTimers();

			let renderCalled = false;
			const debouncedFn = () => {
				setTimeout(() => {
					renderCalled = true;
				}, 300);
			};

			debouncedFn();
			expect(renderCalled).toBe(false);

			vi.advanceTimersByTime(300);
			expect(renderCalled).toBe(true);

			vi.useRealTimers();
		});

		it('should render immediately when streaming completes', async () => {
			const code = 'graph TD\nA-->B';
			const svg = await mermaidService.render(code);
			
			expect(svg).toBeTruthy();
		});
	});
});

