<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';
	import { equalEditorJSON } from '$lib/utils/editorJson';

	import { goto, onNavigate, replaceState } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(calendar);
	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import {
		resolveDefaultModelIds,
		compressImage,
		copyToClipboard,
		convertHeicToJpeg,
		isHeicImage
	} from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { uploadFile } from '$lib/apis/files';
	import { generateOpenAIChatCompletion } from '$lib/apis/openai';

	import {
		config,
		mobile,
		models,
		settings,
		showSidebar,
		socket,
		user,
		WEBUI_NAME,
		pinnedNotes
	} from '$lib/stores';

	import { contentFiles, downloadNote } from './utils';
	import NoteTabs from './NoteTabs.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import type { NotePage, NotePageOperation } from '$lib/apis/notes';

	import Chat from '$lib/components/chat/Chat.svelte';

	import NotePanel from '$lib/components/notes/NotePanel.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';

	import {
		deleteNoteById,
		createNoteChatById,
		getNoteById,
		getNoteChatById,
		getNoteChatsById,
		updateNoteById,
		updateNotePages,
		updateNoteAccessGrants,
		toggleNotePinnedStatusById,
		getPinnedNoteList
	} from '$lib/apis/notes';
	import { deleteChatById } from '$lib/apis/chats';

	import RichTextInput from '../common/RichTextInput.svelte';
	import { fileUploadsKey } from '../common/RichTextInput/FileAttachment';
	import Spinner from '../common/Spinner.svelte';
	import Mic from '../icons/Mic.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import AccessButton from '../common/AccessButton.svelte';
	import ChatParticipants from '../common/ChatParticipants.svelte';

	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import RecordMenu from './RecordMenu.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ArrowUturnLeft from '../icons/ArrowUturnLeft.svelte';
	import ArrowUturnRight from '../icons/ArrowUturnRight.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';

	export let id: null | string = null;

	let editor = null;
	let revealedSearch = '';
	$: if (editor && note?.id === id && $page.url.searchParams.get('search')) {
		const query = $page.url.searchParams.get('search')!.trim().toLowerCase();
		const key = `${id}:${activePageId}:${query}`;
		if (query && revealedSearch !== key) {
			revealedSearch = key;
			tick().then(() => {
				if (!editor || note?.id !== id) return;
				let found = false;
				editor.state.doc.descendants((node, position) => {
					if (found || !node.isText) return;
					const text = (node.text ?? '').toLowerCase();
					const term = [query, ...query.split(/\s+/)].find((term) => text.includes(term));
					if (term) {
						const from = position + text.indexOf(term);
						editor.commands.setTextSelection({ from, to: from + term.length });
						editor.commands.scrollIntoView();
						found = true;
					}
				});
			});
		}
	}
	let autoFormat = true;
	let note = null;
	let activePageId = '';
	let activePage: NotePage;
	let pageBusy = false;
	let showNoteTabs = false;
	let noteTabsPreferenceReady = false;
	$: if (noteTabsPreferenceReady && $user?.id) {
		localStorage.setItem(`note-tabs-open:${$user.id}`, String(showNoteTabs));
	}
	const pendingFileUploads = new Set<Promise<any>>();
	let previousPage: NotePage | null = null;
	let loadGeneration = 0;
	let pageScroll: Record<string, number> = {};
	$: activePage = note?.data?.pages?.find((p) => p.id === activePageId);
	$: activeDocumentId = activePage
		? `note:${note.id}:page:${activePage.id}:${activePage.generation}`
		: '';
	let presenceNoteId = '';
	let cursorTarget = null;
	let liveParticipants: {
		id: string;
		name: string;
		page_id?: string;
		document_id?: string;
		cursor?: any;
		cursor_position?: number;
	}[] = [];
	const clearPresence = () => (liveParticipants = []);
	$: if (presenceNoteId !== note?.id) {
		presenceNoteId = note?.id;
		clearPresence();
	}
	const presenceEventHandler = (event: { note_id: string; users: typeof liveParticipants }) => {
		if (!$socket?.connected || event.note_id !== note?.id) return;
		liveParticipants = event.users.filter((person) => person.id !== $user?.id);
	};
	const joinNote = () => {
		if (note?.id)
			$socket?.emit('note:join', { note_id: note.id, auth: { token: localStorage.token } });
	};
	const goToParticipant = async (person) => {
		const target = liveParticipants.find((participant) => participant.id === person.id);
		if (!target?.page_id || pageBusy) return;
		await selectPage(target.page_id);
		await tick();
		if (activePageId === target.page_id) cursorTarget = { ...target };
	};
	$: if (
		note?.id === id &&
		$page.url.searchParams.get('page') &&
		$page.url.searchParams.get('page') !== activePageId
	) {
		activatePage($page.url.searchParams.get('page'));
	}

	function activatePage(requested: string) {
		const target = note?.data?.pages?.find((p) => p.id === requested);
		if (!target || target.id === activePageId) return;
		const body = document.getElementById('note-content-container');
		if (body && activePageId) pageScroll[activePageId] = body.scrollTop;
		cursorTarget = null;
		activePageId = target.id;
		selectedContent = null;
		versionIdx = null;
		revealedSearch = '';
		localStorage.setItem(`note-page:${$user?.id}:${id}`, target.id);
		tick().then(() => {
			const container = document.getElementById('note-content-container');
			if (container) container.scrollTop = pageScroll[target.id] ?? 0;
			document
				.getElementById(`note-page-tab-${target.id}`)
				?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
		});
	}

	async function flushActivePage() {
		while (pendingFileUploads.size) await Promise.all([...pendingFileUploads]);
		if (note?.write_access && versionIdx === null && inputElement) await inputElement.flush();
		if (debounceTimeout || titleInputFocused) {
			if (debounceTimeout) clearTimeout(debounceTimeout);
			debounceTimeout = null;
			await saveHandler(true);
		}
	}

	async function selectPage(pageId: string) {
		if (pageBusy || pageId === activePageId) return;
		const url = new URL($page.url);
		url.searchParams.set('page', pageId);
		try {
			pageBusy = true;
			await flushActivePage();
			await goto(url.pathname + url.search, { noScroll: true, keepFocus: true });
		} catch (error) {
			toast.error(String(error));
		} finally {
			pageBusy = false;
		}
	}

	async function pageAction(
		operation: Omit<NotePageOperation, 'revision'>
	): Promise<string | null> {
		if (pageBusy) return null;
		pageBusy = true;
		try {
			if (
				['create', 'duplicate'].includes(operation.action) ||
				(operation.action === 'delete' && operation.page_id === activePageId)
			) {
				await flushActivePage();
			}
			const previous = note.data.pages;
			const activeIndex = previous.findIndex((p) => p.id === activePageId);
			const newId = ['create', 'duplicate'].includes(operation.action) ? uuidv4() : undefined;
			const saved = await updateNotePages(localStorage.token, id, {
				...operation,
				new_id: newId,
				revision: note.data.pages_revision
			});
			mergePages(saved.data.pages, saved.data.pages_revision);
			const target =
				newId ??
				(saved.data.pages.some((p) => p.id === activePageId)
					? activePageId
					: saved.data.pages[Math.min(activeIndex, saved.data.pages.length - 1)].id);
			activatePage(target);
			const url = new URL($page.url);
			url.searchParams.set('page', target);
			// The old page was flushed above; the new editor is still initializing.
			await goto(url.pathname + url.search, {
				replaceState: true,
				noScroll: true,
				keepFocus: true
			});
			return newId ?? target;
		} catch (error) {
			toast.error(String(error));
			const current = await getNoteById(localStorage.token, id).catch(() => null);
			if (current) mergePages(current.data.pages, current.data.pages_revision);
			return null;
		} finally {
			pageBusy = false;
		}
	}

	function mergePages(incoming: NotePage[], revision: number) {
		if (!incoming || revision < (note.data.pages_revision ?? 0)) return;
		const previous = note.data.pages;
		const oldIndex = previous.findIndex((p) => p.id === activePageId);
		const oldPage = previous[oldIndex];
		const nextPage = incoming.find((p) => p.id === activePageId);
		if (
			!pageBusy &&
			note.write_access &&
			oldPage?.content?.md &&
			(!nextPage ||
				(nextPage.generation > oldPage.generation && nextPage.content.md !== oldPage.content.md))
		) {
			previousPage = structuredClone(oldPage);
		}
		note.data.pages = incoming.map((remote) => {
			const local = previous.find((p) => p.id === remote.id);
			if (local && local.generation > remote.generation)
				return {
					...local,
					title: remote.title,
					inherit_note_title: remote.inherit_note_title,
					parent_id: remote.parent_id
				};
			if (local && local.generation === remote.generation) {
				if (local.revision > remote.revision)
					return {
						...local,
						title: remote.title,
						inherit_note_title: remote.inherit_note_title,
						parent_id: remote.parent_id
					};
				if (remote.id === activePageId && note.write_access)
					return { ...remote, content: local.content, versions: local.versions };
			}
			return remote;
		});
		note.data.pages_revision = revision;
		if (!note.data.pages.some((p) => p.id === activePageId)) {
			activatePage(note.data.pages[Math.max(0, Math.min(oldIndex, note.data.pages.length - 1))].id);
			const url = new URL($page.url);
			url.searchParams.set('page', activePageId);
			replaceState(url, $page.state);
		}
	}

	const hasPublicReadGrant = (grants) =>
		Array.isArray(grants) &&
		grants.some(
			(grant) =>
				grant?.principal_type === 'user' &&
				grant?.principal_id === '*' &&
				grant?.permission === 'read'
		);

	let wordCount = 0;
	let charCount = 0;

	$: if (editor) {
		wordCount = editor.storage.characterCount.words();
		charCount = editor.storage.characterCount.characters();
	}

	let versionIdx = null;
	let selectedModelId = null;

	let recording = false;
	let displayMediaRecord = false;

	let showNoteChat = false;
	$: if (showNoteChat) showNoteTabs = false;
	let noteChatId = null;
	let noteChatLoading = false;
	let noteChats = [];
	let noteChatDraftKey = '';
	let noteChatCreating = false;

	let selectedContent = null;
	let noteAttachmentFiles = [];
	let noteChatSuggestedPrompts = [];
	$: noteAttachmentFiles = contentFiles(activePage?.content);
	$: noteChatSuggestedPrompts = [
		$i18n.t('Enhance this note and update it.'),
		$i18n.t('Summarize this note.'),
		$i18n.t('Extract action items from this note.'),
		$i18n.t('Rewrite the selected text.')
	];

	let showDeleteConfirm = false;
	let showAccessControlModal = false;
	let savedAccessGrants = [];

	let ignoreBlur = false;
	let titleInputFocused = false;
	let titleGenerating = false;

	let dragged = false;
	let loading = false;

	let inputElement = null;

	// Computed HTML for editor: fall back to markdown if HTML is missing
	$: editorHtml =
		activePage?.content?.html ||
		(activePage?.content?.md ? marked.parse(activePage.content.md) : '');

	const init = async () => {
		const generation = ++loadGeneration;
		const noteId = id;
		autoFormat = true;
		loading = true;
		const res = await getNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (generation !== loadGeneration || id !== noteId) return;
		if (res) {
			if (note?.id && note.id !== res.id) $socket?.emit('note:leave', { note_id: note.id });
			previousPage = null;
			note = res;
			const requested = $page.url.searchParams.get('page');
			const remembered = localStorage.getItem(`note-page:${$user?.id}:${id}`);
			activePageId = '';
			activatePage(
				note.data.pages.find((p) => p.id === (requested || remembered))?.id ?? note.data.pages[0].id
			);
			if (requested && requested !== activePageId)
				toast.info($i18n.t('This page no longer exists'));
			if (!Array.isArray(note?.access_grants)) {
				note.access_grants = [];
			}

			$socket?.off('events:note', noteEventHandler);
			$socket?.on('events:note', noteEventHandler);
			$socket?.off('note:presence', presenceEventHandler);
			$socket?.on('note:presence', presenceEventHandler);
			$socket?.off('disconnect', clearPresence);
			$socket?.on('disconnect', clearPresence);
			$socket?.off('connect', joinNote);
			$socket?.on('connect', joinNote);
			joinNote();
		} else {
			goto('/');
			return;
		}

		loading = false;
	};

	let debounceTimeout: NodeJS.Timeout | null = null;

	const saveHandler = async (propagateError = false) => {
		if (!note) return;
		const res = await updateNoteById(localStorage.token, id, {
			title: note?.title === '' ? $i18n.t('Untitled') : note.title
		}).catch((e) => {
			toast.error(`${e}`);
			if (propagateError) throw e;
		});

		if (res) {
			pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
		}
	};

	const changeDebounceHandler = () => {
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(() => {
			debounceTimeout = null;
			saveHandler();
		}, 200);
	};

	onNavigate(async () => {
		if (!note || !inputElement || loading || pageBusy) return;
		try {
			await flushActivePage();
		} catch (error) {
			toast.error(String(error));
			throw error;
		}
	});

	$: if (id) {
		init();
	}

	function areContentsEqual(a, b) {
		return equalEditorJSON(a, b);
	}

	function insertNoteVersion(note) {
		const current = {
			json: activePage.content.json,
			html: activePage.content.html,
			md: activePage.content.md
		};
		const lastVersion = activePage.versions?.at(-1);

		if (!lastVersion || !areContentsEqual(lastVersion, current)) {
			activePage.versions = (activePage.versions ?? []).concat(current);
			return true;
		}
		return false;
	}

	const generateTitleHandler = async () => {
		const content = note.data.pages.map((p) => `${p.title}\n${p.content.md}`).join('\n\n');
		const DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = `### Task:
Generate a concise title summarizing the content in the content's primary language.
### Guidelines:
- The title should clearly represent the main theme or subject of the content.
- Keep it short: 2-4 words is best.
- Do not use emojis, quotation marks, or special formatting.
- Write the title in the content's primary language.
- Prioritize accuracy over creativity.
- Your entire response must consist solely of the JSON object, without any introductory or concluding text.
- The output must be a single, raw JSON object, without any markdown code fences or other encapsulating text.
- Ensure no conversational text, affirmations, or explanations precede or follow the raw JSON output, as this will cause direct parsing failure.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "Stock Trends" },
- { "title": "Chocolate Chip Cookies" },
- { "title": "Music Streaming" },
- { "title": "Remote Work" }
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

	function setContentByVersion(versionIdx) {
		if (!activePage.versions?.length) return;
		let idx = versionIdx;

		if (idx === null) idx = activePage.versions.length - 1; // latest
		const v = activePage.versions[idx];

		activePage.content.json = v.json;
		activePage.content.html = v.html;
		activePage.content.md = v.md;

		if (versionIdx === null) {
			const lastVersion = activePage.versions.at(-1);
			const currentContent = activePage.content;

			if (areContentsEqual(lastVersion, currentContent)) {
				// remove the last version
				activePage.versions = activePage.versions.slice(0, -1);
			}
		}
	}

	// Navigation
	function versionNavigateHandler(direction) {
		if (!activePage.versions || activePage.versions.length === 0) return;

		if (versionIdx === null) {
			// Get latest snapshots
			const lastVersion = activePage.versions.at(-1);
			const currentContent = activePage.content;

			if (!areContentsEqual(lastVersion, currentContent)) {
				// If the current content is different from the last version, insert a new version
				insertNoteVersion(note);
				versionIdx = activePage.versions.length - 1;
			} else {
				versionIdx = activePage.versions.length;
			}
		}

		if (direction === 'prev') {
			if (versionIdx > 0) versionIdx -= 1;
		} else if (direction === 'next') {
			if (versionIdx < activePage.versions.length - 1) versionIdx += 1;
			else versionIdx = null; // Reset to latest

			if (versionIdx === activePage.versions.length - 1) {
				// If we reach the latest version, reset to null
				versionIdx = null;
			}
		}

		setContentByVersion(versionIdx);
	}

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

	const inputFileHandler = (
		file,
		uploadEditor = editor,
		pos = uploadEditor?.state.selection.from
	) => {
		if (!uploadEditor || uploadEditor.isDestroyed || !file) return Promise.resolve(null);
		const id = uuidv4();
		// Keep upload UI local so unfinished files never enter saved or shared content.
		uploadEditor.view.dispatch(
			uploadEditor.state.tr.setMeta(fileUploadsKey, { add: { id, pos, file } })
		);
		const pending = (async () => {
			try {
				const item = await processInputFile(file);
				if (!item || uploadEditor.isDestroyed) return null;
				const placeholder = fileUploadsKey
					.getState(uploadEditor.state)
					?.find(undefined, undefined, (spec) => spec.id === id)[0];
				if (!placeholder) return null;
				uploadEditor
					.chain()
					.setMeta(fileUploadsKey, { remove: id })
					.insertContentAt(
						placeholder.from,
						item.type === 'image'
							? { type: 'image', attrs: { src: item.url } }
							: { type: 'fileAttachment', attrs: { id: item.id, name: item.name, size: item.size } }
					)
					.focus()
					.run();
				return item;
			} catch (error) {
				toast.error(String(error));
				return null;
			} finally {
				if (!uploadEditor.isDestroyed) {
					uploadEditor.view.dispatch(uploadEditor.state.tr.setMeta(fileUploadsKey, { remove: id }));
				}
			}
		})();
		pendingFileUploads.add(pending);
		pending.finally(() => pendingFileUploads.delete(pending));
		return pending;
	};

	const processInputFile = async (file) => {
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

		if (file['type'].startsWith('image/') || isHeicImage(file)) {
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
						resolve(fileItem);
					} catch (err) {
						reject(err);
					}
				};

				reader.readAsDataURL(isHeicImage(file) ? await convertHeicToJpeg(file) : file);
			});

			return await uploadImagePromise;
		} else {
			if (!file.size) throw new Error($i18n.t('You cannot upload an empty file.'));
			const metadata =
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
					? { language: $settings.audio.stt.language }
					: null;
			// Save the attachment as soon as it is uploaded; transcription runs on the server.
			const uploaded = await uploadFile(localStorage.token, file, metadata, null, false);
			if (!uploaded?.id) return null;
			if (uploaded.error) toast.warning(uploaded.error);
			return { type: 'file', id: uploaded.id, name: file.name, size: file.size };
		}
	};

	const inputFilesHandler = async (
		inputFiles,
		uploadEditor = editor,
		position = uploadEditor?.state.selection.from
	) => {
		for (const file of inputFiles) {
			await inputFileHandler(file, uploadEditor, position);
			position = uploadEditor?.state.selection.to;
		}
	};

	const uploadNoteFilesHandler = () => {
		const input = document.createElement('input');
		input.type = 'file';
		input.multiple = true;
		const uploadEditor = editor;
		const position = uploadEditor?.state.selection.from;
		input.onchange = () => inputFilesHandler(Array.from(input.files ?? []), uploadEditor, position);
		input.click();
	};

	const openNoteChat = async () => {
		console.info('[note-chat] open requested', {
			noteId: note?.id,
			alreadyLoading: noteChatLoading,
			currentChatId: noteChatId,
			sidebarOpen: showNoteChat
		});
		if (!note?.id || noteChatLoading) return;

		noteChatLoading = true;
		const chat = await getNoteChatById(localStorage.token, note.id).catch((error) => {
			console.error('[note-chat] open failed', { noteId: note?.id, error });
			toast.error(`${error}`);
			return null;
		});
		const chats = chat
			? await getNoteChatsById(localStorage.token, note.id).catch((error) => {
					console.error('[note-chat] history failed', { noteId: note?.id, error });
					return null;
				})
			: null;
		noteChatLoading = false;

		if (chat?.id) {
			console.info('[note-chat] open resolved', {
				noteId: note.id,
				chatId: chat.id,
				title: chat.title,
				hasChatPayload: !!chat.chat
			});
			noteChatId = chat.id;
			noteChats = chats ?? [chat];
			showNoteChat = true;
		} else {
			console.warn('[note-chat] open returned no chat id', { noteId: note.id, chat });
		}
	};

	const createNoteChat = async () => {
		if (!note?.id || noteChatLoading) return;

		noteChatId = null;
		noteChatDraftKey = `${Date.now()}`;
		showNoteChat = true;
	};

	const createNoteChatOnFirstMessage = async () => {
		if (!note?.id || noteChatCreating) return null;

		noteChatCreating = true;
		try {
			const chat = await createNoteChatById(localStorage.token, note.id).catch((error) => {
				console.error('[note-chat] create failed', { noteId: note?.id, error });
				toast.error(`${error}`);
				return null;
			});
			const chats = chat
				? await getNoteChatsById(localStorage.token, note.id).catch((error) => {
						console.error('[note-chat] history failed', { noteId: note?.id, error });
						return null;
					})
				: null;

			if (chat?.id) {
				noteChats = chats ?? [chat, ...noteChats.filter((item) => item.id !== chat.id)];
				showNoteChat = true;
			}

			return chat;
		} finally {
			noteChatCreating = false;
		}
	};

	const deleteNoteChat = async (chatId) => {
		if (!note?.id || !chatId) return;

		const deleted = await deleteChatById(localStorage.token, chatId).catch((error) => {
			console.error('[note-chat] delete failed', { noteId: note?.id, chatId, error });
			toast.error(`${error}`);
			return null;
		});

		if (!deleted) return;

		let chats =
			(await getNoteChatsById(localStorage.token, note.id).catch((error) => {
				console.error('[note-chat] history failed', { noteId: note?.id, error });
				return null;
			})) ?? [];

		if (noteChatId === chatId) {
			let nextChat = chats[0];
			if (!nextChat) {
				nextChat = await getNoteChatById(localStorage.token, note.id).catch((error) => {
					console.error('[note-chat] recreate failed after delete', { noteId: note?.id, error });
					toast.error(`${error}`);
					return null;
				});
				chats = nextChat ? [nextChat] : [];
			}
			noteChatId = nextChat?.id ?? null;
		}

		noteChats = chats;
	};

	const downloadHandler = async (type, pageId: string | null = null) => {
		try {
			await flushActivePage();
			const saved = await getNoteById(localStorage.token, id);
			await downloadNote(saved, type, pageId);
		} catch (error) {
			toast.error(String(error));
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			if (debounceTimeout) clearTimeout(debounceTimeout);
			debounceTimeout = null;
			$socket?.emit('note:leave', { note_id: id });
			note = null;
			pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
			toast.success($i18n.t('Note deleted successfully'));
			goto('/notes');
		} else {
			toast.error($i18n.t('Failed to delete note'));
		}
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
		if (_note.id !== id || !note) return;
		if (_note.page) {
			const remote = _note.page;
			const local = note.data.pages.find((p) => p.id === remote.id);
			if (!local || remote.revision < local.revision || remote.generation < local.generation)
				return;
			if (
				remote.id === activePageId &&
				note.write_access &&
				remote.generation === local.generation
			) {
				local.revision = remote.revision;
			} else {
				note.data.pages = note.data.pages.map((p) => (p.id === remote.id ? remote : p));
				if (remote.id === activePageId && !note.write_access)
					editor?.commands.setContent(
						remote.content.json || remote.content.html || marked.parse(remote.content.md)
					);
			}
			return;
		}
		if (_note.data?.pages) mergePages(_note.data.pages, _note.data.pages_revision);
		if (_note.access_grants) note.access_grants = _note.access_grants;
		if (_note.title && !titleInputFocused && !debounceTimeout) note.title = _note.title;

		if (_note.updated_at) note.updated_at = _note.updated_at;
	};

	onMount(async () => {
		showNoteTabs = localStorage.getItem(`note-tabs-open:${$user?.id}`) === 'true';
		noteTabsPreferenceReady = true;
		await tick();

		selectedModelId =
			resolveDefaultModelIds($models, $settings?.models, $config?.default_models?.split(','))[0] ??
			'';

		const dropzoneElement = document.getElementById('note-editor');

		// dropzoneElement?.addEventListener('dragover', onDragOver);
		// dropzoneElement?.addEventListener('drop', onDrop);
		// dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		loadGeneration++;
		if (note?.id) $socket?.emit('note:leave', { note_id: note.id });
		if (debounceTimeout) clearTimeout(debounceTimeout);
		$socket?.off('events:note', noteEventHandler);
		$socket?.off('note:presence', presenceEventHandler);
		$socket?.off('disconnect', clearPresence);
		$socket?.off('connect', joinNote);

		const dropzoneElement = document.getElementById('note-editor');

		if (dropzoneElement) {
			// dropzoneElement?.removeEventListener('dragover', onDragOver);
			// dropzoneElement?.removeEventListener('drop', onDrop);
			// dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{note?.title
			? `${note?.title.length > 30 ? `${note?.title.slice(0, 30)}...` : note?.title} / ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if note && activePage}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessGrants={note.access_grants}
		accessRoles={['read', 'write']}
		share={$user?.permissions?.sharing?.notes || $user?.role === 'admin'}
		sharePublic={$user?.permissions?.sharing?.public_notes || $user?.role === 'admin'}
		shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
		allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) ||
			$user?.role === 'admin'}
		onChange={async () => {
			if (id) {
				try {
					const saved = await updateNoteAccessGrants(
						localStorage.token,
						id,
						note.access_grants ?? []
					);
					savedAccessGrants = structuredClone(saved.access_grants);
					toast.success($i18n.t('Saved'));
				} catch (error) {
					note.access_grants = structuredClone(savedAccessGrants);
					toast.error(`${error}`);
				}
			}
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
		{$i18n.t('This will delete')} <span class="  font-normal">{note?.title}</span>.
	</div>
</DeleteConfirmDialog>

<div class="w-full h-full flex">
	<div class="h-full flex flex-col min-w-0 flex-1 relative">
		<div class="relative flex-1 w-full h-full flex justify-center pt-2" id="note-editor">
			{#if loading}
				<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
					<div class="m-auto">
						<Spinner className="size-5" />
					</div>
				</div>
			{:else if note && activePage}
				<div class=" w-full flex flex-col {loading ? 'opacity-20' : ''}">
					<div class="shrink-0 w-full flex justify-between items-center px-3">
						<div class="w-full min-w-0 flex items-center">
							{#if $mobile}
								<Tooltip
									content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								>
									<button
										id="sidebar-toggle-button"
										class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
										aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
										type="button"
										on:click={() => {
											showSidebar.set(!$showSidebar);
										}}
									>
										<div class=" self-center p-1.5">
											<Sidebar className="size-4" />
										</div>
									</button>
								</Tooltip>
							{/if}

							<input
								class="w-full text-sm font-normal bg-transparent outline-hidden {$mobile
									? 'ml-1'
									: ''}"
								type="text"
								bind:value={note.title}
								placeholder={titleGenerating ? $i18n.t('Generating...') : $i18n.t('Title')}
								disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
									titleGenerating}
								required
								on:focus={() => {
									titleInputFocused = true;
								}}
								on:blur={(e) => {
									// check if target is generate button
									if (ignoreBlur) {
										ignoreBlur = false;
										return;
									}

									if (
										e.relatedTarget instanceof HTMLElement &&
										e.relatedTarget.id === 'generate-title-button'
									) {
										return;
									}

									titleInputFocused = false;
									changeDebounceHandler();
								}}
							/>

							{#if titleInputFocused && !titleGenerating}
								<div
									class="flex self-center items-center space-x-1.5 z-10 translate-y-[0.5px] -translate-x-[0.5px] pl-2 pr-0.5"
								>
									<Tooltip content={$i18n.t('Generate')}>
										<button
											class="flex size-5 items-center justify-center self-center dark:hover:text-white transition disabled:cursor-not-allowed"
											id="generate-title-button"
											aria-label={$i18n.t('Generate')}
											disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
												titleGenerating}
											on:mouseenter={() => {
												ignoreBlur = true;
											}}
											on:blur={() => {
												titleInputFocused = false;
												changeDebounceHandler();
											}}
											on:click={(e) => {
												e.preventDefault();
												e.stopImmediatePropagation();
												e.stopPropagation();

												generateTitleHandler();
												titleInputFocused = false;
											}}
										>
											<Sparkles strokeWidth="1.5" />
										</button>
									</Tooltip>
								</div>
							{/if}

							<div class="flex items-center gap-0.5 shrink-0">
								{#if note?.write_access}
									{#if editor}
										<div>
											<div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
												<button
													class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
													aria-label={$i18n.t('Undo')}
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
													aria-label={$i18n.t('Redo')}
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
								{/if}

								<Tooltip content={$i18n.t('Chat')} placement="top">
									<button
										type="button"
										class="p-1 bg-transparent hover:bg-white/5 transition rounded-lg"
										aria-label={$i18n.t('Chat')}
										on:click={openNoteChat}
									>
										<ChatBubbleOval className="size-4" strokeWidth="1.8" />
									</button>
								</Tooltip>

								{#if note?.write_access}
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
													await inputFileHandler(files[0]);
												}
											};
										}}
									>
										<Tooltip content={$i18n.t('Record')} placement="top">
											<button
												type="button"
												class="p-1 bg-transparent hover:bg-white/5 transition rounded-lg"
												aria-label={$i18n.t('Record')}
											>
												<Mic className="size-4" />
											</button>
										</Tooltip>
									</RecordMenu>
								{/if}

								<NoteMenu
									bind:autoFormat
									showAutoFormat={note?.write_access ?? false}
									onUploadFiles={note?.write_access ? uploadNoteFilesHandler : null}
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
											activePage.content.md,
											activePage.content.html,
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
									isPinned={$pinnedNotes.some((n) => n.id === note.id)}
									onPin={async () => {
										await toggleNotePinnedStatusById(localStorage.token, note.id);
										note.is_pinned = !note.is_pinned;
										pinnedNotes.set(await getPinnedNoteList(localStorage.token).catch(() => []));
									}}
								>
									<button
										type="button"
										class="p-1 bg-transparent hover:bg-white/5 transition rounded-lg"
										aria-label={$i18n.t('Note Menu')}
									>
										<EllipsisHorizontal className="size-5" />
									</button>
								</NoteMenu>

								{#if liveParticipants.length > 0}
									<div class="ms-1 me-0.5">
										<ChatParticipants
											participants={liveParticipants}
											onSelect={goToParticipant}
											mode="presence"
											avatarClass="size-5"
										/>
									</div>
								{/if}

								{#if note?.write_access}
									{#if $user?.permissions?.sharing?.notes || $user?.role === 'admin'}
										<div class="ml-1.5">
											<AccessButton
												on:click={() => {
													savedAccessGrants = structuredClone(note.access_grants ?? []);
													showAccessControlModal = true;
												}}
												disabled={note?.user_id !== $user?.id && $user?.role !== 'admin'}
											/>
										</div>
									{/if}
								{:else}
									<div class="shrink-0 text-xs text-gray-500 px-2 py-1">
										{$i18n.t('Read-Only Access')}
									</div>
								{/if}
							</div>
						</div>
					</div>

					<div class="  px-1.5">
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
								class="flex gap-0.5 items-center text-xs font-normal text-gray-500 dark:text-gray-500 w-full"
							>
								<div class="min-w-0 max-w-40 pl-2 pr-1">
									<button
										class="flex max-w-full items-center gap-1 bg-transparent text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition"
										aria-label={$i18n.t('Toggle pages')}
										aria-expanded={showNoteTabs}
										aria-controls="note-tabs-panel"
										on:click={() => {
											if (!showNoteTabs) showNoteChat = false;
											showNoteTabs = !showNoteTabs;
										}}
										><span class="truncate"
											>{activePage?.id === 'main' && activePage.inherit_note_title !== false
												? note.title || $i18n.t('Untitled')
												: activePage?.title}</span
										><ChevronDown className="size-3 shrink-0" /></button
									>
								</div>
								<div class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg min-w-fit">
									<!-- check for same date, yesterday, last week, and other -->

									{#if dayjs(note.created_at / 1000000)
										.locale($i18n.language)
										.isSame(dayjs().locale($i18n.language), 'day')}
										<span
											>{dayjs(note.created_at / 1000000)
												.locale($i18n.language)
												.format($i18n.t('[Today at] h:mm A'))}</span
										>
									{:else if dayjs(note.created_at / 1000000)
										.locale($i18n.language)
										.isSame(dayjs().locale($i18n.language).subtract(1, 'day'), 'day')}
										<span
											>{dayjs(note.created_at / 1000000)
												.locale($i18n.language)
												.format($i18n.t('[Yesterday at] h:mm A'))}</span
										>
									{:else if dayjs(note.created_at / 1000000)
										.locale($i18n.language)
										.isSame(dayjs().locale($i18n.language).subtract(1, 'week'), 'week')}
										<span
											>{dayjs(note.created_at / 1000000)
												.locale($i18n.language)
												.format($i18n.t('[Last] dddd [at] h:mm A'))}</span
										>
									{:else}
										<span
											>{dayjs(note.created_at / 1000000)
												.locale($i18n.language)
												.format($i18n.t('DD/MM/YYYY'))}</span
										>
									{/if}
								</div>

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

					{#if previousPage}
						<div
							role="status"
							class="flex items-center gap-3 px-4 py-2 text-sm bg-amber-50 dark:bg-amber-950"
						>
							<span class="flex-1"
								>{$i18n.t(
									'A page changed elsewhere. Your previous text is available to download.'
								)}</span
							>
							<button
								class="underline"
								on:click={() =>
									saveAs(
										new Blob([previousPage.content.md], { type: 'text/markdown' }),
										`${previousPage.title}.md`
									)}>{$i18n.t('Download')}</button
							>
							<button on:click={() => (previousPage = null)}>{$i18n.t('Dismiss')}</button>
						</div>
					{/if}
					<div class="flex min-h-0 flex-1">
						<NotePanel
							bind:show={showNoteTabs}
							side="left"
							panelWidth={280}
							minWidth={240}
							closeOnDragBelowMinWidth={false}
							resizerId="note-tabs-resizer"
							storageKey={`note-tabs-width:${$user?.id}`}
							floating
						>
							<NoteTabs
								onClose={() => (showNoteTabs = false)}
								pages={note.data.pages.map((page) =>
									page.id === 'main' && page.inherit_note_title !== false
										? { ...page, title: note.title || $i18n.t('Untitled') }
										: page
								)}
								activeId={activePageId}
								editable={note.write_access}
								busy={pageBusy}
								onSelect={async (pageId) => {
									await selectPage(pageId);
									if ($mobile) showNoteTabs = false;
								}}
								onAction={pageAction}
								onCopyLink={async (pageId) => {
									await copyToClipboard(
										`${window.location.origin}/notes/${id}?page=${encodeURIComponent(pageId)}`
									);
									toast.success($i18n.t('Copied link to clipboard'));
								}}
								onDownload={(pageId, format) => downloadHandler(format, pageId)}
							/>
						</NotePanel>
						<div
							class="min-w-0 flex-1 h-full overflow-auto px-3 relative flex flex-col"
							id="note-content-container"
							role="tabpanel"
							aria-label={activePage?.id === 'main' && activePage.inherit_note_title !== false
								? note.title || $i18n.t('Untitled')
								: activePage?.title}
						>
							{#each [activePage] as renderedPage (`${note.id}:${renderedPage.id}:${renderedPage.generation}:${autoFormat}`)}
								<RichTextInput
									{autoFormat}
									bind:this={inputElement}
									on:editor={(event) => (editor = event.detail)}
									id={`note-${note.id}-${renderedPage.id}`}
									className="input-prose-sm px-0.5 flex-1 min-h-[12rem]"
									json={true}
									bind:value={renderedPage.content.json}
									html={editorHtml}
									documentId={activeDocumentId}
									bind:cursorTarget
									collaboration={true}
									socket={$socket}
									user={$user}
									dragHandle={true}
									link={true}
									image={true}
									attachments={true}
									placeholder={$i18n.t('Write something...')}
									editable={versionIdx === null && note?.write_access}
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
										renderedPage.content.json = content.json;
										renderedPage.content.html = content.html;
										renderedPage.content.md = content.md;
									}}
									fileHandler={true}
									onFileDrop={(currentEditor, files, pos) =>
										inputFilesHandler(files, currentEditor, pos)}
									onFilePaste={() => {}}
									on:paste={(event) => {
										const e = event.detail.event || event;
										const pasted = Array.from(e.clipboardData?.files ?? []);
										if (pasted.length) {
											e.preventDefault();
											inputFilesHandler(pasted);
										}
									}}
								/>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>
		{#if recording}
			<div class="absolute z-50 bottom-0 right-0 p-3.5 flex select-none">
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
								inputFileHandler(data?.file);
							}

							recording = false;
							displayMediaRecord = false;
						}}
					/>
				</div>
			</div>
		{/if}
	</div>
	<NotePanel bind:show={showNoteChat}>
		{#if noteChatLoading}
			<div class="flex h-full items-center justify-center">
				<Spinner className="size-5" />
			</div>
		{:else if note && (noteChatId || noteChatDraftKey)}
			<Chat
				embedded={true}
				chatIdProp={noteChatId ?? ''}
				embeddedChats={noteChats}
				embeddedDraftKey={noteChatDraftKey}
				suggestedPrompts={noteChatSuggestedPrompts}
				selectedText={selectedContent?.text ?? ''}
				notePageId={activePageId}
				noteFiles={noteAttachmentFiles}
				onBeforeNoteSubmit={flushActivePage}
				onInsertToNote={note?.write_access ? insertHandler : null}
				onNewEmbeddedChat={createNoteChat}
				onCreateEmbeddedChat={createNoteChatOnFirstMessage}
				onSelectEmbeddedChat={(chatId) => {
					if (!chatId || chatId === noteChatId) return;
					noteChatId = chatId;
					noteChatDraftKey = '';
				}}
				onDeleteEmbeddedChat={deleteNoteChat}
				onEmbeddedChatTitle={(chatId, title) => {
					noteChats = noteChats.map((chat) =>
						chat.id === chatId
							? {
									...chat,
									title,
									chat: {
										...(chat.chat ?? {}),
										title
									}
								}
							: chat
					);
				}}
				onCloseEmbedded={() => {
					showNoteChat = false;
				}}
			/>
		{/if}
	</NotePanel>
</div>
