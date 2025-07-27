import type {
	GoogleAuthToken,
	GooglePickerCallbackData,
	GoogleOAuthError
} from '$lib/types/google-drive.ts';

// Google Drive Picker API configuration
let API_KEY = '';
let CLIENT_ID = '';

interface ConfigResponse {
	google_drive?: {
		api_key?: string;
		client_id?: string;
	};
}

// Function to fetch credentials from backend config
async function getCredentials(): Promise<void> {
	const response = await fetch('/api/config');
	if (!response.ok) {
		throw new Error('Failed to fetch Google Drive credentials');
	}
	const config: ConfigResponse = await response.json();
	API_KEY = config.google_drive?.api_key || '';
	CLIENT_ID = config.google_drive?.client_id || '';

	if (!API_KEY || !CLIENT_ID) {
		throw new Error('Google Drive API credentials not configured');
	}
}
const SCOPE = [
	'https://www.googleapis.com/auth/drive.readonly',
	'https://www.googleapis.com/auth/drive.file'
];

// Validate required credentials
const validateCredentials = (): void => {
	if (!API_KEY || !CLIENT_ID) {
		throw new Error('Google Drive API credentials not configured');
	}
	if (API_KEY === '' || CLIENT_ID === '') {
		throw new Error('Please configure valid Google Drive API credentials');
	}
};

let oauthToken: string | null = null;
let initialized = false;

export const loadGoogleDriveApi = (): Promise<boolean> => {
	return new Promise((resolve, reject) => {
		if (typeof gapi === 'undefined') {
			const script = document.createElement('script');
			script.src = 'https://apis.google.com/js/api.js';
			script.onload = () => {
				gapi.load('picker', () => {
					resolve(true);
				});
			};
			script.onerror = reject;
			document.body.appendChild(script);
		} else {
			gapi.load('picker', () => {
				resolve(true);
			});
		}
	});
};

export const loadGoogleAuthApi = (): Promise<unknown> => {
	return new Promise((resolve, reject) => {
		if (typeof google === 'undefined') {
			const script = document.createElement('script');
			script.src = 'https://accounts.google.com/gsi/client';
			script.onload = resolve;
			script.onerror = reject;
			document.body.appendChild(script);
		} else {
			resolve(true);
		}
	});
};

export const getAuthToken = async (): Promise<string | null> => {
	if (!oauthToken) {
		return new Promise((resolve, reject) => {
			const tokenClient = google.accounts.oauth2.initTokenClient({
				client_id: CLIENT_ID,
				scope: SCOPE.join(' '),
				callback: (response: GoogleAuthToken) => {
					if (response.access_token) {
						oauthToken = response.access_token;
						resolve(oauthToken);
					} else {
						reject(new Error('Failed to get access token'));
					}
				},
				error_callback: (error: GoogleOAuthError) => {
					reject(new Error(error.message || error.error_description || 'OAuth error occurred'));
				}
			});
			tokenClient.requestAccessToken();
		});
	}
	return oauthToken;
};

const initialize = async (): Promise<void> => {
	if (!initialized) {
		await getCredentials();
		validateCredentials();
		await Promise.all([loadGoogleDriveApi(), loadGoogleAuthApi()]);
		initialized = true;
	}
};

interface PickerFileResult {
	id: string;
	name: string;
	url: string;
	blob: Blob;
	headers: {
		Authorization: string;
		Accept: string;
	};
}

export const createPicker = async (): Promise<PickerFileResult | null> => {
	try {
		console.log('Initializing Google Drive Picker...');
		await initialize();
		console.log('Getting auth token...');
		const token = await getAuthToken();
		if (!token) {
			console.error('Failed to get OAuth token');
			throw new Error('Unable to get OAuth token');
		}
		console.log('Auth token obtained successfully');

		return new Promise((resolve, reject) => {
			const picker = new google.picker.PickerBuilder()
				.enableFeature(google.picker.Feature.NAV_HIDDEN)
				.enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
				.addView(
					new google.picker.DocsView()
						.setIncludeFolders(false)
						.setSelectFolderEnabled(false)
						.setMimeTypes(
							'application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet,application/vnd.google-apps.presentation'
						)
				)
				.setOAuthToken(token)
				.setDeveloperKey(API_KEY)
				// Remove app ID setting as it's not needed and can cause 404 errors
				.setCallback(async (data: GooglePickerCallbackData) => {
					if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
						try {
							const doc = data[google.picker.Response.DOCUMENTS][0];
							const fileId = doc[google.picker.Document.ID];
							const fileName = doc[google.picker.Document.NAME];

							if (!fileId || !fileName) {
								throw new Error('Required file details missing');
							}

							// Construct download URL based on MIME type
							const mimeType = doc[google.picker.Document.MIME_TYPE];

							let downloadUrl;
							let exportFormat;

							if (mimeType.includes('google-apps')) {
								// Handle Google Workspace files
								if (mimeType.includes('document')) {
									exportFormat = 'text/plain';
								} else if (mimeType.includes('spreadsheet')) {
									exportFormat = 'text/csv';
								} else if (mimeType.includes('presentation')) {
									exportFormat = 'text/plain';
								} else {
									exportFormat = 'application/pdf';
								}
								downloadUrl = `https://www.googleapis.com/drive/v3/files/${fileId}/export?mimeType=${encodeURIComponent(exportFormat)}`;
							} else {
								// Regular files use direct download URL
								downloadUrl = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`;
							}
							// Create a Blob from the file download
							const response = await fetch(downloadUrl, {
								headers: {
									Authorization: `Bearer ${token}`,
									Accept: '*/*'
								}
							});

							if (!response.ok) {
								const errorText = await response.text();
								console.error('Download failed:', {
									status: response.status,
									statusText: response.statusText,
									error: errorText
								});
								throw new Error(`Failed to download file (${response.status}): ${errorText}`);
							}

							const blob = await response.blob();
							const result = {
								id: fileId,
								name: fileName,
								url: downloadUrl,
								blob: blob,
								headers: {
									Authorization: `Bearer ${token}`,
									Accept: '*/*'
								}
							};
							resolve(result);
						} catch (error) {
							reject(error);
						}
					} else if (data[google.picker.Response.ACTION] === google.picker.Action.CANCEL) {
						resolve(null);
					}
				})
				.build();
			picker.setVisible(true);
		});
	} catch (error) {
		console.error('Google Drive Picker error:', error);
		throw error;
	}
};
