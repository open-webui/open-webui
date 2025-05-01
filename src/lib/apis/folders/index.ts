import { webuiApiClient } from '../clients';

interface Folder {
	id: string;
	name: string;
	[key: string]: unknown;
}

interface FolderItems {
	chat_ids: string[];
	file_ids: string[];
}

export const createNewFolder = async (token: string, name: string) =>
	webuiApiClient.post<Folder>('/folders/', { name }, { token });

export const getFolders = async (token: string = '') =>
	webuiApiClient.get<Folder[]>('/folders/', { token });

export const getFolderById = async (token: string, id: string) =>
	webuiApiClient.get<Folder>(`/folders/${id}`, { token });

export const updateFolderNameById = async (token: string, id: string, name: string) =>
	webuiApiClient.post<Folder>(`/folders/${id}/update`, { name }, { token });

export const updateFolderIsExpandedById = async (token: string, id: string, isExpanded: boolean) =>
	webuiApiClient.post<Folder>(
		`/folders/${id}/update/expanded`,
		{ is_expanded: isExpanded },
		{ token }
	);

export const updateFolderParentIdById = async (token: string, id: string, parentId?: string) =>
	webuiApiClient.post<Folder>(`/folders/${id}/update/parent`, { parent_id: parentId }, { token });

export const updateFolderItemsById = async (token: string, id: string, items: FolderItems) =>
	webuiApiClient.post<Folder>(`/folders/${id}/update/items`, { items }, { token });

export const deleteFolderById = async (token: string, id: string) =>
	webuiApiClient.del<Folder>(`/folders/${id}`, null, { token });
