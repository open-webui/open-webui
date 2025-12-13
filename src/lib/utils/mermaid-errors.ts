/**
 * Mermaid Error Handling Utilities
 * 
 * Provides error classification, user-friendly messages, and retry logic
 * for Mermaid diagram rendering errors.
 */

export type MermaidErrorType =
	| 'parse-error'
	| 'render-error'
	| 'initialization-error'
	| 'timeout-error'
	| 'cache-error'
	| 'unknown-error';

export interface MermaidError {
	type: MermaidErrorType;
	message: string;
	originalError?: Error;
	codePreview?: string;
	timestamp: number;
}

/**
 * Classify error type based on error message
 */
export function classifyError(error: Error | string): MermaidErrorType {
	const errorMessage = typeof error === 'string' ? error.toLowerCase() : error.message.toLowerCase();

	if (errorMessage.includes('parse') || errorMessage.includes('syntax')) {
		return 'parse-error';
	}
	if (errorMessage.includes('render') || errorMessage.includes('svg')) {
		return 'render-error';
	}
	if (errorMessage.includes('timeout') || errorMessage.includes('exceeded')) {
		return 'timeout-error';
	}
	if (errorMessage.includes('initialize') || errorMessage.includes('init')) {
		return 'initialization-error';
	}
	if (errorMessage.includes('cache') || errorMessage.includes('indexeddb')) {
		return 'cache-error';
	}

	return 'unknown-error';
}

/**
 * Get user-friendly error message
 */
export function getUserMessage(errorType: MermaidErrorType): string {
	switch (errorType) {
		case 'parse-error':
			return 'Invalid Mermaid syntax. Please check your diagram code.';
		case 'render-error':
			return 'Failed to render diagram. Showing code instead.';
		case 'timeout-error':
			return 'Diagram rendering timed out. Try simplifying the diagram.';
		case 'initialization-error':
			return 'Mermaid service unavailable. Please refresh the page.';
		case 'cache-error':
			return 'Cache error occurred. Diagram will be re-rendered.';
		case 'unknown-error':
		default:
			return 'An error occurred while rendering the diagram.';
	}
}

/**
 * Check if error is retryable
 */
export function isRetryableError(errorType: MermaidErrorType): boolean {
	// Don't retry parse errors (syntax won't change)
	// Don't retry initialization errors (needs page refresh)
	// Retry transient errors
	return errorType === 'timeout-error' || errorType === 'render-error' || errorType === 'cache-error';
}

/**
 * Retry render with exponential backoff
 */
export async function retryRender(
	renderFn: () => Promise<string | null>,
	maxRetries: number = 2,
	initialDelay: number = 100
): Promise<string | null> {
	let lastError: Error | null = null;

	for (let attempt = 0; attempt <= maxRetries; attempt++) {
		try {
			const result = await renderFn();
			if (result) {
				if (attempt > 0) {
					console.log(`[Mermaid] Retry successful after ${attempt} attempts`);
				}
				return result;
			}
			// If renderFn returns null, treat as error
			throw new Error('Render returned null');
		} catch (error) {
			lastError = error instanceof Error ? error : new Error(String(error));
			const errorType = classifyError(lastError);
			
			if (!isRetryableError(errorType)) {
				console.log(`[Mermaid] Error not retryable: ${errorType}, stopping retries`);
				break;
			}

			if (attempt < maxRetries) {
				const delay = initialDelay * Math.pow(2, attempt);
				console.log(`[Mermaid] Retry attempt ${attempt + 1}/${maxRetries}: ${lastError.message} (waiting ${delay}ms)`);
				await new Promise((resolve) => setTimeout(resolve, delay));
			} else {
				console.log(`[Mermaid] Retry failed after ${maxRetries} attempts: ${lastError.message}`);
			}
		}
	}

	return null;
}

/**
 * Create MermaidError object
 */
export function createMermaidError(
	error: Error | string,
	codePreview?: string
): MermaidError {
	const errorMessage = typeof error === 'string' ? error : error.message;
	const originalError = typeof error === 'string' ? undefined : error;
	const errorType = classifyError(error);

	console.log(`[Mermaid] Error classified: type=${errorType}, message=${errorMessage}`);

	return {
		type: errorType,
		message: errorMessage,
		originalError,
		codePreview,
		timestamp: Date.now()
	};
}

