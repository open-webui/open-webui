type UmamiPayload = Record<string, unknown>;

const getUmami = () => {
	if (typeof window === 'undefined') {
		return null;
	}

	return window.umami ?? null;
};

export const identifyUmamiUser = (userId: string, data?: UmamiPayload) => {
	if (!userId) {
		return;
	}

	const umami = getUmami();
	if (!umami?.identify) {
		return;
	}

	if (data) {
		umami.identify(userId, data);
		return;
	}

	umami.identify(userId);
};

export const trackUmamiEvent = (eventName: string, data?: UmamiPayload) => {
	if (!eventName) {
		return;
	}

	const umami = getUmami();
	if (!umami?.track) {
		return;
	}

	if (data) {
		umami.track(eventName, data);
		return;
	}

	umami.track(eventName);
};
