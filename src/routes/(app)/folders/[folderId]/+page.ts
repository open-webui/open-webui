import { redirect } from '@sveltejs/kit';
import { loadFolderDetails } from '$lib/stores/folderStates';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url }) => {
	if (!localStorage.token)
		redirect(303, `/auth?redirect=${encodeURIComponent(url.pathname + url.search)}`);
	try {
		// The chat shows the folder at once and refreshes it.
		return { folder: await loadFolderDetails(localStorage.token, params.folderId) };
	} catch (error) {
		redirect(303, `/?error=${encodeURIComponent(String(error))}`);
	}
};
