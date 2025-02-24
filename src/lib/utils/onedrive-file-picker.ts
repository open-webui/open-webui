// src/lib/utils/onedrive-file-picker.ts
import { getToken } from './onedrive-auth';


const baseUrl = "https://onedrive.live.com/picker";
const params = {
	sdk: '8.0',
	entry: {
		oneDrive: {
			files: {}
		}
	},
	authentication: {},
	messaging: {
		origin: 'http://localhost:3000', // 현재 부모 페이지의 origin
		channelId: '27' // 메시징 채널용 임의의 ID
	},
	typesAndSources: {
		mode: 'files',
		pivots: {
			oneDrive: true,
			recent: true
		}
	}
};

/**
 * OneDrive 파일 피커 창을 열고, 사용자가 선택한 파일 메타데이터를 받아오는 함수
 */
export async function openOneDrivePicker(): Promise<any> {
	// SSR 환경(SvelteKit)에서 window 객체가 없을 수 있으므로 가드
	if (typeof window === 'undefined') {
		throw new Error('Not in browser environment');
	}

	return new Promise<any>(async (resolve, reject) => {
		let pickerWindow: Window | null = null;
		let channelPort: MessagePort | null = null;

		try {
			const authToken = await getToken();
			if (!authToken) {
				return reject(new Error('Failed to acquire access token'));
			}

			// 팝업 창 오픈
			pickerWindow = window.open('', 'OneDrivePicker', 'width=800,height=600');
			if (!pickerWindow) {
				return reject(new Error('Failed to open OneDrive picker window'));
			}

			// 쿼리스트링 구성
			const queryString = new URLSearchParams({
				filePicker: JSON.stringify(params)
			});
			const url = `${baseUrl}?${queryString.toString()}`;

			// 새로 연 window에 form을 동적으로 추가하여 POST
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

			// 부모 창에서 message 이벤트 수신
			const handleWindowMessage = (event: MessageEvent) => {
				// pickerWindow가 아닌 다른 window에서 온 메시지는 무시
				if (event.source !== pickerWindow) return;

				const message = event.data;

				// 초기화 메시지 => SharedWorker(MessageChannel) 식으로 포트 받기
				if (
					message?.type === 'initialize' &&
					message?.channelId === params.messaging.channelId
				) {
					channelPort = event.ports?.[0];
					if (!channelPort) return;

					channelPort.addEventListener('message', handlePortMessage);
					channelPort.start();

					// picker iframe에 'activate' 전달
					channelPort.postMessage({
						type: 'activate'
					});
				}
			};

			// 포트 메시지 핸들러
			const handlePortMessage = async (portEvent: MessageEvent) => {
				const portData = portEvent.data;
				switch (portData.type) {
					case 'notification':
						console.log('notification:', portData);
						break;

					case 'command': {
						// picker에 응답
						channelPort?.postMessage({
							type: 'acknowledge',
							id: portData.id
						});

						const command = portData.data;

						switch (command.command) {
							case 'authenticate': {
								// 재인증
								try {
									const newToken = await getToken();
									if (newToken) {
										channelPort?.postMessage({
											type: 'result',
											id: portData.id,
											data: {
												result: 'token',
												token: newToken
											}
										});
									} else {
										throw new Error('Could not retrieve auth token');
									}
								} catch (err) {
									console.error(err);
									channelPort?.postMessage({
										result: 'error',
										error: {
											code: 'tokenError',
											message: 'Failed to get token'
										},
										isExpected: true
									});
								}
								break;
							}

							case 'close': {
								// 사용자가 취소하거나 닫았을 경우
								cleanup();
								resolve(null);
								break;
							}

							case 'pick': {
								// 사용자가 파일 선택 완료
								console.log('Picked:', command);
								/**
								 * command 안에는 사용자가 선택한 파일들의 메타데이터 정보가 들어있습니다.
								 * 필요하다면 Microsoft Graph API 등을 통해 Blob(실제 파일 데이터)을 받아와야 할 수 있습니다.
								 */

								// picker에 응답
								channelPort?.postMessage({
									type: 'result',
									id: portData.id,
									data: {
										result: 'success'
									}
								});

								// 선택한 파일들(메타정보)을 resolve
								cleanup();
								resolve(command);
								break;
							}

							default: {
								console.warn('Unsupported command:', command);
								channelPort?.postMessage({
									result: 'error',
									error: {
										code: 'unsupportedCommand',
										message: command.command
									},
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

			// 메시지 이벤트 등록
			window.addEventListener('message', handleWindowMessage);
		} catch (err) {
			if (pickerWindow) pickerWindow.close();
			reject(err);
		}
	});
}
