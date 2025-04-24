import { goto } from '$app/navigation';
import { default as saveAs } from 'file-saver';
import dayjs from 'dayjs';
import {
	deleteAllChats,
	getAllChats,
	getChatList,
} from '$lib/apis/chats';
import {
	chats,
} from '$lib/stores';

export const EXPORT_FILENAME_PREFIX = 'ionos-gpt-export';

export const deleteAll = async (): Promise<void> => {
	const chatPaginationCurrentChatPage = 1;
	const token = localStorage.token;
	await goto('/');
	await deleteAllChats(token);
	chats.set(await getChatList(token, chatPaginationCurrentChatPage));
};

export const exportAll = async (): Promise<void> => {
	const blob = new Blob([JSON.stringify(await getAllChats(localStorage.token))], {
		type: 'application/json'
	});

	const timestamp = dayjs(Date.now()).format('YYYY-MM-DD--HH-mm');

	saveAs(blob, `${EXPORT_FILENAME_PREFIX}-${timestamp}.json`);
};

export async function hasChats(): Promise<boolean> {
	const chats = await getChatList(localStorage.token, 1);
	return chats.length > 0;
};
