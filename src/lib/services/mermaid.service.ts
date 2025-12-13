import { browser } from '$app/environment';
import mermaid from 'mermaid';
import { v4 as uuidv4 } from 'uuid';
import { MERMAID_CONFIG } from '$lib/constants';

/**
 * MermaidService - Singleton service for Mermaid diagram rendering
 * 
 * Provides centralized Mermaid initialization, rendering, and theme management.
 * Ensures only one Mermaid instance exists globally for maximum performance.
 */
class MermaidService {
	private static instance: MermaidService | null = null;
	private initialized = false;
	private currentTheme: 'dark' | 'light' = 'light';
	private themeObserver: MutationObserver | null = null;

	private constructor() {
		// Private constructor for singleton pattern
	}

	/**
	 * Get singleton instance
	 */
	static getInstance(): MermaidService {
		if (!MermaidService.instance) {
			MermaidService.instance = new MermaidService();
		}
		return MermaidService.instance;
	}

	/**
	 * Initialize Mermaid with theme detection
	 */
	async initialize(): Promise<void> {
		if (!browser) {
			console.warn('[Mermaid] Service: Not in browser environment, skipping initialization');
			return;
		}

		if (this.initialized) {
			console.log('[Mermaid] Service: Already initialized, skipping');
			return;
		}

		try {
			// Detect current theme
			this.currentTheme = this.detectTheme();
			
			// Initialize Mermaid
			mermaid.initialize({
				startOnLoad: false, // Disable auto-rendering
				theme: this.currentTheme,
				securityLevel: 'loose',
				maxTextSize: 50000,
				maxEdges: 1000
			});

			this.initialized = true;
			console.log(`[Mermaid] Service initialized with theme: ${this.currentTheme}`);

			// Watch for theme changes
			this.setupThemeObserver();
		} catch (error) {
			console.error('[Mermaid] Service: Initialization failed:', error);
			throw error;
		}
	}

	/**
	 * Detect current theme from document
	 */
	private detectTheme(): 'dark' | 'light' {
		if (!browser) return 'light';
		return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
	}

	/**
	 * Setup MutationObserver to watch for theme changes
	 */
	private setupThemeObserver(): void {
		if (!browser) return;

		this.themeObserver = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
					const newTheme = this.detectTheme();
					if (newTheme !== this.currentTheme) {
						const oldTheme = this.currentTheme;
						this.currentTheme = newTheme;
						console.log(`[Mermaid] Theme changed: ${oldTheme} → ${newTheme}, re-initializing`);
						this.reinitialize();
					}
				}
			}
		});

		this.themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});
	}

	/**
	 * Re-initialize Mermaid with new theme
	 */
	private async reinitialize(): Promise<void> {
		try {
			mermaid.initialize({
				startOnLoad: false,
				theme: this.currentTheme,
				securityLevel: 'loose',
				maxTextSize: 50000,
				maxEdges: 1000
			});
			console.log(`[Mermaid] Re-initialized Mermaid for theme change`);
		} catch (error) {
			console.error('[Mermaid] Re-initialization failed:', error);
		}
	}

	/**
	 * Cleanup theme observer
	 */
	destroy(): void {
		if (this.themeObserver) {
			this.themeObserver.disconnect();
			this.themeObserver = null;
		}
		this.initialized = false;
	}

	/**
	 * Check if service is initialized
	 */
	isInitialized(): boolean {
		return this.initialized;
	}

	/**
	 * Get current theme
	 */
	getTheme(): 'dark' | 'light' {
		return this.currentTheme;
	}

	/**
	 * Parse Mermaid code to validate syntax
	 */
	async parse(code: string): Promise<boolean> {
		if (!this.initialized) {
			console.warn('[Mermaid] Service: Not initialized, cannot parse');
			return false;
		}

		try {
			const isValid = await mermaid.parse(code);
			if (!isValid) {
				console.log(`[Mermaid] Parse error: Invalid syntax (code preview: ${code.substring(0, 50)}...)`);
			}
			return isValid;
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.error(`[Mermaid] Parse error: ${errorMessage} (code preview: ${code.substring(0, 50)}...)`);
			return false;
		}
	}

	/**
	 * Render Mermaid diagram to SVG
	 */
	async render(code: string, theme?: 'dark' | 'light'): Promise<string | null> {
		if (!this.initialized) {
			console.warn('[Mermaid] Service: Not initialized, cannot render');
			return null;
		}

		const renderTheme = theme || this.currentTheme;
		const renderId = `mermaid-${uuidv4()}`;
		const startTime = performance.now();

		try {
			console.log(`[Mermaid] Rendering diagram: id=${renderId}, codeLength=${code.length}, theme=${renderTheme}`);

			// Parse first
			const isValid = await this.parse(code);
			if (!isValid) {
				console.error(`[Mermaid] Render error: Invalid syntax (id: ${renderId})`);
				return null;
			}

			// Render SVG
			const { svg } = await mermaid.render(renderId, code);
			const duration = performance.now() - startTime;

			console.log(`[Mermaid] Render completed: id=${renderId}, duration=${duration.toFixed(2)}ms`);

			// Performance warning
			if (duration > MERMAID_CONFIG.SLOW_RENDER_WARNING_MS) {
				console.warn(
					`[Mermaid] Performance warning: Render took ${duration.toFixed(2)}ms (threshold: ${MERMAID_CONFIG.SLOW_RENDER_WARNING_MS}ms)`
				);
			}

			return svg;
		} catch (error) {
			const duration = performance.now() - startTime;
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.error(
				`[Mermaid] Render error: ${errorMessage} (id: ${renderId}, duration: ${duration.toFixed(2)}ms, code: ${code.substring(0, 50)}...)`
			);
			return null;
		}
	}
}

// Export singleton instance
export const mermaidService = MermaidService.getInstance();

