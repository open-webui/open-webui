type DisclaimerConfig = {
	ui?: {
		user_disclaimer_content?: string;
		user_disclaimer_version?: string;
	};
};

type DisclaimerSettings = {
	userDisclaimerVersion?: string;
	userDisclaimerAcknowledgedAt?: number | null;
};

/**
 * Whether the configured disclaimer still needs this user's acknowledgement.
 *
 * Empty content disables the disclaimer entirely. Otherwise the user is prompted
 * whenever the version they last acknowledged differs from the configured one, so
 * changing the version re-prompts everybody. A user who has never acknowledged has
 * no stored version at all, which is distinct from having acknowledged the default
 * empty version.
 */
export const shouldShowUserDisclaimer = (
	config?: DisclaimerConfig | null,
	settings?: DisclaimerSettings | null
): boolean => {
	if ((config?.ui?.user_disclaimer_content ?? '').trim() === '') {
		return false;
	}

	return (settings?.userDisclaimerVersion ?? null) !== (config?.ui?.user_disclaimer_version ?? '');
};
