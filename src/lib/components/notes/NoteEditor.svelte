<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import heic2any from 'heic2any';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import jsPDF from 'jspdf';
	import html2canvas from 'html2canvas-pro';

	const i18n = getContext('i18n');

	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(calendar);
	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { compressImage, copyToClipboard, splitStream } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { uploadFile } from '$lib/apis/files';
	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';

	import {
		config,
		mobile,
		models,
		settings,
		showSidebar,
		socket,
		user,
		WEBUI_NAME
	} from '$lib/stores';

	import NotePanel from '$lib/components/notes/NotePanel.svelte';

	import Controls from './NoteEditor/Controls.svelte';
	import Chat from './NoteEditor/Chat.svelte';

	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';

	async function loadLocale(locales) {
		for (const locale of locales) {
			try {
				dayjs.locale(locale);
				break; // Stop after successfully loading the first available locale
			} catch (error) {
				console.error(`Could not load locale '${locale}':`, error);
			}
		}
	}

	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { deleteNoteById, getNoteById, updateNoteById } from '$lib/apis/notes';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Spinner from '../common/Spinner.svelte';
	import MicSolid from '../icons/MicSolid.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';

	import Calendar from '../icons/Calendar.svelte';
	import Users from '../icons/Users.svelte';

	import Image from '../common/Image.svelte';
	import FileItem from '../common/FileItem.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import RecordMenu from './RecordMenu.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import SparklesSolid from '../icons/SparklesSolid.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Bars3BottomLeft from '../icons/Bars3BottomLeft.svelte';
	import ArrowUturnLeft from '../icons/ArrowUturnLeft.svelte';
	import ArrowUturnRight from '../icons/ArrowUturnRight.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import AiMenu from './AIMenu.svelte';
	import AdjustmentsHorizontalOutline from '../icons/AdjustmentsHorizontalOutline.svelte';

	export let id: null | string = null;

	let editor = null;
	let note = null;

	const newNote = {
		title: '',
		data: {
			content: {
				json: null,
				html: '',
				md: ''
			},
			versions: [],
			files: null
		},
		// pages: [], // TODO: Implement pages for notes to allow users to create multiple pages in a note
		meta: null,
		access_control: {}
	};

	let files = [];
	let messages = [];

	let wordCount = 0;
	let charCount = 0;

	let versionIdx = null;
	let selectedModelId = null;

	let recording = false;
	let displayMediaRecord = false;

	let showPanel = false;
	let selectedPanel = 'chat';

	let selectedContent = null;

	let showDeleteConfirm = false;
	let showAccessControlModal = false;

	let ignoreBlur = false;
	let titleInputFocused = false;
	let titleGenerating = false;

	let dragged = false;
	let loading = false;

	let editing = false;
	let streaming = false;

	let stopResponseFlag = false;

	let inputElement = null;

	const init = async () => {
		loading = true;
		const res = await getNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		messages = [];

		if (res) {
			note = res;
			files = res.data.files || [];
		} else {
			goto('/');
			return;
		}

		loading = false;
	};

	let debounceTimeout: NodeJS.Timeout | null = null;

	const changeDebounceHandler = () => {
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			const res = await updateNoteById(localStorage.token, id, {
				title: note?.title === '' ? $i18n.t('Untitled') : note.title,
				data: {
					files: files
				},
				access_control: note?.access_control
			}).catch((e) => {
				toast.error(`${e}`);
			});
		}, 200);
	};

	$: if (id) {
		init();
	}

	function areContentsEqual(a, b) {
		return JSON.stringify(a) === JSON.stringify(b);
	}

	function insertNoteVersion(note) {
		const current = {
			json: note.data.content.json,
			html: note.data.content.html,
			md: note.data.content.md
		};
		const lastVersion = note.data.versions?.at(-1);

		if (!lastVersion || !areContentsEqual(lastVersion, current)) {
			note.data.versions = (note.data.versions ?? []).concat(current);
			return true;
		}
		return false;
	}

	const onEdited = async () => {
		if (!editor) return;
		editor.commands.setContent(note.data.content.html);
	};

	const generateTitleHandler = async () => {
		const content = note.data.content.md;
		const DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = `### Task:
Generate a concise, 3-5 word title with an emoji summarizing the content in the content's primary language.
### Guidelines:
- The title should clearly represent the main theme or subject of the content.
- Use emojis that enhance understanding of the topic, but avoid quotation marks or special formatting.
- Write the title in the content's primary language.
- Prioritize accuracy over excessive creativity; keep it clear and simple.
- Your entire response must consist solely of the JSON object, without any introductory or concluding text.
- The output must be a single, raw JSON object, without any markdown code fences or other encapsulating text.
- Ensure no conversational text, affirmations, or explanations precede or follow the raw JSON output, as this will cause direct parsing failure.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "📉 Stock Market Trends" },
- { "title": "🍪 Perfect Chocolate Chip Recipe" },
- { "title": "Evolution of Music Streaming" },
- { "title": "Remote Work Productivity Tips" },
- { "title": "Artificial Intelligence in Healthcare" },
- { "title": "🎮 Video Game Development Insights" }
### Content:
<content>
${content}
</content>`;

		const oldTitle = JSON.parse(JSON.stringify(note.title));
		note.title = '';
		titleGenerating = true;

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				model: selectedModelId,
				stream: false,
				messages: [
					{
						role: 'user',
						content: DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);
		if (res) {
			// Step 1: Safely extract the response string
			const response = res?.choices[0]?.message?.content ?? '';

			try {
				const jsonStartIndex = response.indexOf('{');
				const jsonEndIndex = response.lastIndexOf('}');

				if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
					const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);
					const parsed = JSON.parse(jsonResponse);

					if (parsed && parsed.title) {
						note.title = parsed.title.trim();
					}
				}
			} catch (e) {
				console.error('Error parsing JSON response:', e);
				toast.error($i18n.t('Failed to generate title'));
			}
		}

		if (!note.title) {
			note.title = oldTitle;
		}

		titleGenerating = false;
		await tick();
		changeDebounceHandler();
	};

	async function enhanceNoteHandler() {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models
			.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
			.find((model) => model.id === selectedModelId);

		if (!model) {
			selectedModelId = '';
			return;
		}

		editing = true;
		await enhanceCompletionHandler(model);
		editing = false;

		onEdited();
		versionIdx = null;
	}

	const stopResponseHandler = async () => {
		stopResponseFlag = true;
		console.log('stopResponse', stopResponseFlag);
	};

	function setContentByVersion(versionIdx) {
		if (!note.data.versions?.length) return;
		let idx = versionIdx;

		if (idx === null) idx = note.data.versions.length - 1; // latest
		const v = note.data.versions[idx];

		note.data.content.json = v.json;
		note.data.content.html = v.html;
		note.data.content.md = v.md;

		if (versionIdx === null) {
			const lastVersion = note.data.versions.at(-1);
			const currentContent = note.data.content;

			if (areContentsEqual(lastVersion, currentContent)) {
				// remove the last version
				note.data.versions = note.data.versions.slice(0, -1);
			}
		}
	}

	// Navigation
	function versionNavigateHandler(direction) {
		if (!note.data.versions || note.data.versions.length === 0) return;

		if (versionIdx === null) {
			// Get latest snapshots
			const lastVersion = note.data.versions.at(-1);
			const currentContent = note.data.content;

			if (!areContentsEqual(lastVersion, currentContent)) {
				// If the current content is different from the last version, insert a new version
				insertNoteVersion(note);
				versionIdx = note.data.versions.length - 1;
			} else {
				versionIdx = note.data.versions.length;
			}
		}

		if (direction === 'prev') {
			if (versionIdx > 0) versionIdx -= 1;
		} else if (direction === 'next') {
			if (versionIdx < note.data.versions.length - 1) versionIdx += 1;
			else versionIdx = null; // Reset to latest

			if (versionIdx === note.data.versions.length - 1) {
				// If we reach the latest version, reset to null
				versionIdx = null;
			}
		}

		setContentByVersion(versionIdx);
	}

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

		// open the settings panel if it is not open
		selectedPanel = 'settings';

		if (!showPanel) {
			showPanel = true;
		}

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

			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

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

		if (files.length > 0) {
			note.data.files = files;
		} else {
			note.data.files = null;
		}

		editor.storage.files = files;

		changeDebounceHandler();

		return fileItem;
	};

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

	const inputFileHandler = async (file) => {
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

		if (file['type'].startsWith('image/')) {
			const uploadImagePromise = new Promise(async (resolve, reject) => {
				let reader = new FileReader();
				reader.onload = async (event) => {
					try {
						let imageUrl = event.target.result;
						imageUrl = await compressImageHandler(imageUrl, $settings, $config);

						const fileId = uuidv4();
						const fileItem = {
							id: fileId,
							type: 'image',
							url: `${imageUrl}`
						};
						files = [...files, fileItem];
						note.data.files = files;
						editor.storage.files = files;

						changeDebounceHandler();
						resolve(fileItem);
					} catch (err) {
						reject(err);
					}
				};

				reader.readAsDataURL(
					file['type'] === 'image/heic'
						? await heic2any({ blob: file, toType: 'image/jpeg' })
						: file
				);
			});

			return await uploadImagePromise;
		} else {
			return await uploadFileHandler(file);
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);
		inputFiles.forEach(async (file) => {
			await inputFileHandler(file);
		});
	};

	const downloadHandler = async (type) => {
		console.log('downloadHandler', type);
		if (type === 'txt') {
			const blob = new Blob([note.data.content.md], { type: 'text/plain' });
			saveAs(blob, `${note.title}.txt`);
		} else if (type === 'md') {
			const blob = new Blob([note.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${note.title}.md`);
		} else if (type === 'pdf') {
			await downloadPdf(note);
		}
	};

	const downloadPdf = async (note) => {
		try {
			// Define a fixed virtual screen size
			const virtualWidth = 1024; // Fixed width (adjust as needed)
			const virtualHeight = 1400; // Fixed height (adjust as needed)

			// STEP 1. Get a DOM node to render
			const html = note.data?.content?.html ?? '';
			let node;
			if (html instanceof HTMLElement) {
				node = html;
			} else {
				// If it's HTML string, render to a temporary hidden element
				node = document.createElement('div');
				node.innerHTML = html;
				document.body.appendChild(node);
			}

			// Render to canvas with predefined width
			const canvas = await html2canvas(node, {
				useCORS: true,
				scale: 2, // Keep at 1x to avoid unexpected enlargements
				width: virtualWidth, // Set fixed virtual screen width
				windowWidth: virtualWidth, // Ensure consistent rendering
				windowHeight: virtualHeight
			});

			// Remove hidden node if needed
			if (!(html instanceof HTMLElement)) {
				document.body.removeChild(node);
			}

			const imgData = canvas.toDataURL('image/jpeg', 0.7);

			// A4 page settings
			const pdf = new jsPDF('p', 'mm', 'a4');
			const imgWidth = 210; // A4 width in mm
			const pageHeight = 297; // A4 height in mm

			// Maintain aspect ratio
			const imgHeight = (canvas.height * imgWidth) / canvas.width;
			let heightLeft = imgHeight;
			let position = 0;

			pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
			heightLeft -= pageHeight;

			// Handle additional pages
			while (heightLeft > 0) {
				position -= pageHeight;
				pdf.addPage();

				pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
				heightLeft -= pageHeight;
			}

			pdf.save(`${note.title}.pdf`);
		} catch (error) {
			console.error('Error generating PDF', error);

			toast.error(`${error}`);
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Note deleted successfully'));
			goto('/notes');
		} else {
			toast.error($i18n.t('Failed to delete note'));
		}
	};

	const scrollToBottom = () => {
		const element = document.getElementById('note-content-container');

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const enhanceCompletionHandler = async (model) => {
		stopResponseFlag = false;
		let enhancedContent = {
			json: null,
			html: '',
			md: ''
		};

		const systemPrompt = `Enhance existing notes using additional context provided from audio transcription or uploaded file content in the content's primary language. Your task is to make the notes more useful and comprehensive by incorporating relevant information from the provided context.

Input will be provided within <notes> and <context> XML tags, providing a structure for the existing notes and context respectively.

# Output Format

Provide the enhanced notes in markdown format. Use markdown syntax for headings, lists, task lists ([ ]) where tasks or checklists are strongly implied, and emphasis to improve clarity and presentation. Ensure that all integrated content from the context is accurately reflected. Return only the markdown formatted note.
`;

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{
						role: 'system',
						content: systemPrompt
					},
					{
						role: 'user',
						content:
							`<notes>${note.data.content.md}</notes>` +
							(files && files.length > 0
								? `\n<context>${files.map((file) => `${file.name}: ${file?.file?.data?.content ?? 'Could not extract content'}\n`).join('')}</context>`
								: '')
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);

		await tick();

		streaming = true;

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}

					editing = false;
					streaming = false;
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								console.log(line);
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (data.choices && data.choices.length > 0) {
									const choice = data.choices[0];
									if (choice.delta && choice.delta.content) {
										enhancedContent.md += choice.delta.content;
										enhancedContent.html = marked.parse(enhancedContent.md);

										note.data.content.md = enhancedContent.md;
										note.data.content.html = enhancedContent.html;
										note.data.content.json = null;

										scrollToBottom();
									}
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}

		streaming = false;
	};

	const onDragOver = (e) => {
		e.preventDefault();

		if (
			e.dataTransfer?.types?.includes('text/plain') ||
			e.dataTransfer?.types?.includes('text/html')
		) {
			dragged = false;
			return;
		}

		// Check if the dragged item is a file or image
		if (e.dataTransfer?.types?.includes('Files') && e.dataTransfer?.items) {
			const items = Array.from(e.dataTransfer.items);
			const hasFiles = items.some((item) => item.kind === 'file');
			const hasImages = items.some((item) => item.type.startsWith('image/'));

			if (hasFiles && !hasImages) {
				dragged = true;
			} else {
				dragged = false;
			}
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

	const insertHandler = (content) => {
		insertNoteVersion(note);
		inputElement?.insertContent(content);
	};

	const noteEventHandler = async (_note) => {
		console.log('noteEventHandler', _note);
		if (_note.id !== id) return;

		if (_note.access_control && _note.access_control !== note.access_control) {
			note.access_control = _note.access_control;
		}

		if (_note.data && _note.data.files) {
			files = _note.data.files;
			note.data.files = files;
		}

		if (_note.title && _note.title) {
			note.title = _note.title;
		}

		editor.storage.files = files;
		await tick();

		for (const file of files) {
			if (file.type === 'image') {
				const e = new CustomEvent('data', { files: files });

				const img = document.getElementById(`image:${file.id}`);
				if (img) {
					img.dispatchEvent(e);
				}
			}
		}
	};

	onMount(async () => {
		await tick();
		$socket?.emit('join-note', {
			note_id: id,
			auth: {
				token: localStorage.token
			}
		});
		$socket?.on('note-events', noteEventHandler);

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}

		if (selectedModelId) {
			const model = $models
				.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
				.find((model) => model.id === selectedModelId);

			if (!model) {
				selectedModelId = '';
			}
		}

		if (!selectedModelId) {
			selectedModelId = $models.at(0)?.id || '';
		}

		const dropzoneElement = document.getElementById('note-editor');

		// dropzoneElement?.addEventListener('dragover', onDragOver);
		// dropzoneElement?.addEventListener('drop', onDrop);
		// dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		console.log('destroy');
		$socket?.off('note-events', noteEventHandler);

		const dropzoneElement = document.getElementById('note-editor');

		if (dropzoneElement) {
			// dropzoneElement?.removeEventListener('dragover', onDragOver);
			// dropzoneElement?.removeEventListener('drop', onDrop);
			// dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<svelte:head>
	<title>
		{note?.title
			? `${note?.title.length > 30 ? `${note?.title.slice(0, 30)}...` : note?.title} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if note}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessControl={note.access_control}
		accessRoles={['read', 'write']}
		onChange={() => {
			changeDebounceHandler();
		}}
	/>
{/if}

<FilesOverlay show={dragged} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete note?')}
	on:confirm={() => {
		deleteNoteHandler(note.id);
		showDeleteConfirm = false;
	}}
>
	<div class=" text-sm text-gray-500">
		{$i18n.t('This will delete')} <span class="  font-semibold">{note.title}</span>.
	</div>
</DeleteConfirmDialog>

<PaneGroup direction="horizontal" class="w-full h-full">
	<Pane defaultSize={70} minSize={30} class="h-full flex flex-col w-full relative">
		<div class="relative flex-1 w-full h-full flex justify-center pt-[11px]" id="note-editor">
			{#if loading}
				<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
					<div class="m-auto">
						<Spinner className="size-5" />
					</div>
				</div>
			{:else}
				<div class=" w-full flex flex-col {loading ? 'opacity-20' : ''}">
					<div class="shrink-0 w-full flex justify-between items-center px-3.5 mb-1.5">
						<div class="w-full flex items-center">
							{#if $mobile}
								<div
									class="{$showSidebar
										? 'md:hidden pl-0.5'
										: ''} flex flex-none items-center pr-1 -translate-x-1"
								>
									<Tooltip
										content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
									>
										<button
											id="sidebar-toggle-button"
											class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
											on:click={() => {
												showSidebar.set(!$showSidebar);
											}}
										>
											<div class=" self-center p-1.5">
												<Sidebar />
											</div>
										</button>
									</Tooltip>
								</div>
							{/if}

							<input
								class="w-full text-2xl font-medium bg-transparent outline-hidden"
								type="text"
								bind:value={note.title}
								placeholder={titleGenerating ? $i18n.t('Generating...') : $i18n.t('Title')}
								disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
									titleGenerating}
								required
								on:input={changeDebounceHandler}
								on:focus={() => {
									titleInputFocused = true;
								}}
								on:blur={(e) => {
									// check if target is generate button
									if (ignoreBlur) {
										ignoreBlur = false;
										return;
									}

									titleInputFocused = false;
									changeDebounceHandler();
								}}
							/>

							{#if titleInputFocused && !titleGenerating}
								<div
									class="flex self-center items-center space-x-1.5 z-10 translate-y-[0.5px] -translate-x-[0.5px] pl-2"
								>
									<Tooltip content={$i18n.t('Generate')}>
										<button
											class=" self-center dark:hover:text-white transition"
											id="generate-title-button"
											disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
												titleGenerating}
											on:mouseenter={() => {
												ignoreBlur = true;
											}}
											on:click={(e) => {
												e.preventDefault();
												e.stopImmediatePropagation();
												e.stopPropagation();

												generateTitleHandler();
												titleInputFocused = false;
											}}
										>
											<Sparkles strokeWidth="2" />
										</button>
									</Tooltip>
								</div>
							{/if}

							<div class="flex items-center gap-0.5 translate-x-1">
								{#if editor}
									<div>
										<div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
											<button
												class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
												on:click={() => {
													editor.chain().focus().undo().run();
													// versionNavigateHandler('prev');
												}}
												disabled={!editor.can().undo()}
											>
												<ArrowUturnLeft className="size-4" />
											</button>

											<button
												class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
												on:click={() => {
													editor.chain().focus().redo().run();
													// versionNavigateHandler('next');
												}}
												disabled={!editor.can().redo()}
											>
												<ArrowUturnRight className="size-4" />
											</button>
										</div>
									</div>
								{/if}

								<Tooltip placement="top" content={$i18n.t('Chat')} className="cursor-pointer">
									<button
										class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
										on:click={() => {
											if (showPanel && selectedPanel === 'chat') {
												showPanel = false;
											} else {
												if (!showPanel) {
													showPanel = true;
												}
												selectedPanel = 'chat';
											}
										}}
									>
										<ChatBubbleOval />
									</button>
								</Tooltip>

								<Tooltip placement="top" content={$i18n.t('Controls')} className="cursor-pointer">
									<button
										class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
										on:click={() => {
											if (showPanel && selectedPanel === 'settings') {
												showPanel = false;
											} else {
												if (!showPanel) {
													showPanel = true;
												}
												selectedPanel = 'settings';
											}
										}}
									>
										<AdjustmentsHorizontalOutline />
									</button>
								</Tooltip>

								<NoteMenu
									onDownload={(type) => {
										downloadHandler(type);
									}}
									onCopyLink={async () => {
										const baseUrl = window.location.origin;
										const res = await copyToClipboard(`${baseUrl}/notes/${note.id}`);

										if (res) {
											toast.success($i18n.t('Copied link to clipboard'));
										} else {
											toast.error($i18n.t('Failed to copy link'));
										}
									}}
									onCopyToClipboard={async () => {
										const res = await copyToClipboard(
											note.data.content.md,
											note.data.content.html,
											true
										).catch((error) => {
											toast.error(`${error}`);
											return null;
										});

										if (res) {
											toast.success($i18n.t('Copied to clipboard'));
										}
									}}
									onDelete={() => {
										showDeleteConfirm = true;
									}}
								>
									<div class="p-1 bg-transparent hover:bg-white/5 transition rounded-lg">
										<EllipsisHorizontal className="size-5" />
									</div>
								</NoteMenu>
							</div>
						</div>
					</div>

					<div class="  px-2.5">
						<div
							class=" flex w-full bg-transparent overflow-x-auto scrollbar-none"
							on:wheel={(e) => {
								if (e.deltaY !== 0) {
									e.preventDefault();
									e.currentTarget.scrollLeft += e.deltaY;
								}
							}}
						>
							<div
								class="flex gap-1 items-center text-xs font-medium text-gray-500 dark:text-gray-500 w-fit"
							>
								<button class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg min-w-fit">
									<Calendar className="size-3.5" strokeWidth="2" />

									<!-- check for same date, yesterday, last week, and other -->

									{#if dayjs(note.created_at / 1000000).isSame(dayjs(), 'day')}
										<span
											>{dayjs(note.created_at / 1000000).format($i18n.t('[Today at] h:mm A'))}</span
										>
									{:else if dayjs(note.created_at / 1000000).isSame(dayjs().subtract(1, 'day'), 'day')}
										<span
											>{dayjs(note.created_at / 1000000).format(
												$i18n.t('[Yesterday at] h:mm A')
											)}</span
										>
									{:else if dayjs(note.created_at / 1000000).isSame(dayjs().subtract(1, 'week'), 'week')}
										<span
											>{dayjs(note.created_at / 1000000).format(
												$i18n.t('[Last] dddd [at] h:mm A')
											)}</span
										>
									{:else}
										<span>{dayjs(note.created_at / 1000000).format($i18n.t('DD/MM/YYYY'))}</span>
									{/if}
								</button>

								<button
									class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg min-w-fit"
									on:click={() => {
										showAccessControlModal = true;
									}}
									disabled={note?.user_id !== $user?.id && $user?.role !== 'admin'}
								>
									<Users className="size-3.5" strokeWidth="2" />

									<span> {note?.access_control ? $i18n.t('Private') : $i18n.t('Everyone')} </span>
								</button>

								{#if editor}
									<div class="flex items-center gap-1 px-1 min-w-fit">
										<div>
											{$i18n.t('{{COUNT}} words', {
												COUNT: wordCount
											})}
										</div>
										<div>
											{$i18n.t('{{COUNT}} characters', {
												COUNT: charCount
											})}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>

					<div
						class=" flex-1 w-full h-full overflow-auto px-3.5 pb-20 relative pt-2.5"
						id="note-content-container"
					>
						{#if editing}
							<div
								class="w-full h-full fixed top-0 left-0 {streaming
									? ''
									: ' backdrop-blur-xs  bg-white/10 dark:bg-gray-900/10'} flex items-center justify-center z-10 cursor-not-allowed"
							></div>
						{/if}

						<RichTextInput
							bind:this={inputElement}
							bind:editor
							id={`note-${note.id}`}
							className="input-prose-sm px-0.5"
							json={true}
							bind:value={note.data.content.json}
							html={note.data?.content?.html}
							documentId={`note:${note.id}`}
							collaboration={true}
							socket={$socket}
							user={$user}
							link={true}
							image={true}
							{files}
							placeholder={$i18n.t('Write something...')}
							editable={versionIdx === null && !editing}
							onSelectionUpdate={({ editor }) => {
								const { from, to } = editor.state.selection;
								const selectedText = editor.state.doc.textBetween(from, to, ' ');

								if (selectedText.length === 0) {
									selectedContent = null;
								} else {
									selectedContent = {
										text: selectedText,
										from: from,
										to: to
									};
								}
							}}
							onChange={(content) => {
								note.data.content.html = content.html;
								note.data.content.md = content.md;

								if (editor) {
									wordCount = editor.storage.characterCount.words();
									charCount = editor.storage.characterCount.characters();
								}
							}}
							fileHandler={true}
							onFileDrop={(currentEditor, files, pos) => {
								files.forEach(async (file) => {
									const fileItem = await inputFileHandler(file).catch((error) => {
										return null;
									});

									if (fileItem.type === 'image') {
										// If the file is an image, insert it directly
										currentEditor
											.chain()
											.insertContentAt(pos, {
												type: 'image',
												attrs: {
													src: `data://${fileItem.id}`
												}
											})
											.focus()
											.run();
									}
								});
							}}
							onFilePaste={() => {}}
							on:paste={async (e) => {
								e = e.detail.event || e;
								const clipboardData = e.clipboardData || window.clipboardData;
								console.log('Clipboard data:', clipboardData);

								if (clipboardData && clipboardData.items) {
									console.log('Clipboard data items:', clipboardData.items);
									for (const item of clipboardData.items) {
										console.log('Clipboard item:', item);
										if (item.type.indexOf('image') !== -1) {
											const blob = item.getAsFile();
											const fileItem = await inputFileHandler(blob);

											if (editor) {
												editor
													?.chain()
													.insertContentAt(editor.state.selection.$anchor.pos, {
														type: 'image',
														attrs: {
															src: `data://${fileItem.id}` // Use data URI for the image
														}
													})
													.focus()
													.run();
											}
										} else if (item?.kind === 'file') {
											const file = item.getAsFile();
											await inputFileHandler(file);
											e.preventDefault();
										}
									}
								}
							}}
						/>
					</div>
				</div>
			{/if}
		</div>
		<div class="absolute z-20 bottom-0 right-0 p-3.5 max-w-full w-full flex">
			<div class="flex gap-1 w-full min-w-full justify-between">
				{#if recording}
					<div class="flex-1 w-full">
						<VoiceRecording
							bind:recording
							className="p-1 w-full max-w-full"
							transcribe={false}
							displayMedia={displayMediaRecord}
							echoCancellation={false}
							noiseSuppression={false}
							onCancel={() => {
								recording = false;
								displayMediaRecord = false;
							}}
							onConfirm={(data) => {
								if (data?.file) {
									uploadFileHandler(data?.file);
								}

								recording = false;
								displayMediaRecord = false;
							}}
						/>
					</div>
				{:else}
					<RecordMenu
						onRecord={async () => {
							displayMediaRecord = false;

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
						onCaptureAudio={async () => {
							displayMediaRecord = true;

							recording = true;
						}}
						onUpload={async () => {
							const input = document.createElement('input');
							input.type = 'file';
							input.accept = 'audio/*';
							input.multiple = false;
							input.click();

							input.onchange = async (e) => {
								const files = e.target.files;

								if (files && files.length > 0) {
									await uploadFileHandler(files[0]);
								}
							};
						}}
					>
						<Tooltip content={$i18n.t('Record')} placement="top">
							<div
								class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
							>
								<MicSolid className="size-4.5" />
							</div>
						</Tooltip>
					</RecordMenu>

					<div
						class="cursor-pointer flex gap-0.5 rounded-full border border-gray-50 dark:border-gray-850 dark:bg-gray-850 transition shadow-xl"
					>
						<Tooltip content={$i18n.t('AI')} placement="top">
							{#if editing}
								<button
									class="p-2 flex justify-center items-center hover:bg-gray-50 dark:hover:bg-gray-800 rounded-full transition shrink-0"
									on:click={() => {
										stopResponseHandler();
									}}
									type="button"
								>
									<Spinner className="size-5" />
								</button>
							{:else}
								<AiMenu
									onEdit={() => {
										enhanceNoteHandler();
									}}
									onChat={() => {
										showPanel = true;
										selectedPanel = 'chat';
									}}
								>
									<div
										class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
									>
										<SparklesSolid />
									</div>
								</AiMenu>
							{/if}
						</Tooltip>
					</div>
				{/if}
			</div>
		</div>
	</Pane>
	<NotePanel bind:show={showPanel}>
		{#if selectedPanel === 'chat'}
			<Chat
				bind:show={showPanel}
				bind:selectedModelId
				bind:messages
				bind:note
				bind:editing
				bind:streaming
				bind:stopResponseFlag
				{editor}
				{inputElement}
				{selectedContent}
				{files}
				onInsert={insertHandler}
				onStop={stopResponseHandler}
				{onEdited}
				insertNoteHandler={() => {
					insertNoteVersion(note);
				}}
				scrollToBottomHandler={scrollToBottom}
			/>
		{:else if selectedPanel === 'settings'}
			<Controls
				bind:show={showPanel}
				bind:selectedModelId
				bind:files
				onUpdate={() => {
					changeDebounceHandler();
				}}
			/>
		{/if}
	</NotePanel>
</PaneGroup>
