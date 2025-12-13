/**
 * Mermaid Error Handling Utilities Test Suite
 */

import { describe, it, expect, vi } from 'vitest';
import {
	classifyError,
	getUserMessage,
	isRetryableError,
	retryRender,
	createMermaidError,
	type MermaidErrorType
} from '../mermaid-errors';

describe('Mermaid Error Utilities', () => {
	describe('classifyError', () => {
		it('should classify parse errors', () => {
			const error = new Error('Parse error: invalid syntax');
			expect(classifyError(error)).toBe('parse-error');
		});

		it('should classify render errors', () => {
			const error = new Error('Failed to render SVG');
			expect(classifyError(error)).toBe('render-error');
		});

		it('should classify timeout errors', () => {
			const error = new Error('Timeout exceeded');
			expect(classifyError(error)).toBe('timeout-error');
		});

		it('should classify initialization errors', () => {
			const error = new Error('Failed to initialize');
			expect(classifyError(error)).toBe('initialization-error');
		});

		it('should classify cache errors', () => {
			const error = new Error('IndexedDB cache error');
			expect(classifyError(error)).toBe('cache-error');
		});

		it('should classify unknown errors', () => {
			const error = new Error('Some random error');
			expect(classifyError(error)).toBe('unknown-error');
		});

		it('should handle string errors', () => {
			expect(classifyError('Parse error')).toBe('parse-error');
		});
	});

	describe('getUserMessage', () => {
		it('should return user-friendly message for parse errors', () => {
			expect(getUserMessage('parse-error')).toContain('syntax');
		});

		it('should return user-friendly message for render errors', () => {
			expect(getUserMessage('render-error')).toContain('render');
		});

		it('should return user-friendly message for timeout errors', () => {
			expect(getUserMessage('timeout-error')).toContain('timed out');
		});

		it('should return user-friendly message for initialization errors', () => {
			expect(getUserMessage('initialization-error')).toContain('refresh');
		});

		it('should return user-friendly message for cache errors', () => {
			expect(getUserMessage('cache-error')).toContain('Cache');
		});

		it('should return user-friendly message for unknown errors', () => {
			expect(getUserMessage('unknown-error')).toContain('error');
		});
	});

	describe('isRetryableError', () => {
		it('should return false for parse errors', () => {
			expect(isRetryableError('parse-error')).toBe(false);
		});

		it('should return false for initialization errors', () => {
			expect(isRetryableError('initialization-error')).toBe(false);
		});

		it('should return true for timeout errors', () => {
			expect(isRetryableError('timeout-error')).toBe(true);
		});

		it('should return true for render errors', () => {
			expect(isRetryableError('render-error')).toBe(true);
		});

		it('should return true for cache errors', () => {
			expect(isRetryableError('cache-error')).toBe(true);
		});
	});

	describe('retryRender', () => {
		it('should succeed on first attempt', async () => {
			const renderFn = vi.fn().mockResolvedValue('<svg>Success</svg>');

			const result = await retryRender(renderFn, 2);

			expect(result).toBe('<svg>Success</svg>');
			expect(renderFn).toHaveBeenCalledTimes(1);
		});

		it('should retry on failure', async () => {
			const renderFn = vi
				.fn()
				.mockRejectedValueOnce(new Error('Render error'))
				.mockResolvedValue('<svg>Success</svg>');

			const result = await retryRender(renderFn, 2);

			expect(result).toBe('<svg>Success</svg>');
			expect(renderFn).toHaveBeenCalledTimes(2);
		});

		it('should fail after max retries', async () => {
			const renderFn = vi.fn().mockRejectedValue(new Error('Render error'));

			const result = await retryRender(renderFn, 2);

			expect(result).toBeNull();
			expect(renderFn).toHaveBeenCalledTimes(3); // Initial + 2 retries
		});

		it('should not retry parse errors', async () => {
			const parseError = new Error('Parse error');
			const renderFn = vi.fn().mockRejectedValue(parseError);

			const result = await retryRender(renderFn, 2);

			expect(result).toBeNull();
			// Should only try once since parse errors are not retryable
			expect(renderFn).toHaveBeenCalledTimes(1);
		});

		it('should use exponential backoff', async () => {
			vi.useFakeTimers();
			const renderFn = vi
				.fn()
				.mockRejectedValueOnce(new Error('Render error'))
				.mockRejectedValueOnce(new Error('Render error'))
				.mockResolvedValue('<svg>Success</svg>');

			const promise = retryRender(renderFn, 2, 10);
			
			// Fast-forward timers
			await vi.advanceTimersByTimeAsync(30);
			await promise;

			expect(renderFn).toHaveBeenCalledTimes(3);
			vi.useRealTimers();
		});
	});

	describe('createMermaidError', () => {
		it('should create error object from Error instance', () => {
			const error = new Error('Test error');
			const mermaidError = createMermaidError(error, 'graph TD');

			expect(mermaidError.type).toBeDefined();
			expect(mermaidError.message).toBe('Test error');
			expect(mermaidError.codePreview).toBe('graph TD');
			expect(mermaidError.originalError).toBe(error);
			expect(mermaidError.timestamp).toBeGreaterThan(0);
		});

		it('should create error object from string', () => {
			const mermaidError = createMermaidError('String error', 'code');

			expect(mermaidError.message).toBe('String error');
			expect(mermaidError.originalError).toBeUndefined();
		});

		it('should classify error type automatically', () => {
			const error = new Error('Parse error: invalid');
			const mermaidError = createMermaidError(error);

			expect(mermaidError.type).toBe('parse-error');
		});
	});
});

