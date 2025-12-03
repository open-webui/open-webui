import { toast } from 'svelte-sonner';

import { createNewNote } from '$lib/apis/notes';

export const createNoteHandler = async (title: string, md?: string, html?: string) => {
	//  $i18n.t('New Note'),
	const res = await createNewNote(localStorage.token, {
		// YYYY-MM-DD
		title: title,
		data: {
			content: {
				json: null,
				html: html || md || '',
				md: md || ''
			}
		},
		meta: null,
		access_grants: []
	}).catch((error) => {
		toast.error(`${error}`);
		return null;
	});

	if (res) {
		return res;
	}
};
