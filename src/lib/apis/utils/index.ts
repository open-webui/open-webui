import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const getGravatarUrl = async (email: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/utils/gravatar`, {
		method: 'GET',
		params: {
			email: email
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	return res;
};

export const formatPythonCode = async (code: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/utils/code/format`, {
		method: 'POST',
		data: {
			code: code
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);

			error = err;
			if (err.detail) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const downloadChatAsPDF = async (title: string, messages: object[]) => {
	let error = null;

	const blob = await canchatAPI(`${WEBUI_API_BASE_PATH}/utils/pdf`, {
		method: 'POST',
		data: {
			title: title,
			messages: messages
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	return blob;
};

export const getHTMLFromMarkdown = async (md: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/utils/markdown`, {
		method: 'POST',
		data: {
			md: md
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	return res.html;
};

export const downloadDatabase = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/utils/db/download`, {
		method: 'GET',
		responseType: 'blob'
	})
		.then(async (response) => {
			return response.data;
		})
		.then((blob) => {
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'webui.db';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}
};
