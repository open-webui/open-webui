<script lang="ts">
	import toast from 'svelte-french-toast';
	import { models, settings, user } from '$lib/stores';

	import { getOllamaModels } from '$lib/apis/ollama';
	import { getOpenAIModels } from '$lib/apis/openai';

	import {
		getOllamaVersion,
		getOllamaModels,
		getOllamaAPIUrl,
		updateOllamaAPIUrl,
		pullModel,
		createModel,
		deleteModel
	} from '$lib/apis/ollama';
	import { updateUserPassword } from '$lib/apis/auths';
	import { createNewChat, deleteAllChats, getAllChats, getChatList } from '$lib/apis/chats';
	import { WEB_UI_VERSION, WEBUI_API_BASE_URL } from '$lib/constants';

	import { config, models, settings, user, chats, theme } from '$lib/stores';
	import { splitStream, getGravatarURL, getImportOrigin, convertOpenAIChats } from '$lib/utils';

	import Advanced from './Settings/Advanced.svelte';
	import Modal from '../common/Modal.svelte';
	import Account from './Settings/Account.svelte';
	import Advanced from './Settings/Advanced.svelte';
	import About from './Settings/About.svelte';
	import Models from './Settings/Models.svelte';
	import General from './Settings/General.svelte';
	import External from './Settings/External.svelte';
	import Interface from './Settings/Interface.svelte';
	import Voice from './Settings/Voice.svelte';
	import Chats from './Settings/Chats.svelte';

	export let show = false;

	const saveSettings = async (updated) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		localStorage.setItem('settings', JSON.stringify($settings));
	};

	let selectedTab = 'general';

	// General
	let API_BASE_URL = '';
	let themes = ['dark', 'light', 'rose-pine dark', 'rose-pine-dawn light', 'thoughtworks dark'];
	let selectedTheme = 'dark';
	let notificationEnabled = false;
	let system = '';

	// Advanced
	let requestFormat = '';
	let options = {
		// Advanced
		seed: 0,
		temperature: '',
		repeat_penalty: '',
		repeat_last_n: '',
		mirostat: '',
		mirostat_eta: '',
		mirostat_tau: '',
		top_k: '',
		top_p: '',
		stop: '',
		tfs_z: '',
		num_ctx: '',
		num_predict: ''
	};

	// Models
	const MAX_PARALLEL_DOWNLOADS = 3;
	const modelDownloadQueue = queue(
		(task: { modelName: string }, cb) =>
			pullModelHandlerProcessor({ modelName: task.modelName, callback: cb }),
		MAX_PARALLEL_DOWNLOADS
	);
	let modelDownloadStatus: Record<string, any> = {};

	let modelTransferring = false;
	let modelTag = '';
	let digest = '';
	let pullProgress = null;

	let modelUploadMode = 'file';
	let modelInputFile = '';
	let modelFileUrl = '';
	let modelFileContent = `TEMPLATE """{{ .System }}\nUSER: {{ .Prompt }}\nASSSISTANT: """\nPARAMETER num_ctx 4096\nPARAMETER stop "</s>"\nPARAMETER stop "USER:"\nPARAMETER stop "ASSSISTANT:"`;
	let modelFileDigest = '';
	let uploadProgress = null;

	let deleteModelTag = '';

	// External
	let OPENAI_API_KEY = '';
	let OPENAI_API_BASE_URL = '';

	// Addons
	let titleAutoGenerate = true;
	let speechAutoSend = false;
	let responseAutoCopy = false;

	let gravatarEmail = '';
	let titleAutoGenerateModel = '';

	// Chats
	let saveChatHistory = true;
	let importFiles;
	let showDeleteConfirm = false;

	// Auth
	let authEnabled = false;
	let authType = 'Basic';
	let authContent = '';

	// Account
	let currentPassword = '';
	let newPassword = '';
	let newPasswordConfirm = '';

	// About
	let ollamaVersion = '';

	$: if (importFiles) {
		console.log(importFiles);

		let reader = new FileReader();
		reader.onload = (event) => {
			let chats = JSON.parse(event.target.result);
			console.log(chats);
			if (getImportOrigin(chats) == 'openai') {
				try {
					chats = convertOpenAIChats(chats);
				} catch (error) {
					console.log('Unable to import chats:', error);
				}
			}
			importChats(chats);
		};

		if (importFiles.length > 0) {
			reader.readAsText(importFiles[0]);
		}
	}

	const importChats = async (_chats) => {
		for (const chat of _chats) {
			console.log(chat);

			if (chat.chat) {
				await createNewChat(localStorage.token, chat.chat);
			} else {
				await createNewChat(localStorage.token, chat);
			}
		}

		await chats.set(await getChatList(localStorage.token));
	};

	const exportChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `chat-export-${Date.now()}.json`);
	};

	const deleteChats = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token);
		await chats.set(await getChatList(localStorage.token));
	};

	const updateOllamaAPIUrlHandler = async () => {
		API_BASE_URL = await updateOllamaAPIUrl(localStorage.token, API_BASE_URL);
		const _models = await getModels('ollama');

		if (_models.length > 0) {
			toast.success('Server connection verified');
			await models.set(_models);
		}
	};

	const updateOpenAIHandler = async () => {
		OPENAI_API_BASE_URL = await updateOpenAIUrl(localStorage.token, OPENAI_API_BASE_URL);
		OPENAI_API_KEY = await updateOpenAIKey(localStorage.token, OPENAI_API_KEY);

		await models.set(await getModels());
	};

	const toggleTheme = async () => {
		if (selectedTheme === 'dark') {
			selectedTheme = 'light';
		} else {
			selectedTheme = 'dark';
		}

		localStorage.theme = selectedTheme;

		document.documentElement.classList.remove(selectedTheme === 'dark' ? 'light' : 'dark');
		document.documentElement.classList.add(selectedTheme);
	};

	const toggleRequestFormat = async () => {
		if (requestFormat === '') {
			requestFormat = 'json';
		} else {
			requestFormat = '';
		}

		saveSettings({ requestFormat: requestFormat !== '' ? requestFormat : undefined });
	};

	const toggleSpeechAutoSend = async () => {
		speechAutoSend = !speechAutoSend;
		saveSettings({ speechAutoSend: speechAutoSend });
	};

	const toggleTitleAutoGenerate = async () => {
		titleAutoGenerate = !titleAutoGenerate;
		saveSettings({ titleAutoGenerate: titleAutoGenerate });
	};

	const toggleNotification = async () => {
		const permission = await Notification.requestPermission();

		if (permission === 'granted') {
			notificationEnabled = !notificationEnabled;
			saveSettings({ notificationEnabled: notificationEnabled });
		} else {
			toast.error(
				'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
			);
		}
	};

	const toggleResponseAutoCopy = async () => {
		const permission = await navigator.clipboard
			.readText()
			.then(() => {
				return 'granted';
			})
			.catch(() => {
				return '';
			});

		console.log(permission);

		if (permission === 'granted') {
			responseAutoCopy = !responseAutoCopy;
			saveSettings({ responseAutoCopy: responseAutoCopy });
		} else {
			toast.error(
				'Clipboard write permission denied. Please check your browser settings to grant the necessary access.'
			);
		}
	};

	const toggleSaveChatHistory = async () => {
		saveChatHistory = !saveChatHistory;
		console.log(saveChatHistory);

		if (saveChatHistory === false) {
			await goto('/');
		}
		saveSettings({ saveChatHistory: saveChatHistory });
	};

	const pullModelHandlerProcessor = async (opts: { modelName: string; callback: Function }) => {
		const res = await pullModel(localStorage.token, opts.modelName).catch((error) => {
			opts.callback({ success: false, error, modelName: opts.modelName });
			return null;
		});

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							if (data.error) {
								throw data.error;
							}
							if (data.detail) {
								throw data.detail;
							}
							if (data.status) {
								if (data.digest) {
									let downloadProgress = 0;
									if (data.completed) {
										downloadProgress = Math.round((data.completed / data.total) * 1000) / 10;
									} else {
										downloadProgress = 100;
									}
									modelDownloadStatus[opts.modelName] = {
										pullProgress: downloadProgress,
										digest: data.digest
									};
								} else {
									toast.success(data.status);
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
					if (typeof error !== 'string') {
						error = error.message;
					}
					opts.callback({ success: false, error, modelName: opts.modelName });
				}
			}
			opts.callback({ success: true, modelName: opts.modelName });
		}
	};

	const pullModelHandler = async () => {
		const sanitizedModelTag = modelTag.trim();
		if (modelDownloadStatus[sanitizedModelTag]) {
			toast.error(`Model '${sanitizedModelTag}' is already in queue for downloading.`);
			return;
		}
		if (Object.keys(modelDownloadStatus).length === 3) {
			toast.error('Maximum of 3 models can be downloaded simultaneously. Please try again later.');
			return;
		}

		modelTransferring = true;

		modelDownloadQueue.push(
			{ modelName: sanitizedModelTag },
			async (data: { modelName: string; success: boolean; error?: Error }) => {
				const { modelName } = data;
				// Remove the downloaded model
				delete modelDownloadStatus[modelName];

				console.log(data);

				if (!data.success) {
					toast.error(data.error);
				} else {
					toast.success(`Model '${modelName}' has been successfully downloaded.`);

					const notification = new Notification(`Ollama`, {
						body: `Model '${modelName}' has been successfully downloaded.`,
						icon: '/favicon.png'
					});

					models.set(await getModels());
				}
			}
		);

		modelTag = '';
		modelTransferring = false;
	};

	const uploadModelHandler = async () => {
		modelTransferring = true;
		uploadProgress = 0;

		let uploaded = false;
		let fileResponse = null;
		let name = '';

		if (modelUploadMode === 'file') {
			const file = modelInputFile[0];
			const formData = new FormData();
			formData.append('file', file);

			fileResponse = await fetch(`${WEBUI_API_BASE_URL}/utils/upload`, {
				method: 'POST',
				headers: {
					...($user && { Authorization: `Bearer ${localStorage.token}` })
				},
				body: formData
			}).catch((error) => {
				console.log(error);
				return null;
			});
		} else {
			fileResponse = await fetch(`${WEBUI_API_BASE_URL}/utils/download?url=${modelFileUrl}`, {
				method: 'GET',
				headers: {
					...($user && { Authorization: `Bearer ${localStorage.token}` })
				}
			}).catch((error) => {
				console.log(error);
				return null;
			});
		}

		if (fileResponse && fileResponse.ok) {
			const reader = fileResponse.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done) break;

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line.replace(/^data: /, ''));

							if (data.progress) {
								uploadProgress = data.progress;
							}

							if (data.error) {
								throw data.error;
							}

							if (data.done) {
								modelFileDigest = data.blob;
								name = data.name;
								uploaded = true;
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}

		if (uploaded) {
			const res = await createModel(
				localStorage.token,
				`${name}:latest`,
				`FROM @${modelFileDigest}\n${modelFileContent}`
			);

			if (res && res.ok) {
				const reader = res.body
					.pipeThrough(new TextDecoderStream())
					.pipeThrough(splitStream('\n'))
					.getReader();

				while (true) {
					const { value, done } = await reader.read();
					if (done) break;

					try {
						let lines = value.split('\n');

						for (const line of lines) {
							if (line !== '') {
								console.log(line);
								let data = JSON.parse(line);
								console.log(data);

								if (data.error) {
									throw data.error;
								}
								if (data.detail) {
									throw data.detail;
								}

								if (data.status) {
									if (
										!data.digest &&
										!data.status.includes('writing') &&
										!data.status.includes('sha256')
									) {
										toast.success(data.status);
									} else {
										if (data.digest) {
											digest = data.digest;

											if (data.completed) {
												pullProgress = Math.round((data.completed / data.total) * 1000) / 10;
											} else {
												pullProgress = 100;
											}
										}
									}
								}
							}
						}
					} catch (error) {
						console.log(error);
						toast.error(error);
					}
				}
			}
		}

		modelFileUrl = '';
		modelInputFile = '';
		modelTransferring = false;
		uploadProgress = null;

		models.set(await getModels());
	};

	const deleteModelHandler = async () => {
		const res = await deleteModel(localStorage.token, deleteModelTag).catch((error) => {
			toast.error(error);
		});

		if (res) {
			toast.success(`Deleted ${deleteModelTag}`);
		}

		deleteModelTag = '';
		models.set(await getModels());
	};

	const getModels = async (type = 'all') => {
		const models = [];
		models.push(
			...(await getOllamaModels(localStorage.token).catch((error) => {
				toast.error(error);
				return [];
			}))
		);

		if (type === 'all') {
			const openAIModels = await getOpenAIModels(localStorage.token).catch((error) => {
				console.log(error);
				return null;
			});
			models.push(...(openAIModels ? [{ name: 'hr' }, ...openAIModels] : []));
		}

		return models;
	};

	const updatePasswordHandler = async () => {
		if (newPassword === newPasswordConfirm) {
			const res = await updateUserPassword(localStorage.token, currentPassword, newPassword).catch(
				(error) => {
					toast.error(error);
					return null;
				}
			);

			if (res) {
				toast.success('Successfully updated.');
			}

			currentPassword = '';
			newPassword = '';
			newPasswordConfirm = '';
		} else {
			toast.error(
				`The passwords you entered don't quite match. Please double-check and try again.`
			);
			newPassword = '';
			newPasswordConfirm = '';
		}
	};

	onMount(async () => {
		console.log('settings', $user.role === 'admin');
		if ($user.role === 'admin') {
			API_BASE_URL = await getOllamaAPIUrl(localStorage.token);
			OPENAI_API_BASE_URL = await getOpenAIUrl(localStorage.token);
			OPENAI_API_KEY = await getOpenAIKey(localStorage.token);
		}

		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');
		console.log(settings);

		selectedTheme = localStorage.theme ?? 'dark';
		notificationEnabled = settings.notificationEnabled ?? false;

		system = settings.system ?? '';
		requestFormat = settings.requestFormat ?? '';

		options.seed = settings.seed ?? 0;
		options.temperature = settings.temperature ?? '';
		options.repeat_penalty = settings.repeat_penalty ?? '';
		options.top_k = settings.top_k ?? '';
		options.top_p = settings.top_p ?? '';
		options.num_ctx = settings.num_ctx ?? '';
		options = { ...options, ...settings.options };
		options.stop = (settings?.options?.stop ?? []).join(',');

		titleAutoGenerate = settings.titleAutoGenerate ?? true;
		speechAutoSend = settings.speechAutoSend ?? false;
		responseAutoCopy = settings.responseAutoCopy ?? false;
		titleAutoGenerateModel = settings.titleAutoGenerateModel ?? '';
		gravatarEmail = settings.gravatarEmail ?? '';

		saveChatHistory = settings.saveChatHistory ?? true;

		authEnabled = settings.authHeader !== undefined ? true : false;
		if (authEnabled) {
			authType = settings.authHeader.split(' ')[0];
			authContent = settings.authHeader.split(' ')[1];
		}

		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			return '';
		});
	});
</script>

<Modal bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 py-4">
			<div class=" text-lg font-medium self-center">Settings</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<hr class=" dark:border-gray-800" />

		<div class="flex flex-col md:flex-row w-full p-4 md:space-x-4">
			<div
				class="tabs flex flex-row overflow-x-auto space-x-1 md:space-x-0 md:space-y-1 md:flex-col flex-1 md:flex-none md:w-40 dark:text-gray-200 text-xs text-left mb-3 md:mb-0"
			>
				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'general'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'general';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M8.34 1.804A1 1 0 019.32 1h1.36a1 1 0 01.98.804l.295 1.473c.497.144.971.342 1.416.587l1.25-.834a1 1 0 011.262.125l.962.962a1 1 0 01.125 1.262l-.834 1.25c.245.445.443.919.587 1.416l1.473.294a1 1 0 01.804.98v1.361a1 1 0 01-.804.98l-1.473.295a6.95 6.95 0 01-.587 1.416l.834 1.25a1 1 0 01-.125 1.262l-.962.962a1 1 0 01-1.262.125l-1.25-.834a6.953 6.953 0 01-1.416.587l-.294 1.473a1 1 0 01-.98.804H9.32a1 1 0 01-.98-.804l-.295-1.473a6.957 6.957 0 01-1.416-.587l-1.25.834a1 1 0 01-1.262-.125l-.962-.962a1 1 0 01-.125-1.262l.834-1.25a6.957 6.957 0 01-.587-1.416l-1.473-.294A1 1 0 011 10.68V9.32a1 1 0 01.804-.98l1.473-.295c.144-.497.342-.971.587-1.416l-.834-1.25a1 1 0 01.125-1.262l.962-.962A1 1 0 015.38 3.03l1.25.834a6.957 6.957 0 011.416-.587l.294-1.473zM13 10a3 3 0 11-6 0 3 3 0 016 0z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center">General</div>
				</button>

				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'advanced'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'advanced';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M17 2.75a.75.75 0 00-1.5 0v5.5a.75.75 0 001.5 0v-5.5zM17 15.75a.75.75 0 00-1.5 0v1.5a.75.75 0 001.5 0v-1.5zM3.75 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5a.75.75 0 01.75-.75zM4.5 2.75a.75.75 0 00-1.5 0v5.5a.75.75 0 001.5 0v-5.5zM10 11a.75.75 0 01.75.75v5.5a.75.75 0 01-1.5 0v-5.5A.75.75 0 0110 11zM10.75 2.75a.75.75 0 00-1.5 0v1.5a.75.75 0 001.5 0v-1.5zM10 6a2 2 0 100 4 2 2 0 000-4zM3.75 10a2 2 0 100 4 2 2 0 000-4zM16.25 10a2 2 0 100 4 2 2 0 000-4z"
							/>
						</svg>
					</div>
					<div class=" self-center">Advanced</div>
				</button>

				{#if $user?.role === 'admin'}
					<button
						class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
						'models'
							? 'bg-gray-200 dark:bg-gray-700'
							: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
						on:click={() => {
							selectedTab = 'models';
						}}
					>
						<div class=" self-center mr-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class=" self-center">Models</div>
					</button>

					<button
						class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
						'external'
							? 'bg-gray-200 dark:bg-gray-700'
							: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
						on:click={() => {
							selectedTab = 'external';
						}}
					>
						<div class=" self-center mr-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									d="M1 9.5A3.5 3.5 0 0 0 4.5 13H12a3 3 0 0 0 .917-5.857 2.503 2.503 0 0 0-3.198-3.019 3.5 3.5 0 0 0-6.628 2.171A3.5 3.5 0 0 0 1 9.5Z"
								/>
							</svg>
						</div>
						<div class=" self-center">External</div>
					</button>
				{/if}

				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'interface'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'interface';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center">Interface</div>
				</button>

				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'voice'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'voice';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M7.557 2.066A.75.75 0 0 1 8 2.75v10.5a.75.75 0 0 1-1.248.56L3.59 11H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h1.59l3.162-2.81a.75.75 0 0 1 .805-.124ZM12.95 3.05a.75.75 0 1 0-1.06 1.06 5.5 5.5 0 0 1 0 7.78.75.75 0 1 0 1.06 1.06 7 7 0 0 0 0-9.9Z"
							/>
							<path
								d="M10.828 5.172a.75.75 0 1 0-1.06 1.06 2.5 2.5 0 0 1 0 3.536.75.75 0 1 0 1.06 1.06 4 4 0 0 0 0-5.656Z"
							/>
						</svg>
					</div>
					<div class=" self-center">Voice</div>
				</button>

				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'chats'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'chats';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M8 2C4.262 2 1 4.57 1 8c0 1.86.98 3.486 2.455 4.566a3.472 3.472 0 0 1-.469 1.26.75.75 0 0 0 .713 1.14 6.961 6.961 0 0 0 3.06-1.06c.403.062.818.094 1.241.094 3.738 0 7-2.57 7-6s-3.262-6-7-6ZM5 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm7-1a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM8 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center">Chats</div>
				</button>

				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'account'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'account';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M15 8A7 7 0 1 1 1 8a7 7 0 0 1 14 0Zm-5-2a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM8 9c-1.825 0-3.422.977-4.295 2.437A5.49 5.49 0 0 0 8 13.5a5.49 5.49 0 0 0 4.294-2.063A4.997 4.997 0 0 0 8 9Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center">Account</div>
				</button>

				<button
					class="px-2.5 py-2.5 min-w-fit rounded-lg flex-1 md:flex-none flex text-right transition {selectedTab ===
					'about'
						? 'bg-gray-200 dark:bg-gray-700'
						: ' hover:bg-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => {
						selectedTab = 'about';
					}}
				>
					<div class=" self-center mr-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center">About</div>
				</button>
			</div>
			<div class="flex-1 md:min-h-[380px]">
				{#if selectedTab === 'general'}
					<General
						{getModels}
						{saveSettings}
						on:save={() => {
							show = false;
						}}
					/>
					<div class="flex flex-col space-y-3">
						<div>
							<div class=" mb-1 text-sm font-medium">WebUI Settings</div>

							<div class=" py-0.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">Theme</div>

								<!-- <button
									class="p-1 px-3 text-xs flex rounded transition"
									on:click={() => {
										toggleTheme();
									}}
								>
									
								</button> -->

								<div class="flex items-center relative">
									<div class=" absolute right-16">
										{#if selectedTheme === 'dark'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													fill-rule="evenodd"
													d="M7.455 2.004a.75.75 0 01.26.77 7 7 0 009.958 7.967.75.75 0 011.067.853A8.5 8.5 0 116.647 1.921a.75.75 0 01.808.083z"
													clip-rule="evenodd"
												/>
											</svg>
										{:else if selectedTheme === 'light'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-4 h-4 self-center"
											>
												<path
													d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM10 7a3 3 0 100 6 3 3 0 000-6zM15.657 5.404a.75.75 0 10-1.06-1.06l-1.061 1.06a.75.75 0 001.06 1.06l1.06-1.06zM6.464 14.596a.75.75 0 10-1.06-1.06l-1.06 1.06a.75.75 0 001.06 1.06l1.06-1.06zM18 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 0118 10zM5 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 015 10zM14.596 15.657a.75.75 0 001.06-1.06l-1.06-1.061a.75.75 0 10-1.06 1.06l1.06 1.06zM5.404 6.464a.75.75 0 001.06-1.06l-1.06-1.06a.75.75 0 10-1.061 1.06l1.06 1.06z"
												/>
											</svg>
										{/if}
									</div>

									<select
										class="w-fit pr-8 rounded py-2 px-2 text-xs bg-transparent outline-none text-right"
										bind:value={selectedTheme}
										placeholder="Select a theme"
										on:change={(e) => {
											localStorage.theme = selectedTheme;

											themes
												.filter((e) => e !== selectedTheme)
												.forEach((e) => {
													e.split(' ').forEach((e) => {
														document.documentElement.classList.remove(e);
													});
												});

											selectedTheme.split(' ').forEach((e) => {
												document.documentElement.classList.add(e);
											});

											console.log(selectedTheme);
											theme.set(selectedTheme);
										}}
									>
										<option value="dark">Dark</option>
										<option value="light">Light</option>
										<option value="rose-pine dark">Rosé Pine</option>
										<option value="rose-pine-dawn light">Rosé Pine Dawn</option>
										<option value="thoughtworks dark">Thoughtworks</option>
									</select>
								</div>
							</div>

							<div>
								<div class=" py-0.5 flex w-full justify-between">
									<div class=" self-center text-xs font-medium">Notification</div>

									<button
										class="p-1 px-3 text-xs flex rounded transition"
										on:click={() => {
											toggleNotification();
										}}
										type="button"
									>
										{#if notificationEnabled === true}
											<span class="ml-2 self-center">On</span>
										{:else}
											<span class="ml-2 self-center">Off</span>
										{/if}
									</button>
								</div>
							</div>
						</div>

						{#if $user.role === 'admin'}
							<hr class=" dark:border-gray-700" />
							<div>
								<div class=" mb-2.5 text-sm font-medium">Ollama API URL</div>
								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<input
											class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
											placeholder="Enter URL (e.g. http://localhost:11434/api)"
											bind:value={API_BASE_URL}
										/>
									</div>
									<button
										class="px-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 rounded transition"
										on:click={() => {
											updateOllamaAPIUrlHandler();
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>

								<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
									Trouble accessing Ollama?
									<a
										class=" text-gray-300 font-medium"
										href="https://github.com/ollama-webui/ollama-webui#troubleshooting"
										target="_blank"
									>
										Click here for help.
									</a>
								</div>
							</div>
						{/if}

						<hr class=" dark:border-gray-700" />

						<div>
							<div class=" mb-2.5 text-sm font-medium">System Prompt</div>
							<textarea
								bind:value={system}
								class="w-full rounded p-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none resize-none"
								rows="4"
							/>
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium">
							<button
								class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
								on:click={() => {
									saveSettings({
										system: system !== '' ? system : undefined
									});
									show = false;
								}}
							>
								Save
							</button>
						</div>
					</div>
				{:else if selectedTab === 'advanced'}
					<Advanced
						on:save={() => {
							show = false;
						}}
						{saveSettings}
					/>
				{:else if selectedTab === 'models'}
					<Models {getModels} />
				{:else if selectedTab === 'external'}
					<External
						{getModels}
						on:save={() => {
							show = false;
						}}
					/>
				{:else if selectedTab === 'interface'}
					<Interface
						{saveSettings}
						on:save={() => {
							show = false;
						}}
					/>
				{:else if selectedTab === 'voice'}
					<Voice
						{saveSettings}
						on:save={() => {
							show = false;
						}}
					/>
				{:else if selectedTab === 'chats'}
					<Chats {saveSettings} />
				{:else if selectedTab === 'account'}
					<Account
						saveHandler={() => {
							show = false;
						}}
					/>
				{:else if selectedTab === 'about'}
					<About />
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
