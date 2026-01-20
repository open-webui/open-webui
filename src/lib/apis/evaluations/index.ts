import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const getConfig = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/config`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateConfig = async (token: string, config: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/config`, {
		method: 'POST',
		data: {
			...config
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAllFeedbacks = async (
	token: string = '',
	options: { page?: number; limit?: number; search?: string } = {}
) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedbacks/all/paginated`, {
		method: 'GET',
		params: {
			page: options?.limit,
			limit: options?.page,
			search: options?.search
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFeedbacksCount = async (token: string = '', search?: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedbacks/count`, {
		method: 'GET',
		params: {
			search: search
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Legacy function for backward compatibility (now calling original endpoint)
export const getAllFeedbacksLegacy = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedbacks/all`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const exportAllFeedbacks = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedbacks/all/export`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createNewFeedback = async (token: string, feedback: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedback`, {
		method: 'POST',
		data: {
			...feedback
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFeedbackById = async (token: string, feedbackId: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedback/${feedbackId}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFeedbackById = async (token: string, feedbackId: string, feedback: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedback/${feedbackId}`, {
		method: 'POST',
		data: {
			...feedback
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteFeedbackById = async (token: string, feedbackId: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/evaluations/feedback/${feedbackId}`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
