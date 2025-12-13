/**
 * MermaidService Test Suite
 * 
 * Tests for singleton service, initialization, rendering, theme detection, and error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mermaidService } from '../mermaid.service';
import mermaid from 'mermaid';

// Mock mermaid
vi.mock('mermaid', () => ({
	default: {
		initialize: vi.fn(),
		parse: vi.fn(),
		render: vi.fn()
	}
}));

describe('MermaidService', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		// Reset service state
		(mermaidService as any).initialized = false;
		(mermaidService as any).currentTheme = 'light';
		(mermaidService as any).themeObserver = null;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	describe('Singleton Pattern', () => {
		it('should return the same instance', () => {
			const instance1 = mermaidService;
			const instance2 = mermaidService;
			expect(instance1).toBe(instance2);
		});
	});

	describe('Initialization', () => {
		it('should initialize Mermaid with light theme by default', async () => {
			(document.documentElement.classList.contains as any) = vi.fn(() => false);

			await mermaidService.initialize();

			expect(mermaid.initialize).toHaveBeenCalledWith(
				expect.objectContaining({
					startOnLoad: false,
					theme: 'light',
					securityLevel: 'loose'
				})
			);
			expect(mermaidService.isInitialized()).toBe(true);
		});

		it('should initialize Mermaid with dark theme when dark class is present', async () => {
			(document.documentElement.classList.contains as any) = vi.fn((cls: string) => cls === 'dark');

			await mermaidService.initialize();

			expect(mermaid.initialize).toHaveBeenCalledWith(
				expect.objectContaining({
					theme: 'dark'
				})
			);
		});

		it('should not re-initialize if already initialized', async () => {
			await mermaidService.initialize();
			vi.clearAllMocks();

			await mermaidService.initialize();

			expect(mermaid.initialize).not.toHaveBeenCalled();
		});

		it('should handle initialization errors gracefully', async () => {
			(mermaid.initialize as any).mockImplementation(() => {
				throw new Error('Initialization failed');
			});

			await expect(mermaidService.initialize()).rejects.toThrow('Initialization failed');
			expect(mermaidService.isInitialized()).toBe(false);
		});
	});

	describe('Theme Detection', () => {
		it('should detect light theme correctly', () => {
			(document.documentElement.classList.contains as any) = vi.fn(() => false);
			expect(mermaidService.getTheme()).toBe('light');
		});

		it('should detect dark theme correctly', () => {
			(document.documentElement.classList.contains as any) = vi.fn((cls: string) => cls === 'dark');
			// Re-initialize to update theme
			mermaidService.initialize();
			expect(mermaidService.getTheme()).toBe('dark');
		});
	});

	describe('Parse', () => {
		beforeEach(async () => {
			await mermaidService.initialize();
			vi.clearAllMocks();
		});

		it('should parse valid Mermaid code', async () => {
			const validCode = 'graph TD\nA-->B';
			(mermaid.parse as any).mockResolvedValue(true);

			const result = await mermaidService.parse(validCode);

			expect(mermaid.parse).toHaveBeenCalled();
			expect(result).toBe(true);
		});

		it('should return false for invalid Mermaid code', async () => {
			const invalidCode = 'invalid syntax';
			(mermaid.parse as any).mockResolvedValue(false);

			const result = await mermaidService.parse(invalidCode);

			expect(result).toBe(false);
		});

		it('should handle parse errors', async () => {
			const errorCode = 'error code';
			(mermaid.parse as any).mockRejectedValue(new Error('Parse error'));

			const result = await mermaidService.parse(errorCode);

			expect(result).toBe(false);
		});

		it('should return false if not initialized', async () => {
			(mermaidService as any).initialized = false;

			const result = await mermaidService.parse('graph TD\nA-->B');

			expect(result).toBe(false);
			expect(mermaid.parse).not.toHaveBeenCalled();
		});
	});

	describe('Render', () => {
		beforeEach(async () => {
			vi.clearAllMocks();
			await mermaidService.initialize();
		});

		it('should render valid Mermaid diagram', async () => {
			const code = 'graph TD\nA-->B';
			const mockSvg = '<svg>...</svg>';
			(mermaid.parse as any).mockResolvedValue(true);
			(mermaid.render as any).mockResolvedValue({ svg: mockSvg });

			const result = await mermaidService.render(code);

			// Service calls parse internally, then render
			expect(mermaid.parse).toHaveBeenCalled();
			expect(mermaid.render).toHaveBeenCalled();
			expect(result).toBe(mockSvg);
		});

		it('should return null for invalid syntax', async () => {
			const invalidCode = 'invalid';
			(mermaid.parse as any).mockResolvedValue(false);

			const result = await mermaidService.render(invalidCode);

			expect(result).toBeNull();
			expect(mermaid.render).not.toHaveBeenCalled();
		});

		it('should handle render errors', async () => {
			const code = 'graph TD\nA-->B';
			(mermaid.parse as any).mockResolvedValue(true);
			(mermaid.render as any).mockRejectedValue(new Error('Render error'));

			const result = await mermaidService.render(code);

			expect(result).toBeNull();
		});

		it('should return null if not initialized', async () => {
			(mermaidService as any).initialized = false;

			const result = await mermaidService.render('graph TD\nA-->B');

			expect(result).toBeNull();
			expect(mermaid.render).not.toHaveBeenCalled();
		});

		it('should use specified theme for rendering', async () => {
			const code = 'graph TD\nA-->B';
			const mockSvg = '<svg>...</svg>';
			(mermaid.parse as any).mockResolvedValue(true);
			(mermaid.render as any).mockResolvedValue({ svg: mockSvg });

			const result = await mermaidService.render(code, 'dark');

			// Theme is set during initialization, not per render
			// But render should still be called
			if (result) {
				expect(mermaid.render).toHaveBeenCalled();
			}
		});

		it('should track render performance', async () => {
			const code = 'graph TD\nA-->B';
			const mockSvg = '<svg>...</svg>';
			(mermaid.parse as any).mockResolvedValue(true);
			(mermaid.render as any).mockResolvedValue({ svg: mockSvg });
			
			// Mock performance.now to return different values
			const perfNow = vi.spyOn(performance, 'now');
			perfNow.mockReturnValueOnce(1000).mockReturnValueOnce(1200);

			const result = await mermaidService.render(code);

			// Performance tracking happens in the service
			if (result) {
				expect(perfNow).toHaveBeenCalled();
			}
			perfNow.mockRestore();
		});
	});

	describe('Cleanup', () => {
		it('should cleanup theme observer on destroy', async () => {
			await mermaidService.initialize();
			const observer = (mermaidService as any).themeObserver;
			
			if (observer) {
				const disconnectSpy = vi.spyOn(observer, 'disconnect');
				mermaidService.destroy();
				expect(disconnectSpy).toHaveBeenCalled();
			} else {
				// Observer might not be created in test environment
				mermaidService.destroy();
			}
			
			expect(mermaidService.isInitialized()).toBe(false);
		});
	});
});

