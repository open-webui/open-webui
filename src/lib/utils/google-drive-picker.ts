// Google Drive Picker API configuration
const API_KEY = import.meta.env.VITE_GOOGLE_API_KEY;
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const SCOPE = ['https://www.googleapis.com/auth/drive.readonly'];

let pickerApiLoaded = false;
let oauthToken: string | null = null;
let initialized = false;

export const loadGoogleDriveApi = () => {
    return new Promise((resolve, reject) => {
        if (typeof gapi === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://apis.google.com/js/api.js';
            script.onload = () => {
                gapi.load('picker', {
                    callback: () => {
                        pickerApiLoaded = true;
                        resolve(true);
                    }
                });
            };
            script.onerror = reject;
            document.body.appendChild(script);
        } else {
            gapi.load('picker', {
                callback: () => {
                    pickerApiLoaded = true;
                    resolve(true);
                }
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
        const tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: CLIENT_ID,
            scope: SCOPE.join(' '),
            callback: (response: any) => {
                if (response.access_token) {
                    oauthToken = response.access_token;
                }
            },
        });
        await tokenClient.requestAccessToken();
    }
    return oauthToken;
};

const initialize = async () => {
    if (!initialized) {
        await Promise.all([loadGoogleDriveApi(), loadGoogleAuthApi()]);
        initialized = true;
    }
};

export const createPicker = () => {
    return new Promise(async (resolve, reject) => {
        try {
            await initialize();
            const token = await getAuthToken();
            if (!token) {
                throw new Error('Unable to get OAuth token');
            }

            const picker = new google.picker.PickerBuilder()
                .addView(google.picker.ViewId.DOCS)
                .setOAuthToken(token)
                .setDeveloperKey(API_KEY)
                .setCallback((data: any) => {
                    if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
                        const doc = data[google.picker.Response.DOCUMENTS][0];
                        const fileId = doc[google.picker.Document.ID];
                        const fileName = doc[google.picker.Document.NAME];
                        const fileUrl = doc[google.picker.Document.URL];
                        
                        resolve({
                            id: fileId,
                            name: fileName,
                            url: fileUrl
                        });
                    } else if (data[google.picker.Response.ACTION] === google.picker.Action.CANCEL) {
                        resolve(null);
                    }
                })
                .build();
            picker.setVisible(true);
        } catch (error) {
            reject(error);
        }
    });
};
