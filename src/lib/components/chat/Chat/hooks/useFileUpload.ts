import { v4 as uuidv4 } from 'uuid';
import { toast } from 'svelte-sonner';
import { processWeb, processWebSearch, processYoutubeVideo } from '$lib/apis/retrieval';
import { uploadFile } from '$lib/apis/files';
import type { ChatFile } from '../types';

export interface FileUploadOptions {
	onProgress?: (progress: number) => void;
	onComplete?: (file: ChatFile) => void;
	onError?: (error: Error) => void;
}

export function useFileUpload() {
	const uploadLocalFile = async (file: File, options?: FileUploadOptions): Promise<ChatFile | null> => {
		const fileId = uuidv4();
		const chatFile: ChatFile = {
			id: fileId,
			name: file.name,
			type: file.type,
			file: file
		};
		
		try {
			const token = localStorage.getItem('token');
			const uploadedFile = await uploadFile(token, file, fileId);
			
			if (uploadedFile) {
				chatFile.url = uploadedFile.url;
				chatFile.collection_name = uploadedFile.collection_name;
				options?.onComplete?.(chatFile);
				return chatFile;
			}
			
			throw new Error('File upload failed');
		} catch (error) {
			console.error('File upload error:', error);
			options?.onError?.(error as Error);
			toast.error('Failed to upload file');
			return null;
		}
	};
	
	const uploadGoogleDriveFile = async (fileData: any): Promise<ChatFile | null> => {
		try {
			const fileId = uuidv4();
			const file = new File([fileData.data], fileData.name, {
				type: fileData.mimeType
			});
			
			return await uploadLocalFile(file);
		} catch (error) {
			console.error('Google Drive file upload error:', error);
			toast.error('Failed to upload Google Drive file');
			return null;
		}
	};
	
	const uploadWebContent = async (url: string): Promise<ChatFile | null> => {
		try {
			const token = localStorage.getItem('token');
			const fileId = uuidv4();
			
			const response = await processWeb(token, {
				url: url,
				collection_name: fileId
			});
			
			if (response) {
				const chatFile: ChatFile = {
					id: fileId,
					name: url,
					type: 'web',
					url: url,
					collection_name: fileId
				};
				
				toast.success('Web content processed successfully');
				return chatFile;
			}
			
			throw new Error('Web content processing failed');
		} catch (error) {
			console.error('Web content upload error:', error);
			toast.error('Failed to process web content');
			return null;
		}
	};
	
	const uploadYoutubeTranscription = async (url: string): Promise<ChatFile | null> => {
		try {
			const token = localStorage.getItem('token');
			const fileId = uuidv4();
			
			const response = await processYoutubeVideo(token, url);
			
			if (response) {
				const chatFile: ChatFile = {
					id: fileId,
					name: `YouTube: ${response.title || url}`,
					type: 'youtube',
					url: url,
					collection_name: fileId
				};
				
				toast.success('YouTube transcription processed successfully');
				return chatFile;
			}
			
			throw new Error('YouTube transcription processing failed');
		} catch (error) {
			console.error('YouTube transcription error:', error);
			toast.error('Failed to process YouTube video');
			return null;
		}
	};
	
	const removeFile = (files: ChatFile[], fileId: string): ChatFile[] => {
		return files.filter(f => f.id !== fileId);
	};
	
	const isValidFileType = (file: File): boolean => {
		// Add your file type validation logic here
		const allowedTypes = [
			'image/jpeg',
			'image/png',
			'image/gif',
			'image/webp',
			'application/pdf',
			'text/plain',
			'text/markdown',
			'application/json',
			'text/csv'
		];
		
		return allowedTypes.includes(file.type) || file.type.startsWith('text/');
	};
	
	const getFileIcon = (fileType: string): string => {
		if (fileType.startsWith('image/')) return '🖼️';
		if (fileType === 'application/pdf') return '📄';
		if (fileType.startsWith('text/')) return '📝';
		if (fileType === 'web') return '🌐';
		if (fileType === 'youtube') return '📺';
		return '📎';
	};
	
	return {
		uploadLocalFile,
		uploadGoogleDriveFile,
		uploadWebContent,
		uploadYoutubeTranscription,
		removeFile,
		isValidFileType,
		getFileIcon
	};
}