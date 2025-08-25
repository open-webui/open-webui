<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import heic2any from 'heic2any';

	import { tick, getContext, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import { config, mobile, settings, socket, user } from '$lib/stores';
	import {
		blobToFile,
		compressImage,
		extractInputVariables,
		getAge,
		getCurrentDateTime,
		getFormattedDate,
		getFormattedTime,
		getUserPosition,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';

	import Tooltip from '../common/Tooltip.svelte';
	import RichTextInput from '../common/RichTextInput.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import InputMenu from './MessageInput/InputMenu.svelte';
	import { uploadFile } from '$lib/apis/files';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import FileItem from '../common/FileItem.svelte';
	import Image from '../common/Image.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import Commands from '../chat/MessageInput/Commands.svelte';
	import InputVariablesModal from '../chat/MessageInput/InputVariablesModal.svelte';
	import { getSessionUser } from '$lib/apis/auths';

	export let placeholder = $i18n.t('Send a Message');

	export let id = null;

	let draggedOver = false;

	let recording = false;
	let content = '';
	let files = [];

	export let chatInputElement;

	let commandsElement;
	let filesInputElement;
	let inputFiles;

	export let typingUsers = [];
	export let inputLoading = false;

	export let onSubmit: Function = (e) => {};
	export let onChange: Function = (e) => {};
	export let onStop: Function = (e) => {};

	export let scrollEnd = true;
	export let scrollToBottom: Function = () => {};

	export let acceptFiles = true;
	export let showFormattingToolbar = true;

	let showInputVariablesModal = false;
	let inputVariables: Record<string, any> = {};
	let inputVariableValues = {};

	const inputVariableHandler = async (text: string) => {
		inputVariables = extractInputVariables(text);
		if (Object.keys(inputVariables).length > 0) {
			showInputVariablesModal = true;
		}
	};

	const textVariableHandler = async (text: string) => {
		if (text.includes('{{CLIPBOARD}}')) {
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

		if (text.includes('{{USER_LOCATION}}')) {
			let location;
			try {
				location = await getUserPosition();
			} catch (error) {
				toast.error($i18n.t('Location access not allowed'));
				location = 'LOCATION_UNKNOWN';
			}
			text = text.replaceAll('{{USER_LOCATION}}', String(location));
		}

		const sessionUser = await getSessionUser(localStorage.token);

		if (text.includes('{{USER_NAME}}')) {
			const name = sessionUser?.name || 'User';
			text = text.replaceAll('{{USER_NAME}}', name);
		}

		if (text.includes('{{USER_BIO}}')) {
			const bio = sessionUser?.bio || '';

			if (bio) {
				text = text.replaceAll('{{USER_BIO}}', bio);
			}
		}

		if (text.includes('{{USER_GENDER}}')) {
			const gender = sessionUser?.gender || '';

			if (gender) {
				text = text.replaceAll('{{USER_GENDER}}', gender);
			}
		}

		if (text.includes('{{USER_BIRTH_DATE}}')) {
			const birthDate = sessionUser?.date_of_birth || '';

			if (birthDate) {
				text = text.replaceAll('{{USER_BIRTH_DATE}}', birthDate);
			}
		}

		if (text.includes('{{USER_AGE}}')) {
			const birthDate = sessionUser?.date_of_birth || '';

			if (birthDate) {
				// calculate age using date
				const age = getAge(birthDate);
				text = text.replaceAll('{{USER_AGE}}', age);
			}
		}

		if (text.includes('{{USER_LANGUAGE}}')) {
			const language = localStorage.getItem('locale') || 'en-US';
			text = text.replaceAll('{{USER_LANGUAGE}}', language);
		}

		if (text.includes('{{CURRENT_DATE}}')) {
			const date = getFormattedDate();
			text = text.replaceAll('{{CURRENT_DATE}}', date);
		}

		if (text.includes('{{CURRENT_TIME}}')) {
			const time = getFormattedTime();
			text = text.replaceAll('{{CURRENT_TIME}}', time);
		}

		if (text.includes('{{CURRENT_DATETIME}}')) {
			const dateTime = getCurrentDateTime();
			text = text.replaceAll('{{CURRENT_DATETIME}}', dateTime);
		}

		if (text.includes('{{CURRENT_TIMEZONE}}')) {
			const timezone = getUserTimezone();
			text = text.replaceAll('{{CURRENT_TIMEZONE}}', timezone);
		}

		if (text.includes('{{CURRENT_WEEKDAY}}')) {
			const weekday = getWeekday();
			text = text.replaceAll('{{CURRENT_WEEKDAY}}', weekday);
		}

		inputVariableHandler(text);
		return text;
	};

	const replaceVariables = (variables: Record<string, any>) => {
		if (!chatInputElement) return;
		console.log('Replacing variables:', variables);

		chatInputElement.replaceVariables(variables);
		chatInputElement.focus();
	};

	export const setText = async (text?: string) => {
		if (!chatInputElement) return;

		text = await textVariableHandler(text || '');

		chatInputElement?.setText(text);
		chatInputElement?.focus();
	};

	const getCommand = () => {
		if (!chatInputElement) return;

		let word = '';
		word = chatInputElement?.getWordAtDocPos();

		return word;
	};

	const replaceCommandWithText = (text) => {
		if (!chatInputElement) return;

		chatInputElement?.replaceCommandWithText(text);
	};

	const insertTextAtCursor = async (text: string) => {
		text = await textVariableHandler(text);

		if (command) {
			replaceCommandWithText(text);
		} else {
			const selection = window.getSelection();
			if (selection && selection.rangeCount > 0) {
				const range = selection.getRangeAt(0);
				range.deleteContents();
				range.insertNode(document.createTextNode(text));
				range.collapse(false);
				selection.removeAllRanges();
				selection.addRange(range);
			}
		}

		await tick();
		const chatInputContainer = document.getElementById('chat-input-container');
		if (chatInputContainer) {
			chatInputContainer.scrollTop = chatInputContainer.scrollHeight;
		}

		await tick();
		if (chatInputElement) {
			chatInputElement.focus();
		}
	};

	let command = '';

	export let showCommands = false;
	$: showCommands = ['/'].includes(command?.charAt(0));

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

	const inputFilesHandler = async (inputFiles) => {
		inputFiles.forEach(async (file) => {
			console.info('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.error('File exceeds max size limit:', {
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

			if (file['type'].startsWith('image/')) {
				const compressImageHandler = async (imageUrl, settings = {}, config = {}) => {
					// Quick shortcut so we don’t do unnecessary work.
					const settingsCompression = settings?.imageCompression ?? false;
					const configWidth = config?.file?.image_compression?.width ?? null;
					const configHeight = config?.file?.image_compression?.height ?? null;

					// If neither settings nor config wants compression, return original URL.
					if (!settingsCompression && !configWidth && !configHeight) {
						return imageUrl;
					}

					// Default to null (no compression unless set)
					let width = null;
					let height = null;

					// If user/settings want compression, pick their preferred size.
					if (settingsCompression) {
						width = settings?.imageCompressionSize?.width ?? null;
						height = settings?.imageCompressionSize?.height ?? null;
					}

					// Apply config limits as an upper bound if any
					if (configWidth && (width === null || width > configWidth)) {
						width = configWidth;
					}
					if (configHeight && (height === null || height > configHeight)) {
						height = configHeight;
					}

					// Do the compression if required
					if (width || height) {
						return await compressImage(imageUrl, width, height);
					}
					return imageUrl;
				};

				let reader = new FileReader();

				reader.onload = async (event) => {
					let imageUrl = event.target.result;

					// Compress the image if settings or config require it
					if ($settings?.imageCompression && $settings?.imageCompressionInChannels) {
						imageUrl = await compressImageHandler(imageUrl, $settings, $config);
					}

					files = [
						...files,
						{
							type: 'image',
							url: `${imageUrl}`
						}
					];
				};

				reader.readAsDataURL(
					file['type'] === 'image/heic'
						? await heic2any({ blob: file, toType: 'image/jpeg' })
						: file
				);
			} else {
				uploadFileHandler(file);
			}
		});
	};

	const uploadFileHandler = async (file) => {
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
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		files = [...files, fileItem];

		try {
			// During the file upload, file content is automatically extracted.

			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (uploadedFile) {
				console.info('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.error('File upload warning:', uploadedFile.error);
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

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			draggedOver = false;
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			draggedOver = true;
		} else {
			draggedOver = false;
		}
	};

	const onDragLeave = () => {
		draggedOver = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();

		if (e.dataTransfer?.files && acceptFiles) {
			const inputFiles = Array.from(e.dataTransfer?.files);
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		draggedOver = false;
	};

	const submitHandler = async () => {
		if (content === '' && files.length === 0) {
			return;
		}

		onSubmit({
			content,
			data: {
				files: files
			}
		});

		content = '';
		files = [];

		if (chatInputElement) {
			chatInputElement?.setText('');

			await tick();

			chatInputElement.focus();
		}
	};

	$: if (content) {
		onChange();
	}

	onMount(async () => {
		window.setTimeout(() => {
			if (chatInputElement) {
				chatInputElement.focus();
			}
		}, 100);

		window.addEventListener('keydown', handleKeyDown);
		await tick();

		const dropzoneElement = document.getElementById('channel-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);

		const dropzoneElement = document.getElementById('channel-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<FilesOverlay show={draggedOver} />

{#if acceptFiles}
	<input
		bind:this={filesInputElement}
		bind:files={inputFiles}
		type="file"
		hidden
		multiple
		on:change={async () => {
			if (inputFiles && inputFiles.length > 0) {
				inputFilesHandler(Array.from(inputFiles));
			} else {
				toast.error($i18n.t(`File not found.`));
			}

			filesInputElement.value = '';
		}}
	/>
{/if}

<InputVariablesModal
	bind:show={showInputVariablesModal}
	variables={inputVariables}
	onSave={(variableValues) => {
		inputVariableValues = { ...inputVariableValues, ...variableValues };
		replaceVariables(inputVariableValues);
	}}
/>

<div class="bg-transparent">
	<div
		class="{($settings?.widescreenMode ?? null)
			? 'max-w-full'
			: 'max-w-6xl'}  mx-auto inset-x-0 relative"
	>
		<div class="absolute top-0 left-0 right-0 mx-auto inset-x-0 bg-transparent flex justify-center">
			<div class="flex flex-col px-3 w-full">
				<div class="relative">
					{#if scrollEnd === false}
						<div
							class=" absolute -top-12 left-0 right-0 flex justify-center z-30 pointer-events-none"
						>
							<button
								class=" bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full pointer-events-auto"
								on:click={() => {
									scrollEnd = true;
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

				<div class="relative">
					<div class=" -mt-5">
						{#if typingUsers.length > 0}
							<div class=" text-xs px-4 mb-1">
								<span class=" font-normal text-black dark:text-white">
									{typingUsers.map((user) => user.name).join(', ')}
								</span>
								{$i18n.t('is typing...')}
							</div>
						{/if}
					</div>

					<Commands
						bind:this={commandsElement}
						show={showCommands}
						{command}
						insertTextHandler={insertTextAtCursor}
					/>
				</div>
			</div>
		</div>

		<div class="">
			{#if recording}
				<VoiceRecording
					bind:recording
					onCancel={async () => {
						recording = false;

						await tick();

						if (chatInputElement) {
							chatInputElement.focus();
						}
					}}
					onConfirm={async (data) => {
						const { text, filename } = data;
						recording = false;

						await tick();
						insertTextAtCursor(text);

						await tick();

						if (chatInputElement) {
							chatInputElement.focus();
						}
					}}
				/>
			{:else}
				<form
					class="w-full flex gap-1.5"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div
						class="flex-1 flex flex-col relative w-full rounded-3xl px-1 bg-gray-600/5 dark:bg-gray-400/5 dark:text-gray-100"
						dir={$settings?.chatDirection ?? 'auto'}
					>
						{#if files.length > 0}
							<div class="mx-2 mt-2.5 -mb-1 flex flex-wrap gap-2">
								{#each files as file, fileIdx}
									{#if file.type === 'image'}
										<div class=" relative group">
											<div class="relative">
												<Image
													src={file.url}
													alt="input"
													imageClassName=" h-16 w-16 rounded-xl object-cover"
												/>
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
											on:dismiss={() => {
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

						<div class="px-2.5">
							<div
								class="scrollbar-hidden font-primary text-left bg-transparent dark:text-gray-100 outline-hidden w-full pt-3 px-1 resize-none h-fit max-h-80 overflow-auto"
							>
								<RichTextInput
									bind:this={chatInputElement}
									json={true}
									messageInput={true}
									{showFormattingToolbar}
									shiftEnter={!($settings?.ctrlEnterToSend ?? false) &&
										(!$mobile ||
											!(
												'ontouchstart' in window ||
												navigator.maxTouchPoints > 0 ||
												navigator.msMaxTouchPoints > 0
											))}
									largeTextAsFile={$settings?.largeTextAsFile ?? false}
									floatingMenuPlacement={'top-start'}
									onChange={(e) => {
										const { md } = e;
										content = md;
										command = getCommand();
									}}
									on:keydown={async (e) => {
										e = e.detail.event;
										const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac

										const commandsContainerElement = document.getElementById('commands-container');

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

												// Submit the content when Enter key is pressed
												if (content !== '' && e.keyCode === 13 && !e.shiftKey) {
													submitHandler();
												}
											}
										}

										if (e.key === 'Escape') {
											console.info('Escape');
										}
									}}
									on:paste={async (e) => {
										e = e.detail.event;
										console.info(e);
									}}
								/>
							</div>
						</div>

						<div class=" flex justify-between mb-2.5 mt-1.5 mx-0.5">
							<div class="ml-1 self-end flex space-x-1 flex-1">
								<slot name="menu">
									{#if acceptFiles}
										<InputMenu
											{screenCaptureHandler}
											uploadFilesHandler={() => {
												filesInputElement.click();
											}}
										>
											<button
												class="bg-transparent hover:bg-white/80 text-gray-800 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5 outline-hidden focus:outline-hidden"
												type="button"
												aria-label="More"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-5"
												>
													<path
														d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
													/>
												</svg>
											</button>
										</InputMenu>
									{/if}
								</slot>
							</div>

							<div class="self-end flex space-x-1 mr-1">
								{#if content === ''}
									<Tooltip content={$i18n.t('Record voice')}>
										<button
											id="voice-input-button"
											class=" text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-full p-1.5 mr-0.5 self-center"
											type="button"
											on:click={async () => {
												try {
													let stream = await navigator.mediaDevices
														.getUserMedia({ audio: true })
														.catch(function (err) {
															toast.error(
																$i18n.t(`Permission denied when accessing microphone: {{error}}`, {
																	error: err
																})
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

								<div class=" flex items-center">
									{#if inputLoading && onStop}
										<div class=" flex items-center">
											<Tooltip content={$i18n.t('Stop')}>
												<button
													class="bg-white hover:bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5"
													on:click={() => {
														onStop();
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 24 24"
														fill="currentColor"
														class="size-5"
													>
														<path
															fill-rule="evenodd"
															d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm6-2.438c0-.724.588-1.312 1.313-1.312h4.874c.725 0 1.313.588 1.313 1.313v4.874c0 .725-.588 1.313-1.313 1.313H9.564a1.312 1.312 0 01-1.313-1.313V9.564z"
															clip-rule="evenodd"
														/>
													</svg>
												</button>
											</Tooltip>
										</div>
									{:else}
										<div class=" flex items-center">
											<Tooltip content={$i18n.t('Send message')}>
												<button
													id="send-message-button"
													class="{content !== '' || files.length !== 0
														? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
														: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 self-center"
													type="submit"
													disabled={content === '' && files.length === 0}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 16 16"
														fill="currentColor"
														class="size-5"
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
								</div>
							</div>
						</div>
					</div>
				</form>
			{/if}
		</div>
	</div>
</div>
