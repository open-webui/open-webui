export const setTextScale = (scale: number | string) => {
	if (typeof document === 'undefined') {
		return;
	}

	document.documentElement.style.setProperty('--app-text-scale', `${scale}`);
};
