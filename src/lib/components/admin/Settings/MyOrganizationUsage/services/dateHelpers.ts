/**
 * Date utilities for handling live vs historical data differentiation
 */

export class DateHelperService {
	/**
	 * Check if a date string matches today's date
	 */
	static isToday(dateString: string): boolean {
		if (!dateString || dateString === 'N/A') return false;
		
		try {
			const inputDate = new Date(dateString);
			const today = new Date();
			
			// Compare YYYY-MM-DD parts only
			return (
				inputDate.getFullYear() === today.getFullYear() &&
				inputDate.getMonth() === today.getMonth() &&
				inputDate.getDate() === today.getDate()
			);
		} catch {
			return false;
		}
	}

	/**
	 * Get current date in YYYY-MM-DD format
	 */
	static getCurrentDateString(): string {
		const today = new Date();
		return today.toISOString().split('T')[0];
	}

	/**
	 * Format date with live indicator for current day
	 */
	static formatDateWithLiveIndicator(dateString: string): string {
		if (!dateString || dateString === 'N/A') return 'N/A';
		
		if (this.isToday(dateString)) {
			return 'Today (live)';
		}
		
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
	 * Check if data is from current day (for styling purposes)
	 */
	static isLiveData(dateString: string): boolean {
		return this.isToday(dateString);
	}
}