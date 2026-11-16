import { redirect } from '@sveltejs/kit';
import { loadFolderDetails } from '$lib/stores/folderStates';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, url }) => {
	if (!localStorage.token)
		redirect(303, `/auth?redirect=${encodeURIComponent(url.pathname + url.search)}`);
	try {
		return { folder: await loadFolderDetails(localStorage.token, params.folderId, true) };
	} catch (error) {
		redirect(303, `/?error=${encodeURIComponent(String(error))}`);
	}
};
