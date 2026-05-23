import { FLEX_AUTO_FLIP_API_BASE_URL } from '$lib/constants';

export type FlexAutoFlipConfig = {
	FLEX_AUTO_FLIP_ENABLED: boolean;
	FLEX_AUTO_FLIP_OFF_PEAK_START_HOUR: number;
	FLEX_AUTO_FLIP_OFF_PEAK_END_HOUR: number;
	FLEX_AUTO_FLIP_OFF_PEAK_TIMEZONE: string;
	FLEX_AUTO_FLIP_THRESHOLD_RATIO: number;
};

export type FlexAutoFlipConfigUpdate = Partial<FlexAutoFlipConfig>;

export const getFlexAutoFlipConfig = async (token: string): Promise<FlexAutoFlipConfig> => {
	let error: any = null;

	const res = await fetch(`${FLEX_AUTO_FLIP_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as FlexAutoFlipConfig;
};

export const updateFlexAutoFlipConfig = async (
	token: string,
	payload: FlexAutoFlipConfigUpdate
): Promise<FlexAutoFlipConfig> => {
	let error: any = null;

	const res = await fetch(`${FLEX_AUTO_FLIP_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...payload })
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as FlexAutoFlipConfig;
};
