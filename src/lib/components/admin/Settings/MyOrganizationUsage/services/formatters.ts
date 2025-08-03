/**
 * Data formatting utilities
 * Currency and number formatting for international display
 */

export class FormatterService {
	/**
	 * Format currency with proper locale support
	 */
	static formatCurrency(amount: number, currency: 'USD' | 'PLN' = 'USD'): string {
		const value = amount || 0;
		const currencyOptions = currency === 'PLN' 
			? { style: 'currency' as const, currency: 'PLN' }
			: { style: 'currency' as const, currency: 'USD' };
			
		// For very small USD amounts, show more decimal places
		if (value > 0 && value < 0.01 && currency === 'USD') {
			return new Intl.NumberFormat('en-US', {
				...currencyOptions,
				minimumFractionDigits: 6,
				maximumFractionDigits: 6
			}).format(value);
		}
		
		return new Intl.NumberFormat(currency === 'PLN' ? 'pl-PL' : 'en-US', currencyOptions).format(value);
	}

	/**
	 * Format dual currency display (USD with PLN in parentheses)
	 */
	static formatDualCurrency(usdAmount: number, plnAmount?: number): string {
		if (plnAmount !== undefined && plnAmount !== null) {
			return `${this.formatCurrency(usdAmount)} (${this.formatCurrency(plnAmount, 'PLN')})`;
		}
		// Fallback to USD only if PLN not available
		return this.formatCurrency(usdAmount);
	}

	/**
	 * Format estimated currency with tilde prefix for live data
	 */
	static formatEstimatedCurrency(usdAmount: number, plnAmount?: number): string {
		const formattedCurrency = this.formatDualCurrency(usdAmount, plnAmount);
		return `~${formattedCurrency}`;
	}

	/**
	 * Format numbers with proper thousand separators
	 */
	static formatNumber(number: number): string {
		return new Intl.NumberFormat('en-US').format(number || 0);
	}

	/**
	 * Format percentage with proper rounding
	 */
	static formatPercentage(value: number): string {
		return `${Math.round(value || 0)}%`;
	}

	/**
	 * Format date for display
	 */
	static formatDate(dateString: string): string {
		if (!dateString || dateString === 'N/A') return 'N/A';
		
		try {
			const date = new Date(dateString);
			return date.toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric'
			});
		} catch {
			return dateString; // Return original if parsing fails
		}
	}

	/**
	 * Format token count with appropriate units
	 */
	static formatTokens(tokens: number): string {
		if (tokens >= 1000000) {
			return `${(tokens / 1000000).toFixed(1)}M tokens`;
		} else if (tokens >= 1000) {
			return `${(tokens / 1000).toFixed(1)}K tokens`;
		}
		return `${this.formatNumber(tokens)} tokens`;
	}

	/**
	 * Format model name for display (shorten if needed)
	 */
	static formatModelName(modelName: string, maxLength: number = 30): string {
		if (!modelName || modelName === 'N/A') return 'N/A';
		
		if (modelName.length <= maxLength) return modelName;
		
		return `${modelName.substring(0, maxLength - 3)}...`;
	}

	/**
	 * Format time for display
	 */
	static formatTime(timeString: string): string {
		if (!timeString || timeString === 'N/A') return 'N/A';
		
		try {
			const time = new Date(timeString);
			return time.toLocaleTimeString('en-US', {
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch {
			return timeString; // Return original if parsing fails
		}
	}
}