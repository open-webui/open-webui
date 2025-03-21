import { type Writable, writable } from 'svelte/store';
import type { KnowledgeFile } from '$lib/apis/knowledge/types';
import { addFile } from '$lib/IONOS/services/knowledge';

export const files: Writable<KnowledgeFile[]> = writable([]);

export function init(initialFiles: KnowledgeFile[]) {
	files.set(initialFiles);
}

export async function upload(knowledgeId: string, filesToUpload: File[]): Promise<void> {
	for (const file of filesToUpload) {
		const uploadedFiles = await addFile(knowledgeId, file);
		files.set(uploadedFiles);
	}
}
