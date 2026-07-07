export const getAvailableFeatureToggleState = (enabled: boolean, available: unknown) =>
	available ? enabled : false;
