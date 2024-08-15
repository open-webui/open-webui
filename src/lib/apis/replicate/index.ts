import { REPLICATE_API_BASE_URL } from '$lib/constants';

export const getReplicateModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${REPLICATE_API_BASE_URL}/models`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const generateReplicateChatCompletion = async (
	token: string = '',
	body: object
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	let error = null;

	const res = await fetch(`${REPLICATE_API_BASE_URL}/chat/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	}).catch((err) => {
		console.log(err);
		error = err;
		return null;
	});
	console.log(res);

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const cancelReplicatePrediction = async (token: string, predictionId: string) => {
	let error = null;

	const res = await fetch(`${REPLICATE_API_BASE_URL}/predictions/${predictionId}/cancel`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		}
	}).catch((err) => {
		console.log(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};