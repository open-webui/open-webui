import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getTimeRange } from '$lib/utils';
import { deleteRequest, getRequest, jsonRequest } from '$lib/apis/helpers';

export const createNewChat = async (token: string, chat: object) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/chats/new`, token, { chat });
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ChatsArray = any[];

export const getChatList = async (token: string = '') => {
	const res = await getRequest<ChatsArray>(`${WEBUI_API_BASE_URL}/chats/`, token);
	return res.map((chat) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getChatListByUserId = async (token: string = '', userId: string) => {
	const res = await getRequest<ChatsArray>(
		`${WEBUI_API_BASE_URL}/chats/list/user/${userId}`,
		token
	);
	return res.map((chat) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getArchivedChatList = async (token: string = '') => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/archived`, token);
};

export const getAllChats = async (token: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/all`, token);
};

export const getAllArchivedChats = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/chats/all/archived`, {
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
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAllUserChats = async (token: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/all/db`, token);
};

export const getAllChatTags = async (token: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/tags/all`, token);
};

export const getChatListByTagName = async (token: string = '', tagName: string) => {
	const res = await jsonRequest<ChatsArray>(`${WEBUI_API_BASE_URL}/chats/tags`, token, {
		name: tagName
	});

	return res.map((chat) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getChatById = async (token: string, id: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/${id}`, token);
};

export const getChatByShareId = async (token: string, share_id: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/share/${share_id}`, token);
};

export const cloneChatById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${id}/clone`, {
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
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const shareChatById = async (token: string, id: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/chats/${id}/share`, token, {});
};

export const archiveChatById = async (token: string, id: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/${id}/archive`, token);
};

export const deleteSharedChatById = async (token: string, id: string) => {
	return deleteRequest(`${WEBUI_API_BASE_URL}/chats/${id}/share`, token);
};

export const updateChatById = async (token: string, id: string, chat: object) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/chats/${id}`, token, { chat });
};

export const deleteChatById = async (token: string, id: string) => {
	return deleteRequest(`${WEBUI_API_BASE_URL}/chats/${id}`, token);
};

export const getTagsById = async (token: string, id: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, token);
};

export const addTagById = async (token: string, id: string, tagName: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, token, {
		tag_name: tagName,
		chat_id: id
	});
};

export const deleteTagById = async (token: string, id: string, tagName: string) => {
	return jsonRequest(
		`${WEBUI_API_BASE_URL}/chats/${id}/tags`,
		token,
		{
			tag_name: tagName,
			chat_id: id
		},
		'DELETE'
	);
};

export const deleteTagsById = async (token: string, id: string) => {
	return deleteRequest(`${WEBUI_API_BASE_URL}/chats/${id}/tags/all`, token);
};

export const deleteAllChats = async (token: string) => {
	return deleteRequest(`${WEBUI_API_BASE_URL}/chats/`, token);
};

export const archiveAllChats = async (token: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/chats/archive/all`, token, {});
};
