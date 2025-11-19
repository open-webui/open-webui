export const setTextScale = (scale) => {
	if (typeof document === 'undefined') {
		return;
	}

	console.log('setTextScale called with:', scale, 'from:', new Error().stack);
	document.documentElement.style.setProperty('--app-text-scale', `${scale}`);
};
