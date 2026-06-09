export const getUserPosition = async (raw = false) => {
	const position = await new Promise<GeolocationPosition>((resolve, reject) => {
		if (!('geolocation' in navigator)) {
			reject(new Error('Geolocation is not supported by this browser'));
			return;
		}
		navigator.geolocation.getCurrentPosition(resolve, reject, {
			timeout: 5000,
			maximumAge: 60_000,
			enableHighAccuracy: false
		});
	}).catch((error) => {
		console.error('Error getting user location:', error);
		throw error;
	});

	if (!position) {
		return 'Location not available';
	}

	const { latitude, longitude } = position.coords;

	if (raw) {
		return { latitude, longitude };
	} else {
		return `${latitude.toFixed(3)}, ${longitude.toFixed(3)} (lat, long)`;
	}
};
