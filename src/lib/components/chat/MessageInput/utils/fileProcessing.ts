import * as pdfjs from 'pdfjs-dist';
import heic2any from 'heic2any';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'svelte-sonner';
import DOMPurify from 'dompurify';

import type { FileItem, FileUploadOptions } from '../types';
import { compressImage, blobToFile, extractContentFromFile } from '$lib/utils';
import { uploadFile, deleteFileById } from '$lib/apis/files';
import { PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

// Initialize PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = import.meta.url + 'pdfjs-dist/build/pdf.worker.mjs';

export async function processFile(
	file: File,
	options: FileUploadOptions = {}
): Promise<FileItem | null> {
	const { fullContext = false, compress = true, maxSize = 10 * 1024 * 1024 } = options;
	
	// Check file size
	if (file.size > maxSize) {
		toast.error(`File "${file.name}" exceeds maximum size of ${maxSize / 1024 / 1024}MB`);
		return null;
	}
	
	const fileItem: FileItem = {
		id: uuidv4(),
		name: file.name,
		type: file.type,
		size: file.size,
		file: file,
		status: 'uploading',
		progress: 0
	};
	
	try {
		// Handle HEIC images
		if (file.type === 'image/heic' || file.name.toLowerCase().endsWith('.heic')) {
			file = await convertHeicToJpeg(file);
			fileItem.type = file.type;
			fileItem.file = file;
		}
		
		// Handle different file types
		if (file.type.startsWith('image/') && compress) {
			await processImage(fileItem, file);
		} else if (file.type === 'application/pdf' || fullContext) {
			await processDocument(fileItem, file, fullContext);
		} else {
			await processGenericFile(fileItem, file);
		}
		
		fileItem.status = 'uploaded';
		fileItem.progress = 100;
		
		return fileItem;
	} catch (error) {
		console.error('File processing error:', error);
		fileItem.status = 'error';
		fileItem.error = error.message;
		toast.error(`Failed to process "${file.name}"`);
		return fileItem;
	}
}

async function convertHeicToJpeg(file: File): Promise<File> {
	try {
		const blob = await heic2any({
			blob: file,
			toType: 'image/jpeg',
			quality: 0.9
		});
		
		return blobToFile(
			Array.isArray(blob) ? blob[0] : blob,
			file.name.replace(/\.heic$/i, '.jpg')
		);
	} catch (error) {
		console.error('HEIC conversion error:', error);
		throw new Error('Failed to convert HEIC image');
	}
}

async function processImage(fileItem: FileItem, file: File): Promise<void> {
	// Compress image
	const compressedUrl = await compressImage(URL.createObjectURL(file), {
		maxWidth: 1024,
		maxHeight: 1024,
		quality: 0.9
	});
	
	// Convert to base64
	const response = await fetch(compressedUrl);
	const blob = await response.blob();
	const reader = new FileReader();
	
	return new Promise((resolve, reject) => {
		reader.onloadend = () => {
			fileItem.base64 = reader.result as string;
			fileItem.url = compressedUrl;
			resolve();
		};
		reader.onerror = reject;
		reader.readAsDataURL(blob);
	});
}

async function processDocument(fileItem: FileItem, file: File, fullContext: boolean): Promise<void> {
	const token = localStorage.getItem('token');
	
	// Extract text content
	const content = await extractContentFromFile(file);
	
	if (fullContext && content) {
		// For full context, include the text directly
		fileItem.context = content.substring(0, PASTED_TEXT_CHARACTER_LIMIT);
	} else {
		// Upload to server for RAG processing
		const uploadedFile = await uploadFile(token, file, fileItem.id);
		if (uploadedFile) {
			fileItem.url = uploadedFile.url;
			fileItem.collection_name = uploadedFile.collection_name;
		}
	}
}

async function processGenericFile(fileItem: FileItem, file: File): Promise<void> {
	const token = localStorage.getItem('token');
	
	// Upload file to server
	const uploadedFile = await uploadFile(token, file, fileItem.id);
	if (uploadedFile) {
		fileItem.url = uploadedFile.url;
		fileItem.collection_name = uploadedFile.collection_name;
	}
}

export async function removeFile(fileId: string, deleteFromServer = true): Promise<void> {
	if (deleteFromServer) {
		const token = localStorage.getItem('token');
		try {
			await deleteFileById(token, fileId);
		} catch (error) {
			console.error('Failed to delete file from server:', error);
		}
	}
}

export function validateFileType(file: File, acceptedTypes?: string[]): boolean {
	if (!acceptedTypes || acceptedTypes.length === 0) {
		return true;
	}
	
	return acceptedTypes.some(type => {
		if (type.endsWith('/*')) {
			// Handle wildcard types like "image/*"
			const baseType = type.slice(0, -2);
			return file.type.startsWith(baseType);
		}
		return file.type === type;
	});
}

export function getFileTypeIcon(fileType: string): string {
	if (fileType.startsWith('image/')) return '🖼️';
	if (fileType === 'application/pdf') return '📄';
	if (fileType.startsWith('video/')) return '🎥';
	if (fileType.startsWith('audio/')) return '🎵';
	if (fileType.startsWith('text/')) return '📝';
	if (fileType === 'application/json') return '📊';
	if (fileType.includes('spreadsheet') || fileType.includes('excel')) return '📊';
	if (fileType.includes('document') || fileType.includes('word')) return '📝';
	if (fileType.includes('presentation') || fileType.includes('powerpoint')) return '📑';
	return '📎';
}

export function formatFileSize(bytes: number): string {
	if (bytes === 0) return '0 Bytes';
	
	const k = 1024;
	const sizes = ['Bytes', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	
	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}