import { toast } from 'svelte-sonner';

import { createNewNote } from '$lib/apis/notes';

export const createNoteHandler = async (title: string, content?: string) => {
	//  $i18n.t('New Note'),
	const res = await createNewNote(localStorage.token, {
		// YYYY-MM-DD
		title: title,
		data: {
			content: {
				json: null,
				html: content ?? '',
				md: content ?? ''
			}
		},
		meta: null,
		access_control: {}
	}).catch((error) => {
		toast.error(`${error}`);
		return null;
	});

	if (res) {
		return res;
	}
};
