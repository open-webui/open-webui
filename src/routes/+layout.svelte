<script>
	import { io } from 'socket.io-client';
	import { spring } from 'svelte/motion';
	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import { Toaster, toast } from 'svelte-sonner';

	let loadingProgress = spring(0, {
		stiffness: 0.05
	});

	import { onMount, tick, setContext, onDestroy } from 'svelte';
	import {
		config,
		user,
		settings,
		theme,
		WEBUI_NAME,
		WEBUI_VERSION,
		WEBUI_DEPLOYMENT_ID,
		mobile,
		socket,
		chatId,
		chats,
		currentChatPage,
		tags,
		temporaryChatEnabled,
		isLastActiveTab,
		isApp,
		appInfo,
		toolServers,
		playingNotificationSound,
		channels,
		channelId
	} from '$lib/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { updated } from '$app/state';

	import i18n, { initI18n, getLanguages, changeLanguage } from '$lib/i18n';

	import '../tailwind.css';
	import '../app.css';
	import 'tippy.js/dist/tippy.css';

	import { executeToolServer, getBackendConfig, getVersion } from '$lib/apis';
	import { getSessionUser, userSignOut } from '$lib/apis/auths';
	import { getAllTags, getChatList } from '$lib/apis/chats';
	import { chatCompletion } from '$lib/apis/openai';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL, WEBUI_HOSTNAME } from '$lib/constants';
	import { bestMatchingLanguage } from '$lib/utils';
	import { setTextScale } from '$lib/utils/text-scale';

	import NotificationToast from '$lib/components/NotificationToast.svelte';
	import AppSidebar from '$lib/components/app/AppSidebar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getUserSettings } from '$lib/apis/users';
	import dayjs from 'dayjs';
	import { getChannels } from '$lib/apis/channels';

	const unregisterServiceWorkers = async () => {
		if ('serviceWorker' in navigator) {
			try {
				const registrations = await navigator.serviceWorker.getRegistrations();
				await Promise.all(registrations.map((r) => r.unregister()));
				return true;
			} catch (error) {
				console.error('Error unregistering service workers:', error);
				return false;
			}
		}
		return false;
	};

	// handle frontend updates (https://svelte.dev/docs/kit/configuration#version)
	beforeNavigate(async ({ willUnload, to }) => {
		if (updated.current && !willUnload && to?.url) {
			await unregisterServiceWorkers();
			location.href = to.url.href;
		}
	});

	setContext('i18n', i18n);

	const bc = new BroadcastChannel('active-tab-channel');

	let loaded = false;
	let tokenTimer = null;

	let showRefresh = false;

	let heartbeatInterval = null;

	const BREAKPOINT = 768;

	const setupSocket = async (enableWebsocket) => {
		const _socket = io(`${WEBUI_BASE_URL}` || undefined, {
			reconnection: true,
			reconnectionDelay: 1000,
			reconnectionDelayMax: 5000,
			randomizationFactor: 0.5,
			path: '/ws/socket.io',
			transports: enableWebsocket ? ['websocket'] : ['polling', 'websocket'],
			auth: { token: localStorage.token }
		});
		await socket.set(_socket);

		_socket.on('connect_error', (err) => {
			console.log('connect_error', err);
		});

		_socket.on('connect', async () => {
			console.log('connected', _socket.id);
			const res = await getVersion(localStorage.token);

			const deploymentId = res?.deployment_id ?? null;
			const version = res?.version ?? null;

			if (version !== null || deploymentId !== null) {
				if (
					($WEBUI_VERSION !== null && version !== $WEBUI_VERSION) ||
					($WEBUI_DEPLOYMENT_ID !== null && deploymentId !== $WEBUI_DEPLOYMENT_ID)
				) {
					await unregisterServiceWorkers();
					location.href = location.href;
					return;
				}
			}

			// Send heartbeat every 30 seconds
			heartbeatInterval = setInterval(() => {
				if (_socket.connected) {
					console.log('Sending heartbeat');
					_socket.emit('heartbeat', {});
				}
			}, 30000);

			if (deploymentId !== null) {
				WEBUI_DEPLOYMENT_ID.set(deploymentId);
			}

			if (version !== null) {
				WEBUI_VERSION.set(version);
			}

			console.log('version', version);

			if (localStorage.getItem('token')) {
				// Emit user-join event with auth token
				_socket.emit('user-join', { auth: { token: localStorage.token } });
			} else {
				console.warn('No token found in localStorage, user-join event not emitted');
			}
		});

		_socket.on('reconnect_attempt', (attempt) => {
			console.log('reconnect_attempt', attempt);
		});

		_socket.on('reconnect_failed', () => {
			console.log('reconnect_failed');
		});

		_socket.on('disconnect', (reason, details) => {
			console.log(`Socket ${_socket.id} disconnected due to ${reason}`);

			if (heartbeatInterval) {
				clearInterval(heartbeatInterval);
				heartbeatInterval = null;
			}

			if (details) {
				console.log('Additional details:', details);
			}
		});
	};

	const executePythonAsWorker = async (id, code, cb) => {
		let result = null;
		let stdout = null;
		let stderr = null;

		let executing = true;
		let packages = [
			/\bimport\s+requests\b|\bfrom\s+requests\b/.test(code) ? 'requests' : null,
			/\bimport\s+bs4\b|\bfrom\s+bs4\b/.test(code) ? 'beautifulsoup4' : null,
			/\bimport\s+numpy\b|\bfrom\s+numpy\b/.test(code) ? 'numpy' : null,
			/\bimport\s+pandas\b|\bfrom\s+pandas\b/.test(code) ? 'pandas' : null,
			/\bimport\s+matplotlib\b|\bfrom\s+matplotlib\b/.test(code) ? 'matplotlib' : null,
			/\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
			/\bimport\s+sklearn\b|\bfrom\s+sklearn\b/.test(code) ? 'scikit-learn' : null,
			/\bimport\s+scipy\b|\bfrom\s+scipy\b/.test(code) ? 'scipy' : null,
			/\bimport\s+re\b|\bfrom\s+re\b/.test(code) ? 'regex' : null,
			/\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
			/\bimport\s+sympy\b|\bfrom\s+sympy\b/.test(code) ? 'sympy' : null,
			/\bimport\s+tiktoken\b|\bfrom\s+tiktoken\b/.test(code) ? 'tiktoken' : null,
			/\bimport\s+pytz\b|\bfrom\s+pytz\b/.test(code) ? 'pytz' : null
		].filter(Boolean);

		const pyodideWorker = new PyodideWorker();

		pyodideWorker.postMessage({
			id: id,
			code: code,
			packages: packages
		});

		setTimeout(() => {
			if (executing) {
				executing = false;
				stderr = 'Execution Time Limit Exceeded';
				pyodideWorker.terminate();

				if (cb) {
					cb(
						JSON.parse(
							JSON.stringify(
								{
									stdout: stdout,
									stderr: stderr,
									result: result
								},
								(_key, value) => (typeof value === 'bigint' ? value.toString() : value)
							)
						)
					);
				}
			}
		}, 60000);

		pyodideWorker.onmessage = (event) => {
			console.log('pyodideWorker.onmessage', event);
			const { id, ...data } = event.data;

			console.log(id, data);

			data['stdout'] && (stdout = data['stdout']);
			data['stderr'] && (stderr = data['stderr']);
			data['result'] && (result = data['result']);

			if (cb) {
				cb(
					JSON.parse(
						JSON.stringify(
							{
								stdout: stdout,
								stderr: stderr,
								result: result
							},
							(_key, value) => (typeof value === 'bigint' ? value.toString() : value)
						)
					)
				);
			}

			executing = false;
		};

		pyodideWorker.onerror = (event) => {
			console.log('pyodideWorker.onerror', event);

			if (cb) {
				cb(
					JSON.parse(
						JSON.stringify(
							{
								stdout: stdout,
								stderr: stderr,
								result: result
							},
							(_key, value) => (typeof value === 'bigint' ? value.toString() : value)
						)
					)
				);
			}
			executing = false;
		};
	};

	const executeTool = async (data, cb) => {
		const toolServer = $settings?.toolServers?.find((server) => server.url === data.server?.url);
		const toolServerData = $toolServers?.find((server) => server.url === data.server?.url);

		console.log('executeTool', data, toolServer);

		if (toolServer) {
			console.log(toolServer);

			let toolServerToken = null;
			const auth_type = toolServer?.auth_type ?? 'bearer';
			if (auth_type === 'bearer') {
				toolServerToken = toolServer?.key;
			} else if (auth_type === 'none') {
				// No authentication
			} else if (auth_type === 'session') {
				toolServerToken = localStorage.token;
			}

			const res = await executeToolServer(
				toolServerToken,
				toolServer.url,
				data?.name,
				data?.params,
				toolServerData
			);

			console.log('executeToolServer', res);
			if (cb) {
				cb(JSON.parse(JSON.stringify(res)));
			}
		} else {
			if (cb) {
				cb(
					JSON.parse(
						JSON.stringify({
							error: 'Tool Server Not Found'
						})
					)
				);
			}
		}
	};

	const chatEventHandler = async (event, cb) => {
		const chat = $page.url.pathname.includes(`/c/${event.chat_id}`);

		let isFocused = document.visibilityState !== 'visible';
		if (window.electronAPI) {
			const res = await window.electronAPI.send({
				type: 'window:isFocused'
			});
			if (res) {
				isFocused = res.isFocused;
			}
		}

		await tick();
		const type = event?.data?.type ?? null;
		const data = event?.data?.data ?? null;

		if ((event.chat_id !== $chatId && !$temporaryChatEnabled) || isFocused) {
			if (type === 'chat:completion') {
				const { done, content, title } = data;

				if (done) {
					if ($settings?.notificationSoundAlways ?? false) {
						playingNotificationSound.set(true);

						const audio = new Audio(`/audio/notification.mp3`);
						audio.play().finally(() => {
							// Ensure the global state is reset after the sound finishes
							playingNotificationSound.set(false);
						});
					}

					if ($isLastActiveTab) {
						if ($settings?.notificationEnabled ?? false) {
							new Notification(`${title} • Open WebUI`, {
								body: content,
								icon: `${WEBUI_BASE_URL}/static/favicon.png`
							});
						}
					}

					toast.custom(NotificationToast, {
						componentProps: {
							onClick: () => {
								goto(`/c/${event.chat_id}`);
							},
							content: content,
							title: title
						},
						duration: 15000,
						unstyled: true
					});
				}
			} else if (type === 'chat:title') {
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			} else if (type === 'chat:tags') {
				tags.set(await getAllTags(localStorage.token));
			}
		} else if (data?.session_id === $socket.id) {
			if (type === 'execute:python') {
				console.log('execute:python', data);
				executePythonAsWorker(data.id, data.code, cb);
			} else if (type === 'execute:tool') {
				console.log('execute:tool', data);
				executeTool(data, cb);
			} else if (type === 'request:chat:completion') {
				console.log(data, $socket.id);
				const { session_id, channel, form_data, model } = data;

				try {
					const directConnections = $settings?.directConnections ?? {};

					if (directConnections) {
						const urlIdx = model?.urlIdx;

						const OPENAI_API_URL = directConnections.OPENAI_API_BASE_URLS[urlIdx];
						const OPENAI_API_KEY = directConnections.OPENAI_API_KEYS[urlIdx];
						const API_CONFIG = directConnections.OPENAI_API_CONFIGS[urlIdx];

						try {
							if (API_CONFIG?.prefix_id) {
								const prefixId = API_CONFIG.prefix_id;
								form_data['model'] = form_data['model'].replace(`${prefixId}.`, ``);
							}

							const [res, controller] = await chatCompletion(
								OPENAI_API_KEY,
								form_data,
								OPENAI_API_URL
							);

							if (res) {
								// raise if the response is not ok
								if (!res.ok) {
									throw await res.json();
								}

								if (form_data?.stream ?? false) {
									cb({
										status: true
									});
									console.log({ status: true });

									// res will either be SSE or JSON
									const reader = res.body.getReader();
									const decoder = new TextDecoder();

									const processStream = async () => {
										while (true) {
											// Read data chunks from the response stream
											const { done, value } = await reader.read();
											if (done) {
												break;
											}

											// Decode the received chunk
											const chunk = decoder.decode(value, { stream: true });

											// Process lines within the chunk
											const lines = chunk.split('\n').filter((line) => line.trim() !== '');

											for (const line of lines) {
												console.log(line);
												$socket?.emit(channel, line);
											}
										}
									};

									// Process the stream in the background
									await processStream();
								} else {
									const data = await res.json();
									cb(data);
								}
							} else {
								throw new Error('An error occurred while fetching the completion');
							}
						} catch (error) {
							console.error('chatCompletion', error);
							cb(error);
						}
					}
				} catch (error) {
					console.error('chatCompletion', error);
					cb(error);
				} finally {
					$socket.emit(channel, {
						done: true
					});
				}
			} else {
				console.log('chatEventHandler', event);
			}
		}
	};

	const channelEventHandler = async (event) => {
		console.log('channelEventHandler', event);
		if (event.data?.type === 'typing') {
			return;
		}

		// handle channel created event
		if (event.data?.type === 'channel:created') {
			await channels.set(
				(await getChannels(localStorage.token)).sort(
					(a, b) =>
						['', null, 'group', 'dm'].indexOf(a.type) - ['', null, 'group', 'dm'].indexOf(b.type)
				)
			);
			return;
		}

		// check url path
		const channel = $page.url.pathname.includes(`/channels/${event.channel_id}`);

		let isFocused = document.visibilityState !== 'visible';
		if (window.electronAPI) {
			const res = await window.electronAPI.send({
				type: 'window:isFocused'
			});
			if (res) {
				isFocused = res.isFocused;
			}
		}

		if ((!channel || isFocused) && event?.user?.id !== $user?.id) {
			await tick();
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if ($channels) {
				if ($channels.find((ch) => ch.id === event.channel_id) && $channelId !== event.channel_id) {
					channels.set(
						$channels.map((ch) => {
							if (ch.id === event.channel_id) {
								if (type === 'message') {
									return {
										...ch,
										unread_count: (ch.unread_count ?? 0) + 1,
										last_message_at: event.created_at
									};
								}
							}
							return ch;
						})
					);
				} else {
					await channels.set(
						(await getChannels(localStorage.token)).sort(
							(a, b) =>
								['', null, 'group', 'dm'].indexOf(a.type) -
								['', null, 'group', 'dm'].indexOf(b.type)
						)
					);
				}
			}

			if (type === 'message') {
				const title = `${data?.user?.name}${event?.channel?.type !== 'dm' ? ` (#${event?.channel?.name})` : ''}`;

				if ($isLastActiveTab) {
					if ($settings?.notificationEnabled ?? false) {
						new Notification(`${title} • Open WebUI`, {
							body: data?.content,
							icon: `${WEBUI_API_BASE_URL}/users/${data?.user?.id}/profile/image`
						});
					}
				}

				toast.custom(NotificationToast, {
					componentProps: {
						onClick: () => {
							goto(`/channels/${event.channel_id}`);
						},
						content: data?.content,
						title: `${title}`
					},
					duration: 15000,
					unstyled: true
				});
			}
		}
	};

	const TOKEN_EXPIRY_BUFFER = 60; // seconds
	const checkTokenExpiry = async () => {
		const exp = $user?.expires_at; // token expiry time in unix timestamp
		const now = Math.floor(Date.now() / 1000); // current time in unix timestamp

		if (!exp) {
			// If no expiry time is set, do nothing
			return;
		}

		if (now >= exp - TOKEN_EXPIRY_BUFFER) {
			const res = await userSignOut();
			user.set(null);
			localStorage.removeItem('token');

			location.href = res?.redirect_url ?? '/auth';
		}
	};

	onMount(async () => {
		let touchstartY = 0;

		function isNavOrDescendant(el) {
			const nav = document.querySelector('nav'); // change selector if needed
			return nav && (el === nav || nav.contains(el));
		}

		document.addEventListener('touchstart', (e) => {
			if (!isNavOrDescendant(e.target)) return;
			touchstartY = e.touches[0].clientY;
		});

		document.addEventListener('touchmove', (e) => {
			if (!isNavOrDescendant(e.target)) return;
			const touchY = e.touches[0].clientY;
			const touchDiff = touchY - touchstartY;
			if (touchDiff > 50 && window.scrollY === 0) {
				showRefresh = true;
				e.preventDefault();
			}
		});

		document.addEventListener('touchend', (e) => {
			if (!isNavOrDescendant(e.target)) return;
			if (showRefresh) {
				showRefresh = false;
				location.reload();
			}
		});

		if (typeof window !== 'undefined') {
			if (window.applyTheme) {
				window.applyTheme();
			}
		}

		if (window?.electronAPI) {
			const info = await window.electronAPI.send({
				type: 'app:info'
			});

			if (info) {
				isApp.set(true);
				appInfo.set(info);

				const data = await window.electronAPI.send({
					type: 'app:data'
				});

				if (data) {
					appData.set(data);
				}
			}
		}

		// Listen for messages on the BroadcastChannel
		bc.onmessage = (event) => {
			if (event.data === 'active') {
				isLastActiveTab.set(false); // Another tab became active
			}
		};

		// Set yourself as the last active tab when this tab is focused
		const handleVisibilityChange = () => {
			if (document.visibilityState === 'visible') {
				isLastActiveTab.set(true); // This tab is now the active tab
				bc.postMessage('active'); // Notify other tabs that this tab is active

				// Check token expiry when the tab becomes active
				checkTokenExpiry();
			}
		};

		// Add event listener for visibility state changes
		document.addEventListener('visibilitychange', handleVisibilityChange);

		// Call visibility change handler initially to set state on load
		handleVisibilityChange();

		theme.set(localStorage.theme);

		mobile.set(window.innerWidth < BREAKPOINT);

		const onResize = () => {
			if (window.innerWidth < BREAKPOINT) {
				mobile.set(true);
			} else {
				mobile.set(false);
			}
		};
		window.addEventListener('resize', onResize);

		user.subscribe(async (value) => {
			if (value) {
				$socket?.off('events', chatEventHandler);
				$socket?.off('events:channel', channelEventHandler);

				$socket?.on('events', chatEventHandler);
				$socket?.on('events:channel', channelEventHandler);

				const userSettings = await getUserSettings(localStorage.token);
				if (userSettings) {
					settings.set(userSettings.ui);
				} else {
					settings.set(JSON.parse(localStorage.getItem('settings') ?? '{}'));
				}
				setTextScale($settings?.textScale ?? 1);

				// Set up the token expiry check
				if (tokenTimer) {
					clearInterval(tokenTimer);
				}
				tokenTimer = setInterval(checkTokenExpiry, 15000);
			} else {
				$socket?.off('events', chatEventHandler);
				$socket?.off('events:channel', channelEventHandler);
			}
		});

		let backendConfig = null;
		try {
			backendConfig = await getBackendConfig();
			console.log('Backend config:', backendConfig);
		} catch (error) {
			console.error('Error loading backend config:', error);
		}
		// Initialize i18n even if we didn't get a backend config,
		// so `/error` can show something that's not `undefined`.

		initI18n(localStorage?.locale);
		if (!localStorage.locale) {
			const languages = await getLanguages();
			const browserLanguages = navigator.languages
				? navigator.languages
				: [navigator.language || navigator.userLanguage];
			const lang = backendConfig.default_locale
				? backendConfig.default_locale
				: bestMatchingLanguage(languages, browserLanguages, 'en-US');
			changeLanguage(lang);
			dayjs.locale(lang);
		}

		if (backendConfig) {
			// Save Backend Status to Store
			await config.set(backendConfig);
			await WEBUI_NAME.set(backendConfig.name);

			if ($config) {
				await setupSocket($config.features?.enable_websocket ?? true);

				const currentUrl = `${window.location.pathname}${window.location.search}`;
				const encodedUrl = encodeURIComponent(currentUrl);

				if (localStorage.token) {
					// Get Session User Info
					const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					});

					if (sessionUser) {
						await user.set(sessionUser);
						await config.set(await getBackendConfig());
					} else {
						// Redirect Invalid Session User to /auth Page
						localStorage.removeItem('token');
						await goto(`/auth?redirect=${encodedUrl}`);
					}
				} else {
					// Don't redirect if we're already on the auth page
					// Needed because we pass in tokens from OAuth logins via URL fragments
					if ($page.url.pathname !== '/auth') {
						await goto(`/auth?redirect=${encodedUrl}`);
					}
				}
			}
		} else {
			// Redirect to /error when Backend Not Detected
			await goto(`/error`);
		}

		await tick();

		if (
			document.documentElement.classList.contains('her') &&
			document.getElementById('progress-bar')
		) {
			loadingProgress.subscribe((value) => {
				const progressBar = document.getElementById('progress-bar');

				if (progressBar) {
					progressBar.style.width = `${value}%`;
				}
			});

			await loadingProgress.set(100);

			document.getElementById('splash-screen')?.remove();

			const audio = new Audio(`/audio/greeting.mp3`);
			const playAudio = () => {
				audio.play();
				document.removeEventListener('click', playAudio);
			};

			document.addEventListener('click', playAudio);

			loaded = true;
		} else {
			document.getElementById('splash-screen')?.remove();
			loaded = true;
		}

		return () => {
			window.removeEventListener('resize', onResize);
		};
	});
</script>

<svelte:head>
	<title>{$WEBUI_NAME}</title>
	<link crossorigin="anonymous" rel="icon" href="{WEBUI_BASE_URL}/static/favicon.png" />

	<meta name="apple-mobile-web-app-title" content={$WEBUI_NAME} />
	<meta name="description" content={$WEBUI_NAME} />
	<link
		rel="search"
		type="application/opensearchdescription+xml"
		title={$WEBUI_NAME}
		href="/opensearch.xml"
		crossorigin="use-credentials"
	/>
</svelte:head>

{#if showRefresh}
	<div class=" py-5">
		<Spinner className="size-5" />
	</div>
{/if}

{#if loaded}
	{#if $isApp}
		<div class="flex flex-row h-screen">
			<AppSidebar />

			<div class="w-full flex-1 max-w-[calc(100%-4.5rem)]">
				<slot />
			</div>
		</div>
	{:else}
		<slot />
	{/if}
{/if}

<Toaster
	theme={$theme.includes('dark')
		? 'dark'
		: $theme === 'system'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
				? 'dark'
				: 'light'
			: 'light'}
	richColors
	position="top-right"
	closeButton
/>
