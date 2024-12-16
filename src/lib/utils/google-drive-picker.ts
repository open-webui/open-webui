// Google Drive Picker API configuration
const API_KEY = import.meta.env.VITE_GOOGLE_API_KEY;
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const SCOPE = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file'];

// Validate required credentials
const validateCredentials = () => {
    if (!API_KEY || !CLIENT_ID) {
        throw new Error('Google Drive API credentials not configured');
    }
    if (API_KEY === 'your-api-key' || CLIENT_ID === 'your-client-id') {
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

            const picker = new google.picker.PickerBuilder()
                .enableFeature(google.picker.Feature.NAV_HIDDEN)
                .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
                .addView(new google.picker.DocsView()
                    .setIncludeFolders(false)
                    .setSelectFolderEnabled(false)
                    .setMimeTypes('application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document'))
                .setOAuthToken(token)
                .setDeveloperKey(API_KEY)
                // Remove app ID setting as it's not needed and can cause 404 errors
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
                                    exportFormat = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
                                } else if (mimeType.includes('presentation')) {
                                    exportFormat = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
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
                                    'Authorization': `Bearer ${token}`,
                                    'Accept': '*/*'
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
                                    'Authorization': `Bearer ${token}`,
                                    'Accept': '*/*'
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
