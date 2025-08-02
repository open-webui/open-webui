// Google Drive TypeScript Type Definitions
// Mirrors backend Python types for consistency

/**
 * Google Drive file information from Google Drive API
 */
export interface GoogleDriveFile {
	id: string;
	name: string;
	mimeType: string;
	modifiedTime: string;
	size?: string; // Optional field, not present for some files
	parents?: string[]; // Optional, may not be present
	path: string; // Custom field added by our service
	webViewLink?: string; // Optional web view URL
}

/**
 * Google Drive folder information
 */
export interface GoogleDriveFolder {
	id: string;
	name: string;
}

/**
 * Google Drive API list response structure
 */
export interface GoogleDriveAPIResponse {
	files: GoogleDriveFile[];
	nextPageToken?: string;
}

/**
 * File download result structure
 */
export interface FileDownloadResult {
	content: ArrayBuffer | string;
	filename: string;
}

/**
 * Google Drive sync configuration stored in knowledge base data
 */
export interface GoogleDriveSyncConfig {
	google_drive_folder_id: string;
	google_drive_include_nested: boolean;
	google_drive_sync_interval_days: number;
	google_drive_last_sync: number; // Unix timestamp
	file_ids: string[]; // List of file IDs in the knowledge base
}

/**
 * Google Drive file metadata stored in file records
 */
export interface GoogleDriveFileMetadata {
	name: string;
	content_type: string;
	size: number;
	google_drive_id: string;
	google_drive_modified: string; // ISO timestamp from Google Drive API
}

/**
 * Google Drive service account email response
 */
export interface GoogleDriveServiceAccount {
	email: string;
	status: 'active' | 'inactive';
}

/**
 * Google Drive sync operation response
 */
export interface GoogleDriveSyncResponse {
	files_added: number;
	files_updated: number;
	files_removed: number;
	errors: string[];
	last_sync_time: string;
	folder_id: string;
	total_files: number;
}

// Google Picker API Types

/**
 * Google Picker configuration options
 */
export interface GooglePickerConfig {
	clientId: string;
	discoveryDocs: string[];
	scope: string;
	immediate?: boolean;
}

/**
 * Google Picker result data structure
 */
export interface GooglePickerResult {
	action: string;
	docs?: GooglePickerDocument[];
}

/**
 * Google Picker API response constants (based on google.picker constants)
 */
export interface GooglePickerResponse {
	ACTION: string;
	DOCUMENTS: string;
}

/**
 * Google Picker callback data structure (matches Google Picker API response format)
 */
export interface GooglePickerCallbackData {
	[key: string]: string | number | GooglePickerDocument[] | GooglePickerDocument;
}

/**
 * Google Picker document structure
 */
export interface GooglePickerDocument {
	id: string;
	name: string;
	mimeType: string;
	sizeBytes?: number;
	url?: string;
	iconUrl?: string;
	parents?: string[];
}

/**
 * Google Auth token response
 */
export interface GoogleAuthToken {
	access_token: string;
	expires_in: number;
	scope: string;
	token_type: string;
}

/**
 * Google Picker callback function types
 */
export type GooglePickerCallback = (result: GooglePickerResult) => void;
export type GooglePickerErrorCallback = (error: GoogleAPIError) => void;

/**
 * Google API error structure
 */
export interface GoogleAPIError {
	code: number;
	message: string;
	status: string;
	details?: Array<{ message: string; domain: string; reason: string }>;
}

/**
 * Google OAuth error structure
 */
export interface GoogleOAuthError {
	error: string;
	error_description?: string;
	error_uri?: string;
	message?: string;
}

/**
 * Knowledge base data with Google Drive fields
 */
export interface KnowledgeDataWithGoogleDrive {
	id?: string;
	name: string;
	description?: string;
	data?: Record<string, unknown>;
	// Google Drive specific fields
	google_drive_folder_id?: string;
	google_drive_include_nested?: boolean;
	google_drive_sync_interval_days?: number;
	google_drive_last_sync?: number;
	google_drive_file_ids?: string[];
}

/**
 * API error response structure
 */
export interface APIError {
	detail: string;
	status?: number;
	code?: string;
}

// Global Google API declarations for TypeScript
declare global {
	interface Window {
		gapi: {
			load: (api: string, callback: () => void) => void;
			auth2: {
				getAuthInstance: () => {
					signIn: () => Promise<GoogleAuthToken>;
					isSignedIn: {
						get: () => boolean;
					};
					currentUser: {
						get: () => {
							getAuthResponse: () => GoogleAuthToken;
						};
					};
				};
				init: (config: GooglePickerConfig) => Promise<void>;
			};
			client: {
				init: (config: GooglePickerConfig) => Promise<void>;
				request: (config: Record<string, unknown>) => Promise<Record<string, unknown>>;
			};
		};
		google: {
			accounts: {
				oauth2: {
					initTokenClient: (config: {
						client_id: string;
						scope: string;
						callback: (response: GoogleAuthToken) => void;
						error_callback: (error: GoogleOAuthError) => void;
					}) => {
						requestAccessToken: () => void;
					};
				};
			};
			picker: {
				api: {
					loaded: () => boolean;
				};
				PickerBuilder: new () => {
					addView: (view: GooglePickerView) => GooglePickerBuilder;
					setCallback: (callback: (data: GooglePickerCallbackData) => void) => GooglePickerBuilder;
					setOAuthToken: (token: string) => GooglePickerBuilder;
					setDeveloperKey: (key: string) => GooglePickerBuilder;
					enableFeature: (feature: GooglePickerFeature) => GooglePickerBuilder;
					build: () => GooglePickerWidget;
				};
				DocsView: new () => GooglePickerView;
				ViewId: {
					DOCS: string;
					FOLDERS: string;
				};
				Feature: {
					NAV_HIDDEN: GooglePickerFeature;
					MULTISELECT_ENABLED: GooglePickerFeature;
				};
				Response: {
					ACTION: string;
					DOCUMENTS: string;
				};
				Action: {
					PICKED: string;
					CANCEL: string;
				};
				Document: {
					ID: string;
					NAME: string;
					URL: string;
					MIME_TYPE: string;
				};
			};
		};
	}

	// Additional Google Picker types
	interface GooglePickerBuilder {
		addView: (view: GooglePickerView) => GooglePickerBuilder;
		setCallback: (callback: (data: GooglePickerCallbackData) => void) => GooglePickerBuilder;
		setOAuthToken: (token: string) => GooglePickerBuilder;
		setDeveloperKey: (key: string) => GooglePickerBuilder;
		enableFeature: (feature: GooglePickerFeature) => GooglePickerBuilder;
		build: () => GooglePickerWidget;
	}

	interface GooglePickerWidget {
		setVisible: (visible: boolean) => void;
	}

	interface GooglePickerView {
		setIncludeFolders: (include: boolean) => GooglePickerView;
		setSelectFolderEnabled: (enabled: boolean) => GooglePickerView;
		setMimeTypes: (types: string) => GooglePickerView;
	}

	interface GooglePickerFeature {}
}
