<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { v4 as uuidv4 } from 'uuid';
	import { createPicker, getAuthToken } from '$lib/utils/google-drive-picker';
	import { pickAndDownloadFile } from '$lib/utils/onedrive-file-picker';

	import { onMount, tick, getContext, createEventDispatcher, onDestroy } from 'svelte';
	const dispatch = createEventDispatcher();

	import {
		type Model,
		mobile,
		settings,
		models,
		config,
		showCallOverlay,
		tools,
		toolServers,
		user as _user,
		showControls,
		TTSWorker,
		temporaryChatEnabled
	} from '$lib/stores';

	import {
		convertHeicToJpeg,
		createMessagesList,
		extractContentFromFile,
		extractCurlyBraceWords,
		extractInputVariables,
		getAge,
		getCurrentDateTime,
		getFormattedDate,
		getFormattedTime,
		getUserPosition,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';
	import { uploadFile } from '$lib/apis/files';
	import type { ReasoningEffort } from '$lib/apis';
	import { generateAutoCompletion } from '$lib/apis';
	import { deleteFileById } from '$lib/apis/files';
	import { getSessionUser } from '$lib/apis/auths';
	import { getTools } from '$lib/apis/tools';

	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

	import { BASE_REASONING_EFFORTS, orderReasoningEfforts } from '$lib/constants/reasoning';

	import InputMenu from './MessageInput/InputMenu.svelte';
	import VoiceRecording from './MessageInput/VoiceRecording.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
	import ToolServersModal from './ToolServersModal.svelte';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import FileItem from '../common/FileItem.svelte';
	import Image from '../common/Image.svelte';

	import XMark from '../icons/XMark.svelte';
	import Headphone from '../icons/Headphone.svelte';
	import GlobeAlt from '../icons/GlobeAlt.svelte';
	import Photo from '../icons/Photo.svelte';
	import Wrench from '../icons/Wrench.svelte';
	import CommandLine from '../icons/CommandLine.svelte';
	import Sparkles from '../icons/Sparkles.svelte';

	import InputVariablesModal from './MessageInput/InputVariablesModal.svelte';
	import Voice from '../icons/Voice.svelte';
	import Terminal from '../icons/Terminal.svelte';
	import IntegrationsMenu from './MessageInput/IntegrationsMenu.svelte';
	import Component from '../icons/Component.svelte';
	import PlusAlt from '../icons/PlusAlt.svelte';

	import { KokoroWorker } from '$lib/workers/KokoroWorker';

	import { getSuggestionRenderer } from '../common/RichTextInput/suggestions';
	import CommandSuggestionList from './MessageInput/CommandSuggestionList.svelte';
	import Knobs from '../icons/Knobs.svelte';
	import ValvesModal from '../workspace/common/ValvesModal.svelte';

	const i18n = getContext('i18n');

	export let onChange: Function = () => {};
	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;
	export let generating = false;

	export let atSelectedModel: Model | undefined = undefined;
	export let selectedModels: [''];

	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	export let history;
	export let taskIds = null;

	export let prompt = '';
	export let files = [];
	const canceledImageUploads = new Set<string>();
	const imageUploadAbortControllers = new Map<string, AbortController>();

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;
	export let studyModeEnabled = false;
	export let codeInterpreterEnabled = false;

	// Reasoning effort functionality
	let reasoningEffort = 'medium'; // default to medium
	let reasoningEffortByModel = {};
	let currentTrackedModel = '';
	let userModifiedEffortForCurrentModel = false;
	let preferencesLoaded = false;

	const getModelReasoningConfig = (modelId: string) => {
		const model = $models.find((m) => m.id === modelId);
		const reasoning = model?.info?.meta?.reasoning;

		return {
			enabled: reasoning?.enabled ?? true,
			extraEfforts: (reasoning?.extra_efforts ?? []).filter((e) => typeof e === 'string' && e)
		};
	};

	const getAllowedEffortsForModel = (modelId: string) => {
		const { enabled, extraEfforts } = getModelReasoningConfig(modelId);
		if (!enabled) return [];
		const extras = Array.from(new Set(extraEfforts));
		return orderReasoningEfforts(Array.from(new Set([...BASE_REASONING_EFFORTS, ...extras])));
	};

	const clampEffortToAllowed = (effort: string, allowedEfforts: string[]) => {
		if (!allowedEfforts || allowedEfforts.length === 0) {
			return null;
		}

		if (allowedEfforts.includes(effort)) {
			return effort;
		}

		// Prefer medium if available; otherwise first allowed
		return allowedEfforts.includes('medium') ? 'medium' : allowedEfforts[0];
	};

	let reasoningEnabledForCurrentModel = true;
	let allowedReasoningEffortsForCurrentModel: string[] = BASE_REASONING_EFFORTS;
	let showReasoningEffortSelector = false;

	$: if (selectedModelIds.length === 1) {
		allowedReasoningEffortsForCurrentModel = getAllowedEffortsForModel(selectedModelIds[0]);
		reasoningEnabledForCurrentModel = allowedReasoningEffortsForCurrentModel.length > 0;
		showReasoningEffortSelector = reasoningEnabledForCurrentModel;
	} else {
		// Multi-model chat: no per-model reasoning selection (would apply to all).
		allowedReasoningEffortsForCurrentModel = [];
		reasoningEnabledForCurrentModel = false;
		showReasoningEffortSelector = false;
	}

	// Load reasoning effort preferences from localStorage
	const loadReasoningEffortPreferences = () => {
		try {
			const stored = localStorage.getItem('reasoningEffortByModel');
			if (stored) {
				reasoningEffortByModel = JSON.parse(stored);
			}
		} catch (e) {
			console.error('Error loading reasoning effort preferences:', e);
		}
		preferencesLoaded = true;
	};

	// Save reasoning effort preferences to localStorage
	const saveReasoningEffortPreferences = () => {
		try {
			localStorage.setItem('reasoningEffortByModel', JSON.stringify(reasoningEffortByModel));
		} catch (e) {
			console.error('Error saving reasoning effort preferences:', e);
		}
	};

	// Update reasoning effort when selected model changes
	$: if (selectedModelIds.length > 0 && preferencesLoaded) {
		const newModelId = selectedModelIds[0];
		if (newModelId !== currentTrackedModel) {
			const isFirstTimeSettingModel = !currentTrackedModel;
			const shouldLoadStoredPreference =
				!isFirstTimeSettingModel || !userModifiedEffortForCurrentModel;

			currentTrackedModel = newModelId;
			userModifiedEffortForCurrentModel = false;

			const allowed = getAllowedEffortsForModel(newModelId);

			if (shouldLoadStoredPreference) {
				const newEffort = reasoningEffortByModel[newModelId] || 'medium';
				reasoningEffort = clampEffortToAllowed(newEffort, allowed) ?? 'medium';
			} else {
				const clamped = clampEffortToAllowed(reasoningEffort, allowed) ?? 'medium';
				reasoningEffort = clamped;
				reasoningEffortByModel[newModelId] = clamped;
				saveReasoningEffortPreferences();
			}
		}
	}

	// If model capabilities change (admin updates), ensure current selection is still valid.
	$: if (selectedModelIds.length === 1 && preferencesLoaded) {
		const modelId = selectedModelIds[0];
		const allowed = getAllowedEffortsForModel(modelId);
		const clamped = clampEffortToAllowed(reasoningEffort, allowed);
		if (clamped && clamped !== reasoningEffort) {
			reasoningEffort = clamped;
			reasoningEffortByModel[modelId] = clamped;
			saveReasoningEffortPreferences();
		}
	}

	// Handle user changes to reasoning effort
	const handleReasoningEffortChange = (event) => {
		const requestedEffort = event.target.value;

		const modelToUse =
			currentTrackedModel || (selectedModelIds.length > 0 ? selectedModelIds[0] : null);
		const allowed = modelToUse ? getAllowedEffortsForModel(modelToUse) : BASE_REASONING_EFFORTS;
		const clamped = clampEffortToAllowed(requestedEffort, allowed) ?? 'medium';

		reasoningEffort = clamped;
		userModifiedEffortForCurrentModel = true;

		if (modelToUse) {
			reasoningEffortByModel[modelToUse] = clamped;
			saveReasoningEffortPreferences();
		}
	};

	let showInputVariablesModal = false;
	let inputVariablesModalCallback = (variableValues) => {};
	let inputVariables = {};
	let inputVariableValues = {};

	let showValvesModal = false;
	let selectedValvesType = 'tool'; // 'tool' or 'function'
	let selectedValvesItemId = null;
	let integrationsMenuCloseOnOutsideClick = true;

	$: if (!showValvesModal) {
		integrationsMenuCloseOnOutsideClick = true;
	}

	$: onChange({
		prompt,
		files: files
			.filter((file) => file.type !== 'image')
			.map((file) => {
				return {
					...file,
					user: undefined,
					access_control: undefined
				};
			}),
		selectedToolIds,
		selectedFilterIds,
		imageGenerationEnabled,
		webSearchEnabled,
		codeInterpreterEnabled,
		// Only include reasoning when the selected model is configured as a reasoning model.
		...(showReasoningEffortSelector ? { reasoning: { effort: reasoningEffort } } : {})
	});

	const inputVariableHandler = async (text: string): Promise<string> => {
		inputVariables = extractInputVariables(text);

		// No variables? return the original text immediately.
		if (Object.keys(inputVariables).length === 0) {
			return text;
		}

		// Show modal and wait for the user's input.
		showInputVariablesModal = true;
		return await new Promise<string>((resolve) => {
			inputVariablesModalCallback = (variableValues) => {
				inputVariableValues = { ...inputVariableValues, ...variableValues };
				replaceVariables(inputVariableValues);
				showInputVariablesModal = false;
				resolve(text);
			};
		});
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

		return text;
	};

	const replaceVariables = (variables: Record<string, any>) => {
		console.log('Replacing variables:', variables);

		const chatInput = document.getElementById('chat-input');

		if (chatInput) {
			chatInputElement.replaceVariables(variables);
			chatInputElement.focus();
		}
	};

	export const setText = async (text?: string, cb?: (text: string) => void) => {
		const chatInput = document.getElementById('chat-input');

		if (chatInput) {
			if (text !== '') {
				text = await textVariableHandler(text || '');
			}

			chatInputElement?.setText(text);
			chatInputElement?.focus();

			if (text !== '') {
				text = await inputVariableHandler(text);
			}

			await tick();
			if (cb) await cb(text);
		}
	};

	const getCommand = () => {
		const chatInput = document.getElementById('chat-input');
		let word = '';

		if (chatInput) {
			word = chatInputElement?.getWordAtDocPos();
		}

		return word;
	};

	const replaceCommandWithText = (text) => {
		const chatInput = document.getElementById('chat-input');
		if (!chatInput) return;

		chatInputElement?.replaceCommandWithText(text);
	};

	const insertTextAtCursor = async (text: string) => {
		const chatInput = document.getElementById('chat-input');
		if (!chatInput) return;

		text = await textVariableHandler(text);

		if (command) {
			replaceCommandWithText(text);
		} else {
			chatInputElement?.insertContent(text);
		}

		await tick();
		text = await inputVariableHandler(text);
		await tick();

		const chatInputContainer = document.getElementById('chat-input-container');
		if (chatInputContainer) {
			chatInputContainer.scrollTop = chatInputContainer.scrollHeight;
		}

		await tick();
		if (chatInput) {
			chatInput.focus();
			chatInput.dispatchEvent(new Event('input'));

			const words = extractCurlyBraceWords(prompt);

			if (words.length > 0) {
				const word = words.at(0);
				await tick();
			} else {
				chatInput.scrollTop = chatInput.scrollHeight;
			}
		}
	};

	let command = '';
	export let showCommands = false;
	$: showCommands = ['/', '#', '@'].includes(command?.charAt(0)) || '\\#' === command?.slice(0, 2);
	let suggestions = null;

	let showTools = false;
	let toolSelectionReady = false;

	let activeServerToolIds: string[] = [];
	$: activeServerToolIds = toolSelectionReady
		? (selectedToolIds ?? []).filter(
				(id) =>
					id.startsWith('server:mcp:') ||
					id.startsWith('server:') ||
					id.startsWith('direct_server:')
			)
		: [];

	const getToolLabel = (toolId: string) => {
		// Local tools + server tools returned by `/tools`
		const tool = ($tools ?? []).find((t) => t.id === toolId);
		if (tool?.name) return tool.name;

		// Direct tool servers (OpenAPI direct connections)
		if (toolId.startsWith('direct_server:')) {
			const idx = Number(toolId.split(':').at(-1));
			const server = Number.isFinite(idx) ? ($toolServers ?? [])[idx] : null;
			return server?.info?.title ?? server?.url ?? toolId;
		}

		return toolId;
	};

	let loaded = false;
	let recording = false;

	let isComposing = false;
	// Safari has a bug where compositionend is not triggered correctly #16615
	// when using the virtual keyboard on iOS.
	let compositionEndedAt = -2e8;
	const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
	function inOrNearComposition(event: Event) {
		if (isComposing) {
			return true;
		}
		// See https://www.stum.de/2016/06/24/handling-ime-events-in-javascript/.
		// On Japanese input method editors (IMEs), the Enter key is used to confirm character
		// selection. On Safari, when Enter is pressed, compositionend and keydown events are
		// emitted. The keydown event triggers newline insertion, which we don't want.
		// This method returns true if the keydown event should be ignored.
		// We only ignore it once, as pressing Enter a second time *should* insert a newline.
		// Furthermore, the keydown event timestamp must be close to the compositionEndedAt timestamp.
		// This guards against the case where compositionend is triggered without the keyboard
		// (e.g. character confirmation may be done with the mouse), and keydown is triggered
		// afterwards- we wouldn't want to ignore the keydown event in this case.
		if (isSafari && Math.abs(event.timeStamp - compositionEndedAt) < 500) {
			compositionEndedAt = -2e8;
			return true;
		}
		return false;
	}

	let chatInputContainerElement;
	let chatInputElement;

	let filesInputElement;
	let commandsElement;

	let inputFiles;

	let dragged = false;
	let shiftKey = false;

	let user = null;
	export let placeholder = '';

	let visionCapableModels = [];
	$: visionCapableModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.vision ?? true
	);

	let effectiveVisionCapableModels = [];
	$: effectiveVisionCapableModels = (
		atSelectedModel?.id ? [atSelectedModel.id] : selectedModels
	).filter((modelId) => {
		const model = $models.find((m) => m.id === modelId);
		return (
			(model?.info?.meta?.capabilities?.vision ?? true) ||
			model?.info?.meta?.vision_preprocessor_model_id
		);
	});

	let fileUploadCapableModels = [];
	$: fileUploadCapableModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.file_upload ?? true
	);

	let webSearchCapableModels = [];
	$: webSearchCapableModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
	);

	let imageGenerationCapableModels = [];
	$: imageGenerationCapableModels = (
		atSelectedModel?.id ? [atSelectedModel.id] : selectedModels
	).filter(
		(model) =>
			$models.find((m) => m.id === model)?.info?.meta?.capabilities?.image_generation ?? true
	);

	let codeInterpreterCapableModels = [];
	$: codeInterpreterCapableModels = (
		atSelectedModel?.id ? [atSelectedModel.id] : selectedModels
	).filter(
		(model) =>
			$models.find((m) => m.id === model)?.info?.meta?.capabilities?.code_interpreter ?? true
	);

	let toggleFilters = [];
	$: toggleFilters = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels)
		.map((id) => ($models.find((model) => model.id === id) || {})?.filters ?? [])
		.reduce((acc, filters) => acc.filter((f1) => filters.some((f2) => f2.id === f1.id)));

	let showToolsButton = false;
	$: showToolsButton = ($tools ?? []).length > 0 || ($toolServers ?? []).length > 0;

	let showWebSearchButton = false;
	$: showWebSearchButton =
		(atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).length ===
			webSearchCapableModels.length &&
		$config?.features?.enable_web_search &&
		($_user.role === 'admin' || $_user?.permissions?.features?.web_search);

	let showStudyModeButton = false;
	$: showStudyModeButton = $config?.features?.enable_study_mode;

	let showImageGenerationButton = false;
	$: showImageGenerationButton =
		(atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).length ===
			imageGenerationCapableModels.length &&
		$config?.features?.enable_image_generation &&
		($_user.role === 'admin' || $_user?.permissions?.features?.image_generation);

	let showCodeInterpreterButton = false;
	$: showCodeInterpreterButton =
		(atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).length ===
			codeInterpreterCapableModels.length &&
		$config?.features?.enable_code_interpreter &&
		($_user.role === 'admin' || $_user?.permissions?.features?.code_interpreter);

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

		if (fileUploadCapableModels.length !== selectedModels.length) {
			toast.error($i18n.t('Model(s) do not support file upload'));
			return null;
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
				url: '',
				name: file.name,
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

		if (!$temporaryChatEnabled) {
			try {
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

				// Upload as a chat attachment (no background content extraction / RAG ingestion).
				const uploadedFile = await uploadFile(localStorage.token, file, metadata);

					if (uploadedFile) {
						console.log('File upload completed:', {
							id: uploadedFile.id,
							name: fileItem.name
						});

					if (uploadedFile.error) {
						console.warn('File upload warning:', uploadedFile.error);
						toast.warning(uploadedFile.error);
					}

					fileItem.status = 'uploaded';
					fileItem.file = uploadedFile;
					fileItem.id = uploadedFile.id;
					fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

					files = files;
				} else {
					files = files.filter((item) => item?.itemId !== tempItemId);
				}
			} catch (e) {
				toast.error(`${e}`);
				files = files.filter((item) => item?.itemId !== tempItemId);
			}
		} else {
			// If temporary chat is enabled, we just add the file to the list without uploading it.

			const content = await extractContentFromFile(file).catch((error) => {
				toast.error(
					$i18n.t('Failed to extract content from the file: {{error}}', { error: error })
				);
				return null;
			});

			if (content === null) {
				toast.error($i18n.t('Failed to extract content from the file.'));
				files = files.filter((item) => item?.itemId !== tempItemId);
				return null;
			} else {
				console.log('Extracted content from file:', {
					name: file.name,
					size: file.size,
					content: content
				});

				fileItem.status = 'uploaded';
				fileItem.type = 'text';
				fileItem.content = content;
				fileItem.id = uuidv4(); // Temporary ID for the file

				files = files;
			}
		}
	};

		const getFileExtension = (filename: string) => {
			const dotIndex = filename.lastIndexOf('.');
			return dotIndex === -1 ? '' : filename.slice(dotIndex).toLowerCase();
		};

		const normalizeImageMimeType = (type: string) => {
			const normalized = (type || '').toLowerCase();
			if (normalized === 'image/jpg') return 'image/jpeg';
			return normalized;
		};

		const inferImageMimeTypeFromExtension = (filename: string) => {
			const ext = getFileExtension(filename || '');
			switch (ext) {
				case '.png':
					return 'image/png';
				case '.jpg':
				case '.jpeg':
					return 'image/jpeg';
				case '.gif':
					return 'image/gif';
				case '.webp':
					return 'image/webp';
				default:
					return null;
			}
		};

		const isHeicLikeImage = (file: File) => {
			const type = (file.type || '').toLowerCase();
			const ext = getFileExtension(file.name || '');
			return (
				type === 'image/heic' ||
				type === 'image/heif' ||
				type === 'image/heic-sequence' ||
				type === 'image/heif-sequence' ||
				ext === '.heic' ||
				ext === '.heif'
			);
		};

		const isImageLikeFile = (file: File) => {
			const type = normalizeImageMimeType(file.type || '');
			if (
				[
					'image/png',
					'image/jpeg',
					'image/webp',
					'image/gif',
					'image/heic',
					'image/heif',
					'image/heic-sequence',
					'image/heif-sequence'
				].includes(type)
			) {
				return true;
			}

			const ext = getFileExtension(file.name || '');
			return ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.heif'].includes(ext);
		};

		const replaceExtension = (filename: string, newExtension: string) => {
			const dotIndex = filename.lastIndexOf('.');
			if (dotIndex === -1) return `${filename}${newExtension}`;
			return `${filename.slice(0, dotIndex)}${newExtension}`;
		};

		const inputFilesHandler = async (inputFiles: File[] | FileList) => {
			const inputFilesArray = Array.from(inputFiles ?? []);
			console.log('Input files handler called with:', inputFilesArray);

			if (
				($config?.file?.max_count ?? null) !== null &&
				files.length + inputFilesArray.length > ($config?.file?.max_count ?? 0)
			) {
				toast.error(
					$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
						maxCount: $config?.file?.max_count
					})
				);
				return;
			}

			const maxSizeMb = $config?.file?.max_size ?? null;
			const maxSizeBytes = maxSizeMb !== null ? maxSizeMb * 1024 * 1024 : null;

			const getErrorText = (err: any) => {
				const truncate = (text: string, maxLength = 500) =>
					text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;

				if (!err) return null;

				let text: string | null = null;

				if (typeof err === 'string') {
					text = err;
				} else if (typeof err?.detail === 'string') {
					text = err.detail;
				} else if (typeof err?.message === 'string') {
					text = err.message;
				} else {
					const detail = err?.detail;
					if (detail && typeof detail === 'object') {
						if (typeof detail.message === 'string') text = detail.message;
						else if (typeof detail.error === 'string') text = detail.error;
						else {
							try {
								text = JSON.stringify(detail);
							} catch {
								// ignore
							}
						}
					}

					if (text === null) {
						try {
							text = JSON.stringify(err);
						} catch {
							// ignore
						}
					}

					if (text === null) {
						text = String(err);
					}
				}

				return text ? truncate(text) : null;
			};

			const handleInputFile = async (file: File) => {
				console.log('Processing file:', {
					name: file.name,
					type: file.type,
					size: file.size,
					extension: file.name.split('.').at(-1)
				});

				const isImageLike = isImageLikeFile(file);
				if (!isImageLike) {
					if (maxSizeBytes !== null && file.size > maxSizeBytes) {
						console.log('File exceeds max size limit:', {
							fileSize: file.size,
							maxSize: maxSizeBytes
						});
						toast.error(
							$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
								maxSize: maxSizeMb
							})
						);
						return;
					}

					await uploadFileHandler(file);
					return;
				}

				if (effectiveVisionCapableModels.length === 0) {
					toast.error($i18n.t('Selected model(s) do not support image inputs'));
					return;
				}

				const tempImageId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
				const abortController = new AbortController();
				imageUploadAbortControllers.set(tempImageId, abortController);

				let fileToUpload: File = file;

				if (!isHeicLikeImage(file)) {
					const normalizedType = normalizeImageMimeType(file.type || '');
					const inferredType = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(normalizedType)
						? normalizedType
						: inferImageMimeTypeFromExtension(file.name || '');

					if (inferredType) {
						const currentType = (fileToUpload.type || '').toLowerCase();
						const fileName = fileToUpload.name || `image-${Date.now()}`;
						fileToUpload =
							currentType === inferredType
								? fileToUpload
								: new File([fileToUpload], fileName, {
										type: inferredType,
										lastModified: fileToUpload.lastModified
									});
					}
				}

				let previewUrl = URL.createObjectURL(fileToUpload);
				files = [
					...files,
					{
						type: 'image',
						url: previewUrl,
						status: 'uploading',
						progress: 0,
						itemId: tempImageId
					}
				];

				const updateProgress = (progress: number) => {
					const fileIndex = files.findIndex((f) => f.itemId === tempImageId);
					if (fileIndex !== -1) {
						// Upload progress can reach 100% before the server responds (e.g. remote storage),
						// so cap at 99% until we actually mark the file as uploaded.
						files[fileIndex].progress = Math.max(0, Math.min(99, progress));
						files = files;
					}
				};

				try {
					if (isHeicLikeImage(file)) {
						let converted: any;
						try {
							converted = await convertHeicToJpeg(file, { quality: 0.92 });
						} catch (conversionErr) {
							const conversionText = getErrorText(conversionErr);
							throw new Error(
								conversionText
									? `HEIC/HEIF conversion failed: ${conversionText}`
									: 'HEIC/HEIF conversion failed'
							);
						}
						const outputName = replaceExtension(file.name || 'image', '.jpg');
						fileToUpload = new File([converted as BlobPart], outputName, {
							type: 'image/jpeg',
							lastModified: file.lastModified
						});

						const jpegPreviewUrl = URL.createObjectURL(fileToUpload);
						URL.revokeObjectURL(previewUrl);
						previewUrl = jpegPreviewUrl;

						const fileIndex = files.findIndex((f) => f.itemId === tempImageId);
						if (fileIndex !== -1) {
							files[fileIndex].url = previewUrl;
							files = files;
						}
					}

					const uploadedFile = await uploadFile(localStorage.token, fileToUpload, null, {
						onProgress: updateProgress,
						signal: abortController.signal
					});

					if (!uploadedFile) {
						throw new Error('Upload failed: server returned an empty response');
					}

					URL.revokeObjectURL(previewUrl);

					const fileIndex = files.findIndex((f) => f.itemId === tempImageId);
					if (fileIndex === -1 || canceledImageUploads.has(tempImageId)) {
						try {
							await deleteFileById(localStorage.token, uploadedFile.id);
						} catch (err) {
							console.error(err);
						}
						return;
					}

					files[fileIndex] = {
						type: 'image',
						url: `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}/content`,
						status: 'uploaded',
						progress: 100,
						itemId: tempImageId,
						file: uploadedFile,
						id: uploadedFile.id
					};
					files = files;
				} catch (err: any) {
					URL.revokeObjectURL(previewUrl);

					const isAbortError = err?.name === 'AbortError';
					if (isAbortError || canceledImageUploads.has(tempImageId)) {
						files = files.filter((f) => f.itemId !== tempImageId);
						return;
					}

					console.error(err);
					files = files.filter((f) => f.itemId !== tempImageId);
					const errorText = getErrorText(err);
					const name = file?.name || 'image';
					toast.error(
						errorText ? `${name}: ${errorText}` : `${name}: ${$i18n.t('Failed to upload image')}`
					);
				} finally {
					canceledImageUploads.delete(tempImageId);
					imageUploadAbortControllers.delete(tempImageId);
				}
			};

			const maxConcurrentUploads = $mobile ? 2 : 4;
			const queue = [...inputFilesArray];
			const workers = Array.from({ length: Math.min(maxConcurrentUploads, queue.length) }, async () => {
				while (queue.length > 0) {
					const nextFile = queue.shift();
					if (nextFile) {
						await handleInputFile(nextFile);
					}
				}
			});

			void Promise.all(workers);
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

	const onKeyDown = (e) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}

		if (e.key === 'Escape') {
			console.log('Escape');
			dragged = false;
			
			// Stop response if generating (allows Escape to work even when input is not focused)
			if (generating || (taskIds && taskIds.length > 0) || (history?.currentId && history.messages[history.currentId]?.done != true)) {
				stopResponse();
			}
		}
	};

	const onKeyUp = (e) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
	};

	onMount(async () => {
		suggestions = [
			{
				char: '@',
				render: getSuggestionRenderer(CommandSuggestionList, {
					i18n,
					onSelect: (e) => {
						const { type, data } = e;

						if (type === 'model') {
							atSelectedModel = data;
						}

						document.getElementById('chat-input')?.focus();
					},

					insertTextHandler: insertTextAtCursor,
					onUpload: (e) => {
						const { type, data } = e;

						if (type === 'file') {
							if (files.find((f) => f.id === data.id)) {
								return;
							}
							files = [
								...files,
								{
									...data,
									status: 'processed'
								}
							];
						} else {
							dispatch('upload', e);
						}
					}
				})
			},
			{
				char: '/',
				render: getSuggestionRenderer(CommandSuggestionList, {
					i18n,
					onSelect: (e) => {
						const { type, data } = e;

						if (type === 'model') {
							atSelectedModel = data;
						}

						document.getElementById('chat-input')?.focus();
					},

					insertTextHandler: insertTextAtCursor,
					onUpload: (e) => {
						const { type, data } = e;

						if (type === 'file') {
							if (files.find((f) => f.id === data.id)) {
								return;
							}
							files = [
								...files,
								{
									...data,
									status: 'processed'
								}
							];
						} else {
							dispatch('upload', e);
						}
					}
				})
			},
			{
				char: '#',
				render: getSuggestionRenderer(CommandSuggestionList, {
					i18n,
					onSelect: (e) => {
						const { type, data } = e;

						if (type === 'model') {
							atSelectedModel = data;
						}

						document.getElementById('chat-input')?.focus();
					},

					insertTextHandler: insertTextAtCursor,
					onUpload: (e) => {
						const { type, data } = e;

						if (type === 'file') {
							if (files.find((f) => f.id === data.id)) {
								return;
							}
							files = [
								...files,
								{
									...data,
									status: 'processed'
								}
							];
						} else {
							dispatch('upload', e);
						}
					}
				})
			}
		];
		loaded = true;

		window.setTimeout(() => {
			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		}, 0);

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		await tick();

		const dropzoneElement = document.getElementById('chat-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);

		// Load tool list then sanitize selectedToolIds before rendering any "active tool" UI.
		// This prevents a brief "1 available tool" flicker when a previously-selected
		// tool server/tool has been deleted in admin settings.
		const fetchedTools = await getTools(localStorage.token);
		await tools.set(fetchedTools);

		const fetchedToolIdSet = new Set((fetchedTools ?? []).map((t) => t?.id).filter(Boolean));
		selectedToolIds = (selectedToolIds ?? []).filter((id) => {
			if (!id) return false;
			if (fetchedToolIdSet.has(id)) return true;

			// Direct tool servers are generated client-side from $toolServers.
			if (id.startsWith('direct_server:')) {
				const idx = Number(id.split(':').at(-1));
				return Number.isFinite(idx) && Boolean(($toolServers ?? [])[idx]?.info);
			}

			return false;
		});
		toolSelectionReady = true;

		// Load reasoning effort preferences
		loadReasoningEffortPreferences();
	});

	onDestroy(() => {
		console.log('destroy');
		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);

		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur', onBlur);

		const dropzoneElement = document.getElementById('chat-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<FilesOverlay show={dragged} />
<ToolServersModal bind:show={showTools} {selectedToolIds} />

<InputVariablesModal
	bind:show={showInputVariablesModal}
	variables={inputVariables}
	onSave={inputVariablesModalCallback}
/>

<ValvesModal
	bind:show={showValvesModal}
	userValves={true}
	type={selectedValvesType}
	id={selectedValvesItemId ?? null}
	on:save={async () => {
		await tick();
	}}
	on:close={() => {
		integrationsMenuCloseOnOutsideClick = true;
	}}
/>

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
			</div>
		</div>

		<div class="bg-transparent">
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
							onCancel={async () => {
								recording = false;

								await tick();
								document.getElementById('chat-input')?.focus();
							}}
							onConfirm={async (data) => {
								const { text, filename } = data;

								recording = false;

								await tick();
								insertTextAtCursor(text);

								await tick();
								document.getElementById('chat-input')?.focus();

								if ($settings?.speechAutoSend ?? false) {
									dispatch('submit', prompt);
								}
							}}
						/>
					{:else}
						<form
							class="w-full flex flex-col gap-1.5"
							on:submit|preventDefault={() => {
								// check if selectedModels support image input
								dispatch('submit', prompt);
							}}
						>
							<div
								id="message-input-container"
								class="flex-1 flex flex-col relative w-full shadow-lg rounded-3xl border {$temporaryChatEnabled
									? 'border-dashed border-gray-100 dark:border-gray-800 hover:border-gray-200 focus-within:border-gray-200 hover:dark:border-gray-700 focus-within:dark:border-gray-700'
									: ' border-gray-100 dark:border-gray-850 hover:border-gray-200 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800'}  transition px-1 bg-white/5 dark:bg-gray-500/5 backdrop-blur-sm dark:text-gray-100"
								dir={$settings?.chatDirection ?? 'auto'}
							>
								{#if atSelectedModel !== undefined}
									<div class="px-3 pt-3 text-left w-full flex flex-col z-10">
										<div class="flex items-center justify-between w-full">
											<div class="pl-[1px] flex items-center gap-2 text-sm dark:text-gray-500">
												<img
													crossorigin="anonymous"
													alt="model profile"
													class="size-3.5 max-w-[28px] object-cover rounded-full"
													src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta
														?.profile_image_url ??
														($i18n.language === 'dg-DG'
															? `${WEBUI_BASE_URL}/doge.png`
															: `${WEBUI_BASE_URL}/static/favicon.png`)}
												/>
												<div class="translate-y-[0.5px]">
													<span class="">{atSelectedModel.name}</span>
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
									</div>
								{/if}

								{#if files.length > 0}
									<div class="mx-2 mt-2.5 pb-1.5 flex items-center flex-wrap gap-2">
										{#each files as file, fileIdx}
											{#if file.type === 'image'}
												<div class="relative group">
													<div class="relative">
														<Image
															src={file.url}
															alt=""
															imageClassName="max-h-48 max-w-64 rounded-xl object-cover"
														/>
														{#if file.status === 'uploading'}
															<div
																class="absolute inset-0 rounded-xl bg-black/40 flex items-center justify-center"
															>
																<!-- Circular progress ring -->
																<svg class="size-12" viewBox="0 0 36 36">
																	<!-- Background circle -->
																	<circle
																		cx="18"
																		cy="18"
																		r="14"
																		fill="none"
																		stroke="rgba(255,255,255,0.3)"
																		stroke-width="3"
																	/>
																	<!-- Progress circle -->
																	<circle
																		cx="18"
																		cy="18"
																		r="14"
																		fill="none"
																		stroke="white"
																		stroke-width="3"
																		stroke-linecap="round"
																		stroke-dasharray={2 * Math.PI * 14}
																		stroke-dashoffset={2 *
																			Math.PI *
																			14 *
																			(1 - (file.progress || 0) / 100)}
																		transform="rotate(-90 18 18)"
																		class="transition-all duration-150"
																	/>
																</svg>
															</div>
														{/if}
														{#if atSelectedModel ? effectiveVisionCapableModels.length === 0 : selectedModels.length !== effectiveVisionCapableModels.length}
															<Tooltip
																className="absolute top-2 left-2"
																content={$i18n.t(
																	'Models without native vision (using preprocessor): {{ models }}',
																	{
																		models: [
																			...(atSelectedModel ? [atSelectedModel] : selectedModels)
																		]
																			.filter((id) => !effectiveVisionCapableModels.includes(id))
																			.join(', ')
																	}
																)}
															>
																<svg
																	xmlns="http://www.w3.org/2000/svg"
																	viewBox="0 0 24 24"
																	fill="currentColor"
																	aria-hidden="true"
																	class="size-5 fill-yellow-300"
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
													<!-- Action buttons (top right) -->
													<div class="absolute top-1.5 right-1.5 flex gap-1">
														<button
															class="p-1.5 bg-white/90 hover:bg-white text-gray-700 rounded-full shadow-sm {($settings?.highContrastMode ??
															false) || $mobile || file.status === 'uploading'
																? ''
																: 'group-hover:opacity-100 opacity-0 transition-opacity'}"
															type="button"
															aria-label={$i18n.t('Remove file')}
																on:click={() => {
																	const fileToRemove = files[fileIdx];
																	if (
																		fileToRemove?.type === 'image' &&
																		fileToRemove?.status === 'uploading' &&
																		fileToRemove?.itemId
																	) {
																		canceledImageUploads.add(fileToRemove.itemId);
																		imageUploadAbortControllers.get(fileToRemove.itemId)?.abort();
																		imageUploadAbortControllers.delete(fileToRemove.itemId);
																	}

																	const url = fileToRemove?.url;
																	if (typeof url === 'string' && url.startsWith('blob:')) {
																		URL.revokeObjectURL(url);
																}

																files.splice(fileIdx, 1);
																files = files;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 20 20"
																fill="currentColor"
																aria-hidden="true"
																class="size-4"
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
													small={true}
													modal={['file', 'collection'].includes(file?.type)}
													on:dismiss={async () => {
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

								<div class="px-2.5">
									<div
										class="scrollbar-hidden rtl:text-right ltr:text-left bg-transparent dark:text-gray-100 outline-hidden w-full pb-1 px-1 resize-none h-fit max-h-96 overflow-auto {files.length ===
										0
											? atSelectedModel !== undefined
												? 'pt-1.5'
												: 'pt-2.5'
											: ''}"
										id="chat-input-container"
									>
										{#if suggestions}
											{#key $settings?.richTextInput ?? true}
												{#key $settings?.showFormattingToolbar ?? false}
													<RichTextInput
														bind:this={chatInputElement}
														id="chat-input"
														onChange={(e) => {
															prompt = e.md;
															command = getCommand();
														}}
														json={true}
														richText={$settings?.richTextInput ?? true}
														messageInput={true}
														showFormattingToolbar={$settings?.showFormattingToolbar ?? false}
														floatingMenuPlacement={'top-start'}
														insertPromptAsRichText={$settings?.insertPromptAsRichText ?? false}
														shiftEnter={!($settings?.ctrlEnterToSend ?? false) &&
															!$mobile &&
															!(
																'ontouchstart' in window ||
																navigator.maxTouchPoints > 0 ||
																navigator.msMaxTouchPoints > 0
															)}
														placeholder={placeholder ? placeholder : $i18n.t('Send a Message')}
														largeTextAsFile={($settings?.largeTextAsFile ?? false) && !shiftKey}
														autocomplete={$config?.features?.enable_autocomplete_generation &&
															($settings?.promptAutocomplete ?? false)}
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
														{suggestions}
														oncompositionstart={() => (isComposing = true)}
														oncompositionend={(e) => {
															compositionEndedAt = e.timeStamp;
															isComposing = false;
														}}
														on:keydown={async (e) => {
															e = e.detail.event;

															const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
															const suggestionsContainerElement =
																document.getElementById('suggestions-container');

															if (e.key === 'Escape') {
																stopResponse();
															}

															// Command/Ctrl + Shift + Enter to submit a message pair
															if (isCtrlPressed && e.key === 'Enter' && e.shiftKey) {
																e.preventDefault();
																createMessagePair(prompt);
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

															if (!suggestionsContainerElement) {
																if (
																	!$mobile ||
																	!(
																		'ontouchstart' in window ||
																		navigator.maxTouchPoints > 0 ||
																		navigator.msMaxTouchPoints > 0
																	)
																) {
																	if (inOrNearComposition(e)) {
																		return;
																	}

																	// Uses keyCode '13' for Enter key for chinese/japanese keyboards.
																	//
																	// Depending on the user's settings, it will send the message
																	// either when Enter is pressed or when Ctrl+Enter is pressed.
																	const enterPressed =
																		($settings?.ctrlEnterToSend ?? false)
																			? (e.key === 'Enter' || e.keyCode === 13) && isCtrlPressed
																			: (e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey;

																	if (enterPressed) {
																		e.preventDefault();
																		if (prompt !== '' || files.length > 0) {
																			dispatch('submit', prompt);
																		}
																	}
																}
															}

															if (e.key === 'Escape') {
																console.log('Escape');
																atSelectedModel = undefined;
																selectedToolIds = [];
																selectedFilterIds = [];

																webSearchEnabled = false;
																imageGenerationEnabled = false;
																codeInterpreterEnabled = false;
															}
														}}
														on:paste={async (e) => {
															e = e.detail.event;
															console.log(e);

															const clipboardData = e.clipboardData || window.clipboardData;

															if (clipboardData && clipboardData.items) {
																for (const item of clipboardData.items) {
																	if (item.type.indexOf('image') !== -1) {
																		const file = item.getAsFile();
																		if (file) {
																			await inputFilesHandler([file]);
																			e.preventDefault();
																		}
																	} else if (item?.kind === 'file') {
																		const file = item.getAsFile();
																		if (file) {
																			const _files = [file];
																			await inputFilesHandler(_files);
																			e.preventDefault();
																		}
																	} else if (item.type === 'text/plain') {
																		if (($settings?.largeTextAsFile ?? false) && !shiftKey) {
																			const text = clipboardData.getData('text/plain');

																			if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
																				e.preventDefault();
																				const blob = new Blob([text], { type: 'text/plain' });
																				const file = new File(
																					[blob],
																					`Pasted_Text_${Date.now()}.txt`,
																					{
																						type: 'text/plain'
																					}
																				);

																				await uploadFileHandler(file, true);
																			}
																		}
																	}
																}
															}
														}}
													/>
												{/key}
											{/key}
										{/if}
									</div>
								</div>

								<div class=" flex justify-between mt-0.5 mb-2.5 mx-0.5 max-w-full" dir="ltr">
									<div class="ml-1 self-end flex items-center flex-1 max-w-[80%]">
										<InputMenu
											bind:files
											selectedModels={atSelectedModel ? [atSelectedModel.id] : selectedModels}
											{fileUploadCapableModels}
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
											uploadOneDriveHandler={async (authorityType) => {
												try {
													const fileData = await pickAndDownloadFile(authorityType);
													if (fileData) {
														const file = new File([fileData.blob], fileData.name, {
															type: fileData.blob.type || 'application/octet-stream'
														});
														await uploadFileHandler(file);
													} else {
														console.log('No file was selected from OneDrive');
													}
												} catch (error) {
													console.error('OneDrive Error:', error);
												}
											}}
											onUpload={async (e) => {
												dispatch('upload', e);
											}}
											onClose={async () => {
												await tick();

												const chatInput = document.getElementById('chat-input');
												chatInput?.focus();
											}}
										>
											<div
												id="input-menu-button"
												class="bg-transparent hover:bg-gray-100 text-gray-700 dark:text-white dark:hover:bg-gray-800 rounded-full size-9 flex justify-center items-center outline-hidden focus:outline-hidden"
											>
												<PlusAlt className="size-6" />
											</div>
										</InputMenu>

										<div
											class="flex self-center w-[1px] h-5 mx-1 bg-gray-200/50 dark:bg-gray-800/50"
										/>

									{#if showWebSearchButton}
										<Tooltip content={$i18n.t('Web Search')} placement="top">
											<button
												on:click|preventDefault={() => (webSearchEnabled = !webSearchEnabled)}
												type="button"
												class="group p-2 flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden {webSearchEnabled ||
												($settings?.webSearch ?? false) === 'always'
													? ' text-sky-500 dark:text-sky-300 bg-sky-50 hover:bg-sky-100 dark:bg-sky-400/10 dark:hover:bg-sky-600/10 border border-sky-200/40 dark:border-sky-500/20'
													: 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 '}"
											>
												<GlobeAlt className="size-5" strokeWidth="1.75" />
												{#if webSearchEnabled}
													<div class="hidden group-hover:block">
														<XMark className="size-4" strokeWidth="1.75" />
													</div>
												{/if}
											</button>
										</Tooltip>
									{/if}

									{#if toolSelectionReady}
										{#each activeServerToolIds as toolId (toolId)}
											<Tooltip content={getToolLabel(toolId)} placement="top">
												<button
													on:click|preventDefault={() => {
														selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
												}}
												type="button"
												class="group px-2 py-1.5 flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden text-sky-500 dark:text-sky-300 bg-sky-50 hover:bg-sky-100 dark:bg-sky-400/10 dark:hover:bg-sky-600/10 border border-sky-200/40 dark:border-sky-500/20"
												aria-label={$i18n.t('Disable {{NAME}}', { NAME: getToolLabel(toolId) })}
											>
												<Wrench className="size-4" strokeWidth="1.75" />
												<span class="max-w-24 truncate text-xs font-medium">{getToolLabel(toolId)}</span>
												<div class="hidden group-hover:block">
													<XMark className="size-4" strokeWidth="1.75" />
												</div>
											</button>
										</Tooltip>
										{/each}
									{/if}

									{#if showStudyModeButton || showImageGenerationButton || showCodeInterpreterButton || showToolsButton || (toggleFilters && toggleFilters.length > 0)}
										<IntegrationsMenu
											selectedModels={atSelectedModel ? [atSelectedModel.id] : selectedModels}
											{toggleFilters}
												showWebSearchButton={false}
												{showStudyModeButton}
												{showImageGenerationButton}
												{showCodeInterpreterButton}
												bind:selectedToolIds
												bind:selectedFilterIds
												bind:webSearchEnabled
												bind:studyModeEnabled
												bind:imageGenerationEnabled
												bind:codeInterpreterEnabled
												closeOnOutsideClick={integrationsMenuCloseOnOutsideClick}
												onShowValves={(e) => {
													const { type, id } = e;
													selectedValvesType = type;
													selectedValvesItemId = id;
													showValvesModal = true;
													integrationsMenuCloseOnOutsideClick = false;
												}}
												onClose={async () => {
													await tick();

													const chatInput = document.getElementById('chat-input');
													chatInput?.focus();
												}}
											>
												<div
													id="integration-menu-button"
													class="bg-transparent hover:bg-gray-100 text-gray-700 dark:text-white dark:hover:bg-gray-800 rounded-full size-9 flex justify-center items-center outline-hidden focus:outline-hidden"
												>
													<Component className="size-5" strokeWidth="1.5" />
												</div>
											</IntegrationsMenu>
										{/if}

										{#if selectedModelIds.length === 1 && $models.find((m) => m.id === selectedModelIds[0])?.has_user_valves}
											<div class="ml-1 flex gap-1.5">
												<Tooltip content={$i18n.t('Valves')} placement="top">
													<button
														id="model-valves-button"
														class="bg-transparent hover:bg-gray-100 text-gray-700 dark:text-white dark:hover:bg-gray-800 rounded-full size-8 flex justify-center items-center outline-hidden focus:outline-hidden"
														on:click={() => {
															selectedValvesType = 'function';
															selectedValvesItemId = selectedModelIds[0]?.split('.')[0];
															showValvesModal = true;
														}}
													>
														<Knobs className="size-4" strokeWidth="1.5" />
													</button>
												</Tooltip>
											</div>
										{/if}

										<div class="ml-1 flex gap-1.5">
										{#if toolSelectionReady && (selectedToolIds ?? []).length > 0}
											<Tooltip
												content={$i18n.t('{{COUNT}} Available Tools', {
													COUNT: selectedToolIds.length
												})}
											>
													<button
														class="translate-y-[0.5px] px-1 flex gap-1 items-center text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg self-center transition"
														aria-label="Available Tools"
														type="button"
														on:click={() => {
															showTools = !showTools;
														}}
													>
														<Wrench className="size-4" strokeWidth="1.75" />

														<span class="text-sm">
															{selectedToolIds.length}
														</span>
													</button>
												</Tooltip>
											{/if}

											{#each selectedFilterIds as filterId}
												{@const filter = toggleFilters.find((f) => f.id === filterId)}
												{#if filter}
													<Tooltip content={filter?.name} placement="top">
														<button
															on:click|preventDefault={() => {
																selectedFilterIds = selectedFilterIds.filter(
																	(id) => id !== filterId
																);
															}}
															type="button"
															class="group p-[7px] flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden {selectedFilterIds.includes(
																filterId
															)
																? 'text-sky-500 dark:text-sky-300 bg-sky-50 hover:bg-sky-100 dark:bg-sky-400/10 dark:hover:bg-sky-600/10 border border-sky-200/40 dark:border-sky-500/20'
																: 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 '} capitalize"
														>
															{#if filter?.icon}
																<div class="size-4 items-center flex justify-center">
																	<img
																		src={filter.icon}
																		class="size-3.5 {filter.icon.includes('svg')
																			? 'dark:invert-[80%]'
																			: ''}"
																		style="fill: currentColor;"
																		alt={filter.name}
																	/>
																</div>
															{:else}
																<Sparkles className="size-4" strokeWidth="1.75" />
															{/if}
															<div class="hidden group-hover:block">
																<XMark className="size-4" strokeWidth="1.75" />
															</div>
														</button>
													</Tooltip>
												{/if}
											{/each}

											{#if showReasoningEffortSelector}
												<!-- Reasoning Effort Selector -->
												<Tooltip content={'Reasoning Effort'} placement="top">
													<div class="relative flex items-center">
														<div
															class="group p-2 flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 border border-transparent hover:border-gray-200 dark:hover:border-gray-700"
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 24 24"
																fill="none"
																stroke="currentColor"
																stroke-width="2"
																stroke-linecap="round"
																stroke-linejoin="round"
																class="size-4"
															>
															<path
																d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
															/>
														</svg>
															<span class="text-xs font-medium">{reasoningEffort}</span>

															<select
																bind:value={reasoningEffort}
																on:change={handleReasoningEffortChange}
																class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
															>
																{#each allowedReasoningEffortsForCurrentModel as effort}
																	<option value={effort}>{effort}</option>
																{/each}
															</select>
														</div>
													</div>
												</Tooltip>
											{/if}

											{#if imageGenerationEnabled}
												<Tooltip content={$i18n.t('Image')} placement="top">
													<button
														on:click|preventDefault={() =>
															(imageGenerationEnabled = !imageGenerationEnabled)}
														type="button"
														class="group p-[7px] flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden {imageGenerationEnabled
															? ' text-sky-500 dark:text-sky-300 bg-sky-50 hover:bg-sky-100 dark:bg-sky-400/10 dark:hover:bg-sky-700/10 border border-sky-200/40 dark:border-sky-500/20'
															: 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 '}"
													>
														<Photo className="size-4" strokeWidth="1.75" />
														<div class="hidden group-hover:block">
															<XMark className="size-4" strokeWidth="1.75" />
														</div>
													</button>
												</Tooltip>
											{/if}

											{#if codeInterpreterEnabled}
												<Tooltip content={$i18n.t('Code Interpreter')} placement="top">
													<button
														aria-label={codeInterpreterEnabled
															? $i18n.t('Disable Code Interpreter')
															: $i18n.t('Enable Code Interpreter')}
														aria-pressed={codeInterpreterEnabled}
														on:click|preventDefault={() =>
															(codeInterpreterEnabled = !codeInterpreterEnabled)}
														type="button"
														class=" group p-[7px] flex gap-1.5 items-center text-sm transition-colors duration-300 max-w-full overflow-hidden {codeInterpreterEnabled
															? ' text-sky-500 dark:text-sky-300 bg-sky-50 hover:bg-sky-100 dark:bg-sky-400/10 dark:hover:bg-sky-700/10 border border-sky-200/40 dark:border-sky-500/20'
															: 'bg-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 '} {($settings?.highContrastMode ??
														false)
															? 'm-1'
															: 'focus:outline-hidden rounded-full'}"
													>
														<Terminal className="size-3.5" strokeWidth="2" />

														<div class="hidden group-hover:block">
															<XMark className="size-4" strokeWidth="1.75" />
														</div>
													</button>
												</Tooltip>
											{/if}
										</div>
									</div>

									<div class="self-end flex space-x-1 mr-1 shrink-0">
										{#if (!history?.currentId || history.messages[history.currentId]?.done == true) && ($_user?.role === 'admin' || ($_user?.permissions?.chat?.stt ?? true))}
											<!-- {$i18n.t('Record voice')} -->
											<Tooltip content={$i18n.t('Dictate')}>
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

										{#if (taskIds && taskIds.length > 0) || (history.currentId && history.messages[history.currentId]?.done != true) || generating}
											<div class=" flex items-center">
												<Tooltip content={$i18n.t('Stop')}>
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
										{:else if prompt === '' && files.length === 0 && ($_user?.role === 'admin' || ($_user?.permissions?.chat?.call ?? true))}
											<div class=" flex items-center">
												<!-- {$i18n.t('Call')} -->
												<Tooltip content={$i18n.t('Voice mode')}>
													<button
														class=" bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full p-1.5 self-center"
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
																let stream = await navigator.mediaDevices.getUserMedia({
																	audio: true
																});
																// If the user grants the permission, proceed to show the call overlay

																if (stream) {
																	const tracks = stream.getTracks();
																	tracks.forEach((track) => track.stop());
																}

																stream = null;

																if ($settings.audio?.tts?.engine === 'browser-kokoro') {
																	// If the user has not initialized the TTS worker, initialize it
																	if (!$TTSWorker) {
																		await TTSWorker.set(
																			new KokoroWorker({
																				dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'
																			})
																		);

																		await $TTSWorker.init();
																	}
																}

																showCallOverlay.set(true);
																showControls.set(true);
															} catch (err) {
																// If the user denies the permission or an error occurs, show an error message
																toast.error(
																	$i18n.t('Permission denied when accessing media devices')
																);
															}
														}}
														aria-label={$i18n.t('Voice mode')}
													>
														<Voice className="size-5" strokeWidth="2.5" />
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
															: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 self-center"
														type="submit"
														disabled={prompt === '' && files.length === 0}
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

							{#if $config?.license_metadata?.input_footer}
								<div class=" text-xs text-gray-500 text-center line-clamp-1 marked">
									{@html DOMPurify.sanitize(marked($config?.license_metadata?.input_footer))}
								</div>
							{:else}
								<div class="mb-1" />
							{/if}
						</form>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
