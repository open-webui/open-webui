import { getTimeRange } from '$lib/utils';
import { webuiApiClient } from '../clients';

interface Chat {
	id: string;
	updated_at: string;
	title?: string;
	content?: string;
	metadata?: Record<string, unknown>;
	[key: string]: unknown;
}

interface ChatResponse {
	data: Chat[];
}

export const createNewChat = async (token: string, chat: Record<string, unknown>) =>
	webuiApiClient.post<ChatResponse>('/chats/new', { chat }, { token });

export const importChat = async (
	token: string,
	chat: Record<string, unknown>,
	meta: Record<string, unknown> | null,
	pinned?: boolean,
	folderId?: string | null
) =>
	webuiApiClient.post<ChatResponse>(
		'/chats/import',
		{ chat, meta: meta ?? {}, pinned, folder_id: folderId },
		{ token }
	);

export const getChatList = async (token: string = '', page: number | null = null) => {
	const searchParams = new URLSearchParams();
	if (page !== null) searchParams.append('page', `${page}`);
	return webuiApiClient
		.get<Chat[]>(`/chats/?${searchParams.toString()}`, { token })
		.then((res) => res.map((chat) => ({ ...chat, time_range: getTimeRange(chat.updated_at) })));
};

export const getChatListByUserId = async (token: string = '', userId: string) =>
	webuiApiClient
		.get<Chat[]>(`/chats/list/user/${userId}`, { token })
		.then((res) => res.map((chat) => ({ ...chat, time_range: getTimeRange(chat.updated_at) })));

export const getArchivedChatList = async (token: string = '') =>
	webuiApiClient.get<Chat[]>('/chats/archived', { token });

export const getAllChats = async (token: string) =>
	webuiApiClient.get<Chat[]>('/chats/all', { token });

export const getChatListBySearchText = async (token: string, text: string, page: number = 1) =>
	webuiApiClient.get<Chat[]>(
		`/chats/search?${new URLSearchParams({ text, page: page.toString() })}`,
		{ token }
	);

export const getChatsByFolderId = async (token: string, folderId: string) =>
	webuiApiClient.get<Chat[]>(`/chats/folder/${folderId}`, { token });

export const getAllArchivedChats = async (token: string) =>
	webuiApiClient.get<Chat[]>('/chats/all/archived', { token });

export const getAllUserChats = async (token: string) =>
	webuiApiClient.get<Chat[]>('/chats/all/user', { token });

export const getAllTags = async (token: string) =>
	webuiApiClient.get<string[]>('/chats/all/tags', { token });

export const getPinnedChatList = async (token: string = '') =>
	webuiApiClient.get<Chat[]>('/chats/pinned', { token });

export const getChatListByTagName = async (token: string = '', tagName: string) =>
	webuiApiClient.get<Chat[]>(`/chats/tag/${tagName}`, { token });

export const getChatById = async (token: string, id: string) =>
	webuiApiClient.get<Chat>(`/chats/${id}`, { token });

export const getChatByShareId = async (token: string, share_id: string) =>
	webuiApiClient.get<Chat>(`/chats/shared/${share_id}`, { token });

export const getChatPinnedStatusById = async (token: string, id: string) =>
	webuiApiClient.get<{ pinned: boolean }>(`/chats/${id}/pinned`, { token });

export const toggleChatPinnedStatusById = async (token: string, id: string) =>
	webuiApiClient.post<{ pinned: boolean }>(`/chats/${id}/pinned/toggle`, {}, { token });

export const cloneChatById = async (token: string, id: string, title?: string) =>
	webuiApiClient.post<Chat>(`/chats/${id}/clone`, { title }, { token });

export const cloneSharedChatById = async (token: string, id: string) =>
	webuiApiClient.post<Chat>(`/chats/shared/${id}/clone`, {}, { token });

export const shareChatById = async (token: string, id: string) =>
	webuiApiClient.post<{ share_id: string }>(`/chats/${id}/share`, {}, { token });

export const updateChatFolderIdById = async (token: string, id: string, folderId?: string) =>
	webuiApiClient.post<Chat>(`/chats/${id}/folder/update`, { folder_id: folderId }, { token });

export const archiveChatById = async (token: string, id: string) =>
	webuiApiClient.post<Chat>(`/chats/${id}/archive`, {}, { token });

export const deleteSharedChatById = async (token: string, id: string) =>
	webuiApiClient.del(`/chats/shared/${id}/delete`, null, { token });

export const updateChatById = async (token: string, id: string, chat: Record<string, unknown>) =>
	webuiApiClient.post<Chat>(`/chats/${id}/update`, chat, { token });

export const deleteChatById = async (token: string, id: string) =>
	webuiApiClient.del(`/chats/${id}/delete`, null, { token });

export const getTagsById = async (token: string, id: string) =>
	webuiApiClient.get<string[]>(`/chats/${id}/tags`, { token });

export const addTagById = async (token: string, id: string, tagName: string) =>
	webuiApiClient.post<string[]>(`/chats/${id}/tags/add`, { tag_name: tagName }, { token });

export const deleteTagById = async (token: string, id: string, tagName: string) =>
	webuiApiClient.del(`/chats/${id}/tags/${tagName}/delete`, null, { token });

export const deleteTagsById = async (token: string, id: string) =>
	webuiApiClient.del(`/chats/${id}/tags/delete`, null, { token });

export const deleteAllChats = async (token: string) =>
	webuiApiClient.del('/chats/all/delete', null, { token });

export const archiveAllChats = async (token: string) =>
	webuiApiClient.post('/chats/all/archive', {}, { token });
