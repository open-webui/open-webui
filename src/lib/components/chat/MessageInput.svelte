<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { createPicker, getAuthToken } from '$lib/utils/google-drive-picker';

	import { onMount, tick, getContext, createEventDispatcher, onDestroy } from 'svelte';
	import ScrollToBottomIcon from '../icons/ScrollToBottomIcon.svelte';
	const dispatch = createEventDispatcher();

	import {
		type Model,
		mobile,
		settings,
		showSidebar,
		models,
		config,
		showCallOverlay,
		tools,
		user as _user,
		showControls,
		companyConfig,
		confirmPromptFn
	} from '$lib/stores';

	import { blobToFile, compressImage, createMessagesList, findWordIndices } from '$lib/utils';
	import { transcribeAudio } from '$lib/apis/audio';
	import { uploadFile } from '$lib/apis/files';
	import { generateAutoCompletion } from '$lib/apis';
	import { deleteFileById } from '$lib/apis/files';

	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

	import InputMenu from './MessageInput/InputMenu.svelte';
	import VoiceRecording from './MessageInput/VoiceRecording.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
	import Commands from './MessageInput/Commands.svelte';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import FileItem from '../common/FileItem.svelte';
	import Image from '../common/Image.svelte';

	import XMark from '../icons/XMark.svelte';
	import Headphone from '../icons/Headphone.svelte';
	import GlobeAlt from '../icons/GlobeAlt.svelte';
	import PhotoSolid from '../icons/PhotoSolid.svelte';
	import Photo from '../icons/Photo.svelte';
	import CommandLine from '../icons/CommandLine.svelte';
	import WebSearchIcon from '../icons/WebSearchIcon.svelte';
	import CodeInterpreterIcon from '../icons/CodeInterpreterIcon.svelte';
	import ImageGenerateIcon from '../icons/ImageGenerateIcon.svelte';
	import InputMenuIcon from '../icons/InputMenuIcon.svelte';
	import VoiceRecorderIcon from '../icons/VoiceRecorderIcon.svelte';
	import CallIcon from '../icons/CallIcon.svelte';
	import MagicSearch from '../icons/MagicSearch.svelte';
	import LoadingIcon from '../icons/LoadingIcon.svelte';

	const i18n = getContext('i18n');

	export let transparentBackground = false;

	export let onChange: Function = () => {};
	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined = undefined;
	export let selectedModels: [''];
	export let isMagicLoading;

	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	export let history;

	export let prompt = '';
	export let files = [];

	export let selectedToolIds = [];

	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;
	export let codeInterpreterEnabled = false;

	$: onChange({
		prompt,
		files,
		selectedToolIds,
		imageGenerationEnabled,
		webSearchEnabled
	});

	let loaded = false;
	let recording = false;

	let chatInputContainerElement;
	let chatInputElement;

	let filesInputElement;
	let commandsElement;

	let inputFiles;
	let dragged = false;

	let user = null;
	export let placeholder = '';

	let visionCapableModels = [];
	$: visionCapableModels = [...(atSelectedModel ? [atSelectedModel] : selectedModels)].filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.vision ?? true
	);

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element.scrollTo({
			top: element.scrollHeight,
			behavior: 'smooth'
		});
	};

	const screenCaptureHandler = async () => {
		try {
			// Request screen media
			const mediaStream = await navigator.mediaDevices.getDisplayMedia({
				video: { cursor: 'never' },
				audio: false
			});
			// Once the user selects a screen, temporarily create a video element
			const video = document.createElement('video');
			video.srcObject = mediaStream;
			// Ensure the video loads without affecting user experience or tab switching
			await video.play();
			// Set up the canvas to match the video dimensions
			const canvas = document.createElement('canvas');
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			// Grab a single frame from the video stream using the canvas
			const context = canvas.getContext('2d');
			context.drawImage(video, 0, 0, canvas.width, canvas.height);
			// Stop all video tracks (stop screen sharing) after capturing the image
			mediaStream.getTracks().forEach((track) => track.stop());

			// bring back focus to this current tab, so that the user can see the screen capture
			window.focus();

			// Convert the canvas to a Base64 image URL
			const imageUrl = canvas.toDataURL('image/png');
			// Add the captured image to the files array to render it
			files = [...files, { type: 'image', url: imageUrl }];
			// Clean memory: Clear video srcObject
			video.srcObject = null;
		} catch (error) {
			// Handle any errors (e.g., user cancels screen sharing)
			console.error('Error capturing screen:', error);
		}
	};

	const uploadFileHandler = async (file, fullContext: boolean = false) => {
		if ($_user?.role !== 'admin' && !($_user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return null;
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId,
			...(fullContext ? { context: 'full' } : {})
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		files = [...files, fileItem];
		// Check if the file is an audio file and transcribe/convert it to text file
		if (['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a'].includes(file['type'])) {
			const res = await transcribeAudio(localStorage.token, file).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				console.log(res);
				const blob = new Blob([res.text], { type: 'text/plain' });
				file = blobToFile(blob, `${file.name}.txt`);

				fileItem.name = file.name;
				fileItem.size = file.size;
			}
		}

		try {
			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file);

			if (uploadedFile) {
				console.log('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.collection_name =
					uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;
				fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

				files = files;
			} else {
				files = files.filter((item) => item?.itemId !== tempItemId);
			}
		} catch (e) {
			toast.error(`${e}`);
			files = files.filter((item) => item?.itemId !== tempItemId);
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);
		inputFiles.forEach((file) => {
			console.log('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.log('File exceeds max size limit:', {
					fileSize: file.size,
					maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
				});
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file['type'])) {
				if (visionCapableModels.length === 0) {
					toast.error($i18n.t('Selected model(s) do not support image inputs'));
					return;
				}
				let reader = new FileReader();
				reader.onload = async (event) => {
					let imageUrl = event.target.result;

					if ($settings?.imageCompression ?? false) {
						const width = $settings?.imageCompressionSize?.width ?? null;
						const height = $settings?.imageCompressionSize?.height ?? null;

						if (width || height) {
							imageUrl = await compressImage(imageUrl, width, height);
						}
					}

					files = [
						...files,
						{
							type: 'image',
							url: `${imageUrl}`
						}
					];
				};
				reader.readAsDataURL(file);
			} else {
				uploadFileHandler(file);
			}
		});
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			dragged = false;
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being dragged.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
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
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		dragged = false;
	};

	onMount(async () => {
		loaded = true;

		window.setTimeout(() => {
			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		}, 0);

		window.addEventListener('keydown', handleKeyDown);

		await tick();

		const dropzoneElement = document.getElementById('chat-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	const confirmPrompt = async (command) => {
		let text = command.content;

		if (command.content.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			const clipboardItems = await navigator.clipboard.read();

			let imageUrl = null;
			for (const item of clipboardItems) {
				// Check for known image types
				for (const type of item.types) {
					if (type.startsWith('image/')) {
						const blob = await item.getType(type);
						imageUrl = URL.createObjectURL(blob);
					}
				}
			}

			if (imageUrl) {
				files = [
					...files,
					{
						type: 'image',
						url: imageUrl
					}
				];
			}

			text = text.replaceAll('{{CLIPBOARD}}', clipboardText);
		}

		if (command.content.includes('{{USER_LOCATION}}')) {
			const location = await getUserPosition();
			text = text.replaceAll('{{USER_LOCATION}}', String(location));
		}

		if (command.content.includes('{{USER_NAME}}')) {
			console.log($user);
			const name = `${$user.first_name} ${$user.last_name}` || 'User';
			text = text.replaceAll('{{USER_NAME}}', name);
		}

		if (command.content.includes('{{USER_LANGUAGE}}')) {
			const language = localStorage.getItem('locale') || 'en-US';
			text = text.replaceAll('{{USER_LANGUAGE}}', language);
		}

		if (command.content.includes('{{CURRENT_DATE}}')) {
			const date = getFormattedDate();
			text = text.replaceAll('{{CURRENT_DATE}}', date);
		}

		if (command.content.includes('{{CURRENT_TIME}}')) {
			const time = getFormattedTime();
			text = text.replaceAll('{{CURRENT_TIME}}', time);
		}

		if (command.content.includes('{{CURRENT_DATETIME}}')) {
			const dateTime = getCurrentDateTime();
			text = text.replaceAll('{{CURRENT_DATETIME}}', dateTime);
		}

		if (command.content.includes('{{CURRENT_TIMEZONE}}')) {
			const timezone = getUserTimezone();
			text = text.replaceAll('{{CURRENT_TIMEZONE}}', timezone);
		}

		if (command.content.includes('{{CURRENT_WEEKDAY}}')) {
			const weekday = getWeekday();
			text = text.replaceAll('{{CURRENT_WEEKDAY}}', weekday);
		}

		prompt = text;

		const chatInputContainerElement = document.getElementById('chat-input-container');
		const chatInputElement = document.getElementById('chat-input');

		await tick();
		if (chatInputContainerElement) {
			chatInputContainerElement.style.height = '';
			chatInputContainerElement.style.height =
				Math.min(chatInputContainerElement.scrollHeight, 200) + 'px';
		}

		await tick();
		if (chatInputElement) {
			chatInputElement.focus();
			chatInputElement.dispatchEvent(new Event('input'));
		}
	};

	onMount(() => {
		confirmPromptFn.set(confirmPrompt);
	})

	onDestroy(() => confirmPromptFn.set(null))

	onMount(() => {
		const stored = localStorage.getItem('selectedPrompt');
		if (stored) {
			const prompt = JSON.parse(stored);
			confirmPrompt(prompt);		
			localStorage.removeItem('selectedPrompt'); 
		}
	});

	onDestroy(() => {
		console.log('destroy');
		window.removeEventListener('keydown', handleKeyDown);

		const dropzoneElement = document.getElementById('chat-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});

	let customModel = null;
	$: console.log(customModel)

	$: {
		if(selectedModels.length === 1) {
			customModel = $models.find(model => model.id === selectedModels[0] && model.info?.base_model_id !== null);
		}
	}
</script>

<FilesOverlay show={dragged} />

{#if loaded}
	<div class="w-full font-primary">
		<div class=" mx-auto inset-x-0 bg-transparent flex justify-center">
			<div
				class="flex flex-col px-3 {($settings?.widescreenMode ?? null)
					? 'max-w-full'
					: 'max-w-6xl'} w-full"
			>
				<div class="relative">
					{#if autoScroll === false && history?.currentId}
						<div
							class=" absolute -top-12 left-0 right-0 flex justify-center z-30 pointer-events-none"
						>
							<button
								class="border-none p-1.5 rounded-full pointer-events-auto text-white dark:text-[#7C7A7A]"
								on:click={() => {
									autoScroll = true;
									scrollToBottom();
								}}
							>
							<ScrollToBottomIcon className="size-6"/>	
							</button>
						</div>
					{/if}
				</div>
				<!-- class="px-3 pb-0.5 pt-1.5 text-left w-full flex flex-col absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white dark:from-gray-900 z-10" -->
				<div class="w-full relative">
					{#if atSelectedModel !== undefined || selectedToolIds.length > 0 || webSearchEnabled || ($settings?.webSearch ?? false) === 'always' || imageGenerationEnabled || codeInterpreterEnabled}
						<div>
							{#if selectedToolIds.length > 0}
								<div class="flex items-center justify-between w-full">
									<div class="flex items-center gap-2.5 text-base dark:text-gray-500">
										<div class="pl-1">
											<span class="relative flex size-2">
												<span
													class="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"
												/>
												<span class="relative inline-flex rounded-full size-2 bg-yellow-500" />
											</span>
										</div>
										<div class="  text-ellipsis line-clamp-1 flex">
											{#each selectedToolIds.map((id) => {
												return $tools ? $tools.find((t) => t.id === id) : { id: id, name: id };
											}) as tool, toolIdx (toolIdx)}
												<Tooltip
													content={tool?.meta?.description ?? ''}
													className=" {toolIdx !== 0 ? 'pl-0.5' : ''} flex-shrink-0"
													placement="top"
												>
													{tool.name}
												</Tooltip>

												{#if toolIdx !== selectedToolIds.length - 1}
													<span>, </span>
												{/if}
											{/each}
										</div>
									</div>
								</div>
							{/if}

							<!-- {#if webSearchEnabled || ($settings?.webSearch ?? false) === 'always'}
								<div class="flex items-center justify-between w-full">
									<div class="flex items-center gap-2.5 text-base dark:text-gray-500">
										<div class="pl-1">
											<span class="relative flex size-2">
												<span
													class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"
												/>
												<span class="relative inline-flex rounded-full size-2 bg-blue-500" />
											</span>
										</div>
										<div class=" translate-y-[0.5px]">{$i18n.t('Search the internet')}</div>
									</div>
								</div>
							{/if} -->

							<!-- {#if imageGenerationEnabled}
								<div class="flex items-center justify-between w-full">
									<div class="flex items-center gap-2.5 text-base dark:text-gray-500">
										<div class="pl-1">
											<span class="relative flex size-2">
												<span
													class="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"
												/>
												<span class="relative inline-flex rounded-full size-2 bg-teal-500" />
											</span>
										</div>
										<div class=" translate-y-[0.5px]">{$i18n.t('Generate an image')}</div>
									</div>
								</div>
							{/if} -->

							<!-- {#if codeInterpreterEnabled}
								<div class="flex items-center justify-between w-full">
									<div class="flex items-center gap-2.5 text-base dark:text-gray-500">
										<div class="pl-1">
											<span class="relative flex size-2">
												<span
													class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
												/>
												<span class="relative inline-flex rounded-full size-2 bg-green-500" />
											</span>
										</div>
										<div class=" translate-y-[0.5px]">{$i18n.t('Execute code for analysis')}</div>
									</div>
								</div>
							{/if} -->

							{#if atSelectedModel !== undefined}
								<div class="flex items-center justify-between w-full">
									<div class="pl-[1px] flex items-center gap-2 text-base dark:text-gray-500">
										<img
											crossorigin="anonymous"
											alt="model profile"
											class="size-3.5 max-w-[28px] object-cover rounded-full"
											src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta
												?.profile_image_url ??
												($i18n.language === 'dg-DG'
													? `/doge.png`
													: `${WEBUI_BASE_URL}/static/favicon.png`)}
										/>
										<div class="translate-y-[0.5px]">
											Talking to <span class=" font-medium">{atSelectedModel.name}</span>
										</div>
									</div>
									<div>
										<button
											class="flex items-center dark:text-gray-500"
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
					{/if}

					<!-- <Commands
						bind:this={commandsElement}
						bind:prompt
						bind:files
						on:upload={(e) => {
							dispatch('upload', e.detail);
						}}
						on:select={(e) => {
							const data = e.detail;

							if (data?.type === 'model') {
								atSelectedModel = data.data;
							}

							const chatInputElement = document.getElementById('chat-input');
							chatInputElement?.focus();
						}}
					/> -->
				</div>
			</div>
		</div>

		<div class="{transparentBackground ? 'bg-transparent' : 'bg-lightGray-300 dark:bg-customGray-900'} ">
			<div
				class="{($settings?.widescreenMode ?? null)
					? 'max-w-full'
					: 'max-w-6xl'} px-2.5 mx-auto inset-x-0"
			>
				<div class="">
					<input
						bind:this={filesInputElement}
						bind:files={inputFiles}
						type="file"
						hidden
						multiple
						on:change={async () => {
							if (inputFiles && inputFiles.length > 0) {
								const _inputFiles = Array.from(inputFiles);
								inputFilesHandler(_inputFiles);
							} else {
								toast.error($i18n.t(`File not found.`));
							}

							filesInputElement.value = '';
						}}
					/>

					{#if recording}
						<VoiceRecording
							bind:recording
							on:cancel={async () => {
								recording = false;

								await tick();
								document.getElementById('chat-input')?.focus();
							}}
							on:confirm={async (e) => {
								const { text, filename } = e.detail;
								prompt = `${prompt}${text} `;

								recording = false;

								await tick();
								document.getElementById('chat-input')?.focus();

								if ($settings?.speechAutoSend ?? false) {
									dispatch('submit', prompt);
								}
							}}
						/>
					{:else}
						<form
							class="w-full flex gap-1.5"
							on:submit|preventDefault={() => {
								// check if selectedModels support image input
								dispatch('submit', prompt);
							}}
						>
							<div
								class="flex-1 flex flex-col relative w-full rounded-3xl px-1 bg-lightGray-800 dark:bg-customGray-800 dark:text-gray-100"
								dir={$settings?.chatDirection ?? 'LTR'}
							>
								{#if files.length > 0}
									<div class="mx-2 mt-2.5 -mb-1 flex items-center flex-wrap gap-2">
										{#each files as file, fileIdx}
											{#if file.type === 'image'}
												<div class=" relative group">
													<div class="relative flex items-center">
														<Image
															src={file.url}
															alt="input"
															imageClassName=" size-14 rounded-xl object-cover"
														/>
														{#if atSelectedModel ? visionCapableModels.length === 0 : selectedModels.length !== visionCapableModels.length}
															<Tooltip
																className=" absolute top-1 left-1"
																content={$i18n.t('{{ models }}', {
																	models: [
																		...(atSelectedModel ? [atSelectedModel] : selectedModels)
																	]
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
													<div class=" absolute -top-1 -right-1">
														<button
															class=" bg-white text-black border border-white rounded-full group-hover:visible invisible transition"
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
											{:else}
												<FileItem
													item={file}
													name={file.name}
													type={file.type}
													size={file?.size}
													loading={file.status === 'uploading'}
													dismissible={true}
													edit={true}
													on:dismiss={async () => {
														if (file.type !== 'collection' && !file?.collection) {
															if (file.id) {
																// This will handle both file deletion and Chroma cleanup
																await deleteFileById(localStorage.token, file.id);
															}
														}

														// Remove from UI state
														files.splice(fileIdx, 1);
														files = files;
													}}
													on:click={() => {
														console.log(file);
													}}
												/>
											{/if}
										{/each}
									</div>
								{/if}

								<div class="px-2.5 min-h-[60px]">
									{#if $settings?.richTextInput ?? true}
										<div
											class="scrollbar-hidden text-left bg-transparent dark:text-gray-100 outline-none w-full pt-5 px-3 resize-none h-fit max-h-80 overflow-auto"
										>
											<RichTextInput
												bind:this={chatInputElement}
												bind:value={prompt}
												id="chat-input"
												messageInput={true}
												shiftEnter={!$mobile ||
													!(
														'ontouchstart' in window ||
														navigator.maxTouchPoints > 0 ||
														navigator.msMaxTouchPoints > 0
													)}
												placeholder={placeholder ? placeholder : $i18n.t('Send a Message')}
												largeTextAsFile={$settings?.largeTextAsFile ?? false}
												autocomplete={false}
												generateAutoCompletion={async (text) => {
													if (selectedModelIds.length === 0 || !selectedModelIds.at(0)) {
														toast.error($i18n.t('Please select a model first.'));
													}

													const res = await generateAutoCompletion(
														localStorage.token,
														selectedModelIds.at(0),
														text,
														history?.currentId
															? createMessagesList(history, history.currentId)
															: null
													).catch((error) => {
														console.log(error);

														return null;
													});

													console.log(res);
													return res;
												}}
												on:keydown={async (e) => {
													e = e.detail.event;

													const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
													const commandsContainerElement =
														document.getElementById('commands-container');

													if (e.key === 'Escape') {
														stopResponse();
													}

													// Command/Ctrl + Shift + Enter to submit a message pair
													if (isCtrlPressed && e.key === 'Enter' && e.shiftKey) {
														e.preventDefault();
														createMessagePair(prompt);
													}

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

														if (userMessageElement) {
															userMessageElement.scrollIntoView({ block: 'center' });
															const editButton = [
																...document.getElementsByClassName('edit-user-message-button')
															]?.at(-1);

															editButton?.click();
														}
													}

													if (commandsContainerElement) {
														if (commandsContainerElement && e.key === 'ArrowUp') {
															e.preventDefault();
															commandsElement.selectUp();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);
															commandOptionButton.scrollIntoView({ block: 'center' });
														}

														if (commandsContainerElement && e.key === 'ArrowDown') {
															e.preventDefault();
															commandsElement.selectDown();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);
															commandOptionButton.scrollIntoView({ block: 'center' });
														}

														if (commandsContainerElement && e.key === 'Tab') {
															e.preventDefault();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);

															commandOptionButton?.click();
														}

														if (commandsContainerElement && e.key === 'Enter') {
															e.preventDefault();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);

															if (commandOptionButton) {
																commandOptionButton?.click();
															} else {
																document.getElementById('send-message-button')?.click();
															}
														}
													} else {
														if (
															!$mobile ||
															!(
																'ontouchstart' in window ||
																navigator.maxTouchPoints > 0 ||
																navigator.msMaxTouchPoints > 0
															)
														) {
															// Prevent Enter key from creating a new line
															// Uses keyCode '13' for Enter key for chinese/japanese keyboards
															if (e.keyCode === 13 && !e.shiftKey) {
																e.preventDefault();
															}

															// Submit the prompt when Enter key is pressed
															if (prompt !== '' && e.keyCode === 13 && !e.shiftKey) {
																dispatch('submit', prompt);
															}
														}
													}

													if (e.key === 'Escape') {
														console.log('Escape');
														atSelectedModel = undefined;
														selectedToolIds = [];
														webSearchEnabled = false;
														imageGenerationEnabled = false;
													}
												}}
												on:paste={async (e) => {
													e = e.detail.event;
													console.log(e);

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
															} else if (item.type === 'text/plain') {
																if ($settings?.largeTextAsFile ?? false) {
																	const text = clipboardData.getData('text/plain');

																	if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
																		e.preventDefault();
																		const blob = new Blob([text], { type: 'text/plain' });
																		const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, {
																			type: 'text/plain'
																		});

																		await uploadFileHandler(file, true);
																	}
																}
															}
														}
													}
												}}
											/>
										</div>
									{:else}
										<textarea
											id="chat-input"
											bind:this={chatInputElement}
											class="scrollbar-hidden bg-transparent dark:text-gray-100 outline-none w-full pt-3 px-1 resize-none"
											placeholder={placeholder ? placeholder : $i18n.t('Send a Message')}
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
														dispatch('submit', prompt);
													}
												}
											}}
											on:keydown={async (e) => {
												const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
												const commandsContainerElement =
													document.getElementById('commands-container');

												if (e.key === 'Escape') {
													stopResponse();
												}
												// Command/Ctrl + Shift + Enter to submit a message pair
												if (isCtrlPressed && e.key === 'Enter' && e.shiftKey) {
													e.preventDefault();
													createMessagePair(prompt);
												}

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

												if (commandsContainerElement && e.key === 'ArrowUp') {
													e.preventDefault();
													commandsElement.selectUp();

													const commandOptionButton = [
														...document.getElementsByClassName('selected-command-option-button')
													]?.at(-1);
													commandOptionButton.scrollIntoView({ block: 'center' });
												}

												if (commandsContainerElement && e.key === 'ArrowDown') {
													e.preventDefault();
													commandsElement.selectDown();

													const commandOptionButton = [
														...document.getElementsByClassName('selected-command-option-button')
													]?.at(-1);
													commandOptionButton.scrollIntoView({ block: 'center' });
												}

												if (commandsContainerElement && e.key === 'Enter') {
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

												if (commandsContainerElement && e.key === 'Tab') {
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
													e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
												}

												if (e.key === 'Escape') {
													console.log('Escape');
													atSelectedModel = undefined;
													selectedToolIds = [];
													webSearchEnabled = false;
													imageGenerationEnabled = false;
												}
											}}
											rows="1"
											on:input={async (e) => {
												e.target.style.height = '';
												e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
											}}
											on:focus={async (e) => {
												e.target.style.height = '';
												e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
											}}
											on:paste={async (e) => {
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
														} else if (item.type === 'text/plain') {
															if ($settings?.largeTextAsFile ?? false) {
																const text = clipboardData.getData('text/plain');

																if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
																	e.preventDefault();
																	const blob = new Blob([text], { type: 'text/plain' });
																	const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, {
																		type: 'text/plain'
																	});

																	await uploadFileHandler(file, true);
																}
															}
														}
													}
												}
											}}
										/>
									{/if}
								</div>

								<div class=" flex justify-between mt-1.5 mb-5 mx-4 max-w-full">
									<div class="ml-1 self-end gap-0.5 flex items-center flex-1 max-w-[80%]">
										<InputMenu
											bind:selectedToolIds
											{screenCaptureHandler}
											{inputFilesHandler}
											uploadFilesHandler={() => {
												filesInputElement.click();
											}}
											uploadGoogleDriveHandler={async () => {
												try {
													const fileData = await createPicker();
													if (fileData) {
														const file = new File([fileData.blob], fileData.name, {
															type: fileData.blob.type
														});
														await uploadFileHandler(file);
													} else {
														console.log('No file was selected from Google Drive');
													}
												} catch (error) {
													console.error('Google Drive Error:', error);
													toast.error(
														$i18n.t('Error accessing Google Drive: {{error}}', {
															error: error.message
														})
													);
												}
											}}
											onClose={async () => {
												await tick();

												const chatInput = document.getElementById('chat-input');
												chatInput?.focus();
											}}
										>
											<button
												class="bg-transparent hover:bg-gray-100 text-customGray-900 dark:text-customGray-100 dark:hover:bg-customGray-900 transition rounded-md p-[3px] outline-none focus:outline-none"
												type="button"
												aria-label="More"
											>
												<InputMenuIcon />
											</button>
										</InputMenu>

										<div class="flex gap-1 items-center overflow-x-auto scrollbar-none flex-1">
											{#if $_user}
												{#if $companyConfig?.config?.rag?.web?.search?.enable && ($_user.role === 'admin' || $_user?.permissions?.features?.web_search) && (customModel?.meta?.capabilities?.websearch ?? true)}
													<Tooltip content={$i18n.t('Search the internet')} placement="top">
														<button
															on:click|preventDefault={() => {
																webSearchEnabled = !webSearchEnabled;
																imageGenerationEnabled = false;
																codeInterpreterEnabled = false;
															}}
															type="button"
															class="p-[3px] flex gap-1.5 items-center text-xs rounded-md font-medium transition-colors duration-300 focus:outline-none max-w-full overflow-hidden {webSearchEnabled ||
															($settings?.webSearch ?? false) === 'always'
																? 'bg-blue-100 dark:bg-customBlue-700/60 text-blue-500 dark:text-white'
																: 'bg-transparent text-customGray-900 dark:text-customGray-100 border-gray-200 hover:bg-gray-100 dark:hover:bg-customGray-900'}"
														>
															<WebSearchIcon />
															{#if webSearchEnabled || ($settings?.webSearch ?? false) === 'always'}
																<span
																	class="hidden @sm:block whitespace-nowrap overflow-hidden text-ellipsis mr-0.5"
																	>{$i18n.t('Web Search')}</span
																>
															{/if}
														</button>
													</Tooltip>
												{/if}

												{#if $companyConfig?.config?.image_generation?.enable && ($_user.role === 'admin' || $_user?.permissions?.features?.image_generation) && (customModel?.meta?.capabilities?.image_generation ?? true)}
													<Tooltip content={$i18n.t('Generate an image')} placement="top">
														<button
															on:click|preventDefault={() => {
																imageGenerationEnabled = !imageGenerationEnabled;
																codeInterpreterEnabled = false;
																webSearchEnabled = false;
															}}
															type="button"
															class="p-[3px] flex gap-1.5 items-center text-xs rounded-md font-medium transition-colors duration-300 focus:outline-none max-w-full overflow-hidden {imageGenerationEnabled
																? 'bg-gray-100 dark:bg-customBlue-700/60 text-gray-600 dark:text-white'
																: 'bg-transparent text-customGray-900 dark:text-customGray-100 border-gray-200 hover:bg-gray-100 dark:hover:bg-customGray-900 '}"
														>
															<ImageGenerateIcon />
															{#if imageGenerationEnabled}
																<span
																	class="hidden @sm:block whitespace-nowrap overflow-hidden text-ellipsis mr-0.5"
																	>{$i18n.t('Image')}</span
																>
															{/if}
														</button>
													</Tooltip>
												{/if}

												{#if ($_user.role === 'admin' || $_user?.permissions?.features?.code_interpreter) && (customModel?.meta?.capabilities?.code_interpreter ?? true)}
													<Tooltip content={$i18n.t('Execute code for analysis')} placement="top">
														<button
															on:click|preventDefault={() => {
																codeInterpreterEnabled = !codeInterpreterEnabled;
																imageGenerationEnabled = false;
																webSearchEnabled = false;
															}}
															type="button"
															class="p-[3px] flex gap-1.5 items-center text-xs rounded-lg font-medium transition-colors duration-300 focus:outline-none max-w-full overflow-hidden {codeInterpreterEnabled
																? 'bg-gray-100 dark:bg-customBlue-700/60 text-gray-600 dark:text-white'
																: 'bg-transparent text-customGray-900 dark:text-customGray-100 border-gray-200 hover:bg-gray-100 dark:hover:bg-customGray-900 '}"
														>
															<CodeInterpreterIcon />
															{#if codeInterpreterEnabled}
																<span
																	class="hidden @sm:block whitespace-nowrap overflow-hidden text-ellipsis mr-0.5"
																	>{$i18n.t('Code Interpreter')}</span
																>
															{/if}
														</button>
													</Tooltip>
												{/if}
											{/if}
										</div>
									</div>

									<div class="self-end flex space-x-1 mr-1 flex-shrink-0">
										{#if !history?.currentId || history.messages[history.currentId]?.done == true}
											<Tooltip content={$i18n.t('Magic prompt')}>
												<button
													id="magic-search-button"
													class={`${isMagicLoading ? 'dark:bg-customBlue-700/60' : ''} text-customGray-900 dark:text-customGray-100 text-xs leading-none hover:text-gray-700 dark:hover:text-white ${!isMagicLoading? 'dark:hover:bg-customGray-900' : ''}  transition rounded-md py-[3px] px-[5px] mr-0.5 self-center`}
													type="button"
													aria-label="Magic Prompt"
													disabled={prompt === '' || isMagicLoading}
													on:click|preventDefault={() => {
														dispatch('magicPrompt', prompt);
													}}
												>
													{#if isMagicLoading}
														<span class="flex items-center"
															><LoadingIcon /><span class="ml-1">{$i18n.t('Magic prompt')}</span
															></span
														>
													{:else}
														<MagicSearch />
													{/if}
												</button>
											</Tooltip>
										{/if}
										{#if !history?.currentId || history.messages[history.currentId]?.done == true}
											<Tooltip content={$i18n.t('Record voice')}>
												<button
													id="voice-input-button"
													class=" text-customGray-900 dark:text-customGray-100 hover:text-gray-700 dark:hover:text-gray-200 dark:hover:bg-customGray-900 transition rounded-md p-[3px] mr-0.5 self-center"
													type="button"
													on:click={async () => {
														try {
															let stream = await navigator.mediaDevices
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

															if (stream) {
																recording = true;
																const tracks = stream.getTracks();
																tracks.forEach((track) => track.stop());
															}
															stream = null;
														} catch {
															toast.error($i18n.t('Permission denied when accessing microphone'));
														}
													}}
													aria-label="Voice Input"
												>
													<VoiceRecorderIcon />
												</button>
											</Tooltip>
										{/if}

										{#if !history.currentId || history.messages[history.currentId]?.done == true}
											{#if prompt === ''}
												<div class=" flex items-center">
													<Tooltip content={$i18n.t('Call')}>
														<button
															class=" dark:hover:bg-gray-900 dark:bg-transparent text-customGray-900 dark:text-customGray-100 dark:hover:bg-customGray-900 transition rounded-md p-[3px] self-center"
															type="button"
															on:click={async () => {
																if (selectedModels.length > 1) {
																	toast.error($i18n.t('Select only one model to call'));

																	return;
																}

																if ($config.audio.stt.engine === 'web') {
																	toast.error(
																		$i18n.t(
																			'Call feature is not supported when using Web STT engine'
																		)
																	);

																	return;
																}
																// check if user has access to getUserMedia
																try {
																	let stream = await navigator.mediaDevices.getUserMedia({
																		audio: true
																	});
																	// If the user grants the permission, proceed to show the call overlay

																	if (stream) {
																		const tracks = stream.getTracks();
																		tracks.forEach((track) => track.stop());
																	}

																	stream = null;

																	showCallOverlay.set(true);
																	showControls.set(true);
																} catch (err) {
																	// If the user denies the permission or an error occurs, show an error message
																	toast.error(
																		$i18n.t('Permission denied when accessing media devices')
																	);
																}
															}}
															aria-label="Call"
														>
															<CallIcon />
														</button>
													</Tooltip>
												</div>
											{:else}
												<div class=" flex items-center">
													<Tooltip content={$i18n.t('Send message')}>
														<button
															id="send-message-button"
															class="{!(prompt === '' && files.length === 0)
																? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
																: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1 self-center"
															type="submit"
															disabled={prompt === '' && files.length === 0}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="size-3"
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
											<div class=" flex items-center">
												<Tooltip content={$i18n.t('Stop')}>
													<button
														class=" text-gray-800 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
														on:click={() => {
															stopResponse();
														}}
													>
														<svg
															width="16"
															height="16"
															viewBox="0 0 13 13"
															fill="none"
															xmlns="http://www.w3.org/2000/svg"
														>
															<path
																d="M0 6.5C-1.27195e-08 7.35359 0.168127 8.19883 0.494783 8.98744C0.821438 9.77606 1.30023 10.4926 1.90381 11.0962C2.50739 11.6998 3.22394 12.1786 4.01256 12.5052C4.80117 12.8319 5.64641 13 6.5 13C7.35359 13 8.19883 12.8319 8.98744 12.5052C9.77606 12.1786 10.4926 11.6998 11.0962 11.0962C11.6998 10.4926 12.1786 9.77606 12.5052 8.98744C12.8319 8.19883 13 7.35359 13 6.5C13 5.64641 12.8319 4.80117 12.5052 4.01256C12.1786 3.22394 11.6998 2.50739 11.0962 1.90381C10.4926 1.30023 9.77606 0.821438 8.98744 0.494783C8.19883 0.168127 7.35359 0 6.5 0C5.64641 0 4.80117 0.168127 4.01256 0.494783C3.22394 0.821438 2.50739 1.30023 1.90381 1.90381C1.30023 2.50739 0.821438 3.22394 0.494783 4.01256C0.168127 4.80117 -1.27195e-08 5.64641 0 6.5Z"
																fill="white"
															/>
															<g clip-path="url(#clip0_495_25245)">
																<path
																	d="M3.79175 4.56483C3.79175 4.3596 3.87327 4.16278 4.01839 4.01766C4.16351 3.87254 4.36033 3.79102 4.56556 3.79102H8.43461C8.63983 3.79102 8.83665 3.87254 8.98177 4.01766C9.12689 4.16278 9.20842 4.3596 9.20842 4.56483V8.43387C9.20842 8.6391 9.12689 8.83592 8.98177 8.98104C8.83665 9.12616 8.63983 9.20768 8.43461 9.20768H4.56556C4.36033 9.20768 4.16351 9.12616 4.01839 8.98104C3.87327 8.83592 3.79175 8.6391 3.79175 8.43387V4.56483Z"
																	fill="#272525"
																/>
															</g>
															<defs>
																<clipPath id="clip0_495_25245">
																	<rect
																		width="9.28571"
																		height="9.28571"
																		fill="white"
																		transform="translate(1.85718 1.85645)"
																	/>
																</clipPath>
															</defs>
														</svg>
													</button>
												</Tooltip>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</form>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
