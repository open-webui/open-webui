export const WEB_SPEECH_INACTIVITY_TIMEOUT_MS = 5000;

type WebSpeechInactivityControllerOptions = {
	stop: () => void;
	timeoutMs?: number;
};

export const createWebSpeechInactivityController = ({
	stop,
	timeoutMs = WEB_SPEECH_INACTIVITY_TIMEOUT_MS
}: WebSpeechInactivityControllerOptions) => {
	let timeoutId: ReturnType<typeof setTimeout> | null = null;

	const clear = () => {
		if (timeoutId !== null) {
			clearTimeout(timeoutId);
			timeoutId = null;
		}
	};

	const handleSpeechEnd = () => {
		clear();
		timeoutId = setTimeout(() => {
			timeoutId = null;
			stop();
		}, timeoutMs);
	};

	return {
		handleSpeechStart: clear,
		handleSpeechEnd,
		dispose: clear
	};
};
