<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick, getContext } from 'svelte';
	import {
		type Model,
		mobile,
		settings,
		showSidebar,
		models,
		config,
		showCallOverlay,
		tools,
		user as _user
	} from '$lib/stores';
	import { blobToFile, calculateSHA256, findWordIndices } from '$lib/utils';

	import {
		uploadDocToVectorDB,
		uploadWebToVectorDB,
		uploadYoutubeTranscriptionToVectorDB
	} from '$lib/apis/rag';
	import { SUPPORTED_FILE_TYPE, SUPPORTED_FILE_EXTENSIONS, WEBUI_BASE_URL } from '$lib/constants';

	import Prompts from './MessageInput/PromptCommands.svelte';
	import Suggestions from './MessageInput/Suggestions.svelte';
	import AddFilesPlaceholder from '../AddFilesPlaceholder.svelte';
	import Documents from './MessageInput/Documents.svelte';
	import Models from './MessageInput/Models.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import InputMenu from './MessageInput/InputMenu.svelte';
	import Headphone from '../icons/Headphone.svelte';
	import VoiceRecording from './MessageInput/VoiceRecording.svelte';
	import { transcribeAudio } from '$lib/apis/audio';

	const i18n = getContext('i18n');

	export let submitPrompt: Function;
	export let stopResponse: Function;

	export let autoScroll = true;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	let recording = false;

	let chatTextAreaElement: HTMLTextAreaElement;
	let filesInputElement;

	let promptsElement;
	let documentsElement;
	let modelsElement;

	let inputFiles;
	let dragged = false;

	let user = null;
	let chatInputPlaceholder = '';

	export let files = [];

	export let availableToolIds = [];
	export let selectedToolIds = [];
	export let webSearchEnabled = false;

	export let prompt = '';
	export let messages = [];

	let visionCapableModels = [];
	$: visionCapableModels = [...(atSelectedModel ? [atSelectedModel] : selectedModels)].filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.vision ?? true
	);

	$: if (prompt) {
		if (chatTextAreaElement) {
			chatTextAreaElement.style.height = '';
			chatTextAreaElement.style.height = Math.min(chatTextAreaElement.scrollHeight, 200) + 'px';
		}
	}

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollHeight;
	};

	const uploadDoc = async (file) => {
		console.log(file);

		const doc = {
			type: 'doc',
			name: file.name,
			collection_name: '',
			upload_status: false,
			error: ''
		};

		try {
			files = [...files, doc];

			if (['audio/mpeg', 'audio/wav'].includes(file['type'])) {
				const res = await transcribeAudio(localStorage.token, file).catch((error) => {
					toast.error(error);
					return null;
				});

				if (res) {
					console.log(res);
					const blob = new Blob([res.text], { type: 'text/plain' });
					file = blobToFile(blob, `${file.name}.txt`);
				}
			}

			const res = await uploadDocToVectorDB(localStorage.token, '', file);

			if (res) {
				doc.upload_status = true;
				doc.collection_name = res.collection_name;
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== file.name);
			toast.error(e);
		}
	};

	const uploadWeb = async (url) => {
		console.log(url);

		const doc = {
			type: 'doc',
			name: url,
			collection_name: '',
			upload_status: false,
			url: url,
			error: ''
		};

		try {
			files = [...files, doc];
			const res = await uploadWebToVectorDB(localStorage.token, '', url);

			if (res) {
				doc.upload_status = true;
				doc.collection_name = res.collection_name;
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(e);
		}
	};

	const uploadYoutubeTranscription = async (url) => {
		console.log(url);

		const doc = {
			type: 'doc',
			name: url,
			collection_name: '',
			upload_status: false,
			url: url,
			error: ''
		};

		try {
			files = [...files, doc];
			const res = await uploadYoutubeTranscriptionToVectorDB(localStorage.token, url);

			if (res) {
				doc.upload_status = true;
				doc.collection_name = res.collection_name;
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(e);
		}
	};

	onMount(() => {
		window.setTimeout(() => chatTextAreaElement?.focus(), 0);

		const dropZone = document.querySelector('body');

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				console.log('Escape');
				dragged = false;
			}
		};

		const onDragOver = (e) => {
			e.preventDefault();
			dragged = true;
		};

		const onDragLeave = () => {
			dragged = false;
		};

		const onDrop = async (e) => {
			e.preventDefault();
			console.log(e);

			if (e.dataTransfer?.files) {
				const inputFiles = Array.from(e.dataTransfer?.files);

				if (inputFiles && inputFiles.length > 0) {
					inputFiles.forEach((file) => {
						console.log(file, file.name.split('.').at(-1));
						if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file['type'])) {
							if (visionCapableModels.length === 0) {
								toast.error($i18n.t('Selected model(s) do not support image inputs'));
								return;
							}
							let reader = new FileReader();
							reader.onload = (event) => {
								files = [
									...files,
									{
										type: 'image',
										url: `${event.target.result}`
									}
								];
							};
							reader.readAsDataURL(file);
						} else if (
							SUPPORTED_FILE_TYPE.includes(file['type']) ||
							SUPPORTED_FILE_EXTENSIONS.includes(file.name.split('.').at(-1))
						) {
							uploadDoc(file);
						} else {
							toast.error(
								$i18n.t(
									`Unknown File Type '{{file_type}}', but accepting and treating as plain text`,
									{ file_type: file['type'] }
								)
							);
							uploadDoc(file);
						}
					});
				} else {
					toast.error($i18n.t(`File not found.`));
				}
			}

			dragged = false;
		};

		window.addEventListener('keydown', handleKeyDown);

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);

		return () => {
			window.removeEventListener('keydown', handleKeyDown);

			dropZone?.removeEventListener('dragover', onDragOver);
			dropZone?.removeEventListener('drop', onDrop);
			dropZone?.removeEventListener('dragleave', onDragLeave);
		};
	});
</script>

{#if dragged}
	<div
		class="fixed {$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}  w-full h-full flex z-50 touch-none pointer-events-none"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div class="absolute w-full h-full backdrop-blur bg-gray-800/40 flex justify-center">
			<div class="m-auto pt-64 flex flex-col justify-center">
				<div class="max-w-md">
					<AddFilesPlaceholder />
				</div>
			</div>
		</div>
	</div>
{/if}

<div class="w-full">
	<div class=" -mb-0.5 mx-auto inset-x-0 bg-transparent flex justify-center">
		<div class="flex flex-col max-w-6xl px-2.5 md:px-6 w-full">
			<div class="relative">
				{#if autoScroll === false && messages.length > 0}
					<div class=" absolute -top-12 left-0 right-0 flex justify-center z-30">
						<button
							class=" bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full"
							on:click={() => {
								autoScroll = true;
								scrollToBottom();
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-5 h-5"
							>
								<path
									fill-rule="evenodd"
									d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
					</div>
				{/if}
			</div>

			<div class="w-full relative">
				{#if prompt.charAt(0) === '/'}
					<Prompts bind:this={promptsElement} bind:prompt bind:files />
				{:else if prompt.charAt(0) === '#'}
					<Documents
						bind:this={documentsElement}
						bind:prompt
						on:youtube={(e) => {
							console.log(e);
							uploadYoutubeTranscription(e.detail);
						}}
						on:url={(e) => {
							console.log(e);
							uploadWeb(e.detail);
						}}
						on:select={(e) => {
							console.log(e);
							files = [
								...files,
								{
									type: e?.detail?.type ?? 'doc',
									...e.detail,
									upload_status: true
								}
							];
						}}
					/>
				{/if}

				<Models
					bind:this={modelsElement}
					bind:prompt
					bind:user
					bind:chatInputPlaceholder
					{messages}
					on:select={(e) => {
						atSelectedModel = e.detail;
						chatTextAreaElement?.focus();
					}}
				/>

				{#if atSelectedModel !== undefined}
					<div
						class="px-3 py-2.5 text-left w-full flex justify-between items-center absolute bottom-0 left-0 right-0 bg-gradient-to-t from-50% from-white dark:from-gray-900"
					>
						<div class="flex items-center gap-2 text-sm dark:text-gray-500">
							<img
								crossorigin="anonymous"
								alt="model profile"
								class="size-5 max-w-[28px] object-cover rounded-full"
								src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta
									?.profile_image_url ??
									($i18n.language === 'dg-DG'
										? `/doge.png`
										: `${WEBUI_BASE_URL}/static/favicon.png`)}
							/>
							<div>
								Talking to <span class=" font-medium">{atSelectedModel.name}</span>
							</div>
						</div>
						<div>
							<button
								class="flex items-center"
								on:click={() => {
									atSelectedModel = undefined;
								}}
							>
								<XMark />
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="bg-white dark:bg-gray-900">
		<div class="max-w-6xl px-2.5 md:px-6 mx-auto inset-x-0">
			<div class=" pb-2">
				<input
					bind:this={filesInputElement}
					bind:files={inputFiles}
					type="file"
					hidden
					multiple
					on:change={async () => {
						if (inputFiles && inputFiles.length > 0) {
							const _inputFiles = Array.from(inputFiles);
							_inputFiles.forEach((file) => {
								if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file['type'])) {
									if (visionCapableModels.length === 0) {
										toast.error($i18n.t('Selected model(s) do not support image inputs'));
										inputFiles = null;
										filesInputElement.value = '';
										return;
									}
									let reader = new FileReader();
									reader.onload = (event) => {
										files = [
											...files,
											{
												type: 'image',
												url: `${event.target.result}`
											}
										];
										inputFiles = null;
										filesInputElement.value = '';
									};
									reader.readAsDataURL(file);
								} else if (
									SUPPORTED_FILE_TYPE.includes(file['type']) ||
									SUPPORTED_FILE_EXTENSIONS.includes(file.name.split('.').at(-1))
								) {
									uploadDoc(file);
									filesInputElement.value = '';
								} else {
									toast.error(
										$i18n.t(
											`Unknown File Type '{{file_type}}', but accepting and treating as plain text`,
											{ file_type: file['type'] }
										)
									);
									uploadDoc(file);
									filesInputElement.value = '';
								}
							});
						} else {
							toast.error($i18n.t(`File not found.`));
						}
					}}
				/>

				{#if recording}
					<VoiceRecording
						bind:recording
						on:cancel={async () => {
							recording = false;

							await tick();
							document.getElementById('chat-textarea')?.focus();
						}}
						on:confirm={async (e) => {
							const response = e.detail;
							prompt = `${prompt}${response} `;

							recording = false;

							await tick();
							document.getElementById('chat-textarea')?.focus();

							if ($settings?.speechAutoSend ?? false) {
								submitPrompt(prompt, user);
							}
						}}
					/>
				{:else}
					<form
						class="w-full flex gap-1.5"
						on:submit|preventDefault={() => {
							// check if selectedModels support image input
							submitPrompt(prompt, user);
						}}
					>
						<div
							class="flex-1 flex flex-col relative w-full rounded-3xl px-1.5 bg-gray-50 dark:bg-gray-850 dark:text-gray-100"
							dir={$settings?.chatDirection ?? 'LTR'}
						>
							{#if files.length > 0}
								<div class="mx-2 mt-2 mb-1 flex flex-wrap gap-2">
									{#each files as file, fileIdx}
										<div class=" relative group">
											{#if file.type === 'image'}
												<div class="relative">
													<img
														src={file.url}
														alt="input"
														class=" h-16 w-16 rounded-xl object-cover"
													/>
													{#if atSelectedModel ? visionCapableModels.length === 0 : selectedModels.length !== visionCapableModels.length}
														<Tooltip
															className=" absolute top-1 left-1"
															content={$i18n.t('{{ models }}', {
																models: [...(atSelectedModel ? [atSelectedModel] : selectedModels)]
																	.filter((id) => !visionCapableModels.includes(id))
																	.join(', ')
															})}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 24 24"
																fill="currentColor"
																class="size-4 fill-yellow-300"
															>
																<path
																	fill-rule="evenodd"
																	d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
																	clip-rule="evenodd"
																/>
															</svg>
														</Tooltip>
													{/if}
												</div>
											{:else if file.type === 'doc'}
												<div
													class="h-16 w-[15rem] flex items-center space-x-3 px-2.5 dark:bg-gray-600 rounded-xl border border-gray-200 dark:border-none"
												>
													<div class="p-2.5 bg-red-400 text-white rounded-lg">
														{#if file.upload_status}
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 24 24"
																fill="currentColor"
																class="w-6 h-6"
															>
																<path
																	fill-rule="evenodd"
																	d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0 0 16.5 9h-1.875a1.875 1.875 0 0 1-1.875-1.875V5.25A3.75 3.75 0 0 0 9 1.5H5.625ZM7.5 15a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 7.5 15Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H8.25Z"
																	clip-rule="evenodd"
																/>
																<path
																	d="M12.971 1.816A5.23 5.23 0 0 1 14.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 0 1 3.434 1.279 9.768 9.768 0 0 0-6.963-6.963Z"
																/>
															</svg>
														{:else}
															<svg
																class=" w-6 h-6 translate-y-[0.5px]"
																fill="currentColor"
																viewBox="0 0 24 24"
																xmlns="http://www.w3.org/2000/svg"
																><style>
																	.spinner_qM83 {
																		animation: spinner_8HQG 1.05s infinite;
																	}
																	.spinner_oXPr {
																		animation-delay: 0.1s;
																	}
																	.spinner_ZTLf {
																		animation-delay: 0.2s;
																	}
																	@keyframes spinner_8HQG {
																		0%,
																		57.14% {
																			animation-timing-function: cubic-bezier(0.33, 0.66, 0.66, 1);
																			transform: translate(0);
																		}
																		28.57% {
																			animation-timing-function: cubic-bezier(0.33, 0, 0.66, 0.33);
																			transform: translateY(-6px);
																		}
																		100% {
																			transform: translate(0);
																		}
																	}
																</style><circle
																	class="spinner_qM83"
																	cx="4"
																	cy="12"
																	r="2.5"
																/><circle
																	class="spinner_qM83 spinner_oXPr"
																	cx="12"
																	cy="12"
																	r="2.5"
																/><circle
																	class="spinner_qM83 spinner_ZTLf"
																	cx="20"
																	cy="12"
																	r="2.5"
																/></svg
															>
														{/if}
													</div>

													<div class="flex flex-col justify-center -space-y-0.5">
														<div class=" dark:text-gray-100 text-sm font-medium line-clamp-1">
															{file.name}
														</div>

														<div class=" text-gray-500 text-sm">{$i18n.t('Document')}</div>
													</div>
												</div>
											{:else if file.type === 'collection'}
												<div
													class="h-16 w-[15rem] flex items-center space-x-3 px-2.5 dark:bg-gray-600 rounded-xl border border-gray-200 dark:border-none"
												>
													<div class="p-2.5 bg-red-400 text-white rounded-lg">
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 24 24"
															fill="currentColor"
															class="w-6 h-6"
														>
															<path
																d="M7.5 3.375c0-1.036.84-1.875 1.875-1.875h.375a3.75 3.75 0 0 1 3.75 3.75v1.875C13.5 8.161 14.34 9 15.375 9h1.875A3.75 3.75 0 0 1 21 12.75v3.375C21 17.16 20.16 18 19.125 18h-9.75A1.875 1.875 0 0 1 7.5 16.125V3.375Z"
															/>
															<path
																d="M15 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 17.25 7.5h-1.875A.375.375 0 0 1 15 7.125V5.25ZM4.875 6H6v10.125A3.375 3.375 0 0 0 9.375 19.5H16.5v1.125c0 1.035-.84 1.875-1.875 1.875h-9.75A1.875 1.875 0 0 1 3 20.625V7.875C3 6.839 3.84 6 4.875 6Z"
															/>
														</svg>
													</div>

													<div class="flex flex-col justify-center -space-y-0.5">
														<div class=" dark:text-gray-100 text-sm font-medium line-clamp-1">
															{file?.title ?? `#${file.name}`}
														</div>

														<div class=" text-gray-500 text-sm">{$i18n.t('Collection')}</div>
													</div>
												</div>
											{/if}

											<div class=" absolute -top-1 -right-1">
												<button
													class=" bg-gray-400 text-white border border-white rounded-full group-hover:visible invisible transition"
													type="button"
													on:click={() => {
														files.splice(fileIdx, 1);
														files = files;
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
														/>
													</svg>
												</button>
											</div>
										</div>
									{/each}
								</div>
							{/if}

							<div class=" flex">
								<div class=" ml-0.5 self-end mb-1.5 flex space-x-1">
									<InputMenu
										bind:webSearchEnabled
										bind:selectedToolIds
										tools={$tools.reduce((a, e, i, arr) => {
											if (availableToolIds.includes(e.id) || ($_user?.role ?? 'user') === 'admin') {
												a[e.id] = {
													name: e.name,
													description: e.meta.description,
													enabled: false
												};
											}
											return a;
										}, {})}
										uploadFilesHandler={() => {
											filesInputElement.click();
										}}
										onClose={async () => {
											await tick();
											chatTextAreaElement?.focus();
										}}
									>
										<button
											class="bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-2 outline-none focus:outline-none"
											type="button"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="size-5"
											>
												<path
													d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
												/>
											</svg>
										</button>
									</InputMenu>
								</div>

								<textarea
									id="chat-textarea"
									bind:this={chatTextAreaElement}
									class="scrollbar-hidden bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-none w-full py-3 px-1 rounded-xl resize-none h-[48px]"
									placeholder={chatInputPlaceholder !== ''
										? chatInputPlaceholder
										: $i18n.t('Send a Message')}
									bind:value={prompt}
									on:keypress={(e) => {
										if (
											!$mobile ||
											!(
												'ontouchstart' in window ||
												navigator.maxTouchPoints > 0 ||
												navigator.msMaxTouchPoints > 0
											)
										) {
											// Prevent Enter key from creating a new line
											if (e.key === 'Enter' && !e.shiftKey) {
												e.preventDefault();
											}

											// Submit the prompt when Enter key is pressed
											if (prompt !== '' && e.key === 'Enter' && !e.shiftKey) {
												submitPrompt(prompt, user);
											}
										}
									}}
									on:keydown={async (e) => {
										const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac

										// Check if Ctrl + R is pressed
										if (prompt === '' && isCtrlPressed && e.key.toLowerCase() === 'r') {
											e.preventDefault();
											console.log('regenerate');

											const regenerateButton = [
												...document.getElementsByClassName('regenerate-response-button')
											]?.at(-1);

											regenerateButton?.click();
										}

										if (prompt === '' && e.key == 'ArrowUp') {
											e.preventDefault();

											const userMessageElement = [
												...document.getElementsByClassName('user-message')
											]?.at(-1);

											const editButton = [
												...document.getElementsByClassName('edit-user-message-button')
											]?.at(-1);

											console.log(userMessageElement);

											userMessageElement.scrollIntoView({ block: 'center' });
											editButton?.click();
										}

										if (['/', '#', '@'].includes(prompt.charAt(0)) && e.key === 'ArrowUp') {
											e.preventDefault();

											(promptsElement || documentsElement || modelsElement).selectUp();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);
											commandOptionButton.scrollIntoView({ block: 'center' });
										}

										if (['/', '#', '@'].includes(prompt.charAt(0)) && e.key === 'ArrowDown') {
											e.preventDefault();

											(promptsElement || documentsElement || modelsElement).selectDown();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);
											commandOptionButton.scrollIntoView({ block: 'center' });
										}

										if (['/', '#', '@'].includes(prompt.charAt(0)) && e.key === 'Enter') {
											e.preventDefault();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);

											if (e.shiftKey) {
												prompt = `${prompt}\n`;
											} else if (commandOptionButton) {
												commandOptionButton?.click();
											} else {
												document.getElementById('send-message-button')?.click();
											}
										}

										if (['/', '#', '@'].includes(prompt.charAt(0)) && e.key === 'Tab') {
											e.preventDefault();

											const commandOptionButton = [
												...document.getElementsByClassName('selected-command-option-button')
											]?.at(-1);

											commandOptionButton?.click();
										} else if (e.key === 'Tab') {
											const words = findWordIndices(prompt);

											if (words.length > 0) {
												const word = words.at(0);
												const fullPrompt = prompt;

												prompt = prompt.substring(0, word?.endIndex + 1);
												await tick();

												e.target.scrollTop = e.target.scrollHeight;
												prompt = fullPrompt;
												await tick();

												e.preventDefault();
												e.target.setSelectionRange(word?.startIndex, word.endIndex + 1);
											}

											e.target.style.height = '';
											e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
										}

										if (e.key === 'Escape') {
											console.log('Escape');
											atSelectedModel = undefined;
										}
									}}
									rows="1"
									on:input={(e) => {
										e.target.style.height = '';
										e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
										user = null;
									}}
									on:focus={(e) => {
										e.target.style.height = '';
										e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
									}}
									on:paste={(e) => {
										const clipboardData = e.clipboardData || window.clipboardData;

										if (clipboardData && clipboardData.items) {
											for (const item of clipboardData.items) {
												if (item.type.indexOf('image') !== -1) {
													const blob = item.getAsFile();
													const reader = new FileReader();

													reader.onload = function (e) {
														files = [
															...files,
															{
																type: 'image',
																url: `${e.target.result}`
															}
														];
													};

													reader.readAsDataURL(blob);
												}
											}
										}
									}}
								/>

								<div class="self-end mb-2 flex space-x-1 mr-1">
									{#if messages.length == 0 || messages.at(-1).done == true}
										<Tooltip content={$i18n.t('Record voice')}>
											<button
												id="voice-input-button"
												class=" text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-full p-1.5 mr-0.5 self-center"
												type="button"
												on:click={async () => {
													try {
														const res = await navigator.mediaDevices
															.getUserMedia({ audio: true })
															.catch(function (err) {
																toast.error(
																	$i18n.t(
																		`Permission denied when accessing microphone: {{error}}`,
																		{
																			error: err
																		}
																	)
																);
																return null;
															});

														if (res) {
															recording = true;
														}
													} catch {
														toast.error($i18n.t('Permission denied when accessing microphone'));
													}
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="w-5 h-5 translate-y-[0.5px]"
												>
													<path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
													<path
														d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}
								</div>
							</div>
						</div>
						<div class="flex items-end w-10">
							{#if messages.length == 0 || messages.at(-1).done == true}
								{#if prompt === ''}
									<div class=" flex items-center mb-1">
										<Tooltip content={$i18n.t('Call')}>
											<button
												class=" text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-full p-2 self-center"
												type="button"
												on:click={async () => {
													if (selectedModels.length > 1) {
														toast.error($i18n.t('Select only one model to call'));

														return;
													}

													if ($config.audio.stt.engine === 'web') {
														toast.error(
															$i18n.t('Call feature is not supported when using Web STT engine')
														);

														return;
													}
													// check if user has access to getUserMedia
													try {
														await navigator.mediaDevices.getUserMedia({ audio: true });
														// If the user grants the permission, proceed to show the call overlay

														showCallOverlay.set(true);
													} catch (err) {
														// If the user denies the permission or an error occurs, show an error message
														toast.error($i18n.t('Permission denied when accessing media devices'));
													}
												}}
											>
												<Headphone className="size-6" />
											</button>
										</Tooltip>
									</div>
								{:else}
									<div class=" flex items-center mb-1">
										<Tooltip content={$i18n.t('Send message')}>
											<button
												id="send-message-button"
												class="{prompt !== ''
													? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
													: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
												type="submit"
												disabled={prompt === ''}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="size-6"
												>
													<path
														fill-rule="evenodd"
														d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
														clip-rule="evenodd"
													/>
												</svg>
											</button>
										</Tooltip>
									</div>
								{/if}
							{:else}
								<div class=" flex items-center mb-1.5">
									<button
										class="bg-white hover:bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5"
										on:click={() => {
											stopResponse();
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											fill="currentColor"
											class="size-6"
										>
											<path
												fill-rule="evenodd"
												d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm6-2.438c0-.724.588-1.312 1.313-1.312h4.874c.725 0 1.313.588 1.313 1.313v4.874c0 .725-.588 1.313-1.313 1.313H9.564a1.312 1.312 0 01-1.313-1.313V9.564z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							{/if}
						</div>
					</form>
				{/if}

				<div class="mt-1.5 text-xs text-gray-500 text-center line-clamp-1">
					{$i18n.t('LLMs can make mistakes. Verify important information.')}
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
