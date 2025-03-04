import { v4 as uuidv4 } from 'uuid';

let CLIENT_ID = '';

async function getCredentials() {
	if (CLIENT_ID) return;
	const response = await fetch('/api/config');
	if (!response.ok) {
		throw new Error('Failed to fetch OneDrive credentials');
	}
	const config = await response.json();
	CLIENT_ID = config.onedrive?.client_id;
	if (!CLIENT_ID) {
		throw new Error('OneDrive client ID not configured');
	}
}

function loadMsalScript(): Promise<void> {
	return new Promise((resolve, reject) => {
		const win = window;
		if (win.msal) {
			resolve();
			return;
		}
		const script = document.createElement('script');
		script.src = 'https://alcdn.msauth.net/browser/2.19.0/js/msal-browser.min.js';
		script.async = true;
		script.onload = () => resolve();
		script.onerror = () => reject(new Error('Failed to load MSAL script'));
		document.head.appendChild(script);
	});
}

let msalInstance: any;

// Initialize MSAL authentication
async function initializeMsal() {
	if (!CLIENT_ID) {
		await getCredentials();
	}
	const msalParams = {
		auth: {
			authority: 'https://login.microsoftonline.com/consumers',
			clientId: CLIENT_ID
		}
	};
	try {
		await loadMsalScript();
		const win = window;
		msalInstance = new win.msal.PublicClientApplication(msalParams);
		if (msalInstance.initialize) {
			await msalInstance.initialize();
		}
	} catch (error) {
		console.error('MSAL initialization error:', error);
	}
}

// Retrieve OneDrive access token
async function getToken(): Promise<string> {
	const authParams = { scopes: ['OneDrive.ReadWrite'] };
	let accessToken = '';
	try {
		await initializeMsal();
		const resp = await msalInstance.acquireTokenSilent(authParams);
		accessToken = resp.accessToken;
	} catch (err) {
		const resp = await msalInstance.loginPopup(authParams);
		msalInstance.setActiveAccount(resp.account);
		if (resp.idToken) {
			const resp2 = await msalInstance.acquireTokenSilent(authParams);
			accessToken = resp2.accessToken;
		}
	}
	return accessToken;
}

const baseUrl = 'https://onedrive.live.com/picker';
const params = {
	sdk: '8.0',
	entry: {
		oneDrive: {
			files: {}
		}
	},
	authentication: {},
	messaging: {
		origin: window?.location?.origin,
		channelId: uuidv4()
	},
	typesAndSources: {
		mode: 'files',
		pivots: {
			oneDrive: true,
			recent: true
		}
	}
};

// Download file from OneDrive
async function downloadOneDriveFile(fileInfo: any): Promise<Blob> {
	const accessToken = await getToken();
	if (!accessToken) {
		throw new Error('Unable to retrieve OneDrive access token.');
	}
	const fileInfoUrl = `${fileInfo['@sharePoint.endpoint']}/drives/${fileInfo.parentReference.driveId}/items/${fileInfo.id}`;
	const response = await fetch(fileInfoUrl, {
		headers: {
			Authorization: `Bearer ${accessToken}`
		}
	});
	if (!response.ok) {
		throw new Error('Failed to fetch file information.');
	}
	const fileData = await response.json();
	const downloadUrl = fileData['@content.downloadUrl'];
	const downloadResponse = await fetch(downloadUrl);
	if (!downloadResponse.ok) {
		throw new Error('Failed to download file.');
	}
	return await downloadResponse.blob();
}

// Open OneDrive file picker and return selected file metadata
export async function openOneDrivePicker(): Promise<any | null> {
	if (typeof window === 'undefined') {
		throw new Error('Not in browser environment');
	}
	return new Promise((resolve, reject) => {
		let pickerWindow: Window | null = null;
		let channelPort: MessagePort | null = null;

		const handleWindowMessage = (event: MessageEvent) => {
			if (event.source !== pickerWindow) return;
			const message = event.data;
			if (message?.type === 'initialize' && message?.channelId === params.messaging.channelId) {
				channelPort = event.ports?.[0];
				if (!channelPort) return;
				channelPort.addEventListener('message', handlePortMessage);
				channelPort.start();
				channelPort.postMessage({ type: 'activate' });
			}
		};

		const handlePortMessage = async (portEvent: MessageEvent) => {
			const portData = portEvent.data;
			switch (portData.type) {
				case 'notification':
					break;
				case 'command': {
					channelPort?.postMessage({ type: 'acknowledge', id: portData.id });
					const command = portData.data;
					switch (command.command) {
						case 'authenticate': {
							try {
								const newToken = await getToken();
								if (newToken) {
									channelPort?.postMessage({
										type: 'result',
										id: portData.id,
										data: { result: 'token', token: newToken }
									});
								} else {
									throw new Error('Could not retrieve auth token');
								}
							} catch (err) {
								console.error(err);
								channelPort?.postMessage({
									result: 'error',
									error: { code: 'tokenError', message: 'Failed to get token' },
									isExpected: true
								});
							}
							break;
						}
						case 'close': {
							cleanup();
							resolve(null);
							break;
						}
						case 'pick': {
							channelPort?.postMessage({
								type: 'result',
								id: portData.id,
								data: { result: 'success' }
							});
							cleanup();
							resolve(command);
							break;
						}
						default: {
							console.warn('Unsupported command:', command);
							channelPort?.postMessage({
								result: 'error',
								error: { code: 'unsupportedCommand', message: command.command },
								isExpected: true
							});
							break;
						}
					}
					break;
				}
			}
		};

		function cleanup() {
			window.removeEventListener('message', handleWindowMessage);
			if (channelPort) {
				channelPort.removeEventListener('message', handlePortMessage);
			}
			if (pickerWindow) {
				pickerWindow.close();
				pickerWindow = null;
			}
		}

		const initializePicker = async () => {
			try {
				const authToken = await getToken();
				if (!authToken) {
					return reject(new Error('Failed to acquire access token'));
				}
				pickerWindow = window.open('', 'OneDrivePicker', 'width=800,height=600');
				if (!pickerWindow) {
					return reject(new Error('Failed to open OneDrive picker window'));
				}
				const queryString = new URLSearchParams({
					filePicker: JSON.stringify(params)
				});
				const url = `${baseUrl}?${queryString.toString()}`;
				const form = pickerWindow.document.createElement('form');
				form.setAttribute('action', url);
				form.setAttribute('method', 'POST');
				const input = pickerWindow.document.createElement('input');
				input.setAttribute('type', 'hidden');
				input.setAttribute('name', 'access_token');
				input.setAttribute('value', authToken);
				form.appendChild(input);
				pickerWindow.document.body.appendChild(form);
				form.submit();
				window.addEventListener('message', handleWindowMessage);
			} catch (err) {
				if (pickerWindow) pickerWindow.close();
				reject(err);
			}
		};

		initializePicker();
	});
}

// Pick and download file from OneDrive
export async function pickAndDownloadFile(): Promise<{ blob: Blob; name: string } | null> {
	try {
		const pickerResult = await openOneDrivePicker();
		if (!pickerResult || !pickerResult.items || pickerResult.items.length === 0) {
			return null;
		}
		const selectedFile = pickerResult.items[0];
		const blob = await downloadOneDriveFile(selectedFile);
		return { blob, name: selectedFile.name };
	} catch (error) {
		console.error('Error occurred during OneDrive file pick/download:', error);
		throw error;
	}
}

export { downloadOneDriveFile };
