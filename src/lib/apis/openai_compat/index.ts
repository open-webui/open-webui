import { OPENAI_COMPAT_API_BASE_URL } from '$lib/constants';

export const getOpenAICompatUrlList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/url`, {
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

	return res.OPENAI_COMPAT_API_BASE_URL_LIST;
};

export const updateOpenAICompatUrlList = async (token: string = '', url: string) => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/url/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			url: url
		})
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

	return res.OPENAI_COMPAT_API_BASE_URL_LIST;
};

export const getOpenAICompatKeyList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/key`, {
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

	return res.OPENAI_COMPAT_API_KEY_LIST;
};

export const updateOpenAICompatKeyList = async (token: string = '', key: string) => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/key/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			key: key
		})
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

	return res.OPENAI_COMPAT_API_KEY_LIST;
};

export const getOpenAICompatModelLabelList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/label`, {
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

	return res.OPENAI_COMPAT_MODEL_LABEL_LIST;
};

export const updateOpenAICompatModelLabelList = async (token: string = '', label: string) => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/label/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			label: label
		})
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

	return res.OPENAI_COMPAT_MODEL_LABEL_LIST;
};

export const getOpenAICompatModels = async (token: string = '') => {
	let error = null;

	// TODO: call backend and split
	const res: {"OPENAI_COMPAT_MODEL_LABEL_LIST": string} = await getOpenAICompatModelLabelList(token)
		.then(async (res) => {
			if (!res) throw 'Server connection failed';
			return res;
		})
		.catch((err) => {
			console.log(err);
			error = `OpenAI (compatible API): ${err?.error?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	console.log("getOpenAICompatModelLabels res", res);
	const labels = res.OPENAI_COMPAT_MODEL_LABEL_LIST.split(';');
	console.log("getOpenAICompatModelLabels labels", labels);
	return labels
		? labels
				.map((label) => ({ 
					name: label,
					model: label,
					external_compat: true,
				}))
				.sort((a, b) => {
					return a.name.localeCompare(b.name);
				})
		: labels;
};

export const generateOpenAICompatChatCompletion = async (token: string = '', body: object) => {
	let error = null;

	const res = await fetch(`${OPENAI_COMPAT_API_BASE_URL}/chat/completions`, {
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

	if (error) {
		throw error;
	}

	return res;
};
