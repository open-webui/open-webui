import { detectAndUpdateUserTimezone, getUserTimezoneFromSettings } from '$lib/apis/users';
import { getUserTimezone } from '$lib/utils';

/**
 * Service to handle timezone detection and user preferences
 */
export class TimezoneService {
	private static instance: TimezoneService;
	private userTimezone: string | null = null;

	private constructor() {}

	public static getInstance(): TimezoneService {
		if (!TimezoneService.instance) {
			TimezoneService.instance = new TimezoneService();
		}
		return TimezoneService.instance;
	}

	/**
	 * Initialize timezone detection for the authenticated user
	 * @param token - User authentication token
	 * @returns Promise<string> - The user's timezone
	 */
	public async initializeUserTimezone(token: string): Promise<string> {
		try {
			// First, try to get the user's stored timezone preference
			const storedTimezone = await getUserTimezoneFromSettings(token);

			if (storedTimezone) {
				this.userTimezone = storedTimezone;
				// console.log(`Using stored timezone: ${storedTimezone}`);
				return storedTimezone;
			}

			// If no stored timezone, detect and update
			const detectedTimezone = await detectAndUpdateUserTimezone(token);
			this.userTimezone = detectedTimezone;
			console.log(`Detected and stored timezone: ${detectedTimezone}`);
			return detectedTimezone;
		} catch (error) {
			console.error('Failed to initialize user timezone:', error);
			// Fallback to browser timezone without storing
			const browserTimezone = getUserTimezone();
			this.userTimezone = browserTimezone;
			return browserTimezone;
		}
	}

	/**
	 * Get the current user's timezone
	 * @returns string - User's timezone or fallback
	 */
	public getUserTimezone(): string {
		return this.userTimezone || getUserTimezone();
	}

	/**
	 * Update the user's timezone preference
	 * @param token - User authentication token
	 * @param timezone - New timezone preference
	 */
	public async updateUserTimezone(token: string, timezone: string): Promise<void> {
		const { updateUserTimezone } = await import('$lib/apis/users');
		await updateUserTimezone(token, timezone);
		this.userTimezone = timezone;
		console.log(`Updated user timezone to: ${timezone}`);
	}

	/**
	 * Detect if user's timezone has changed and update if necessary
	 * @param token - User authentication token
	 */
	public async checkAndUpdateTimezone(token: string): Promise<void> {
		try {
			const currentBrowserTimezone = getUserTimezone();
			const storedTimezone = await getUserTimezoneFromSettings(token);

			if (!storedTimezone || storedTimezone !== currentBrowserTimezone) {
				await this.updateUserTimezone(token, currentBrowserTimezone);
			}
		} catch (error) {
			console.error('Failed to check and update timezone:', error);
		}
	}

	/**
	 * Clear the cached timezone (used on logout)
	 */
	public clearTimezone(): void {
		this.userTimezone = null;
	}
}

// Export singleton instance
export const timezoneService = TimezoneService.getInstance();
