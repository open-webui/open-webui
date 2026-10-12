export const acquireWakeLock = () => {
	if (typeof navigator === 'undefined' || !('wakeLock' in navigator)) return () => {};

	let lock: WakeLockSentinel | null = null;
	let stopped = false;
	let pending = false;

	const request = async () => {
		if (stopped || pending || (lock && !lock.released) || document.visibilityState !== 'visible')
			return;
		pending = true;
		try {
			const acquired = await navigator.wakeLock.request('screen');
			// Cleanup can run while the browser is still granting the lock.
			if (stopped) await acquired.release();
			else lock = acquired;
		} catch (error) {
			console.log('Wake Lock request failed:', error);
		} finally {
			pending = false;
		}
	};

	document.addEventListener('visibilitychange', request);
	void request();
	return () => {
		stopped = true;
		document.removeEventListener('visibilitychange', request);
		void lock?.release().catch((error) => console.log('Wake Lock release failed:', error));
		lock = null;
	};
};
