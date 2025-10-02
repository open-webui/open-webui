// Google Drive Picker API configuration
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
		if (typeof gapi === 'undefined') {
			const script = document.createElement('script');
			script.src = 'https://apis.google.com/js/api.js';
			script.onload = () => {
				gapi.load('picker', () => {
					pickerApiLoaded = true;
					resolve(true);
				});
			};
			script.onerror = reject;
			document.body.appendChild(script);
		} else {
			gapi.load('picker', () => {
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

// Helper function to download a file from Google Drive
const downloadFile = async (fileId: string, fileName: string, mimeType: string, token: string) => {
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
	return {
		id: fileId,
		name: fileName,
		url: downloadUrl,
		blob: blob,
		headers: {
			Authorization: `Bearer ${token}`,
			Accept: '*/*'
		}
	};
};

// Helper function to list files in a folder
const listFilesInFolder = async (folderId: string, token: string) => {
	const response = await fetch(
		`https://www.googleapis.com/drive/v3/files?q='${folderId}'+in+parents&fields=files(id,name,mimeType)`,
		{
			headers: {
				Authorization: `Bearer ${token}`
			}
		}
	);

	if (!response.ok) {
		throw new Error('Failed to list files in folder');
	}

	const data = await response.json();
	return data.files || [];
};

export const createPicker = (options: { allowFolders?: boolean } = {}) => {
	const { allowFolders = false } = options;

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

			const picker = new google.picker.PickerBuilder()
				.enableFeature(google.picker.Feature.NAV_HIDDEN)
				.enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
				.addView(
					new google.picker.DocsView()
						.setIncludeFolders(allowFolders)
						.setSelectFolderEnabled(allowFolders)
						.setMimeTypes(
							allowFolders
								? 'application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet,application/vnd.google-apps.presentation,application/vnd.google-apps.folder'
								: 'application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet,application/vnd.google-apps.presentation'
						)
				)
				.setOAuthToken(token)
				.setDeveloperKey(API_KEY)
				// Remove app ID setting as it's not needed and can cause 404 errors
				.setCallback(async (data: any) => {
					if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
						try {
							const docs = data[google.picker.Response.DOCUMENTS];
							const results = [];

							for (const doc of docs) {
								const fileId = doc[google.picker.Document.ID];
								const fileName = doc[google.picker.Document.NAME];
								const mimeType = doc[google.picker.Document.MIME_TYPE];

								if (!fileId || !fileName) {
									throw new Error('Required file details missing');
								}

								// Check if it's a folder
								if (mimeType === 'application/vnd.google-apps.folder') {
									// List all files in the folder
									const filesInFolder = await listFilesInFolder(fileId, token);

									// Download each file in the folder
									for (const file of filesInFolder) {
										// Skip folders within folders for now
										if (file.mimeType !== 'application/vnd.google-apps.folder') {
											const result = await downloadFile(file.id, file.name, file.mimeType, token);
											results.push(result);
										}
									}
								} else {
									// Regular file
									const result = await downloadFile(fileId, fileName, mimeType, token);
									results.push(result);
								}
							}

							// Return single file or array of files
							resolve(results.length === 1 ? results[0] : results);
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
