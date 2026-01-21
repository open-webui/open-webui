// Google Drive Picker API configuration

// Declare global types for Google APIs
declare const gapi: {
	load: (api: string, callback: () => void) => void;
};

declare const google: {
	accounts: {
		oauth2: {
			initTokenClient: (config: {
				client_id: string;
				scope: string;
				callback: (response: { access_token?: string }) => void;
				error_callback: (error: { message?: string }) => void;
			}) => {
				requestAccessToken: () => void;
			};
		};
	};
	picker: {
		PickerBuilder: new () => {
			enableFeature: (feature: unknown) => unknown;
			addView: (view: unknown) => unknown;
			setOAuthToken: (token: string) => unknown;
			setDeveloperKey: (key: string) => unknown;
			setCallback: (callback: (data: Record<string, unknown>) => void) => unknown;
			build: () => { setVisible: (visible: boolean) => void };
		};
		DocsView: new () => {
			setIncludeFolders: (include: boolean) => unknown;
			setSelectFolderEnabled: (enabled: boolean) => unknown;
			setMimeTypes: (types: string) => unknown;
		};
		Feature: {
			NAV_HIDDEN: unknown;
			MULTISELECT_ENABLED: unknown;
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

let API_KEY = '';
let CLIENT_ID = '';

// Function to fetch credentials from backend config
async function getCredentials() {
	const response = await fetch('/api/config');
	if (!response.ok) {
		throw new Error('Failed to fetch Google Drive credentials');
	}
	const config = await response.json();
	API_KEY = config.google_drive?.api_key;
	CLIENT_ID = config.google_drive?.client_id;

	if (!API_KEY || !CLIENT_ID) {
		throw new Error('Google Drive API credentials not configured');
	}
}
const SCOPE = [
	'https://www.googleapis.com/auth/drive.readonly',
	'https://www.googleapis.com/auth/drive.file'
];

// Validate required credentials
const validateCredentials = () => {
	if (!API_KEY || !CLIENT_ID) {
		throw new Error('Google Drive API credentials not configured');
	}
	if (API_KEY === '' || CLIENT_ID === '') {
		throw new Error('Please configure valid Google Drive API credentials');
	}
};

let pickerApiLoaded = false;
let oauthToken: string | null = null;
let initialized = false;

export const loadGoogleDriveApi = () => {
	return new Promise((resolve, reject) => {
		// Check if gapi is available in window
		const windowGapi = (window as unknown as { gapi?: typeof gapi }).gapi;
		if (!windowGapi) {
			const script = document.createElement('script');
			script.src = 'https://apis.google.com/js/api.js';
			script.onload = () => {
				const loadedGapi = (window as unknown as { gapi: typeof gapi }).gapi;
				loadedGapi.load('picker', () => {
					pickerApiLoaded = true;
					resolve(true);
				});
			};
			script.onerror = reject;
			document.body.appendChild(script);
		} else {
			windowGapi.load('picker', () => {
				pickerApiLoaded = true;
				resolve(true);
			});
		}
	});
};

export const loadGoogleAuthApi = () => {
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

export const getAuthToken = async () => {
	if (!oauthToken) {
		return new Promise((resolve, reject) => {
			const tokenClient = google.accounts.oauth2.initTokenClient({
				client_id: CLIENT_ID,
				scope: SCOPE.join(' '),
				callback: (response: any) => {
					if (response.access_token) {
						oauthToken = response.access_token;
						resolve(oauthToken);
					} else {
						reject(new Error('Failed to get access token'));
					}
				},
				error_callback: (error: any) => {
					reject(new Error(error.message || 'OAuth error occurred'));
				}
			});
			tokenClient.requestAccessToken();
		});
	}
	return oauthToken;
};

const initialize = async () => {
	if (!initialized) {
		await getCredentials();
		validateCredentials();
		await Promise.all([loadGoogleDriveApi(), loadGoogleAuthApi()]);
		initialized = true;
	}
};

export const createPicker = () => {
	return new Promise(async (resolve, reject) => {
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

			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const pickerBuilder = new google.picker.PickerBuilder() as any;
			const picker = pickerBuilder
				.enableFeature(google.picker.Feature.NAV_HIDDEN)
				.enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
				.addView(
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					(new google.picker.DocsView() as any)
						.setIncludeFolders(false)
						.setSelectFolderEnabled(false)
						.setMimeTypes(
							'application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet,application/vnd.google-apps.presentation'
						)
				)
				.setOAuthToken(token as string)
				.setDeveloperKey(API_KEY)
				// Remove app ID setting as it's not needed and can cause 404 errors
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				.setCallback(async (data: any) => {
					if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
						try {
							const doc = data[google.picker.Response.DOCUMENTS][0];
							const fileId = doc[google.picker.Document.ID];
							const fileName = doc[google.picker.Document.NAME];
							const fileUrl = doc[google.picker.Document.URL];

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
		} catch (error) {
			console.error('Google Drive Picker error:', error);
			reject(error);
		}
	});
};
