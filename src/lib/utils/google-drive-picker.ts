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
                    console.log('Picker callback received:', data);
                    if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
                        try {
                            console.log('File picked from Google Drive');
                            const doc = data[google.picker.Response.DOCUMENTS][0];
                            console.log('Document object:', doc);
                            
                            const fileId = doc[google.picker.Document.ID];
                            const fileName = doc[google.picker.Document.NAME];
                            const fileUrl = doc[google.picker.Document.URL];
                            
                            console.log('Extracted file details:', {
                                id: fileId,
                                name: fileName,
                                url: fileUrl
                            });
                            
                            if (!fileId || !fileName) {
                                throw new Error('Required file details missing');
                            }
                        
                            // Construct download URL using usercontent format
                            console.log('Constructing download URL for fileId:', fileId);
                            const downloadUrl = `https://drive.usercontent.google.com/u/0/uc?id=${fileId}&export=download`;
                            console.log('Download URL constructed:', downloadUrl);

                            console.log('Current token value:', token ? 'Token exists' : 'No token');
                            // Create a Blob from the file download
                            console.log('Fetching file content...');
                            const response = await fetch(downloadUrl, {
                                headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Accept': '*/*'
                                }
                            });

                            if (!response.ok) {
                                throw new Error(`Failed to download file: ${response.statusText}`);
                            }

                            const blob = await response.blob();
                            console.log('File downloaded, size:', blob.size);

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
                            console.log('Created result object with blob');
                            resolve(result);
                        } catch (error) {
                            console.error('Error in picker callback:', error);
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
