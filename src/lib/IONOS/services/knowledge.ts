import type {
	Knowledge,
	KnowledgeFile,
} from '$lib/apis/knowledge/types';
import {
	uploadFile,
} from '$lib/apis/files';
import {
	createNewKnowledge,
	deleteKnowledgeById,
	addFileToKnowledgeById,
	removeFileFromKnowledgeById,
} from '$lib/apis/knowledge';

export const ACCESS_CONTROL_PRIVATE = Object.freeze({
	"read": Object.freeze({
		"group_ids": Object.freeze([]),
	}),
	"write": Object.freeze({
		"group_ids": Object.freeze([]),
	}),
});

export async function create(name: string, description: string): Promise<void> {
	if (name.trim() === '' || description.trim() === '') {
		throw new Error('The fields name and description may not be empty');
	}

	let res: Knowledge;
	try {
		res = await createNewKnowledge(
			localStorage.token,
			name,
			description,
			ACCESS_CONTROL_PRIVATE,
		);
	} catch (e) {
		throw new Error(`Exception while creating knowledge: ${e}`);
	}

	if (!res) {
		throw new Error('Error creating knowledge');
	}
}

export async function remove(knowledgeId: string): Promise<void> {
	let res: boolean;
	try {
		res = await deleteKnowledgeById(localStorage.token, knowledgeId);
	} catch (e) {
		throw new Error(`Exception while deleting knowledge: ${e}`);
	}

	if (!res) {
		throw new Error('Error deleting knowledge');
	}
}

export async function removeFile(knowledgeId: string, fileId: string): Promise<void> {
	let res: Knowledge;
	try {
		res = await removeFileFromKnowledgeById(localStorage.token, knowledgeId, fileId);
	} catch (e) {
		throw new Error(`Exception while error deleting file: ${e}`);
	}

	if (!res) {
		throw new Error(`Error deleting file with file=${fileId} knowledge=${knowledgeId}`);
	}
}

export async function addFile(knowledgeId: string, file: File): Promise<KnowledgeFile[]> {
	let uploadedFile: KnowledgeFile;
	try {
		uploadedFile = await uploadFile(localStorage.token, file);
	} catch (e) {
		throw new Error(`Exception while uploading file: ${e}`);
	}

	if (!uploadedFile) {
		throw new Error(`Error uploading file`);
	}

	let updatedKnowledge: Knowledge;
	try {
		updatedKnowledge = await addFileToKnowledgeById(localStorage.token, knowledgeId, uploadedFile.id);
	} catch (e) {
		throw new Error(`Exception while adding file to knowledge base: ${e}`);
	}

	if (!updatedKnowledge) {
		throw new Error(`Error adding file to knowledge base knowledge=${knowledgeId}`);
	}

	return updatedKnowledge.files ?? [];
}
