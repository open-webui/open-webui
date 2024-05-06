import { AZURE_OPENAI_API_BASE_URL } from '$lib/constants';

export const getAzureOpenAIUrls = async (token: string = '') => {
	let error = null;
	console.log('getAzureOpenAIUrls');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/urls`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			console.log(res)
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

	return res.AZURE_OPENAI_API_BASE_URLS;
};

export const updateAzureOpenAIUrls = async (token: string = '', urls: string[]) => {
	let error = null;
	console.log('updateAzureOpenAIUrls');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/urls/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			urls: urls
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

	return res.AZURE_OPENAI_API_BASE_URLS;
};

export const getAzureOpenAIKeys = async (token: string = '') => {
	let error = null;
	console.log('getAzureOpenAIKeys');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/keys`, {
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

	return res.AZURE_OPENAI_API_KEYS;
};

export const updateAzureOpenAIKeys = async (token: string = '', keys: string[]) => {
	let error = null;
	console.log('updateAzureOpenAIKeys');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/keys/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			keys: keys
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

	return res.AZURE_OPENAI_API_KEYS;
};

export const getAzureOpenAIAPIVersions = async (token: string = '') => {
	let error = null;
	console.log('getAzureOpenAIAPIVersions');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/apiversions`, {
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

	return res.AZURE_OPENAI_API_VERSIONS;
};

export const updateAzureOpenAIAPIVersions = async (token: string = '', apiversions: string[]) => {
	let error = null;
	console.log('updateAzureOpenAIAPIVersions');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/apiversions/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			apiversions: apiversions
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

	return res.AZURE_OPENAI_API_VERSIONS;
};

export const getAzureOpenAIDeploymentModelNames = async (token: string = '') => {
	let error = null;
	console.log('getAzureOpenAIDeploymentModelNames');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/deploymentmodelnames`, {
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

	return res.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES;
};

export const updateAzureOpenAIDeploymentModelNames = async (token: string = '', deploymentmodelnames: string[][]) => {
	let error = null;
	console.log("updateAzureOpenAIDeploymentModelNames")

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/deploymentmodelnames/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			deploymentmodelnames: deploymentmodelnames
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

	return res.AZURE_OPENAI_DEPLOYMENT_MODEL_NAMES;
};

export const getAzureOpenAIModels = async (token: string = '') => {
	let error = null;
	console.log('getAzureOpenAIModels');

	const res = await fetch(`${AZURE_OPENAI_API_BASE_URL}/models`, {
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
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	const models = Array.isArray(res) ? res : res?.data ?? null;

	return models
		? models
				.map((model) => ({ id: model.id, name: model.name ?? model.id, external: true, azure: true }))
				.sort((a, b) => {
					return a.name.localeCompare(b.name);
				})
		: models;
};

export const generateAzureOpenAIChatCompletion = async (
	token: string = '',
	body: object,
	url: string = AZURE_OPENAI_API_BASE_URL
) => {
	let error = null;
	console.log('generateAzureOpenAIChatCompletion');

	const res = await fetch(`${url}/chat/completions`, {
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

export const generateTitle = async (
	token: string = '',
	template: string,
	model: string,
	prompt: string,
	url: string = AZURE_OPENAI_API_BASE_URL
) => {
	let error = null;
	console.log('generateTitle');

	template = template.replace(/{{prompt}}/g, prompt);

	console.log(template);

	const res = await fetch(`${url}/chat/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			messages: [
				{
					role: 'user',
					content: template
				}
			],
			stream: false
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
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.choices[0]?.message?.content ?? 'New Chat';
};