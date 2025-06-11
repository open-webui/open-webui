<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { createPicker } from '$lib/utils/google-drive-picker';

	import { onMount, tick, getContext, createEventDispatcher, onDestroy } from 'svelte';
	const dispatch = createEventDispatcher();

	import {
		type Model,
		mobile,
		settings,
		models,
		config,
		user as _user,
	} from '$lib/stores';

	import { blobToFile, compressImage, findWordIndices } from '$lib/utils';
	import { transcribeAudio } from '$lib/apis/audio';
	import { uploadFile } from '$lib/apis/files';

	import { WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import InputMenu from '$lib/IONOS/components/chat/MessageInput/InputMenu.svelte';
	import FilesOverlay from '$lib/components/chat/MessageInput/FilesOverlay.svelte';
	import Commands from '$lib/components/chat/MessageInput/Commands.svelte';
	import SelectedFileBadges from '$lib/IONOS/components/chat/SelectedFileBadges.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
	import Sparkles from '$lib/IONOS/components/icons/Sparkles.svelte';
	import Stop from '$lib/IONOS/components/icons/Stop.svelte';
	import Attachement from '../icons/Attachement.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	export let transparentBackground = false;

	// eslint-disable-next-line @typescript-eslint/ban-types
	export let onChange: Function = () => {};
	// eslint-disable-next-line @typescript-eslint/ban-types
	export let createMessagePair: Function;
	// eslint-disable-next-line @typescript-eslint/ban-types
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined = undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];

	export let selectedToolIds = [];

	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;

	$: onChange({
		prompt,
		files,
		selectedToolIds,
		imageGenerationEnabled,
		webSearchEnabled
	});

	let loaded = false;

	let chatInputElement;

	let filesInputElement;
	let commandsElement;

	let inputFiles;
	let dragged = false;

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
			toast.error(e);
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
								class=" bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full pointer-events-auto"
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
					<Commands
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
					/>
				</div>
			</div>
		</div>

		<div class="{transparentBackground ? 'bg-transparent' : 'bg-white dark:bg-gray-900'} ">
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

					<form
						class="w-full flex gap-1.5 justify-center "
						on:submit|preventDefault={() => {
							// check if selectedModels support image input
							dispatch('submit', prompt);
						}}
					>
						<div
							class="flex-1 flex flex-col relative w-full rounded-2xl max-w-3xl bg-gray-100 dark:bg-gray-400/5 dark:text-gray-100 "
							dir={$settings?.chatDirection ?? 'LTR'}
						>
							<div class="flex flex-col justify-between h-[105px]">
								<textarea
									id="chat-input"
									lang="de"
									bind:this={chatInputElement}
									class="scrollbar-hidden bg-transparent text-blue-700 placeholder:text-gray-400 dark:text-gray-100 outline-none w-full py-3 px-4 rounded-xl resize-none text-sm"
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

								<div class="flex flex-row">
									<div class="ml-1 self-end mb-1.5 flex space-x-1">
										<InputMenu
											bind:webSearchEnabled
											bind:selectedToolIds
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
											on:knowledge={() => {
												prompt += '#';
											}}
											onClose={async () => {
												await tick();

												const chatInput = document.getElementById('chat-input');
												chatInput?.focus();
											}}
										>
											<button
												class="bg-transparent hover:bg-white/80 text-gray-800 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-2 outline-none focus:outline-none"
												type="button"
												aria-label="More"
											>
												<Attachement className="size-5" />
											</button>
										</InputMenu>
									</div>

									<div class="grow">
										{#if files.length > 0}
											<SelectedFileBadges
												{files}
											/>
										{/if}
									</div>

									<div class="self-end mb-1.5 flex space-x-1 mr-1">
										{#if !history.currentId || history.messages[history.currentId]?.done == true}
											<div class=" flex items-center">
												<Tooltip content={$i18n.t('Send message')}>
													<Button
														id="send-message-button"
														name="send"
														iconOnly={true}
														type={ButtonType.special}
														disabled={prompt === ''}
														label={$i18n.t('Send message')}
													>
														<Sparkles className="w-4 h-4 fill-purple-300" />
													</Button>
												</Tooltip>
											</div>
										{:else}
											<div class=" flex items-center">
												<Tooltip content={$i18n.t('Stop')}>
													<Button
														name="stop-responding"
														on:click={stopResponse}
														iconOnly={true}
														type={ButtonType.special}
														label={$i18n.t('Stop')}
													>
														<Stop className="w-4 h-4 fill-gray-500" />
													</Button>
												</Tooltip>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					</form>
				</div>
			</div>
		</div>
	</div>
{/if}
