import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

import { settings, type FolderListSection } from '$lib/stores';
import { updateUserSettings } from '$lib/apis/users';

type FolderListSettings = {
	folderOrder?: Record<string, string[]>;
	folderSections?: FolderListSection[];
};

/** Saves sidebar folder settings here and to the user's account. */
export const saveFolderListSettings = (ui: FolderListSettings) => {
	settings.set({ ...get(settings), ...ui });
	return updateUserSettings(localStorage.token, { ui }).catch((error) => {
		toast.error(`${error}`);
	});
};

/** The sections with the folder in the given one only, or in none. */
export const placeInSection = (
	sections: FolderListSection[],
	folderId: string,
	sectionId?: string
) =>
	sections.map((section) => ({
		...section,
		folderIds: [
			...section.folderIds.filter((id) => id !== folderId),
			...(section.id === sectionId ? [folderId] : [])
		]
	}));
