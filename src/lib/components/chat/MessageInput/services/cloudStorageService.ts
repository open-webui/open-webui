import { toast } from 'svelte-sonner';
import { createPicker, getAuthToken } from '$lib/utils/google-drive-picker';
import { pickAndDownloadFile } from '$lib/utils/onedrive-file-picker';
import type { CloudStorageFile } from '../types';

export class CloudStorageService {
	private googleAuthToken: string | null = null;
	
	async pickFromGoogleDrive(): Promise<CloudStorageFile | null> {
		try {
			// Get auth token if not already cached
			if (!this.googleAuthToken) {
				this.googleAuthToken = await getAuthToken();
			}
			
			if (!this.googleAuthToken) {
				toast.error('Failed to authenticate with Google Drive');
				return null;
			}
			
			// Create and show picker
			const picker = createPicker(
				this.googleAuthToken,
				this.handleGoogleDriveSelection.bind(this)
			);
			
			return new Promise((resolve) => {
				// Store resolver to be called from callback
				(window as any).__googleDriveResolver = resolve;
			});
		} catch (error) {
			console.error('Google Drive picker error:', error);
			toast.error('Failed to open Google Drive picker');
			return null;
		}
	}
	
	private async handleGoogleDriveSelection(data: any) {
		const resolver = (window as any).__googleDriveResolver;
		delete (window as any).__googleDriveResolver;
		
		if (data.action !== google.picker.Action.PICKED) {
			resolver(null);
			return;
		}
		
		const file = data.docs[0];
		if (!file) {
			resolver(null);
			return;
		}
		
		try {
			// Download file content
			const response = await fetch(
				`https://www.googleapis.com/drive/v3/files/${file.id}?alt=media`,
				{
					headers: {
						Authorization: `Bearer ${this.googleAuthToken}`
					}
				}
			);
			
			if (!response.ok) {
				throw new Error('Failed to download file');
			}
			
			const blob = await response.blob();
			
			const cloudFile: CloudStorageFile = {
				id: file.id,
				name: file.name,
				mimeType: file.mimeType,
				data: blob,
				size: file.sizeBytes || blob.size
			};
			
			resolver(cloudFile);
		} catch (error) {
			console.error('Failed to download Google Drive file:', error);
			toast.error('Failed to download file from Google Drive');
			resolver(null);
		}
	}
	
	async pickFromOneDrive(): Promise<CloudStorageFile | null> {
		try {
			const result = await pickAndDownloadFile();
			
			if (!result) {
				return null;
			}
			
			const cloudFile: CloudStorageFile = {
				id: result.id,
				name: result.name,
				mimeType: result.file.type,
				data: result.file,
				size: result.file.size
			};
			
			return cloudFile;
		} catch (error) {
			console.error('OneDrive picker error:', error);
			toast.error('Failed to pick file from OneDrive');
			return null;
		}
	}
	
	async convertCloudFileToFile(cloudFile: CloudStorageFile): Promise<File> {
		let blob: Blob;
		
		if (cloudFile.data instanceof ArrayBuffer) {
			blob = new Blob([cloudFile.data], { type: cloudFile.mimeType });
		} else {
			blob = cloudFile.data;
		}
		
		return new File([blob], cloudFile.name, { type: cloudFile.mimeType });
	}
}

// Singleton instance
export const cloudStorageService = new CloudStorageService();