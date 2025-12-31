import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/config`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAllFeedbacks = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedbacks/all`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFeedbackItems = async (token: string = '', orderBy, direction, page) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (orderBy) searchParams.append('order_by', orderBy);
	if (direction) searchParams.append('direction', direction);
	if (page) searchParams.append('page', page.toString());

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/evaluations/feedbacks/list?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const exportAllFeedbacks = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedbacks/all/export`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createNewFeedback = async (token: string, feedback: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedback`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...feedback
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFeedbackById = async (token: string, feedbackId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedback/${feedbackId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFeedbackById = async (token: string, feedbackId: string, feedback: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedback/${feedbackId}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...feedback
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteFeedbackById = async (token: string, feedbackId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedback/${feedbackId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ============================================
// Message Feedback API (New Simple System)
// ============================================

export type MessageFeedbackRating = 'good' | 'bad' | null;

export interface MessageFeedbackRequest {
	chat_id: string;
	message_id: string;
	rating: MessageFeedbackRating;
}

export interface MessageFeedbackResponse {
	id: string;
	user_id: string;
	version: number;
	type: 'message_feedback';
	data: {
		rating: 'good' | 'bad';
	};
	meta: {
		chat_id: string;
		message_id: string;
	};
	snapshot: null;
	created_at: number;
	updated_at: number;
}

/**
 * Submit message feedback (create/update/delete)
 * POST /api/v1/evaluations/feedback/message
 */
export const submitMessageFeedback = async (
	token: string,
	chatId: string,
	messageId: string,
	rating: MessageFeedbackRating
): Promise<MessageFeedbackResponse | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedback/message`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			chat_id: chatId,
			message_id: messageId,
			rating: rating
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Get feedback for a specific message
 * GET /api/v1/evaluations/feedback/message/{chat_id}/{message_id}
 */
export const getMessageFeedback = async (
	token: string,
	chatId: string,
	messageId: string
): Promise<MessageFeedbackResponse | null> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/evaluations/feedback/message/${chatId}/${messageId}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Get all message feedbacks for a chat
 * GET /api/v1/evaluations/feedback/chat/{chat_id}
 */
export const getChatMessageFeedbacks = async (
	token: string,
	chatId: string
): Promise<Record<string, MessageFeedbackRating>> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/evaluations/feedback/chat/${chatId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return {};
		});

	if (error) {
		throw error;
	}

	return res ?? {};
};
