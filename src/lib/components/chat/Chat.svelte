<script lang="ts">
	import { getMachines } from '$lib/apis/machines';
	import { resolveToolApprovalMode } from '$lib/utils/toolPermissions';
	import type { AppLayoutContext, MachineContext } from '$lib/types';
	import { setChatContext } from './context';
	import {
		estimateTokens,
		estimateMessagesTokens,
		estimateUsageGrowth,
		captureUsageCheckpoint
	} from '$lib/utils/contextUsage';
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { fade } from 'svelte/transition';
	const i18n: Writable<i18nType> = getContext('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	import { goto, beforeNavigate, afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';

	import { get, writable, type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getModels } from '$lib/apis';
	import equal from 'fast-deep-equal';

	import {
		chatId as _chatId,
		config,
		type Model,
		models as _models,
		tags as allTags,
		settings,
		showSidebar,
		WEBUI_NAME,
		banners,
		user,
		socket,
		audioQueue as _audioQueue,
		showTabs as _showTabs,
		chatTabRequest,
		openEmbeddedChatIds,
		voiceCall as _voiceCall,
		temporaryChat as _temporaryChat,
		mobile,
		chatTitle as _chatTitle,
		tools,
		skills,
		machineSkills as _machineSkills,
		machines,
		functions,
		selectedFolder as _selectedFolder,
		folders as _folders,
		showEmbeds as _showEmbeds,
		selectedMachineId as _selectedMachineId,
		showFileNavPath,
		showFileNavDir,
		chatRequestQueues,
		desktopEvent
	} from '$lib/stores';
	import { refreshChatList, refreshFolderChatLists, setChatTitle } from '$lib/stores/chatList';
	import { updateFolderById } from '$lib/apis/folders';
	import {
		getFolderAgentModels,
		loadFolderAgentModels,
		setFolderModelConnections,
		isCancelledFolderRequest,
		updateFolderChatLists,
		updateFolderDetails,
		type FolderDetails
	} from '$lib/stores/folderStates';
	import { closeChatTabs } from '$lib/stores/chatViewStates';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import {
		resolveDefaultModelIds,
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		createMessagesList,
		getDeepestChildId,
		sanitizeHistory,
		getPromptVariables,
		processDetails,
		removeAllDetails,
		getCodeBlockContents,
		displayFileHandler,
		getUsageTokenCount,
		isRasterImageContentType
	} from '$lib/utils';
	import { AudioQueue } from '$lib/utils/audio';
	import { RealtimeCall, getBridgeTurnState, type BridgeSubmission } from '$lib/utils/realtime';
	import { acquireWakeLock } from '$lib/utils/wakeLock';
	import { routeAvatarAnimation } from '$lib/utils/voice-avatar';
	import { createTemporaryChatId, isSavedChatId, isTemporaryChatId } from '$lib/utils/chatId';
	import { canUseTemporaryChats } from '$lib/utils/settings-access';
	import { resolveLocalizedModelPromptSuggestions } from '$lib/utils/localizedContent';
	import { resumeTemporaryChat } from '$lib/apis';
	import {
		applyResponseStreamEvent,
		getOutputText,
		getPendingAskUserFromMessage,
		setOutputText
	} from './Messages/structuredOutput';

	import {
		addTagById,
		archiveChatById,
		compactChatById,
		createNewChat,
		deleteChatById,
		deleteChatMessageById,
		forkChatById,
		getAllTags,
		getChatById,
		getTagsById,
		importChats,
		resolveChatMessageToolCall,
		updateChatById,
		updateChatParams,
		updateChatFolderIdById
	} from '$lib/apis/chats';
	import {
		listMachineSkills,
		resolveMachineTarget,
		setCwd,
		type FilesystemFile
	} from '$lib/apis/machines';
	import { generateOpenAIChatCompletion, getErrorMessage } from '$lib/apis/openai';
	import { processUrl, processWebSearch } from '$lib/apis/retrieval';
	import {
		getAndUpdateUserLocation,
		getUserInfoById,
		getUserSettings,
		updateUserSettings
	} from '$lib/apis/users';
	import {
		generateTitle,
		generateTags,
		generateQueries,
		chatAction,
		generateMoACompletion,
		stopTask,
		stopTasksByChatId,
		getTaskIdsByChatId
	} from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';
	import { uploadFile } from '$lib/apis/files';
	import { createOpenAITextStream } from '$lib/apis/streaming';
	import { getFunctions } from '$lib/apis/functions';
	import { initiateOAuthRedirect } from '$lib/apis/configs';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import Sparkles from '$lib/components/layout/Sidebar/icons/Sparkles.svelte';
	import Tabs from './Tabs.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import ElicitationDialog from './ElicitationDialog.svelte';
	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import WebSearchConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import Suggestions from './Suggestions.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
	import NotificationToast from '../NotificationToast.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Modal from '../common/Modal.svelte';
	import { isEmbedWindow } from '../common/FullHeightIframe.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import Image from '../common/Image.svelte';
	import XMark from '../icons/XMark.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import EmbeddedChatHistoryDropdown from './EmbeddedChatHistoryDropdown.svelte';
	import ChatMenu from '$lib/components/layout/Navbar/Menu.svelte';
	import ShareChatModal from './ShareChatModal.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import InputVariablesModal from './MessageInput/InputVariablesModal.svelte';
	import {
		isMachine,
		isMachineRef,
		machineEventName,
		machineIdOf,
		metaMachineIdOf
	} from '$lib/utils/machines';

	export let chatIdProp = '';
	export let initialPage = '';
	let mainChatHref = '/';
	// Unsaved chats have no /c/ page, so they keep the new-chat address set by initNewChat.
	$: if (isSavedChatId($chatId)) mainChatHref = `/c/${$chatId}`;
	export let embedded = false;
	export let tabbed = false;
	const chatId = embedded ? writable('') : _chatId;
	const chatTitle = embedded ? writable('') : _chatTitle;
	const audioQueue = embedded ? writable<AudioQueue | null>(null) : _audioQueue;
	const temporaryChat = embedded ? writable(false) : _temporaryChat;
	export const isTemporary = () => get(temporaryChat);
	const isTemporaryEnforced = () =>
		$user?.role !== 'admin' &&
		!!$user?.permissions?.chat?.temporary &&
		!!$user?.permissions?.chat?.temporary_enforced;
	const selectedFolder = embedded ? writable<FolderDetails | null>(null) : _selectedFolder;
	const showTabs = embedded ? writable(get(_showTabs)) : _showTabs;
	// the call lives in the main chat's voice tab, so a side chat is never in it
	const voiceCall = embedded ? writable(false) : _voiceCall;
	const showEmbeds = embedded ? writable(false) : _showEmbeds;
	const selectedMachineId = tabbed ? writable(get(_selectedMachineId)) : _selectedMachineId;
	const machineSkills = tabbed ? writable<any[]>([]) : _machineSkills;
	const models = tabbed ? writable(get(_models)) : _models;
	setChatContext({
		chatId,
		models,
		temporary: temporaryChat,
		audioQueue,
		submitPrompt: (prompt) => submitHandler(prompt),
		getCurrentDirectory: (machineId) => tabs?.getCurrentDirectory(machineId)
	});
	export let embeddedTitle = '';
	export let embeddedChats = [];
	export let embeddedDraftKey = '';
	export let embeddedDraft: {
		controls?: ReturnType<typeof getChatInputControls>;
		machineId?: string | null;
		machineContext?: MachineContext | null;
		chatVariables?: Record<string, any>;
		submit?: boolean;
		selectedModels: string[];
		params: Record<string, any>;
		history: typeof history;
		chatFiles: any[];
		temporary: boolean;
		prompt: string;
		files: any[];
	} | null = null;
	export let initialPrompt = '';
	export let parentChatId = '';
	export let draftTitle = '';
	export let draftFolderId: string | null = null;
	export let suggestedPrompts = [];
	export let selectedText = '';
	export let notePageId = '';
	export let noteFiles = [];
	export let onBeforeNoteSubmit: (() => Promise<void>) | null = null;
	export let onInsertToNote: ((content: string) => void) | null = null;
	export let onCloseEmbedded: (() => void) | null = null;
	// Collapsed embedded chats render only the composer; the host expands them on demand.
	export let embeddedCollapsed = false;
	export let onCollapseEmbedded: (() => void) | null = null;
	// Pads the header and messages when the host draws the composer flush to its frame.
	export let embeddedInset = false;
	export let onRecordedAudio: ((file: File) => unknown) | null = null;
	export let onNewEmbeddedChat: (() => void | Promise<void>) | null = null;
	export let onCreateEmbeddedChat:
		| ((chat: {
				models: string[];
				params: Record<string, any>;
				variables: Record<string, any>;
		  }) => any | Promise<any>)
		| null = null;
	export let onSelectEmbeddedChat: ((chatId: string) => void | Promise<void>) | null = null;
	export let onDeleteEmbeddedChat: ((chatId: string) => void | Promise<void>) | null = null;
	export let onEmbeddedChatTitle: ((chatId: string, title: string) => void | Promise<void>) | null =
		null;
	// The HTML and SVG found in this chat's answers. An embedded chat can open them only
	// through onOpenArtifacts; the main chat opens them in its own tabs.
	export let artifacts: Writable<{ type: string; content: string }[]> = writable([]);
	export let onOpenArtifacts: ((code?: string) => void) | null = null;

	let loading = true;
	const instanceId = uuidv4();
	const messagesContainerId = embedded ? `note-messages-${instanceId}` : 'messages-container';
	const inputId = embedded ? `note-chat-input-${instanceId}` : 'chat-input';
	let audioElement: HTMLAudioElement;
	$: chatContainerId = embedded ? `note-chat-container-${instanceId}` : 'chat-container';
	$: messageInputDropzoneId = embedded ? `note-chat-input-dropzone-${instanceId}` : 'chat-pane';
	$: dropzoneId = tabbed ? chatContainerId : messageInputDropzoneId;
	const onTemporaryChange = tabbed
		? (value: boolean) => {
				if (!processing) temporaryChat.set(value);
			}
		: embedded
			? null
			: async (value: boolean) => {
					// The URL keeps a choice that differs from the default across reloads.
					const search =
						value === ($settings?.temporaryChatByDefault ?? false)
							? ''
							: `?temporary-chat=${value}`;
					if (location.pathname !== '/' && !location.pathname.startsWith('/folders/')) {
						await goto(`/${search}`);
						return;
					}
					window.history.replaceState(window.history.state, '', `${location.pathname}${search}`);
					if ($chatId) await initNewChat({ temporary: value });
					else temporaryChat.set(value);
				};

	const eventTarget = new EventTarget();

	export let messageInput: MessageInput | undefined = undefined;
	let messagesRef: Messages | undefined;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;
	$: lastScrollTop = messagesContainerElement?.scrollTop ?? 0;
	$: isNearTop = lastScrollTop <= 100;

	let showEventConfirmation = false;
	let pendingUrlActions: { urls: string[]; call: boolean } | null = null;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventConfirmationInputType = '';
	let eventConfirmationInputOptions: ({ label?: string; value: string } | string)[] = [];
	let eventCallback: (value: any) => void = () => {};
	let eventInteractionId: string | null = null;
	type BrowserInteraction = {
		id: string;
		messageId: string;
		type: string;
		data: any;
		callback: (value: any) => void;
	};
	let browserInteractions: BrowserInteraction[] = [];
	let browserApprovalMode: string | null = null;
	$: browserInteraction = browserInteractions[0];

	const resolveBrowserInteraction = (interaction: BrowserInteraction, value: any) => {
		if (!browserInteractions.includes(interaction)) return;
		browserInteractions = browserInteractions.filter((item) => item !== interaction);
		interaction.callback(value);
	};

	const cancelBrowserInteractions = () => {
		browserApprovalMode = null;
		for (const interaction of browserInteractions) {
			resolveBrowserInteraction(interaction, { status: 'cancelled', answers: {} });
		}
	};

	let selectedModels = [''];
	let selectedModelIdx = 0;
	$: selectedModelIdx = Math.max(0, selectedModels.length - 1);
	$: backgroundImage = embedded
		? null
		: ($selectedFolder as { meta?: { background_image_url?: string } } | null)?.meta
				?.background_image_url ||
			atSelectedModel?.info?.meta?.background_image_url ||
			($models ?? []).find((model) => model.id === selectedModels[selectedModelIdx])?.info?.meta
				?.background_image_url ||
			($settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url);

	let atSelectedModel: Model | undefined;
	let selectedModelIds: string[] = [];
	$: if (atSelectedModel !== undefined) {
		selectedModelIds = [atSelectedModel.id];
	} else {
		selectedModelIds = selectedModels;
	}
	$: modelSuggestionPrompts =
		resolveLocalizedModelPromptSuggestions(atSelectedModel, $i18n.language) ??
		resolveLocalizedModelPromptSuggestions(
			($models ?? []).find((model) => model.id === selectedModels[selectedModelIdx]),
			$i18n.language
		);
	let serverContextUsage = null;
	let contextUsage = null;

	const normalizeSelectedModels = (modelIds: string[] = []) => {
		if (
			modelIds.some(
				(id) =>
					id.startsWith('agent:') && decodeURIComponent(id.split(':')[1]) === $selectedMachineId
			)
		)
			return modelIds;
		const selected = resolveDefaultModelIds(
			$models ?? [],
			modelIds,
			$settings?.models,
			$config?.default_models?.split(',')
		);
		return selected.length ? selected : [''];
	};

	$: {
		const modelSearchParam =
			$page.url.searchParams.get('models') || $page.url.searchParams.get('model');

		if (
			chatIdProp === '' &&
			($models ?? []).length > 0 &&
			!selectedModels?.some((modelId) => modelId) &&
			!modelSearchParam
		) {
			const fallbackModels = normalizeSelectedModels(selectedModels);
			if (!equal(fallbackModels, selectedModels)) {
				selectedModels = fallbackModels;
				if (!loading && !modelDefaults) setDefaults();
			}
		}
	}

	$: contextCompactionEnabled = Boolean($config?.features?.enable_context_compaction);

	const getContextThreshold = (
		modelId: string | undefined,
		models: Model[],
		params: { compact_token_threshold?: unknown }
	) => {
		const model = models.find((item) => item.id === modelId);
		const threshold = Number(
			model?.info?.params?.compact_token_threshold ?? params?.compact_token_threshold
		);
		return Number.isFinite(threshold) && threshold > 0 ? threshold : null;
	};

	const getContextUsage = (
		chatHistory: typeof history,
		system: string,
		threshold: number | null
	) => {
		if (!chatHistory?.currentId) {
			return null;
		}

		const messages = createMessagesList(chatHistory, chatHistory.currentId);
		const systemTokens = estimateTokens(system);
		let estimatedTokens = systemTokens;
		let hasUsageCheckpoint = false;
		let summary = '';
		let startIdx = 0;

		for (let idx = 0; idx < messages.length; idx += 1) {
			const value = messages[idx]?.contextSummary ?? messages[idx]?.context_summary;
			if (typeof value === 'string' && value.trim()) {
				summary = value;
				startIdx = idx;
			}
		}

		const activeMessages = messages.slice(startIdx);

		for (let idx = activeMessages.length - 1; idx >= 0; idx -= 1) {
			const usage = activeMessages[idx]?.usage ?? activeMessages[idx]?.info?.usage;
			const usageTokens = getUsageTokenCount(usage);
			if (usageTokens) {
				hasUsageCheckpoint = true;
				estimatedTokens =
					usageTokens +
					estimateUsageGrowth(activeMessages[idx]) +
					estimateMessagesTokens(activeMessages.slice(idx + 1));
				break;
			}
		}

		if (!hasUsageCheckpoint) {
			estimatedTokens += estimateTokens(summary) + estimateMessagesTokens(activeMessages);
		}

		return {
			tokens: estimatedTokens,
			estimated_tokens: estimatedTokens,
			threshold,
			percent: threshold > 0 ? Math.max(0, Math.round((estimatedTokens / threshold) * 100)) : null,
			source: 'estimated'
		};
	};

	$: contextThreshold = contextCompactionEnabled
		? (getContextThreshold(
				atSelectedModel?.id ?? selectedModels.find((id) => id),
				$models ?? [],
				params
			) ??
			serverContextUsage?.threshold ??
			null)
		: null;
	$: contextUsage =
		getContextUsage(history, $settings?.system ?? '', contextThreshold) ??
		(contextCompactionEnabled ? serverContextUsage : null);
	$: embeddedHeaderTitle = embeddedTitle || $chatTitle || $i18n.t('Chat');

	let selectedToolIds: string[] = [];
	let selectedSkillIds: string[] = [];
	let selectedFilterIds: string[] = [];
	let pendingOAuthTools: { id: string; name: string; serverId: string; authType: string | null }[] =
		[];

	let imageGenerationEnabled = false;
	let selectedImageModelId = '';
	let videoGenerationEnabled = false;
	let selectedVideoModelId = '';
	let webSearchEnabled = false;
	let codeInterpreterEnabled = false;
	let webSearchActive = false;
	let showWebSearchConfirm = false;
	let pendingWebSearchPrompt: string | null = null;
	let webSearchConfirmed = false;

	// Before webSearchActive, so it sees the new defaults in the same update
	$: if (!loading && modelDefaults && !equal(selectedModelIds, defaultsModelIds)) {
		setDefaults(true);
	}

	$: {
		const currentModels = atSelectedModel?.id ? [atSelectedModel.id] : selectedModels;
		const allModelsSupportWebSearch =
			currentModels.filter(
				(model) =>
					($models ?? []).find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
			).length === currentModels.length;

		webSearchActive = Boolean(
			$config?.features?.enable_web_search &&
			($user?.role === 'admin' || $user?.permissions?.features?.web_search) &&
			(webSearchEnabled ||
				(allModelsSupportWebSearch && ($settings?.webSearch ?? false) === 'always'))
		);
	}

	const openWebSearchConfirm = () => {
		window.setTimeout(() => {
			showWebSearchConfirm = true;
		}, 0);
	};

	const handleWebSearchToggle = (enabled: boolean) => {
		if ($selectedFolder && !$chatId) return;
		if (enabled && $config?.features?.enable_web_search_confirmation && !webSearchConfirmed) {
			webSearchEnabled = false;
			pendingWebSearchPrompt = null;
			openWebSearchConfirm();
		}
	};

	const resetWebSearchConfirmation = () => {
		webSearchConfirmed = false;
		pendingWebSearchPrompt = null;
		showWebSearchConfirm = false;
	};

	$: if (!webSearchActive) {
		resetWebSearchConfirmation();
	}

	let showCommands = false;

	let generating = false;
	let dragged = false;
	let generationController = null;
	const openArtifacts = (code?: string) => {
		// the list is rebuilt after a debounce, so it can lag behind the block being opened
		getContents();
		if (embedded) onOpenArtifacts?.(code);
		else tabs?.openArtifacts(code);
	};
	// a notes chat has nowhere to show them
	$: canOpenArtifacts = !embedded || !!onOpenArtifacts;

	let chat: any = null;
	let tags = [];

	// Non-owners may reply when the sharing mode allows it, but cannot save chat edits.
	$: isShared = chat != null && chat.user_id !== $user?.id;
	$: if (isShared && $voiceCall) voiceCall.set(false);
	$: canClone = isShared && ($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true));
	$: canOpenChatTab =
		$user?.role === 'admin' ||
		($user?.role === 'user' && ($user.permissions?.chat?.side_chat ?? false));
	let cloning = false;

	const cloneSharedChat = async () => {
		if (!canClone || cloning) return;
		cloning = true;
		try {
			const [copy] = await importChats(localStorage.token, [
				{
					chat: {
						...chat.chat,
						title: $i18n.t('Clone of {{TITLE}}', { TITLE: chat.title }),
						originalChatId: chat.id,
						branchPointMessageId: history.currentId
					}
				}
			]);
			if (copy) {
				if (!embedded) await goto(`/c/${copy.id}`);
				await refreshChatList(localStorage.token);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			cloning = false;
		}
	};

	let chatOwner = null;

	const resolveChatOwner = async (userId) => {
		if (chatOwner?.id === userId) {
			return;
		}

		chatOwner = await getUserInfoById(localStorage.token, userId).catch((error) => {
			console.error(error);
			return null;
		});
	};

	$: if (isShared && chat?.user_id) {
		void resolveChatOwner(chat.user_id);
	} else {
		chatOwner = null;
	}

	let chatTasks = [];

	let history: { currentId: string | null; messages: Record<string, any> } = {
		messages: {},
		currentId: null
	};
	// Context inherited at creation is hidden up to this message.
	let branchPointMessageId: string | null = null;
	$: contextOnly = !!branchPointMessageId && history.currentId === branchPointMessageId;
	$: inputHistory = contextOnly ? { messages: {}, currentId: null } : history;

	let taskIds = null;
	let liveStatus = '';
	export let streaming = false;

	$: streaming =
		!loading &&
		(generating ||
			Object.values(history.messages).some(
				(message) => message.role === 'assistant' && message.done === false
			));

	$: if (loading || !history.currentId) {
		liveStatus = '';
	} else if (
		Object.values(history.messages).some(
			(message) => message.role === 'assistant' && message.done === false
		)
	) {
		liveStatus = $i18n.t('Generating...');
	} else if (liveStatus) {
		liveStatus = $i18n.t('Response complete');
	}

	// Chat Input
	export let prompt = '';
	let chatFiles: any[] = [];
	export let files: any[] = [];
	let machineContext: MachineContext | null = null;
	const askFile = async (instruction: string, file: FilesystemFile) => {
		if (selectedModels.includes('')) throw new Error($i18n.t('Model not selected'));
		const attachments = [structuredClone(file)];
		if (fullWidthTabs) {
			tabs?.focusMainChat();
			await tick();
			if (!$voiceCall) messageInput?.focus({ preventScroll: true });
		}
		const last = history.currentId ? history.messages[history.currentId] : null;
		if (last?.role === 'assistant' && !last.done) {
			chatRequestQueues.update((queues) => ({
				...queues,
				[$chatId]: [
					...(queues[$chatId] ?? []),
					{ id: uuidv4(), prompt: instruction, files: attachments }
				]
			}));
		} else {
			await submitPrompt(instruction, attachments);
		}
	};

	// Adds text to the composer for the user to review, keeping any draft already there.
	const draftPrompt = async (text: string) => {
		if (fullWidthTabs) {
			tabs?.focusMainChat();
			await tick();
		}
		messageInput?.setText(prompt.trim() ? `${prompt.trimEnd()}\n\n${text}` : text);
		messageInput?.focus({ preventScroll: true });
	};

	let params = {};
	let chatVariables = {};
	let showChatVariablesModal = false;
	let loadedChatIdProp = '';
	let currentDraftKey = '';

	// Chat parameters own the approval mode; chats without an override use the user default.
	$: toolApprovalMode = resolveToolApprovalMode(
		params?.tool_approval_mode ?? $settings?.params?.tool_approval_mode,
		$config?.features?.enable_tool_permissions_auto ?? false
	);

	const handleToolApprovalModeChange = async (mode: string) => {
		const tool_approval_mode = resolveToolApprovalMode(
			mode,
			$config?.features?.enable_tool_permissions_auto ?? false
		);
		browserApprovalMode = tool_approval_mode;
		params = {
			...params,
			tool_approval_mode
		};

		settings.set({
			...$settings,
			params: {
				...($settings?.params ?? {}),
				tool_approval_mode
			}
		});
		await saveParam('tool_approval_mode', tool_approval_mode);
		await updateUserSettings(localStorage.token, { ui: { params: $settings.params } }).catch(
			(err) => {
				console.error('[tool permissions settings]', err);
			}
		);

		if (tool_approval_mode === 'full') {
			if (isTemporaryChatId($chatId)) {
				if (browserApprovalMode !== 'full') return;
				for (const interaction of browserInteractions) {
					if (interaction.data?.tool_call) resolveBrowserInteraction(interaction, true);
				}
				return;
			}
			const messages = [...Object.values(history?.messages ?? {})].reverse() as any[];
			for (const message of messages) {
				if (message.id === branchPointMessageId) break;
				if ((message.user_id ?? chat?.user_id ?? $user?.id) !== $user?.id) continue;
				const output = (Array.isArray(message?.output) ? message.output : []) as any[];
				const resultCallIds = new Set(
					output
						.filter((item: any) => item?.type === 'function_call_output' && item?.call_id)
						.map((item: any) => item.call_id)
				);
				const pendingCall = output.find((item: any) => {
					const callId = item?.call_id ?? item?.id;
					return (
						item?.type === 'function_call' &&
						item?.name !== 'ask_user' &&
						(item?.status === 'pending' || item?.status === 'requires_approval') &&
						callId &&
						!resultCallIds.has(callId)
					);
				});
				const callId = pendingCall?.call_id ?? pendingCall?.id;
				if (!message?.id || !callId) {
					continue;
				}

				const res = await resolveChatMessageToolCall(
					localStorage.token,
					$chatId,
					message.id,
					callId,
					'approve'
				).catch(async (error) => {
					toast.error(`${error}`);
					await loadChat();
					return null;
				});
				if (res) onToolCallResolved(res);
				break;
			}
		}
	};

	const findPendingAskUser = (chatHistory) => {
		if (!chatHistory?.messages) {
			return null;
		}
		const messages = chatHistory.currentId
			? createMessagesList(chatHistory, chatHistory.currentId)
			: Object.values(chatHistory.messages);
		for (const message of [...messages].reverse()) {
			if (message.id === branchPointMessageId) break;
			if ((message.user_id ?? chat?.user_id ?? $user?.id) !== $user?.id) continue;
			const pending = getPendingAskUserFromMessage(message);
			if (pending) return pending;
		}
		return null;
	};

	const messageHasPendingAskUser = (message) => {
		return !!getPendingAskUserFromMessage(message);
	};

	const answerPendingAskUser = async (messageId, callId, answers, timedOut = false) => {
		if (!$chatId || !messageId || !callId) {
			return;
		}

		const res = await resolveChatMessageToolCall(
			localStorage.token,
			$chatId,
			messageId,
			callId,
			'answer',
			{
				answers,
				timed_out: timedOut
			}
		).catch(async (error) => {
			toast.error(`${error}`);
			await loadChat();
		});
		onToolCallResolved(res);
	};

	const rejectPendingAskUser = async (messageId, callId) => {
		if (!$chatId || !messageId || !callId) {
			return;
		}

		const res = await resolveChatMessageToolCall(
			localStorage.token,
			$chatId,
			messageId,
			callId,
			'reject'
		).catch(async (error) => {
			toast.error(`${error}`);
			await loadChat();
		});
		onToolCallResolved(res);
	};

	$: pendingAskUser = findPendingAskUser(history);
	$: savedAskUserPrompt = pendingAskUser
		? {
				show: true,
				questions: Array.isArray(pendingAskUser.args?.questions)
					? pendingAskUser.args.questions
					: [],
				allowOther: pendingAskUser.args?.allow_other !== false,
				timeoutMs: null,
				onConfirm: (value) => {
					void answerPendingAskUser(
						pendingAskUser.message.id,
						pendingAskUser.call.call_id || pendingAskUser.call.id,
						value?.answers ?? {},
						false
					);
				},
				onCancel: () => {
					void rejectPendingAskUser(
						pendingAskUser.message.id,
						pendingAskUser.call.call_id || pendingAskUser.call.id
					);
				}
			}
		: null;

	$: socketAskUserPrompt = ((interaction: BrowserInteraction | undefined) => ({
		id: interaction?.id,
		show: interaction?.type === 'request:user_input',
		questions: interaction?.data?.questions ?? [],
		allowOther: interaction?.data?.allow_other ?? true,
		timeoutMs: interaction?.data?.timeout_ms ?? null,
		onConfirm: (value: any) => interaction && resolveBrowserInteraction(interaction, value),
		onCancel: () =>
			interaction && resolveBrowserInteraction(interaction, { status: 'cancelled', answers: {} })
	}))(browserInteraction);

	const mergeChatVariableSchemas = (modelIds = [], availableModels = []) => {
		const byKey: Record<string, any> = {};
		const conflicts: any[] = [];

		for (const modelId of modelIds.filter(Boolean)) {
			const fields =
				availableModels.find((model) => model.id === modelId)?.info?.meta?.chat_variables_schema
					?.fields ?? [];
			for (const rawField of fields) {
				const field = {
					...rawField,
					type: rawField?.type ?? 'text',
					required: Boolean(rawField?.required)
				};
				if (!field?.key) continue;
				const { required, ...shape } = field;

				const existing = byKey[field.key];
				if (!existing) {
					byKey[field.key] = {
						field,
						modelIds: [modelId],
						shape
					};
					continue;
				}

				if (!equal(existing.shape, shape)) {
					conflicts.push({
						key: field.key,
						modelIds: [...existing.modelIds, modelId]
					});
					continue;
				}

				existing.field = {
					...existing.field,
					required: existing.field.required || field.required
				};
				existing.modelIds.push(modelId);
			}
		}

		return {
			fields: Object.values(byKey).map((item: any) => item.field),
			conflicts
		};
	};

	const hasValue = (value) => value !== undefined && value !== null && value !== '';

	const getChatVariablesForm = (modelIds = [], values = {}, availableModels = []) => {
		const { fields, conflicts } = mergeChatVariableSchemas(modelIds, availableModels);
		const empty =
			fields.length > 0 &&
			fields.every((field) => !hasValue(values?.[field.key]) && !hasValue(field.default));
		const missing = fields.some(
			(field) => field.required && !hasValue(values?.[field.key]) && !hasValue(field.default)
		);
		const variables = fields.reduce(
			(acc, field) => {
				const { key, ...inputField } = field;
				acc[key] = {
					...inputField,
					default: hasValue(values?.[key]) ? values[key] : inputField.default
				};
				return acc;
			},
			{} as Record<string, any>
		);

		return { conflicts, empty, missing, variables };
	};

	const saveChatVariables = async (values) => {
		chatVariables = { ...chatVariables, ...values };
		if (isShared) return;

		if ($chatId && !$temporaryChat && !isTemporaryChatId($chatId)) {
			const res = await updateChatById(localStorage.token, $chatId, {}, chatVariables).catch(
				(err) => {
					console.error('[chat variables save]', err);
					toast.error($i18n.t('Failed to save chat variables'));
					return null;
				}
			);
			if (res) chat = res;
		}
	};

	const onToolCallResolved = (res) => {
		const newTaskIds = res?.task_ids ?? (res?.task_id ? [res.task_id] : []);
		if (newTaskIds.length > 0) {
			taskIds = [...(taskIds ?? []), ...newTaskIds];
		}
	};

	const mergeFiles = (current, incoming) => {
		const seen = new Set();
		return [...(incoming ?? []), ...(current ?? [])].filter((file) => {
			const key = `${file?.type ?? ''}:${file?.id ?? file?.url ?? file?.name ?? ''}`;
			if (seen.has(key)) return false;
			seen.add(key);
			return true;
		});
	};

	const applyChatInputControls = (input: ReturnType<typeof getChatInputControls>) => {
		selectedToolIds = input.selectedToolIds ?? [];
		selectedSkillIds = input.selectedSkillIds ?? [];
		selectedFilterIds = input.selectedFilterIds ?? [];
		webSearchEnabled = input.webSearchEnabled ?? false;
		imageGenerationEnabled = input.imageGenerationEnabled ?? false;
		selectedImageModelId = input.selectedImageModelId ?? '';
		videoGenerationEnabled = input.videoGenerationEnabled ?? false;
		selectedVideoModelId = input.selectedVideoModelId ?? '';
		codeInterpreterEnabled = input.codeInterpreterEnabled ?? false;
	};

	const restoreChatInput = async (storageChatInput: string | null) => {
		if (!storageChatInput || $temporaryChat) {
			return false;
		}

		try {
			const input = JSON.parse(storageChatInput);
			prompt = input.prompt ?? '';
			messageInput?.setText(prompt);
			files = input.files ?? [];
			applyChatInputControls(input);
			// Ignore approval modes in older drafts. Restoring input must not overwrite chat
			// parameters or invoke the change handler, which can save settings and approve tools.
			return true;
		} catch (e) {
			return false;
		}
	};

	const withSelectedText = (text: string) => {
		if (!embedded) return text;
		return (
			text +
			(notePageId ? `\n\nActive note page_id: ${notePageId}` : '') +
			(selectedText?.trim()
				? `\n\nSelected note text for replace_note_content operations:\n${selectedText.trim()}`
				: '')
		);
	};
	const noteChatDebug = (message: string, data: Record<string, unknown> = {}) => {
		if (!embedded) return;
		console.info('[note-chat]', message, {
			chatIdProp,
			activeChatId: $chatId,
			loading,
			...data
		});
	};

	$: if (chatIdProp && chatIdProp !== loadedChatIdProp) {
		noteChatDebug('chatIdProp changed; loading linked chat', {
			previousChatIdProp: loadedChatIdProp
		});
		loadedChatIdProp = chatIdProp;
		navigateHandler();
	}

	$: if (embedded && embeddedDraftKey && embeddedDraftKey !== currentDraftKey) {
		noteChatDebug('embedded draft requested', { embeddedDraftKey });
		if (currentDraftKey) sessionStorage.removeItem(getChatInputKey(currentDraftKey));
		currentDraftKey = embeddedDraftKey;
		initEmbeddedDraft();
	}

	let saveControlsTimer;
	$: if (!loading && !$temporaryChat && $chatId && chatFiles) {
		clearTimeout(saveControlsTimer);
		saveControlsTimer = setTimeout(saveControls, 400);
	}

	let chatLoadController = new AbortController();
	const startChatLoad = () => {
		chatLoadController.abort();
		chatLoadController = new AbortController();
		return chatLoadController.signal;
	};
	onDestroy(() => chatLoadController.abort());
	const navigateHandler = async () => {
		loading = true;
		selectedFolder.set(null);
		tabs?.resetForChatSwitch();
		const signal = startChatLoad();
		modelDefaults = null;
		cancelBrowserInteractions();
		bridge?.end();
		noteChatDebug('navigateHandler start');
		// Mark the outgoing chat as read before loading the new one.
		// $chatId still holds the previous chat here — loadChat() updates it.
		if ($chatId && $chatId !== chatIdProp && !$temporaryChat) {
			noteChatDebug('marking outgoing chat read', { outgoingChatId: $chatId });
			updateLastReadAt($chatId);
		}

		clearTimeout(saveControlsTimer);
		await saveControls();
		if (signal.aborted) {
			pendingChatRequest = null;
			return;
		}
		loading = true;

		prompt = '';
		messageInput?.setText('');

		files = [];
		if (embeddedDraft) ({ prompt, files } = embeddedDraft);
		selectedToolIds = [];
		selectedSkillIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;
		selectedImageModelId = '';
		videoGenerationEnabled = false;
		selectedVideoModelId = '';

		if (chatIdProp) {
			await loadChat(signal);
		} else if (!embedded) {
			await goto('/');
		} else {
			loading = false;
		}
	};

	const initEmbeddedDraft = async () => {
		const signal = startChatLoad();
		modelDefaults = null;
		machineContext = embeddedDraft?.machineContext ?? null;
		clearTimeout(saveControlsTimer);
		await saveControls();

		if ($chatId && !$temporaryChat) {
			updateLastReadAt($chatId);
		}

		loading = true;
		loadedChatIdProp = '';
		chat = null;
		tags = [];
		taskIds = null;
		chatTasks = [];
		serverContextUsage = null;
		history = {
			messages: {},
			currentId: null
		};
		params = {};
		chatVariables = {};
		chatFiles = [];
		files = [];
		selectedToolIds = [];
		selectedSkillIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;
		selectedImageModelId = '';
		videoGenerationEnabled = false;
		selectedVideoModelId = '';
		prompt = '';
		messageInput?.setText('');
		await chatId.set('');
		await chatTitle.set('');
		if (embeddedDraft) {
			({ selectedModels, params, history, chatFiles, prompt, files } = embeddedDraft);
			branchPointMessageId = history.currentId;
			await temporaryChat.set(isTemporaryEnforced() || embeddedDraft.temporary);
		}

		if (embeddedDraft?.controls) {
			chatVariables = embeddedDraft.chatVariables ?? {};
			selectedMachineId.set(embeddedDraft.machineId ?? null);
			applyChatInputControls(embeddedDraft.controls);
		}
		await setDefaults(!!embeddedDraft?.controls);
		loading = false;
		await tick();
		if (embeddedDraft) {
			({ prompt, files } = embeddedDraft);
			messageInput?.setText(prompt);
		}
		if (!$mobile) messageInput?.focus({ preventScroll: true });
		if (embeddedDraft?.submit || initialPrompt) {
			await tick();
			if (!signal.aborted)
				submitHandler(embeddedDraft?.submit ? embeddedDraft.prompt : initialPrompt);
		}
	};

	const onSelect = async (e) => {
		const { type, data } = e;

		if (type === 'prompt') {
			// Handle prompt selection
			messageInput?.setTextHandler(data, async () => {
				if (!($settings?.insertSuggestionPrompt ?? false)) {
					await tick();
					submitHandler(prompt);
				}
			});
		}
	};

	$: if (selectedModels && chatIdProp !== '') {
		saveSessionSelectedModels();
	}

	const saveSessionSelectedModels = () => {
		const selectedModelsString = JSON.stringify(selectedModels);
		if (
			tabbed ||
			selectedModels.length === 0 ||
			(selectedModels.length === 1 && selectedModels[0] === '') ||
			sessionStorage.selectedModels === selectedModelsString
		) {
			return;
		}
		sessionStorage.selectedModels = selectedModelsString;
		console.log('saveSessionSelectedModels', selectedModels, sessionStorage.selectedModels);
	};

	// The backend only marks a tool as system_oauth when the user's SSO session is gone, so
	// signing in again is the fix. These tools never block sending or redirect on their own.
	const isSystemOAuthTool = (toolId: string) =>
		($tools ?? []).find((tool) => tool.id === toolId)?.auth_type === 'system_oauth';

	const continueOAuthRedirect = async () => {
		if (tabbed) {
			pendingOAuthTools = [];
			return;
		}
		if (pendingOAuthTools.length === 0) {
			sessionStorage.removeItem('oauthRedirectInProgressToolId');
			return;
		}

		if (chatIdProp) {
			return;
		}

		const nextTool = pendingOAuthTools.find((tool) => !isSystemOAuthTool(tool.id));
		if (!nextTool) {
			sessionStorage.removeItem('oauthRedirectInProgressToolId');
			return;
		}
		if (sessionStorage.getItem('oauthRedirectInProgressToolId') === nextTool.id) {
			sessionStorage.removeItem('oauthRedirectInProgressToolId');
			return;
		}

		await oauthRedirectHandler(nextTool);
	};

	const resetInput = async () => {
		// Let the $: update finish first, or webSearchActive misses the default-feature writes
		await tick();
		selectedToolIds = [];
		selectedSkillIds = [];
		selectedFilterIds = [];
		pendingOAuthTools = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;
		selectedImageModelId = '';
		videoGenerationEnabled = false;
		selectedVideoModelId = '';

		if (selectedModelIds.filter((id) => id).length > 0) {
			await setDefaults();
		}
	};

	/** Check whether a machine ID references an available machine. */
	const isMachineAvailable = (tid: string): boolean => {
		return (
			$config?.features?.enable_tool_servers === true &&
			($machines ?? []).some((t) => !!tid && t.id === tid)
		);
	};

	$: if (
		$temporaryChat &&
		($machines ?? []).some(
			(t) => !!$selectedMachineId && t.id === $selectedMachineId && t.scope === 'chat'
		)
	) {
		selectedMachineId.set(null);
	}

	let lastMachineSkillSelector: string | null = null;

	let appliedFolderDefaults: FolderDetails['data'] = null;
	let loadedAgentEnvironment: { key: string; models: Model[] } | null = null;
	$: setFolderModelConnections($machines);

	const getAgentEnvironment = () => {
		const machineId = $selectedMachineId;
		const directory = machineContext?.currentDirectory;
		return machineId && directory
			? JSON.stringify([
					machineId,
					directory,
					($machines ?? []).find((server) => server.id === machineId)?.scope === 'chat'
						? $chatId
						: null,
					$config,
					$settings,
					$machines
				])
			: null;
	};

	const refreshAgentModels = async (
		folder: FolderDetails | null = null,
		signal = chatLoadController.signal
	) => {
		const machineId = $selectedMachineId;
		const environment = folder ? null : getAgentEnvironment();
		loadedAgentEnvironment = null;
		const retained = folder ? getFolderAgentModels(folder) : null;
		models.update((available) => [
			...(available ?? []).filter(
				(model) =>
					!isMachine(model.owned_by) || (!folder && machineIdOf(model.agent) === $selectedMachineId)
			),
			...(retained ?? [])
		]);

		const refresh = async () => {
			try {
				const discovered = folder
					? await loadFolderAgentModels(localStorage.token, folder, !!retained)
					: await getModels(localStorage.token, false, false, {
							machineId,
							chatId: $chatId,
							cwd: machineContext?.currentDirectory ?? null
						});
				if (signal.aborted || machineId !== $selectedMachineId) return;
				if (
					folder &&
					($selectedFolder?.id !== folder.id ||
						$selectedMachineId !== machineIdOf(folder.data) ||
						machineContext?.currentDirectory !== (folder.data?.working_directory ?? '') ||
						!getFolderAgentModels(folder))
				)
					return;

				const available = folder
					? [...($models ?? []).filter((model) => !isMachine(model.owned_by)), ...discovered]
					: discovered;
				models.set(available);
				loadedAgentEnvironment = environment ? { key: environment, models: available } : null;
				// Folder refreshes update the catalog without overwriting a draft's model choice.
				if (folder) return;
				const remaining = selectedModels.filter(
					(id) =>
						!id.startsWith('agent:') ||
						(chat?.chat?.models?.includes(id) &&
							decodeURIComponent(id.split(':')[1]) === $selectedMachineId) ||
						available.some((model: Model) => model.id === id)
				);
				selectedModels =
					remaining.length || equal(remaining, selectedModels)
						? remaining
						: normalizeSelectedModels(remaining);
			} catch (error) {
				if (!isCancelledFolderRequest(error)) console.error('Agent model discovery failed', error);
			}
		};
		if (retained) void refresh();
		else await refresh();
	};

	$: if ($models !== null && $selectedMachineId !== lastMachineSkillSelector) {
		if (machineContext?.machineId !== $selectedMachineId) machineContext = null;
		selectedSkillIds = selectedSkillIds.filter((id) => !isMachineRef(id));
		machineSkills.set([]);
		lastMachineSkillSelector = $selectedMachineId;
		// Folder initialization already requests this exact environment.
		if (
			!(
				(loading || !history.currentId) &&
				machineIdOf($selectedFolder?.data) === $selectedMachineId
			)
		) {
			void refreshAgentModels();
		}
	}

	// Sent skill mentions and the + menu's Skills entry need the machine's skills before any list opens.
	$: {
		const machineId = $selectedMachineId;
		void listMachineSkills(
			resolveMachineTarget(machineId, $machines ?? [], localStorage.token, {
				chatId: $chatId || null,
				modelId: selectedModels[0] ?? null
			})
		).then((items) => {
			if (machineId === $selectedMachineId) machineSkills.set(items);
		});
	}

	const applyFolderMachine = (folder: any) => {
		const machineId = machineIdOf(folder?.data);
		if (!machineId) return;
		selectedMachineId.set(machineId);
		machineContext = { machineId, currentDirectory: folder.data?.working_directory ?? '' };
	};

	let defaultsModelIds: string[] = [];
	let modelDefaults: Record<string, any> | null = null;
	let settingDefaults: Promise<void> | null = null;

	const setDefaults = async (preserveSelections = false) => {
		const modelIds = atSelectedModel ? [atSelectedModel.id] : [...selectedModels];
		const id = $chatId;
		const signal = chatLoadController.signal;
		while (settingDefaults) await settingDefaults;
		let resolveDefaults = () => {};
		settingDefaults = new Promise<void>((resolve) => (resolveDefaults = resolve));

		try {
			if (!$tools) tools.set(await getTools(localStorage.token));
			if (!$functions) functions.set(await getFunctions(localStorage.token));
			if (!$skills) skills.set(await getSkills(localStorage.token));
			if ($tools === null || $functions === null || $skills === null) return;
			if (
				signal.aborted ||
				id !== $chatId ||
				!equal(modelIds, atSelectedModel ? [atSelectedModel.id] : selectedModels)
			)
				return;

			const currentModels: any[] = modelIds.map((id) =>
				($models ?? []).find((model) => model.id === id)
			);
			if (!currentModels.length || currentModels.some((model) => !model)) return;
			const supports = (feature: string) =>
				currentModels.every((model) => model.info?.meta?.capabilities?.[feature] ?? true);
			const featureAvailable = (
				feature: 'web_search' | 'image_generation' | 'video_generation' | 'code_interpreter'
			) =>
				supports(feature) &&
				$config?.features?.[`enable_${feature}`] &&
				($user?.role === 'admin' || $user?.permissions?.features?.[feature]);
			const defaultFeature = (
				feature: 'web_search' | 'image_generation' | 'video_generation' | 'code_interpreter'
			) =>
				featureAvailable(feature) &&
				currentModels.every((model) => model.info?.meta?.defaultFeatureIds?.includes(feature));
			// A saved chat keeps its machine, including an explicit deselection, and a folder's machine
			// overrides the model's.
			const machineId =
				(loading && $chatId) || (!history.currentId && machineIdOf($selectedFolder?.data))
					? null
					: metaMachineIdOf(currentModels[0]?.info?.meta);
			const defaults: Record<string, any> = {
				selectedToolIds: [
					...new Set(
						currentModels.flatMap(
							(model) =>
								model.info?.meta?.toolIds?.filter(
									(id: string) =>
										selectedToolIds.includes(id) || ($tools as any[]).some((tool) => tool.id === id)
								) ??
								($settings as any)?.tools ??
								[]
						)
					)
				],
				selectedSkillIds: [
					...new Set(currentModels.flatMap((model) => model.info?.meta?.skillIds ?? []))
				].filter(
					(id) =>
						selectedSkillIds.includes(id) ||
						$skills.some((skill) => skill.id === id && skill.is_active)
				),
				selectedFilterIds: [
					...new Set(currentModels.flatMap((model) => model.info?.meta?.defaultFilterIds ?? []))
				],
				webSearchEnabled: !!defaultFeature('web_search'),
				imageGenerationEnabled: !!defaultFeature('image_generation'),
				videoGenerationEnabled: !!defaultFeature('video_generation'),
				codeInterpreterEnabled: !!defaultFeature('code_interpreter'),
				selectedImageModelId: currentModels.every(
					(model) =>
						(model.info?.meta?.imageModelId ?? '') ===
						(currentModels[0]?.info?.meta?.imageModelId ?? '')
				)
					? (currentModels[0]?.info?.meta?.imageModelId ?? '')
					: '',
				selectedVideoModelId: currentModels.every(
					(model) =>
						(model.info?.meta?.videoModelId ?? '') ===
						(currentModels[0]?.info?.meta?.videoModelId ?? '')
				)
					? (currentModels[0]?.info?.meta?.videoModelId ?? '')
					: '',
				machineId:
					machineId &&
					isMachineAvailable(machineId) &&
					currentModels.every((model) => metaMachineIdOf(model.info?.meta) === machineId)
						? machineId
						: $selectedMachineId
			};

			if (preserveSelections) {
				const current: Record<string, any> = {
					selectedToolIds: [...selectedToolIds, ...pendingOAuthTools.map((tool) => tool.id)],
					selectedSkillIds,
					selectedFilterIds,
					webSearchEnabled,
					imageGenerationEnabled,
					videoGenerationEnabled,
					codeInterpreterEnabled,
					selectedImageModelId,
					selectedVideoModelId,
					machineId: $selectedMachineId
				};
				if (!modelDefaults) {
					modelDefaults = structuredClone(defaults);
					defaultsModelIds = modelIds;
				}
				for (const key of Object.keys(defaults)) {
					const previous = modelDefaults[key];
					if (Array.isArray(previous)) {
						const added = current[key].filter((id: string) => !previous.includes(id));
						const removed = previous.filter((id: string) => !current[key].includes(id));
						// Keep deselected defaults in the baseline so later presets cannot re-enable them.
						modelDefaults[key] = [
							...new Set([...removed, ...defaults[key].filter((id: string) => !added.includes(id))])
						];
						defaults[key] = [
							...new Set([...defaults[key].filter((id: string) => !removed.includes(id)), ...added])
						];
					} else if (
						(key !== 'machineId' || equal(modelIds, defaultsModelIds)) &&
						current[key] !== previous
					) {
						defaults[key] = current[key];
					} else {
						modelDefaults[key] = defaults[key];
					}
				}
			} else {
				modelDefaults = structuredClone(defaults);
			}

			defaults.selectedFilterIds = defaults.selectedFilterIds.filter((id: string) =>
				currentModels.every((model) =>
					model.filters?.some((filter: { id: string }) => filter.id === id)
				)
			);
			defaults.webSearchEnabled &&= !!featureAvailable('web_search');
			defaults.imageGenerationEnabled &&= !!featureAvailable('image_generation');
			defaults.videoGenerationEnabled &&= !!featureAvailable('video_generation');
			defaults.codeInterpreterEnabled &&= !!featureAvailable('code_interpreter');
			if (!currentModels.some((model) => model.info?.meta?.capabilities?.terminal ?? true)) {
				defaults.machineId = null;
			}
			if (defaults.machineId) defaults.codeInterpreterEnabled = false;
			defaultsModelIds = modelIds;
			({
				selectedToolIds,
				selectedSkillIds,
				selectedFilterIds,
				webSearchEnabled,
				imageGenerationEnabled,
				videoGenerationEnabled,
				codeInterpreterEnabled,
				selectedImageModelId,
				selectedVideoModelId
			} = defaults);
			selectedMachineId.set(defaults.machineId);

			pendingOAuthTools = [];
			selectedToolIds = selectedToolIds.filter((id) => {
				const tool = ($tools as any[]).find((tool) => tool.id === id);
				if (tool?.authenticated !== false) return true;
				const parts = id.split(':');
				pendingOAuthTools.push({
					id,
					name: tool.name ?? id,
					serverId: parts.at(-1) ?? id,
					authType: parts.length > 1 ? (parts[0] === 'server' ? parts[1] : parts[0]) : null
				});
				return false;
			});
			await continueOAuthRedirect();
		} finally {
			settingDefaults = null;
			resolveDefaults();
		}
	};

	let revealedSearchMessage = '';
	$: if (
		!embedded &&
		!loading &&
		messagesRef &&
		chat &&
		chat.id === $page.params.id &&
		(!fullWidthTabs || mainChatActive)
	) {
		const target = $page.url.searchParams.get('message');
		const key = `${chat.id}:${target}`;
		if (target && history.messages[target] && key !== revealedSearchMessage) {
			revealedSearchMessage = key;
			autoScroll = false;
			history.currentId = getDeepestChildId(history, target);
			tick().then(() => messagesRef?.scrollToMessage(target));
		} else if (!target) revealedSearchMessage = '';
	}

	const showMessage = async (message, scroll = true, save = true) => {
		const _chatId = JSON.parse(JSON.stringify($chatId));
		let _messageId = JSON.parse(JSON.stringify(message.id));

		history.currentId = getDeepestChildId(history, _messageId);

		await tick();

		if (($settings?.scrollOnBranchChange ?? true) && scroll) {
			const messageElement = document.getElementById(`message-${message.id}`);
			if (messageElement) {
				messageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		}

		await tick();
		await tick();
		await tick();

		if (save) {
			saveChatHandler(_chatId, history);
		}
	};

	const updateLastReadAt = (id) => {
		$socket?.emit('events:chat', {
			chat_id: id,
			data: { type: 'last_read_at' }
		});
	};

	const machineEventHandler = (type: string, data: any, message: any) => {
		const attachment = history.messages[message?.parentId]?.files?.find(
			(file: any) => file.type === 'filesystem'
		);
		if (attachment) {
			if (machineIdOf(attachment) && machineIdOf(attachment) !== $selectedMachineId) return;
			if (machineEventName(type) === 'display_file' && machineContext?.file?.path === data.path)
				showFileNavDir.set(data.path);
			return;
		}
		const event = machineEventName(type);
		if (event === 'display_file') {
			if (!data?.path) return;
			if (($settings?.machineFileDisplay ?? $settings?.terminalFileDisplay) === 'inline') return;
			displayFileHandler(data.path, { showTabs, showFileNavPath }, { page: data?.page });
		} else if (event === 'write_file' || event === 'replace_file_content') {
			if (!data?.path) return;
			showFileNavDir.set(data.path);
		} else if (event === 'run_command' && !machineContext?.file) {
			showFileNavDir.set('/');
		}
	};

	let joinedChatId = '';
	let liveParticipants: { id: string; name: string }[] = [];
	const clearPresence = () => (liveParticipants = []);
	let chatRefresh: { id: string; promise: Promise<void> } | null = null;
	let typingUsers: { id: string; name: string }[] = [];
	let typingUsersTimeout: Record<string, ReturnType<typeof setTimeout>> = {};
	let lastTypingEmit = 0;

	const emitTyping = (typing: boolean) => {
		if (!$socket?.connected || !joinedChatId) return;
		if (typing && (joinedChatId !== $chatId || (isShared && !chat?.write_access))) return;
		if (typing ? Date.now() - lastTypingEmit < 2000 : !lastTypingEmit) return;
		lastTypingEmit = typing ? Date.now() : 0;
		$socket.emit('events:chat', {
			chat_id: joinedChatId,
			data: { type: 'typing', data: { typing } }
		});
	};

	const removeTypingUser = (id: string) => {
		clearTimeout(typingUsersTimeout[id]);
		delete typingUsersTimeout[id];
		typingUsers = typingUsers.filter((user) => user.id !== id);
	};

	const clearTyping = () => {
		emitTyping(false);
		Object.values(typingUsersTimeout).forEach(clearTimeout);
		typingUsersTimeout = {};
		typingUsers = [];
		lastTypingEmit = 0;
	};
	$: if (!prompt.trim()) emitTyping(false);

	const mergeChatMessages = (
		incoming: typeof history,
		baseline: Record<string, any> | null = null
	) => {
		const currentId = history.currentId;
		const next = incoming?.messages ?? {};
		// An edited prompt adds a sibling; other viewers should keep their selected branch.
		const hasNewBranch = Object.values(next).some(
			(message: any) =>
				message.role === 'user' &&
				!history.messages[message.id] &&
				Object.values(history.messages).some(
					(existing: any) => existing.role === 'user' && existing.parentId === message.parentId
				)
		);
		const follow =
			!hasNewBranch &&
			!generating &&
			!(
				taskIds?.length &&
				Object.values(history.messages).some(
					(message: any) =>
						message.role === 'assistant' &&
						message.done === false &&
						(message.user_id ?? chat?.user_id) === $user?.id
				)
			) &&
			Object.keys(next).some((id) => !history.messages[id]);
		for (const [id, message] of Object.entries(next) as [string, any][]) {
			const local = history.messages[id];
			const ownActive =
				local?.done === false &&
				(local.user_id ?? chat?.user_id) === $user?.id &&
				(taskIds?.length || generating);
			if (!local || (!ownActive && (!baseline || baseline[id] === local))) {
				history.messages[id] = { ...local, ...message };
				// Keep recovered replies finished unless their task is active or has been replaced.
				if (
					local?.done === true &&
					message.done === false &&
					local.meta?.task_id &&
					local.meta.task_id === message.meta?.task_id &&
					!taskIds?.includes(local.meta.task_id)
				) {
					history.messages[id].done = true;
				}
			}
			if (local) {
				history.messages[id] = {
					...history.messages[id],
					childrenIds: [...new Set([...(local.childrenIds ?? []), ...(message.childrenIds ?? [])])]
				};
			}
		}
		if ((!currentId || follow) && incoming.currentId && next[incoming.currentId]) {
			history.currentId = incoming.currentId;
			autoScrollToBottom();
		}
		history = history;
	};

	const refreshChat = () => {
		const id = $chatId;
		if (!id || $temporaryChat) return Promise.resolve();
		if (chatRefresh?.id === id) return chatRefresh.promise;
		const baseline = { ...history.messages };
		const signal = chatLoadController.signal;
		const promise = (async () => {
			try {
				const fresh = await getChatById(localStorage.token, id, signal);
				if ($chatId !== id || joinedChatId !== id || signal.aborted) return;
				chat = fresh;
				mergeChatMessages(fresh.chat.history, baseline);
			} catch (error) {
				if ($chatId === id && joinedChatId === id && !signal.aborted) {
					clearPresence();
					chat = null;
					history = { messages: {}, currentId: null };
					if (!embedded) await goto('/');
				}
			} finally {
				if (chatRefresh?.id === id) chatRefresh = null;
			}
		})();
		chatRefresh = { id, promise };
		return promise;
	};

	const syncChatRoom = (socket: typeof $socket, id: string, temporary: boolean) => {
		const next = socket?.connected && id && !temporary && !isTemporaryChatId(id) ? id : '';
		if (next === joinedChatId) return;
		clearTyping();
		clearPresence();
		if (joinedChatId && socket?.connected)
			socket.emit('events:chat', { chat_id: joinedChatId, data: { type: 'leave' } });
		joinedChatId = next;
		const connectionId = socket?.id;
		if (next && socket)
			socket.emit('events:chat', { chat_id: next, data: { type: 'join' } }, (accepted: boolean) => {
				if (!socket.connected || socket.id !== connectionId || $chatId !== next) return;
				if (!accepted) clearPresence();
				// A refused join can mean access was lost; the refresh then sends the reader home.
				void refreshChat();
			});
	};
	$: syncChatRoom($socket, $chatId, $temporaryChat);
	let openEmbeddedChatId: string = '';
	$: if (embedded && $chatId !== openEmbeddedChatId) {
		openEmbeddedChatIds.update((ids) => {
			const next = new Set(ids);
			next.delete(openEmbeddedChatId);
			if ($chatId) next.add($chatId);
			return next;
		});
		openEmbeddedChatId = $chatId;
	}

	const chatEventHandler = async (event, cb) => {
		if (isTemporaryChatId(event.chat_id) && event.chat_id !== $chatId) return;
		if (event?.data?.type === 'chat:presence') {
			if (!$socket?.connected || event.chat_id !== $chatId || event.chat_id !== joinedChatId)
				return;
			liveParticipants = (event.data.data?.users ?? []).filter(
				(person: { id: string; name: string }) => person.id !== $user?.id
			);
			return;
		}
		console.log(event);
		if (event?.data?.type === 'voice:play_animation') {
			cb?.(
				routeAvatarAnimation(eventTarget, event, {
					active: $voiceCall && callMode === 'current' && selectedModelIds.length === 1,
					chatId: $chatId,
					modelId: selectedModelIds[0],
					messageId: history.currentId,
					message: history.messages[event.message_id]
				})
			);
			return;
		}
		if (event.shared && event.user_id === $user?.id && event.data?.type !== 'chat:messages') return;
		// The first event can identify a new chat before the HTTP response arrives.
		if (!tabbed && !$chatId && event.chat_id && history.messages[event.message_id]) {
			chatId.set(event.chat_id);
		}
		const interactionType = event?.data?.type;
		const interactionData = event?.data?.data;
		if (interactionType === 'request:interaction:done') {
			if (eventInteractionId && eventInteractionId === interactionData?.interaction_id) {
				showEventConfirmation = false;
				eventInteractionId = null;
			}
			browserInteractions = browserInteractions.filter(
				(item) => item.id !== interactionData?.interaction_id
			);
			return;
		}
		if (
			interactionType === 'request:user_input' ||
			interactionType === 'request:elicitation' ||
			(interactionType === 'confirmation' && interactionData?.tool_call)
		) {
			if (!cb) return;
			if (event.chat_id !== $chatId) {
				if (!embedded && !$openEmbeddedChatIds.has(event.chat_id))
					cb({ status: 'cancelled', answers: {} });
				return;
			}
			if (
				interactionData?.tool_call &&
				isTemporaryChatId(event.chat_id) &&
				browserApprovalMode === 'full'
			) {
				cb(true);
				return;
			}
			browserInteractions = [
				...browserInteractions,
				{
					id: interactionData?.interaction_id ?? uuidv4(),
					messageId: event.message_id,
					type: interactionType,
					data: interactionData,
					callback: cb
				}
			];
			return;
		}

		if (event.chat_id === $chatId) {
			await tick();
			const type = event?.data?.type ?? null;
			if (type === 'typing') {
				const sender = event.user;
				if (!sender?.id || sender.id === $user?.id || (isShared && !chat?.write_access)) return;
				if (event.data.data?.typing) {
					if (!typingUsers.some((entry) => entry.id === sender.id))
						typingUsers = [...typingUsers, { id: sender.id, name: sender.name }];
					clearTimeout(typingUsersTimeout[sender.id]);
					typingUsersTimeout[sender.id] = setTimeout(() => removeTypingUser(sender.id), 5000);
				} else {
					removeTypingUser(sender.id);
				}
				return;
			}
			if (event.shared) {
				if (type === 'chat:messages') {
					removeTypingUser(event.user_id);
					mergeChatMessages(event.data.data);
					return;
				}
				if (type === 'chat:access' || type === 'chat:active') {
					if (type === 'chat:access') clearTyping();
					if (type === 'chat:access' || event.data.data?.active === false) await refreshChat();
					return;
				}
				if (!history.messages[event.message_id]) await refreshChat();
				if ($chatId !== event.chat_id) return;
			}
			if (type === 'chat:reload') {
				await loadChat();
				return;
			}
			if (type === 'chat:list') {
				return;
			}
			let message = history.messages[event.message_id];
			if (message) message = { ...message };

			if (message || type === 'confirmation' || type === 'input') {
				const data = event?.data?.data ?? null;

				queueMicrotask(() => bridge?.update());
				if (type === 'status') {
					if (message?.statusHistory) {
						message.statusHistory.push(data);
					} else {
						message.statusHistory = [data];
					}
				} else if (type === 'context_compaction') {
					if (data?.checkpoint_message_id && history.messages[data.checkpoint_message_id]) {
						history.messages[data.checkpoint_message_id].contextSummary = data.context_summary;
					}
					autoScrollToBottom();
				} else if (type === 'chat:active') {
					if (!data?.active) {
						taskIds = null;
						if ($chatId && !$temporaryChat && hasPendingAssistantLeaf(event?.message_id ?? null)) {
							await loadChat();
							// The message copy is stale after the reload.
							message = history.messages[event.message_id];
						}
						if ($chatId && !$temporaryChat) {
							updateLastReadAt($chatId);
						}
					}
				} else if (type === 'response:completion' || type === 'chat:completion') {
					if (type === 'response:completion') {
						responseCompletionEventHandler(data, message);
					} else {
						await chatCompletionEventHandler(data, message, event.chat_id, event.shared);
					}
					autoScrollToBottom();
				} else if (type === 'chat:tasks:cancel') {
					for (const interaction of browserInteractions) {
						if (interaction.messageId === event.message_id) {
							resolveBrowserInteraction(interaction, { status: 'cancelled', answers: {} });
						}
					}
					message.bridgeCancelled = true;
					bridgeCancellations.get(event.message_id)?.();
					if (data?.output) {
						message.output = data.output;
					}
					if (!event.shared && event.message_id === history.currentId) {
						taskIds = null;
						// Set all response messages to done
						for (const messageId of history.messages[message.parentId].childrenIds) {
							history.messages[messageId].done = true;
						}
						message.done = true;
						await processNextInQueue($chatId);
					} else {
						message.done = true;
					}
				} else if (type === 'chat:message:delta' || type === 'message') {
					message.content += data.content;
				} else if (type === 'chat:message' || type === 'replace') {
					message.content = data.content;
				} else if (type === 'chat:message:voice') {
					message.meta = { ...message.meta, voice: data.voice };
				} else if (type === 'chat:message:files' || type === 'files') {
					message.files = isTemporaryChatId(event.chat_id)
						? [...(message.files ?? []), ...data.files]
						: data.files;
				} else if (type === 'chat:message:tasks') {
					chatTasks = data.tasks;
				} else if (type === 'chat:message:embeds' || type === 'embeds') {
					message.embeds = data.embeds;

					// Auto-scroll to the embed once it's rendered in the DOM
					await tick();
					setTimeout(() => {
						const embedEl = document.getElementById(`${event.message_id}-embeds-container`);
						if (embedEl) {
							embedEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
						}
					}, 100);
				} else if (type === 'chat:message:error') {
					const responseCompleted = message.done;
					if (event.shared) {
						message.error = data.error;
						message.done = true;
					} else handleOpenAIError(data.error, message);
					if (!event.shared && !responseCompleted) {
						if (event.message_id === history.currentId) {
							await processNextInQueue(event.chat_id);
						}
					}
				} else if (type === 'chat:message:follow_ups') {
					message.followUps = data.follow_ups;

					if (shouldAutoScrollResponse()) {
						scrollToBottom('smooth');
					}
				} else if (type === 'chat:outlet') {
					// Outlet filter ran on backend — sync in-memory state
					const outletMessages = data.messages ?? [];
					for (const msg of outletMessages) {
						if (msg?.id && history.messages[msg.id]) {
							const existing = history.messages[msg.id];
							if (existing.content !== msg.content) {
								history.messages[msg.id] = {
									...existing,
									originalContent: existing.content,
									...msg
								};
							}
						}
					}
					history = history;
					return; // Patches history.messages directly; skip the trailing write-back.
				} else if (type === 'chat:message:favorite') {
					// Update message favorite status
					message.favorite = data.favorite;
				} else if (type === 'chat:title') {
					setChatTitle(event.chat_id, data);
					chatTitle.set(data);
					if (embedded && $chatId) {
						await onEmbeddedChatTitle?.($chatId, data);
					}
					await refreshChatList(localStorage.token);
					return; // The message copy is stale after the await; skip the trailing write-back.
				} else if (type === 'chat:tags') {
					chat = await getChatById(localStorage.token, $chatId);
					allTags.set(await getAllTags(localStorage.token));
					return;
				} else if (type === 'source' || type === 'citation') {
					if (data?.type === 'code_execution') {
						// Code execution; update existing code execution by ID, or add new one.
						if (!message?.code_executions) {
							message.code_executions = [];
						}

						const existingCodeExecutionIndex = message.code_executions.findIndex(
							(execution) => execution.id === data.id
						);

						if (existingCodeExecutionIndex !== -1) {
							message.code_executions[existingCodeExecutionIndex] = data;
						} else {
							message.code_executions.push(data);
						}

						message.code_executions = message.code_executions;
					} else {
						// Regular source.
						if (message?.sources) {
							message.sources.push(data);
						} else {
							message.sources = [data];
						}
					}
				} else if (type === 'notification') {
					const toastType = data?.type ?? 'info';
					const toastContent = data?.content ?? '';

					if (toastType === 'success') {
						toast.success(toastContent);
					} else if (toastType === 'error') {
						toast.error(toastContent);
					} else if (toastType === 'warning') {
						toast.warning(toastContent);
					} else {
						toast.info(toastContent);
					}
				} else if (type === 'confirmation') {
					eventCallback = cb;
					eventInteractionId = data.interaction_id ?? null;

					eventConfirmationInput = false;
					showEventConfirmation = true;
					eventConfirmationInputOptions = [];

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
				} else if (type === 'execute') {
					try {
						// Use Function constructor to evaluate code in a safer way
						const asyncFunction = new Function(`return (async () => { ${data.code} })()`);
						const result = await asyncFunction(); // Await the result of the async function

						if (cb) {
							cb(result);
						}
					} catch (error) {
						console.error('Error executing code:', error);
					}
				} else if (type === 'input') {
					eventCallback = cb;
					eventInteractionId = data.interaction_id ?? null;

					eventConfirmationInput = true;
					showEventConfirmation = true;

					eventConfirmationTitle = data.title;
					eventConfirmationMessage = data.message;
					eventConfirmationInputPlaceholder = data.placeholder;
					eventConfirmationInputValue = data?.value ?? '';
					eventConfirmationInputType = data?.input?.type ?? data?.type ?? '';
					eventConfirmationInputOptions = data?.input?.options ?? data?.options ?? [];
				} else if (machineEventName(type)) {
					machineEventHandler(type, data, message);
				} else {
					console.log('Unknown message type', data);
				}

				if (message) history.messages[event.message_id] = message;
			}
		} else {
			// Non-active chat completion: queue stays in the global store.
			// navigateHandler will process it when the user returns to that chat.
		}
	};

	const onMessageHandler = async (event: {
		origin: string;
		source: unknown;
		data: { type: string; text?: string; toolId?: string; error?: string | null };
	}) => {
		const isSameOrigin = event.origin === window.origin;
		const type = event.data?.type;

		// Prompt-driving types are trusted only same-origin, from our own embed iframes
		// (opaque srcdoc origin, submission still confirmed below) or via explicit opt-in.
		const promptTypes = ['input:prompt', 'input:prompt:submit', 'action:submit'];
		const isOwnEmbed = isEmbedWindow(event.source);
		const isTrusted =
			isSameOrigin || isOwnEmbed || ($settings?.iframeSandboxAllowSameOrigin ?? false);

		// Non-prompt message types are always restricted to same-origin only.
		if (!isSameOrigin && !promptTypes.includes(type)) {
			return;
		}

		// Prompt types from an untrusted cross-origin source are silently dropped.
		if (promptTypes.includes(type) && !isTrusted) {
			return;
		}

		const iframe = [...document.querySelectorAll('iframe')].find(
			(frame) => frame.contentWindow === event.source
		);
		const sourceChat = iframe?.closest('[data-chat]')?.getAttribute('data-chat') ?? 'main';
		if (sourceChat !== (embedded ? instanceId : 'main')) {
			return;
		}

		if (type === 'action:submit') {
			console.debug(event.data.text);

			if (prompt !== '') {
				if (isSameOrigin) {
					await tick();
					submitHandler(prompt);
				} else {
					eventConfirmationInput = false;
					eventConfirmationTitle = $i18n.t('Confirm Prompt from Embed');
					eventConfirmationMessage = prompt;
					eventInteractionId = null;
					eventCallback = async (confirmed: boolean) => {
						if (confirmed) {
							await tick();
							submitHandler(prompt);
						}
					};
					showEventConfirmation = true;
				}
			}
		}

		if (type === 'input:prompt') {
			console.debug(event.data.text);

			const inputElement = document.getElementById(inputId);

			if (inputElement) {
				messageInput?.setTextHandler(event.data.text);
				messageInput?.focus({ preventScroll: true });
			}
		}

		if (type === 'input:prompt:submit') {
			console.debug(event.data.text);

			if (event.data.text !== '') {
				if (isSameOrigin) {
					await tick();
					submitHandler(event.data.text);
				} else {
					eventConfirmationInput = false;
					eventConfirmationTitle = $i18n.t('Confirm Prompt from Embed');
					eventConfirmationMessage = event.data.text;
					eventInteractionId = null;
					eventCallback = async (confirmed: boolean) => {
						if (confirmed) {
							await tick();
							submitHandler(event.data.text);
						}
					};
					showEventConfirmation = true;
				}
			}
		}
	};

	const stopAudio = () => {
		try {
			speechSynthesis.cancel();
			$audioQueue?.stop();
		} catch {}
	};

	const hasPendingAssistantLeaf = (messageId: string | null = null) =>
		(messageId ? [history.messages[messageId]] : Object.values(history.messages)).some(
			(message: any) =>
				message?.role === 'assistant' && !message.done && (message.childrenIds?.length ?? 0) === 0
		);

	const handleSocketConnect = async () => {
		clearTyping();
		if (!$chatId || !$socket?.id) return;
		if (isTemporaryChatId($chatId)) {
			const id = $chatId;
			try {
				const result = await resumeTemporaryChat(localStorage.token, id, $socket.id);
				if ($chatId !== id) return;
				taskIds = result.task_ids.length ? result.task_ids : null;
				for (const stream of result.streams) {
					const message = history.messages[stream.message_id];
					if (message && !message.done) message.output = stream.output;
				}

				if (!taskIds) {
					for (const message of Object.values(history.messages) as any[]) {
						if (message.role === 'assistant' && !message.done) {
							message.done = true;
							message.error = { content: $i18n.t('Connection lost. Please retry.') };
						}
					}
				}
				history = history;
			} catch (error) {
				toast.error(getErrorMessage(error));
			}
			return;
		}
		joinedChatId = '';
		syncChatRoom($socket, $chatId, $temporaryChat);
		const id = $chatId;
		const tasks = await getTaskIdsByChatId(localStorage.token, id).catch(() => null);
		if ($chatId !== id || !tasks) return;
		taskIds = tasks.task_ids?.length ? tasks.task_ids : null;
		if (!taskIds && hasPendingAssistantLeaf()) {
			// A server restart can leave unfinished messages without a completion event.
			const loaded = await loadChat();
			if (loaded && $chatId === id) await processNextInQueue(id);
		}
	};

	onMount(() => {
		loading = true;
		console.log('mounted');
		if (!embedded && appLayout) appLayout.initNewChat = initNewChat;
		window.addEventListener('message', onMessageHandler);
		$socket?.on('events', chatEventHandler);
		$socket?.on('connect', handleSocketConnect);
		$socket?.on('disconnect', clearTyping);
		$socket?.on('disconnect', clearPresence);
		$socket?.on('disconnect', cancelBrowserInteractions);

		$audioQueue?.destroy();

		const audioQueueInstance = new AudioQueue(
			audioElement,
			() => $settings.responseAutoPlayback ?? false
		);
		audioQueue.set(audioQueueInstance);

		const selectedFolderSubscribe = selectedFolder.subscribe(async (folder) => {
			await tick();
			// Navigation applies defaults in initNewChat; only explicit settings edits reach here.
			if (
				loading ||
				history.currentId ||
				!folder ||
				mainChatHref !== `/folders/${folder.id}` ||
				equal(appliedFolderDefaults, folder.data)
			)
				return;
			appliedFolderDefaults = folder.data;
			applyFolderMachine(folder);
			if (machineIdOf(folder.data)) await refreshAgentModels(folder);
			if (
				history.currentId ||
				$selectedFolder?.id !== folder.id ||
				appliedFolderDefaults !== folder.data
			)
				return;
			selectedModels = normalizeSelectedModels(folder.data?.model_ids ?? []);
		});

		const storageChatInput = sessionStorage.getItem(
			getChatInputKey(chatIdProp || embeddedDraftKey)
		);

		const init = async () => {
			if (!chatIdProp) {
				loading = false;
				await tick();
			}

			if (storageChatInput) {
				prompt = '';
				messageInput?.setText('');

				files = [];
				selectedToolIds = [];
				selectedSkillIds = [];
				selectedFilterIds = [];
				webSearchEnabled = false;
				imageGenerationEnabled = false;
				codeInterpreterEnabled = false;
				selectedImageModelId = '';
				videoGenerationEnabled = false;
				selectedVideoModelId = '';

				await restoreChatInput(storageChatInput);
			}

			if (!$mobile) messageInput?.focus({ preventScroll: true });
		};
		if (embedded) init();
		else
			void tick().then(() => {
				if (!routeInitialized) routeChanged = true;
			});

		return () => {
			try {
				cancelBrowserInteractions();
				clearTimeout(saveControlsTimer);
				saveControls();
				if (chatIdProp && !$temporaryChat) {
					updateLastReadAt(chatIdProp);
				}
				if (appLayout?.initNewChat === initNewChat) delete appLayout.initNewChat;
				selectedFolderSubscribe();
				if (!embedded) selectedFolder.set(null);

				// Clear the selected chat when leaving the chat surface (e.g. navigating
				// to the admin panel), otherwise the previously-viewed chat stays selected
				// in the sidebar and deleting/archiving it wrongly navigates away.
				clearTyping();
				clearPresence();
				if (joinedChatId && $socket?.connected)
					$socket.emit('events:chat', { chat_id: joinedChatId, data: { type: 'leave' } });
				joinedChatId = '';
				if (embedded && $chatId) {
					if ($temporaryChat) stopTasksByChatId(localStorage.token, $chatId).catch(console.error);
					openEmbeddedChatIds.update((ids) => {
						const next = new Set(ids);
						next.delete($chatId);
						return next;
					});
				}
				chatId.set('');
				chatTitle.set('');

				window.removeEventListener('message', onMessageHandler);
				$socket?.off('events', chatEventHandler);
				$socket?.off('connect', handleSocketConnect);
				$socket?.off('disconnect', clearTyping);
				$socket?.off('disconnect', clearPresence);
				$socket?.off('disconnect', cancelBrowserInteractions);
				audioQueueInstance?.destroy();
				audioQueue.set(null);
			} catch (e) {
				console.error(e);
			}
		};
	});

	// File upload functions

	const uploadGoogleDriveFile = async (fileData) => {
		console.log('Starting uploadGoogleDriveFile with:', {
			id: fileData.id,
			name: fileData.name,
			url: fileData.url,
			headers: {
				Authorization: `Bearer ${token}`
			}
		});

		// Validate input
		if (!fileData?.id || !fileData?.name || !fileData?.url || !fileData?.headers?.Authorization) {
			throw new Error('Invalid file data provided');
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: fileData.url,
			name: fileData.name,
			collection_name: '',
			status: 'uploading',
			error: '',
			itemId: tempItemId,
			size: 0
		};

		try {
			files = [...files, fileItem];
			console.log('Processing web file with URL:', fileData.url);

			// Configure fetch options with proper headers
			const fetchOptions = {
				headers: {
					Authorization: fileData.headers.Authorization,
					Accept: '*/*'
				},
				method: 'GET'
			};

			// Attempt to fetch the file
			console.log('Fetching file content from Google Drive...');
			const fileResponse = await fetch(fileData.url, fetchOptions);

			if (!fileResponse.ok) {
				const errorText = await fileResponse.text();
				throw new Error(`Failed to fetch file (${fileResponse.status}): ${errorText}`);
			}

			// Get content type from response
			const contentType = fileResponse.headers.get('content-type') || 'application/octet-stream';
			console.log('Response received with content-type:', contentType);

			// Convert response to blob
			console.log('Converting response to blob...');
			const fileBlob = await fileResponse.blob();

			if (fileBlob.size === 0) {
				throw new Error('Retrieved file is empty');
			}

			console.log('Blob created:', {
				size: fileBlob.size,
				type: fileBlob.type || contentType
			});

			// Create File object with proper MIME type
			const file = new File([fileBlob], fileData.name, {
				type: fileBlob.type || contentType
			});

			console.log('File object created:', {
				name: file.name,
				size: file.size,
				type: file.type
			});

			if (file.size === 0) {
				throw new Error('Created file is empty');
			}

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

			// Upload file to server
			console.log('Uploading file to server...');
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (!uploadedFile) {
				throw new Error('Server returned null response for file upload');
			}

			console.log('File uploaded successfully:', uploadedFile);

			// Update file item with upload results
			fileItem.status = 'uploaded';
			fileItem.file = uploadedFile;
			fileItem.id = uploadedFile.id;
			fileItem.size = file.size;
			fileItem.collection_name = uploadedFile?.meta?.collection_name;
			fileItem.url = `${uploadedFile.id}`;

			files = files;
			toast.success($i18n.t('File uploaded successfully'));
		} catch (e) {
			console.error('Error uploading file:', e);
			fileItem.status = 'error';
			fileItem.error = e.message || `${e}`;
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error(
				$i18n.t('Error uploading file: {{error}}', {
					error: e.message || 'Unknown error'
				})
			);
		}
	};

	const uploadWeb = async (urls) => {
		if ($user?.role !== 'admin' && !($user?.permissions?.chat?.web_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload web content.'));
			return;
		}

		if (!Array.isArray(urls)) {
			urls = [urls];
		}

		// Create file items first
		const fileItems = urls.map((url) => ({
			type: 'text',
			name: url,
			collection_name: '',
			status: 'uploading',
			context: 'full',
			url,
			error: ''
		}));

		// Display all items at once
		files = [...files, ...fileItems];

		for (const fileItem of fileItems) {
			try {
				const res = await processUrl(localStorage.token, fileItem.url);

				if (res) {
					const uploadedFile = res.file;
					fileItem.status = 'uploaded';
					fileItem.name = res.name ?? fileItem.name;
					fileItem.collection_name = res.collection_name;

					if (res.type === 'image' && uploadedFile) {
						fileItem.type = 'image';
						fileItem.file = uploadedFile;
						fileItem.id = uploadedFile.id;
						fileItem.url = `${uploadedFile.id}`;
						fileItem.content_type = uploadedFile.meta?.content_type;
						fileItem.size = uploadedFile.meta?.size;
					} else if (res.type === 'file' && uploadedFile) {
						fileItem.type = 'file';
						fileItem.file = uploadedFile;
						fileItem.id = uploadedFile.id;
						fileItem.url = `${uploadedFile.id}`;
						fileItem.content_type = uploadedFile.meta?.content_type;
						fileItem.size = uploadedFile.meta?.size;
						fileItem.collection_name =
							res.collection_name ??
							uploadedFile.meta?.collection_name ??
							uploadedFile.collection_name;
					} else {
						fileItem.type = 'text';
						fileItem.file = {
							data: {
								content: res.content
							},
							meta: {
								name: res.name ?? fileItem.name,
								source: res.url ?? fileItem.url
							}
						};
					}
				}

				files = [...files];
			} catch (e) {
				fileItem.status = 'error';
				fileItem.error = `${e}`;
				files = files.filter((f) => f.name !== fileItem.name);
				toast.error(`${e}`);
			}
		}

		await onUpdate();
	};

	const onUpdate = async ({ file }: { file?: any } = {}) => {
		if (file?.itemId) {
			chatRequestQueues.update((q) => ({
				...q,
				[$chatId]: (q[$chatId] ?? []).map((message) =>
					(message.files ?? []).some((item) => item.itemId === file.itemId)
						? {
								...message,
								files: message.files.map((item) => (item.itemId === file.itemId ? file : item))
							}
						: message
				)
			}));
		}

		await processNextInQueue($chatId);
	};

	const onUpload = async (event) => {
		const { type, data } = event;

		if (type === 'google-drive') {
			await uploadGoogleDriveFile(data);
		} else if (type === 'web') {
			await uploadWeb(data);
		}
	};

	const onHistoryChange = (history) => {
		if (history) {
			bridge?.update();
			clearTimeout(contentsRAF);
			contentsRAF = setTimeout(() => {
				getContents();
				contentsRAF = null;
			}, 0);
		} else {
			artifacts.set([]);
		}
	};

	$: onHistoryChange(history);

	let callMode = 'current';
	let bridge: RealtimeCall;
	let releaseCallWakeLock = () => {};
	const updateCallWakeLock = (active: boolean) => {
		releaseCallWakeLock();
		releaseCallWakeLock = active ? acquireWakeLock() : () => {};
	};
	$: callInProgress =
		($voiceCall && callMode === 'current') || !!(bridge?.connected || bridge?.connecting);
	$: updateCallWakeLock(callInProgress);
	onDestroy(() => releaseCallWakeLock());

	const bridgeCancellations = new Map<string, () => void>();
	const visibleMessageText = (message: any) =>
		getOutputText(message?.output) || removeAllDetails(message?.content ?? '');

	const generateVoiceChatMetadata = async (
		_chatId: string,
		modelId: string,
		content: string,
		initialTitle: string
	) => {
		const token = localStorage.token;
		const messages = [{ role: 'user', content }];
		const autoTitle = $settings?.title?.auto ?? true;
		const autoTags = $settings?.autoTags ?? true;
		const title = autoTitle
			? await generateTitle(token, modelId, messages, _chatId).catch((error) => {
					console.error('Could not generate voice chat title', error);
					return null;
				})
			: null;
		const savedChat = await getChatById(token, _chatId);
		if (savedChat.title === initialTitle) {
			const updated = await updateChatById(token, _chatId, {
				title: title || content.slice(0, 100)
			});
			if ($chatId === _chatId) {
				chatTitle.set(updated.title);
				if (embedded) await onEmbeddedChatTitle?.(_chatId, updated.title);
			}
			await refreshChatList(token);
		}
		if (autoTags) {
			const tags = await generateTags(token, modelId, messages, _chatId);
			for (const tag of tags) await addTagById(token, _chatId, tag);
			allTags.set(await getAllTags(token));
		}
	};

	const addVoiceMessage = async (
		role: string,
		content: string,
		voice: any,
		parentId: string | null = history.currentId
	) => {
		const branch = createMessagesList(history, history.currentId);
		let parentIndex = branch.findIndex((entry) => entry.id === parentId);
		// A chat answer can have been inserted while this spoken reply was being generated.
		// Keep the reply on that branch, before the next user turn, rather than losing it as a sibling.
		if (role === 'assistant' && parentIndex >= 0) {
			while (branch[parentIndex + 1]?.role === 'assistant') parentIndex++;
			parentId = branch[parentIndex].id;
		}
		const nextMessage = parentIndex >= 0 ? branch[parentIndex + 1] : null;
		const id = uuidv4();
		const message = {
			id,
			parentId,
			childrenIds: [] as string[],
			role,
			content,
			done: true,
			timestamp: Math.floor(Date.now() / 1000),
			meta: { voice },
			...(role === 'assistant' ? { model: voice.model, modelName: voice.model, modelIdx: 0 } : {})
		};
		const changedMessages: Record<string, any> = { [id]: message };
		history.messages[id] = message;
		if (parentId && history.messages[parentId]) {
			history.messages[parentId].childrenIds.push(id);
			// A second transcript can arrive before the first spoken reply finishes.
			// Insert that reply before the next user message without switching branches.
			if (role === 'assistant' && nextMessage?.role === 'user') {
				nextMessage.parentId = id;
				message.childrenIds.push(nextMessage.id);
				history.messages[parentId].childrenIds = history.messages[parentId].childrenIds.filter(
					(childId: string) => childId !== nextMessage.id
				);
				changedMessages[nextMessage.id] = nextMessage;
			}
		}
		if (history.currentId === parentId) history.currentId = id;
		history = history;
		if (!$chatId) {
			const modelId = selectedModelIds[0];
			const _chatId = await initChatHandler(history);
			if (_chatId && !$temporaryChat) {
				// Realtime replies need no chat completion; start metadata work at chat creation.
				void generateVoiceChatMetadata(_chatId, modelId, content, chat.title).catch((error) => {
					console.error('Could not save voice chat metadata', error);
				});
			}
		} else if (!$temporaryChat) {
			// Patch only the new message, so a running backend turn keeps its current output.
			await updateChatById(localStorage.token, $chatId, {
				history: { currentId: history.currentId, messages: changedMessages }
			});
		}
		return id;
	};

	const saveVoice = async (id: string, voice: any) => {
		const message = history.messages[id];
		if (!message) return;
		const previous = message.meta?.voice ?? {};
		const speech = new Map((previous.speech ?? []).map((item: any) => [item.item_id, item]));
		for (const item of voice.speech ?? []) speech.set(item.item_id, item);
		const merged = { ...previous, ...voice, speech: [...speech.values()] };
		message.meta = { ...message.meta, voice: merged };
		history = history;
		if ($chatId && !$temporaryChat) {
			const response = await fetch(`${WEBUI_API_BASE_URL}/chats/${$chatId}/messages/${id}`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ voice: merged })
			});
			if (!response.ok) throw new Error('Could not save voice metadata');
		}
	};

	onMount(() => {
		bridge = new RealtimeCall({
			context: () => {
				const model =
					selectedModelIds.length === 1
						? ($models ?? []).find((model) => model.id === selectedModelIds[0])
						: null;
				return {
					chatId: isTemporaryChatId($chatId) ? undefined : $chatId || undefined,
					modelId: model ? model.id : '',
					machineId: $selectedMachineId || undefined,
					voiceModel: $config?.audio?.realtime?.model,
					voice: model?.info?.meta?.voice?.voice || $config?.audio?.realtime?.voice,
					messages: createMessagesList(history, history.currentId).map((message) => {
						const voice = message.meta?.voice;
						const spoken = voice && message.model === voice.model && !message.output?.length;
						const state = getBridgeTurnState(message);
						const speech = !spoken
							? (voice?.speech ?? [])
									.map((item: any) => item.transcript)
									.filter(Boolean)
									.join('\n')
							: '';
						let content = visibleMessageText(message);
						if (message.role === 'assistant') {
							const source = spoken
								? 'Historical voice transcript, not current task status'
								: 'Chat model';
							content = `[${source}; message_id=${message.id}; state=${state}]\n${state === 'completed' ? content : ''}`;
							if (speech)
								content += `\n[Historical voice transcript, not current task status]\n${speech}`;
						}
						return { role: message.role, content };
					})
				};
			},
			addMessage: addVoiceMessage,
			submit: submitHandler,
			message: (id) => history.messages[id],
			visibleText: visibleMessageText,
			saveVoice,
			stop: async (id) => {
				const message = history.messages[id];
				if (!message || message.bridgeCancelled) return;
				let timer: ReturnType<typeof setTimeout> | undefined;
				const settled = new Promise<void>((resolve, reject) => {
					bridgeCancellations.set(id, resolve);
					timer = setTimeout(
						() => reject(new Error('Backend cancellation was not confirmed')),
						15000
					);
				});
				try {
					await Promise.all([stopResponse(false, id), settled]);
				} finally {
					clearTimeout(timer);
					bridgeCancellations.delete(id);
				}
			},
			change: () => {
				bridge = bridge;
			},
			error: (message) => toast.error(message)
		});
		return () => bridge?.end();
	});
	// The layout keeps this component mounted; route changes update only the main pane.
	let routeInitialized = false;
	const followRoute = async () => {
		const preserveTabs = routeInitialized;
		routeInitialized = true;
		await tick();
		if ($page.route.id === '/(app)/c/[id]') {
			chatIdProp = $page.params.id ?? '';
		} else if ($page.params.folderId || $page.url.pathname === '/') {
			selectedFolder.set($page.data.folder ?? null);
			// On a first load the input is on screen before set-up, which resets it;
			// what was typed there goes back in.
			const typed = preserveTabs ? '' : prompt;
			await initNewChat({ preserveTabs, url: $page.url });
			if (typed) messageInput?.setText(typed);
		} else if (initialPage) {
			if (!preserveTabs) await initNewChat();
			loading = false;
			tabs?.openPageTab({ href: initialPage, label: '' });
		}
	};
	// Set-up checks its choices against the model list, so a page is followed once the list is in.
	let routeChanged = false;
	$: if (routeChanged && $models !== null) {
		routeChanged = false;
		void followRoute();
	}
	// A chat opened by link needs no model list, so its request starts before the list is in.
	let pendingChatRequest: { id: string; promise: ReturnType<typeof getChatById> } | null = null;
	$: if (routeChanged && $models === null && $page.params.id !== pendingChatRequest?.id) {
		pendingChatRequest =
			$page.route.id === '/(app)/c/[id]'
				? { id: $page.params.id, promise: getChatById(localStorage.token, $page.params.id) }
				: null;
		pendingChatRequest?.promise.catch(() => {});
	}
	afterNavigate(() => {
		routeChanged = !embedded;
		stopAudio();
	});
	beforeNavigate(() => {
		if (!loading && !$temporaryChat) void saveDraft(getChatInputDraft(), getDraftChatId(), false);
		bridge?.end();
		pendingUrlActions = null;
	});
	$: if (!$user && (bridge?.connected || bridge?.connecting)) bridge.end();
	$: if (selectedModelIds && $models && $config) bridge?.syncModel();

	const dispatchCallOverlayAudio = (message, final = false) => {
		if (message.error || !$voiceCall || callMode !== 'current') {
			return;
		}

		const ttsSplitOn = $config?.audio?.tts?.split_on ?? 'punctuation';
		const messageContentParts = getMessageContentParts(
			getOutputText(message?.output) || removeAllDetails(message?.content ?? ''),
			ttsSplitOn
		);

		const sentContentPartCount = message.ttsSentContentPartCount ?? 0;
		const nextContentParts = (final ? messageContentParts : messageContentParts.slice(0, -1)).slice(
			sentContentPartCount
		);
		const pendingContentPartIndex = nextContentParts.findIndex(
			(content) =>
				!final &&
				ttsSplitOn === 'punctuation' &&
				(content.split(/\s+/).length < 4 || content.length < 50)
		);
		const dispatchContentParts =
			pendingContentPartIndex === -1
				? nextContentParts
				: nextContentParts.slice(0, pendingContentPartIndex);

		dispatchContentParts.forEach((content) => {
			eventTarget.dispatchEvent(
				new CustomEvent('chat', {
					detail: {
						id: message.id,
						content
					}
				})
			);
		});
		message.ttsSentContentPartCount = sentContentPartCount + dispatchContentParts.length;
	};

	const getContents = () => {
		const messages = history ? createMessagesList(history, history.currentId) : [];
		let contents: { type: string; content: string }[] = [];
		messages.forEach((message) => {
			if (message?.role !== 'user') {
				const messageContent =
					getOutputText(message?.output) || removeAllDetails(message?.content ?? '');
				if (!messageContent.trim()) {
					return;
				}

				const { codeBlocks: codeBlocks, htmlGroups: htmlGroups } =
					getCodeBlockContents(messageContent);

				if (htmlGroups && htmlGroups.length > 0) {
					htmlGroups.forEach((group) => {
						const renderedContent = `
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
							<${''}style>
								body {
									background-color: white; /* Ensure the iframe has a white background */
								}

								${group.css}
							</${''}style>
                        </head>
                        <body>
                            ${group.html}

							<${''}script>
                            	${group.js}
							</${''}script>
                        </body>
                        </html>
                    `;
						contents = [...contents, { type: 'iframe', content: renderedContent }];
					});
				} else {
					// Check for SVG content
					for (const block of codeBlocks) {
						if (block.lang === 'svg' || (block.lang === 'xml' && block.code.includes('<svg'))) {
							contents = [...contents, { type: 'svg', content: block.code }];
						}
					}
				}
			}
		});

		artifacts.set(contents);
	};

	// Web functions

	const openCallOverlay = () => {
		if (isShared) return;

		if (!($user?.role === 'admin' || ($user?.permissions?.chat?.call ?? true))) {
			return;
		}

		if (
			$user?.role !== 'admin' &&
			!($user?.permissions?.chat?.stt ?? true) &&
			!$config?.audio?.realtime?.enabled
		) {
			return;
		}

		if (selectedModels.length > 1) {
			toast.error($i18n.t('Select only one model to call'));
			return;
		}

		if (
			!bridge?.connected &&
			!bridge?.connecting &&
			!$config?.audio?.realtime?.enabled &&
			$config?.audio?.stt?.engine === 'web'
		) {
			toast.error($i18n.t('Call feature is not supported when using Web STT engine'));
			return;
		}

		voiceCall.set(true);
		showTabs.set(true);
	};

	const initNewChat: NonNullable<AppLayoutContext['initNewChat']> = async ({
		preserveTabs = false,
		temporary,
		url = initialPage || preserveTabs ? undefined : $page.url
	} = {}) => {
		if (!loading && !$temporaryChat) void saveDraft(getChatInputDraft(), getDraftChatId(), false);
		const destinationFolder = $selectedFolder
			? (structuredClone($selectedFolder) as FolderDetails)
			: null;
		const searchParams = url?.searchParams ?? new URLSearchParams();
		mainChatHref = '/';
		if (url?.pathname === '/') {
			mainChatHref += url.search + url.hash;
		}
		if (destinationFolder?.id) mainChatHref = `/folders/${destinationFolder.id}`;

		if (preserveTabs) tabs?.carryPagesToNewChat();
		else tabs?.resetForChatSwitch();
		loading = true;
		if (
			!embedded &&
			($showTabs === 'comments' || $showTabs === 'chat' || typeof $showTabs === 'object')
		)
			showTabs.set(false);
		const signal = startChatLoad();
		appliedFolderDefaults = destinationFolder?.data;
		modelDefaults = null;
		clearTimeout(saveControlsTimer);
		await saveControls();
		if (signal.aborted) return;
		if ($chatId) machineContext = null;
		cancelBrowserInteractions();
		bridge?.end();
		console.log('initNewChat');
		resetWebSearchConfirmation();

		// Mark the outgoing chat as read before resetting; in-place created chats
		// keep chatIdProp undefined, so navigateHandler never marks them read.
		if ($chatId && !$temporaryChat) {
			updateLastReadAt($chatId);
		}

		const param = searchParams.get('temporary-chat');
		temporaryChat.set(
			isTemporaryEnforced() ||
				(!!canUseTemporaryChats({ user: $user, config: $config }) &&
					(temporary ?? (param ? param === 'true' : !!$settings?.temporaryChatByDefault)))
		);

		const availableModels = ($models ?? [])
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

		const defaultModels = normalizeSelectedModels();

		let modelSearch = '';
		const openModelSelectorWithSearch = async (modelId: string) => {
			const modelSelectorButton = document.getElementById('model-selector-model-button');
			modelSelectorButton?.click();

			await tick();

			const modelSelectorInput = document.getElementById(
				'model-search-input'
			) as HTMLInputElement | null;
			if (modelSelectorInput) {
				modelSelectorInput.focus();
				modelSelectorInput.value = modelId;
				modelSelectorInput.dispatchEvent(new Event('input', { bubbles: true }));
			}
		};

		if (searchParams.get('models') || searchParams.get('model')) {
			const urlModels = (searchParams.get('models') || searchParams.get('model') || '')?.split(',');

			if (urlModels.length === 1) {
				if (!($models ?? []).find((m) => m.id === urlModels[0])) {
					// Model not found; open model selector and prefill
					modelSearch = urlModels[0];
				} else {
					// Model found; set it as selected
					selectedModels = urlModels;
				}
			} else {
				// Multiple models; set as selected
				selectedModels = urlModels;
			}

			// Unavailable models filtering
			selectedModels = selectedModels.filter(
				(modelId) =>
					modelId.startsWith('agent:') || ($models ?? []).map((m) => m.id).includes(modelId)
			);
		} else {
			if (destinationFolder) {
				// A configured folder machine overrides the previous selection.
				applyFolderMachine(destinationFolder);
				if (machineIdOf(destinationFolder.data)) {
					await refreshAgentModels(destinationFolder, signal);
					if (signal.aborted) return;
				}
				selectedModels = normalizeSelectedModels(destinationFolder.data?.model_ids ?? []);
			} else {
				if (sessionStorage.selectedModels) {
					// Set from session storage (temporary selection)
					selectedModels = JSON.parse(sessionStorage.selectedModels);
					sessionStorage.removeItem('selectedModels');
				} else {
					if ($settings?.models) {
						// Set from user settings
						selectedModels = $settings?.models;
					} else if (defaultModels && defaultModels.length > 0) {
						// Set from default models
						selectedModels = defaultModels;
					}
				}
			}

			// Unavailable & hidden models filtering
			selectedModels = normalizeSelectedModels(selectedModels);
		}

		// Ensure at least one model is selected
		if (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === '')) {
			if (availableModels.length > 0) {
				if (defaultModels && defaultModels.length > 0) {
					selectedModels = defaultModels.filter((modelId) => availableModels.includes(modelId));
				}

				if (
					selectedModels.length === 0 ||
					(selectedModels.length === 1 && selectedModels[0] === '')
				) {
					// Only fall back to first available model if default models didn't resolve
					selectedModels = [availableModels?.at(0) ?? ''];
				}
			} else {
				selectedModels = [''];
			}
		}

		if (!($user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true))) {
			selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
		}

		if ($mobile) {
			await showTabs.set(false);
		}
		await voiceCall.set(false);

		if (!embedded && !preserveTabs && $page.url.pathname.includes('/c/')) {
			window.history.replaceState(window.history.state, '', `/`);
		}

		autoScroll = true;

		// resetInput() must stay last: the selected model's defaults override the draft's selection.
		prompt = '';
		files = [];
		const chatInputPrompt = (await restoreChatInput(sessionStorage.getItem(getChatInputKey())))
			? prompt
			: null;
		if (signal.aborted) return;
		// Clear the previous chat first, so its id and history don't affect the new chat's defaults.
		await chatId.set('');
		if (preserveTabs) {
			chatIdProp = '';
			loadedChatIdProp = '';
			chat = null;
			tags = [];
			serverContextUsage = null;
		}
		await chatTitle.set('');

		history = {
			messages: {},
			currentId: null
		};

		chatFiles = [];
		params = {};
		chatVariables = {};
		taskIds = null;
		chatTasks = [];

		await resetInput();
		if (signal.aborted) return;
		// A chat opened or a message sent in the meantime keeps its id and history
		if ($chatId || history.currentId) {
			loading = false;
			return;
		}

		// Apply folder defaults after restoring the draft and model defaults.
		applyFolderMachine(destinationFolder);

		const youtube = searchParams.get('youtube');
		const loadUrl = searchParams.get('load-url');
		const urls = [
			...(youtube ? [`https://www.youtube.com/watch?v=${youtube}`] : []),
			...(loadUrl ? [loadUrl] : [])
		];
		const call = searchParams.get('call') === 'true' || searchParams.get('voice') === 'true';
		pendingUrlActions = urls.length || call ? { urls, call } : null;

		if (searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		if (searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

		if (searchParams.get('video-generation') === 'true') {
			videoGenerationEnabled = true;
		}

		if (searchParams.get('code-interpreter') === 'true') {
			codeInterpreterEnabled = true;
		}

		if (searchParams.get('tools')) {
			selectedToolIds = searchParams
				.get('tools')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id && ($tools ?? []).find((t) => t.id === id));
		} else if (searchParams.get('tool-ids')) {
			selectedToolIds = searchParams
				.get('tool-ids')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id && ($tools ?? []).find((t) => t.id === id));
		}

		// Restore tool selection after OAuth redirect
		const pendingToolId = sessionStorage.getItem('pendingOAuthToolId');
		if (pendingToolId) {
			sessionStorage.removeItem('pendingOAuthToolId');
			if (!selectedToolIds.includes(pendingToolId) && !isSystemOAuthTool(pendingToolId)) {
				selectedToolIds = [...selectedToolIds, pendingToolId];
			}
		}

		if (signal.aborted) return;
		if (preserveTabs) tabs?.focusMainChat();
		loading = false;
		await tick();
		if (signal.aborted) return;
		// The new-chat input stays mounted through set-up, so set its text either way.
		messageInput?.setText(chatInputPrompt ?? '');
		if (modelSearch) await openModelSelectorWithSearch(modelSearch);

		// Consume call requests or the acknowledged Tether handoff.
		if ($desktopEvent && (!$desktopEvent.handoff || !embedded)) {
			const event = $desktopEvent;
			desktopEvent.set(null);

			if (event.handoff && !event.handoff.isCurrent()) {
				event.handoff.complete('The signed-in account changed. Try again from Tether.');
			} else if (event.type === 'call' || event.type === 'voice') {
				openCallOverlay();
				event.handoff?.complete(
					$voiceCall
						? undefined
						: 'Voice mode is unavailable. Check your model, permissions and voice settings in WebUI.'
				);
			} else if (event.type === 'query') {
				if (!messageInput) {
					event.handoff.complete('The WebUI composer is not ready. Send again from Spotlight.');
				} else {
					// Replace the restored new-chat draft; do not mix in its old attachments.
					files = event.data.files.map((file) => ({
						type: 'image',
						url: file.dataUrl,
						name: file.name
					}));
					messageInput.setText(event.data.query ?? '');
					await tick();
					if (event.handoff.isCurrent()) {
						event.handoff.complete();
						void submitHandler(event.data.query ?? '');
					} else {
						event.handoff.complete('The handoff expired. Send again from Spotlight.');
					}
				}
			}
		} else if (searchParams.get('q')) {
			const q = searchParams.get('q') ?? '';

			messageInput?.setTextHandler(q);
		}

		selectedModels = selectedModels.map((modelId) =>
			modelId.startsWith('agent:') || ($models ?? []).map((m) => m.id).includes(modelId)
				? modelId
				: ''
		);

		await tick();
		if (!$mobile) messageInput?.focus({ preventScroll: true });
	};

	const loadChat = async (signal = startChatLoad()) => {
		if (chatIdProp && chatIdProp !== $chatId) tabs?.resetForChatSwitch();
		if (chatIdProp && chatIdProp !== $chatId) {
			machineContext = null;
			history = { messages: {}, currentId: null };
		}
		const initialHistory = { ...history, messages: { ...history.messages } };
		noteChatDebug('loadChat start');
		// chatIdProp is empty for chats started from the home page (URL set via replaceState)
		chatId.set(chatIdProp || $chatId);
		noteChatDebug('loadChat set active chat id');

		if ($temporaryChat) {
			noteChatDebug('loadChat disabling temporary chat');
			temporaryChat.set(false);
		}

		const id = $chatId;
		const request =
			pendingChatRequest?.id === id
				? pendingChatRequest.promise
				: getChatById(localStorage.token, id, signal);
		pendingChatRequest = null;
		const loadedChat = await request.catch(async (error) => {
			if (tabbed && !signal.aborted) toast.error(`${error}`);
			console.error('[note-chat] getChatById failed', {
				chatIdProp,
				activeChatId: $chatId,
				error
			});
			return null;
		});
		if (signal.aborted) return;
		noteChatDebug('getChatById completed', {
			found: !!loadedChat,
			chatId: loadedChat?.id,
			hasChatPayload: !!loadedChat?.chat,
			title: loadedChat?.title
		});

		if (loadedChat) {
			const loadedTags = await getTagsById(localStorage.token, id, signal).catch(async (error) => {
				console.warn('[note-chat] getTagsById failed; continuing without tags', {
					chatIdProp,
					activeChatId: $chatId,
					error
				});
				return [];
			});
			if (signal.aborted) return;
			chat = loadedChat;
			tags = loadedTags;
			noteChatDebug('getTagsById completed', { tagCount: tags?.length ?? 0 });

			const chatContent = chat.chat;
			chatVariables = chat?.variables ?? {};

			if (chatContent) {
				noteChatDebug('chat payload found', {
					models: chatContent?.models,
					hasHistory: !!chatContent?.history,
					messageCount: Object.keys(chatContent?.history?.messages ?? {}).length
				});

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];
				if ($machines === null) {
					const servers = await getMachines(localStorage.token);
					if (signal.aborted) return;
					machines.set(servers);
				}
				const machineId = machineIdOf(chatContent);
				selectedMachineId.set(machineId && isMachineAvailable(machineId) ? machineId : null);
				machineContext =
					$selectedMachineId &&
					$selectedMachineId === machineId &&
					typeof chatContent.working_directory === 'string'
						? { machineId: $selectedMachineId, currentDirectory: chatContent.working_directory }
						: null;
				if (selectedModels[0]?.startsWith('agent:')) {
					if ($selectedMachineId) {
						const environment = getAgentEnvironment();
						if (
							!environment ||
							environment !== loadedAgentEnvironment?.key ||
							$models !== loadedAgentEnvironment?.models
						) {
							await refreshAgentModels(null, signal);
						}
					} else selectedModels = selectedModels.filter((modelId) => !modelId.startsWith('agent:'));
				}

				if (signal.aborted) return;

				// An empty model list is not evidence that the chat's models are gone.
				if (($models ?? []).length > 0) {
					selectedModels = selectedModels.filter(
						(modelId) =>
							modelId.startsWith('agent:') || ($models ?? []).map((m) => m.id).includes(modelId)
					);
				}

				if (!($user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true))) {
					selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
				}
				if (
					selectedModels.length === 0 ||
					(selectedModels.length === 1 && selectedModels[0] === '')
				) {
					selectedModels = normalizeSelectedModels(selectedModels);
					noteChatDebug('normalized empty selected models after load', { selectedModels });
				}

				chatContent.history ??= convertMessagesToHistory(chatContent.messages);
				// Keep live updates received while the chat and tags were loading.
				for (const [id, message] of Object.entries(history.messages)) {
					if (initialHistory.messages[id] !== message)
						chatContent.history.messages[id] = { ...chatContent.history.messages[id], ...message };
				}
				if (history.currentId !== initialHistory.currentId)
					chat.current_message_id = history.currentId;
				history = chatContent.history;
				if (chat?.current_message_id && history?.messages?.[chat.current_message_id]) {
					history.currentId = chat.current_message_id;
				}

				// Sanitize history: repair orphaned references and structurally-malformed
				// nodes from failed regenerations (#24424, #24157, #20474)
				sanitizeHistory(history);

				chatTitle.set(chatContent.title);
				branchPointMessageId =
					chatContent.originalChatId === parentChatId
						? (chatContent.branchPointMessageId ?? null)
						: null;
				if (tabbed) await onEmbeddedChatTitle?.(id, chatContent.title);

				params = structuredClone(chatContent?.params ?? {});
				delete params.note_id;
				chatFiles = structuredClone(chatContent?.files ?? []);

				// Load tasks from chat-level DB field
				chatTasks = chat?.tasks ?? [];
				serverContextUsage = chat?.context_usage ?? null;

				autoScroll = true;
				await tick();
				if (signal.aborted) return;

				// Mark all non-current assistant messages as done
				if (history.currentId) {
					for (const message of Object.values(history.messages)) {
						if (
							message &&
							message.role === 'assistant' &&
							message.id !== history.currentId &&
							message.done !== false
						) {
							message.done = true;
						}
					}
				}

				// Reconcile active tasks with message state:
				// If the response is already done, remaining tasks are just background
				// work (follow-ups, title gen) that shouldn't block the input.
				const activeTaskIds = taskIds;
				const pendingTaskIds = await getTaskIdsByChatId(localStorage.token, id, signal)
					.then((res) => res?.task_ids ?? [])
					.catch((error) => {
						console.warn('[note-chat] getTaskIdsByChatId failed; continuing without tasks', {
							chatIdProp,
							activeChatId: $chatId,
							error
						});
						return [];
					});
				if (signal.aborted) return;
				const currentMessage = history.currentId ? history.messages[history.currentId] : null;
				noteChatDebug('task reconciliation completed', {
					pendingTaskCount: pendingTaskIds.length,
					hasCurrentMessage: !!currentMessage
				});
				const responseComplete = currentMessage?.role === 'assistant' && currentMessage?.done;

				if (taskIds === activeTaskIds) {
					if (pendingTaskIds.length > 0 && !responseComplete) {
						taskIds = pendingTaskIds;
					} else {
						taskIds = null;
						// No active tasks and message incomplete → generation was interrupted
						if (pendingTaskIds.length === 0) {
							for (const message of Object.values(history.messages)) {
								if (
									message?.role === 'assistant' &&
									(message.user_id ?? chat?.user_id) === $user?.id &&
									!message.done &&
									!messageHasPendingAskUser(message) &&
									!message.output?.some(
										(item) => item?.type === 'function_call' && item?.status === 'pending'
									)
								) {
									message.done = true;
									history = history;
								}
							}
						}
					}
				}

				await tick();

				if (signal.aborted) return;
				if (loading) {
					if (chatIdProp && !$temporaryChat) updateLastReadAt(chatIdProp);

					const lastMessage = history.currentId ? history.messages[history.currentId] : null;
					if (!lastMessage || lastMessage.role !== 'assistant' || lastMessage.done) {
						await processNextInQueue(chatIdProp);
					}
					if (signal.aborted) return;
					const restored = await restoreChatInput(
						sessionStorage.getItem(getChatInputKey(chatIdProp))
					);
					const chatInputPrompt = restored ? prompt : null;
					if (signal.aborted) return;
					await setDefaults(restored);
					if (signal.aborted) return;
					loading = false;
					await tick();
					if (signal.aborted) return;
					// Mounting the editor clears prompt, so apply the saved text afterward.
					if (chatInputPrompt !== null) messageInput?.setText(chatInputPrompt);
					if (embeddedDraft) {
						({ prompt, files } = embeddedDraft);
						messageInput?.setText(prompt);
					}
					if (!$mobile) messageInput?.focus({ preventScroll: true });
				}
				return true;
			} else {
				console.warn('[note-chat] chat response missing chat payload', {
					chatIdProp,
					activeChatId: $chatId,
					chat
				});
			}
		}
		console.warn('[note-chat] no chat returned from getChatById', {
			chatIdProp,
			activeChatId: $chatId
		});
		chat = null;
		if (!embedded) await goto('/');
		else loading = false;
		return false;
	};

	const scrollToBottom = async (behavior = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});
			lastScrollTop = messagesContainerElement.scrollTop;

			// Re-scroll over two frames as content-visibility resolves estimated message heights.
			requestAnimationFrame(() => {
				if (messagesContainerElement && autoScroll) {
					messagesContainerElement.scrollTo({
						top: messagesContainerElement.scrollHeight,
						behavior
					});
					lastScrollTop = messagesContainerElement.scrollTop;
					requestAnimationFrame(() => {
						if (messagesContainerElement && autoScroll) {
							messagesContainerElement.scrollTo({
								top: messagesContainerElement.scrollHeight,
								behavior
							});
							lastScrollTop = messagesContainerElement.scrollTop;
						}
					});
				}
			});
		}
	};

	$: if (
		!loading &&
		(!fullWidthTabs || mainChatActive) &&
		autoScroll &&
		!$page.url.searchParams.has('message')
	) {
		scrollToBottom();
	}

	const scrollToTop = async () => {
		await messagesRef?.scrollToTop();
	};

	const shouldAutoScrollResponse = () =>
		autoScroll && ($settings?.scrollOnResponseGeneration ?? true);

	let scrollRAF = null;
	let contentsRAF = null;
	const autoScrollToBottom = () => {
		if (!shouldAutoScrollResponse()) return;

		if (!scrollRAF) {
			scrollRAF = requestAnimationFrame(async () => {
				scrollRAF = null;
				if (shouldAutoScrollResponse()) await scrollToBottom();
			});
		}
	};

	let processingQueueChats = new Set<string>();

	const processNextInQueue = async (targetChatId: string) => {
		if (processingQueueChats.has(targetChatId) || targetChatId !== $chatId) return;

		const queue = $chatRequestQueues[targetChatId];
		if (!queue || queue.length === 0 || queue[0].error) return;
		const lastMessage = history.currentId ? history.messages[history.currentId] : null;
		if (
			(lastMessage?.role === 'assistant' &&
				!lastMessage.done &&
				!usesBackendQueue(queue.flatMap((m) => m.files ?? []))) ||
			queue.some((m) =>
				(m.files ?? []).some((file) => ['uploading', 'error'].includes(file.status))
			)
		) {
			return;
		}

		processingQueueChats.add(targetChatId);
		const boundary = queue.findIndex((entry) =>
			entry.files.some((file: any) => file.type === 'filesystem')
		);
		const queuedMessages =
			embedded || boundary === 0
				? queue.slice(0, 1)
				: boundary < 0
					? [...queue]
					: queue.slice(0, boundary);
		const queuedMessageIds = new Set(queuedMessages.map((m) => m.id));
		try {
			const combinedPrompt = queuedMessages.map((m) => m.prompt).join('\n\n');
			const combinedFiles = queuedMessages.flatMap((m) => m.files);

			chatRequestQueues.update((q) => ({
				...q,
				[targetChatId]: (q[targetChatId] ?? []).filter((m) => !queuedMessageIds.has(m.id))
			}));

			await submitPrompt(combinedPrompt, combinedFiles);
		} catch (error) {
			console.error(error);
			chatRequestQueues.update((q) => ({
				...q,
				[targetChatId]: [
					...queuedMessages.map((entry) => ({ ...entry, error: String(error) })),
					...(q[targetChatId] ?? [])
				]
			}));
		} finally {
			processingQueueChats.delete(targetChatId);
		}
	};

	// The backend queues messages sent to your own saved chat while a reply runs; the reply ends at its next
	// step and they are answered next. Files on a machine stay in this browser's queue.
	const usesBackendQueue = (messageFiles: any[] = []) =>
		($settings?.enableMessageQueue ?? true) &&
		!$temporaryChat &&
		!!$chatId &&
		!isTemporaryChatId($chatId) &&
		(chat?.user_id ?? $user?.id) === $user?.id &&
		!messageFiles.some((file) => file.type === 'filesystem');

	// Messages the backend queued under the reply shown, listed with the browser's queue.
	$: backendQueue = (
		(history.currentId ? history.messages[history.currentId]?.childrenIds : null) ?? []
	)
		.map((id: string) => history.messages[id])
		.filter(
			(message: any) =>
				message?.role === 'user' &&
				message.meta?.status === 'pending' &&
				message.meta?.internal !== true
		);
	$: messageQueue = [
		...backendQueue.map((message: any) => ({
			id: message.id,
			prompt: message.content,
			files: message.files ?? []
		})),
		...($chatRequestQueues[$chatId] ?? [])
	];

	const removeFromBackendQueue = async (id: string) => {
		const message = history.messages[id];
		await deleteChatMessageById(localStorage.token, $chatId, id);
		const parent = history.messages[message?.parentId];
		if (parent) parent.childrenIds = parent.childrenIds.filter((childId: string) => childId !== id);
		delete history.messages[id];
		history = history;
		return message;
	};

	const sendQueuedMessageNow = async (id) => {
		if (history.messages[id]?.meta?.status === 'pending') {
			// Stopping the reply answers its queued messages right away.
			await stopResponse(false);
			return;
		}
		if (processingQueueChats.has($chatId)) return;

		const queue = $chatRequestQueues[$chatId] ?? [];
		const item = queue.find((m) => m.id === id);
		if (!item || (item.files ?? []).some((file) => ['uploading', 'error'].includes(file.status))) {
			return;
		}

		const targetChatId = $chatId;
		processingQueueChats.add(targetChatId);
		try {
			chatRequestQueues.update((q) => ({
				...q,
				[targetChatId]: queue.filter((m) => m.id !== id)
			}));
			await stopResponse(false);
			await tick();
			await submitPrompt(item.prompt, item.files);
		} catch (error) {
			toast.error(String(error));
			chatRequestQueues.update((q) => ({
				...q,
				[targetChatId]: [{ ...item, error: String(error) }, ...(q[targetChatId] ?? [])]
			}));
		} finally {
			processingQueueChats.delete(targetChatId);
			// Completion can arrive before submitPrompt returns, while the queue is locked.
			if ($chatId === targetChatId) {
				await processNextInQueue(targetChatId);
			}
		}
	};

	const editQueuedMessage = async (id) => {
		if (history.messages[id]?.meta?.status === 'pending') {
			const message = await removeFromBackendQueue(id).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
			if (!message) return;
			files = message.files ?? [];
			messageInput?.setText(message.content);
			return;
		}
		const queue = $chatRequestQueues[$chatId] ?? [];
		const item = queue.find((m) => m.id === id);
		if (!item) return;

		chatRequestQueues.update((q) => ({
			...q,
			[$chatId]: queue.filter((m) => m.id !== id)
		}));
		files = item.files;
		messageInput?.setText(item.prompt);

		await processNextInQueue($chatId);
	};

	const deleteQueuedMessage = async (id) => {
		if (history.messages[id]?.meta?.status === 'pending') {
			await removeFromBackendQueue(id).catch((error) => toast.error(`${error}`));
			return;
		}
		const queue = $chatRequestQueues[$chatId] ?? [];
		chatRequestQueues.update((q) => ({
			...q,
			[$chatId]: queue.filter((m) => m.id !== id)
		}));

		await processNextInQueue($chatId);
	};

	// Takes back a message whose chat could not be set up; it returns to the input after any draft.
	const unsendMessage = async (id: string) => {
		const message = history.messages[id];
		const parent = history.messages[message?.parentId];
		if (parent) parent.childrenIds = parent.childrenIds.filter((childId: string) => childId !== id);
		delete history.messages[id];
		if (history.currentId === id) history.currentId = message.parentId;
		history = history;
		files = [...files, ...(message.files ?? [])];
		// An emptied chat shows the placeholder's input again.
		await tick();
		await draftPrompt(message.content);
	};

	const chatCompletedHandler = async (_chatId, modelId, responseMessageId, messages) => {
		// Backend handles outlet filters and persistence inline.
		// Just refresh the sidebar chat list.
		if ($chatId == _chatId && !$temporaryChat) {
			await refreshChatList(localStorage.token);
		}
	};

	const chatActionHandler = async (_chatId, actionId, modelId, responseMessageId, event = null) => {
		const messages = createMessagesList(history, responseMessageId);
		// Actions can also update this message through events.
		const original = structuredClone(history.messages[responseMessageId]);

		const res = await chatAction(localStorage.token, actionId, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: getOutputText(m.output) || m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			...(event ? { event: event } : {}),
			chat_id: _chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			if ($chatId === _chatId && history.messages[responseMessageId]) {
				history.messages[responseMessageId].error = { content: error };
			}
			return null;
		});

		if ($chatId !== _chatId) return;

		let changed = !equal(original, history.messages[responseMessageId]);
		if (res?.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				const updated = {
					...history.messages[message.id],
					...(history.messages[message.id].content !== message.content
						? { originalContent: history.messages[message.id].content }
						: {}),
					...(typeof message.content === 'string' && history.messages[message.id].output?.length
						? { output: setOutputText(history.messages[message.id].output, message.content) }
						: {}),
					...message
				};
				if (!equal(history.messages[message.id], updated)) {
					history.messages[message.id] = updated;
					changed = true;
				}
			}
		}

		if (changed && !$temporaryChat) {
			chat = await updateChatById(localStorage.token, _chatId, {
				models: selectedModels,
				messages: createMessagesList(history, responseMessageId),
				history: history,
				files: chatFiles
			});

			await refreshChatList(localStorage.token);
		}
	};

	const getChatEventEmitter = async (modelId: string, chatId: string = '') => {
		return setInterval(() => {
			$socket?.emit('usage', {
				action: 'chat',
				model: modelId,
				chat_id: chatId
			});
		}, 1000);
	};

	const createMessagePair = async (userPrompt) => {
		if (isShared) return;
		messageInput?.setText('');
		if (selectedModels.length === 0) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const userMessageId = uuidv4();

			const responseMessages = [];
			for (const [modelIdx, modelId] of selectedModels.entries()) {
				const model = ($models ?? []).filter((m) => m.id === modelId).at(0);

				if (model) {
					const responseMessageId = uuidv4();
					responseMessages.push({
						id: responseMessageId,
						parentId: userMessageId,
						childrenIds: [],
						role: 'assistant',
						user_id: $user?.id,
						content: `[RESPONSE] ${responseMessageId}`,
						done: true,

						model: modelId,
						modelName: model.name ?? model.id,
						modelIdx: modelIdx,
						timestamp: Math.floor(Date.now() / 1000)
					});
				}
			}

			if (responseMessages.length === 0) {
				toast.error($i18n.t('Model not found'));
				return;
			}

			const messages = createMessagesList(history, history.currentId);
			const parentMessage = messages.length !== 0 ? messages.at(-1) : null;

			const userMessage = {
				id: userMessageId,
				parentId: parentMessage ? parentMessage.id : null,
				childrenIds: responseMessages.map((m) => m.id),
				role: 'user',
				user_id: $user?.id,
				user: { id: $user?.id, name: $user?.name },
				content: userPrompt ? userPrompt : `[PROMPT] ${userMessageId}`,
				timestamp: Math.floor(Date.now() / 1000),
				models: selectedModels
			};

			if (parentMessage) {
				parentMessage.childrenIds.push(userMessageId);
				history.messages[parentMessage.id] = parentMessage;
			}
			history.messages[userMessageId] = userMessage;
			for (const responseMessage of responseMessages) {
				history.messages[responseMessage.id] = responseMessage;
			}

			history.currentId = responseMessages.at(-1).id;

			await tick();

			if (autoScroll) {
				scrollToBottom();
			}

			const _chatId = $chatId || (await getChatId(history));
			if (_chatId === null) return;
			if (_chatId) {
				await saveChatHandler(_chatId, history);
			} else {
				await initChatHandler(history);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }) => {
		const model = ($models ?? []).filter((m) => m.id === modelId).at(0);

		let parentMessage = history.messages[parentId];
		let currentParentId = parentMessage ? parentMessage.id : null;
		for (const message of messages) {
			let messageId = uuidv4();

			if (message.role === 'user') {
				const userMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = userMessage;
				parentMessage = userMessage;
				currentParentId = messageId;
			} else {
				const responseMessage = {
					id: messageId,
					parentId: currentParentId,
					childrenIds: [],
					done: true,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: 0,
					timestamp: Math.floor(Date.now() / 1000),
					...message
				};

				if (parentMessage) {
					parentMessage.childrenIds.push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = responseMessage;
				parentMessage = responseMessage;
				currentParentId = messageId;
			}
		}

		history.currentId = currentParentId;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (!$chatId) {
			await initChatHandler(history);
		} else {
			await saveChatHandler($chatId, history);
		}
	};

	const responseCompletionEventHandler = (data, message) => {
		message.output = applyResponseStreamEvent(message.output ?? [], data);

		if (data?.type === 'response.output_text.delta') {
			const value = data.delta ?? '';
			if (!(message.content == '' && value == '\n')) {
				message.content += value;

				if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
					navigator.vibrate(5);
				}
				dispatchCallOverlayAudio(message);
			}
		} else if (data?.type === 'response.completed' || data?.type?.endsWith('.done')) {
			message.content = getOutputText(message.output) || message.content;
		}

		history.messages[message.id] = message;
		history = history;
	};

	const chatCompletionEventHandler = async (data, message, chatId, shared = false) => {
		const {
			id,
			done,
			choices,
			content,
			output,
			sources,
			selected_model_id,
			strategy,
			error,
			usage
		} = data;

		if (error) {
			if (shared) message.error = error;
			else handleOpenAIError(error, message);
		}

		// Store raw OR-aligned output items from backend
		if (output) {
			message.output = output;
			message.content = getOutputText(output);
			if (
				data.type === 'response.output_text.delta' &&
				!shared &&
				navigator.vibrate &&
				$settings?.hapticFeedback
			) {
				navigator.vibrate(5);
			}
			if (!shared) dispatchCallOverlayAudio(message);
		}

		if (sources && !message?.sources) {
			message.sources = sources;
		}

		if (choices && !output) {
			if (choices[0]?.message?.content) {
				// Non-stream response
				message.content += choices[0]?.message?.content;
				if (!shared) dispatchCallOverlayAudio(message);
			} else {
				// Stream response
				let value = choices[0]?.delta?.content ?? '';
				if (message.content == '' && value == '\n') {
					console.log('Empty response');
				} else {
					message.content += value;

					if (!shared && navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
						navigator.vibrate(5);
					}
					if (!shared) dispatchCallOverlayAudio(message);
				}
			}
		}

		if (content && !output) {
			// REALTIME_CHAT_SAVE is disabled
			message.content = content;

			if (!shared && navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
				navigator.vibrate(5);
			}
			if (!shared) dispatchCallOverlayAudio(message);
		}

		if (selected_model_id) {
			message.selectedModelId = selected_model_id;
			message.strategy = strategy ?? null;
		}

		if (usage) {
			message.usage = usage;
			captureUsageCheckpoint(message);
		}

		history.messages[message.id] = message;
		history = history;

		if (done) {
			message.done = true;
			message.meta = { ...message.meta, response_ended_at: Date.now() / 1000 };
			if (shared) return;
			if (message.error) {
				bridge?.update();
				await processNextInQueue(chatId);
				return;
			}
			const visibleContent =
				getOutputText(message?.output) || removeAllDetails(message?.content ?? '');

			if ($settings.responseAutoCopy) {
				copyToClipboard(visibleContent);
			}

			if ($settings.responseAutoPlayback && !$voiceCall && !bridge?.connected) {
				await tick();
				document.getElementById(`speak-button-${message.id}`)?.click();
			}

			// Emit chat event for TTS (only when call overlay is active)
			dispatchCallOverlayAudio(message, true);
			eventTarget.dispatchEvent(
				new CustomEvent('chat:finish', {
					detail: {
						id: message.id,
						content: visibleContent
					}
				})
			);

			history.messages[message.id] = message;

			await tick();
			if (shouldAutoScrollResponse()) {
				scrollToBottom();
			}

			// Fire-and-forget: run chatCompletedHandler for background work
			// (outlet filters, chat save, title gen, follow-ups, tags)
			// without blocking the user from sending new messages.
			chatCompletedHandler(
				chatId,
				message.model,
				message.id,
				createMessagesList(history, message.id)
			);

			// Process next queued request if any
			await processNextInQueue(chatId);
		}

		bridge?.update();
	};

	// Chat functions

	const submitPrompt = async (
		inputContent: string,
		inputFiles: any[],
		bridgeRequest: { userMessageId: string; modelId: string } | null = null
	) => {
		if (selectedModels.includes('')) throw new Error($i18n.t('Model not selected'));
		if ($selectedFolder && !$chatId && !bridgeRequest) {
			if (tabs?.openFeatureTab('chat', false, inputContent, inputFiles)) {
				atSelectedModel = undefined;
				return { status: 'submitted' as const };
			}
			prompt = inputContent;
			files = inputFiles;
			messageInput?.setText(prompt);
			return { status: 'deferred' as const };
		}
		const _files = structuredClone(inputFiles);

		chatFiles.push(
			..._files.filter(
				(item) =>
					['doc', 'text', 'note', 'chat', 'folder', 'collection'].includes(item.type) ||
					(item.type === 'file' && !isRasterImageContentType(item?.content_type))
			)
		);
		chatFiles = chatFiles.filter(
			// One copy per attachment; the model does not need an encore.
			(item, index, array) => array.findIndex((i) => equal(i, item)) === index
		);

		const lastMessage = history.currentId ? history.messages[history.currentId] : null;
		const queued =
			!bridgeRequest &&
			lastMessage?.role === 'assistant' &&
			(lastMessage.done === false || backendQueue.length > 0) &&
			usesBackendQueue(_files);

		// Create user message
		let userMessageId = bridgeRequest?.userMessageId ?? uuidv4();
		let userMessage = {
			id: userMessageId,
			parentId: history.currentId ?? null,
			childrenIds: [],
			role: 'user',
			user: { id: $user?.id, name: $user?.name },
			user_id: $user?.id,
			content: inputContent,
			files: _files.length > 0 ? _files : undefined,
			timestamp: Math.floor(Date.now() / 1000), // Unix epoch
			models: selectedModels,
			...(queued ? { meta: { status: 'pending' } } : {})
		};

		// A transcribed Bridge message already exists in the same history.
		const existingUserMessage = history.messages[userMessageId];
		if (existingUserMessage) userMessage = { ...existingUserMessage, files: userMessage.files };
		history.messages[userMessageId] = userMessage;

		// Append messageId to childrenIds of parent message
		if (!existingUserMessage && history.currentId !== null) {
			history.messages[history.currentId].childrenIds.push(userMessageId);
		}

		// A queued message waits in the queue list; the running reply stays the end of the transcript.
		if (!queued) history.currentId = userMessageId;
		else history = history;

		// focus on chat input (skip during voice call to avoid triggering mobile keyboard)
		if (!$voiceCall) {
			messageInput?.focus({ preventScroll: true });
		}

		saveSessionSelectedModels();

		const currentHistory = history;
		let _chatId: string | null = null;
		processing = 'uploading';
		try {
			await tick();
			if (history !== currentHistory) return { status: 'rejected' as const };
			_chatId = await getChatId(currentHistory, _files);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			processing = '';
		}
		if (_chatId === null) {
			if (!existingUserMessage && history === currentHistory) await unsendMessage(userMessageId);
			return { status: 'rejected' as const };
		}

		return await sendMessage(history, userMessageId, {
			modelId: bridgeRequest?.modelId ?? null
		});
	};

	let compacting = false;
	const handleManualCompact = async () => {
		if (!contextCompactionEnabled) {
			toast.message($i18n.t('Context compaction is disabled'));
			return;
		}

		if (!$chatId || !history?.currentId) {
			toast.message($i18n.t('No chat to compact'));
			return;
		}

		const currentMessage = history.messages?.[history.currentId];
		if (
			generating ||
			taskIds?.length ||
			(currentMessage?.role === 'assistant' && !currentMessage.done)
		) {
			toast.warning($i18n.t('Wait for the current response to finish before compacting.'));
			return;
		}

		if (compacting) return;
		compacting = true;
		const model = atSelectedModel?.id ?? selectedModels.find((modelId) => modelId);
		const compactChatId = $chatId;
		const toastId = toast.loading($i18n.t('Compacting context...'));

		try {
			const result = await compactChatById(localStorage.token, compactChatId, model);
			if (!result?.compacted) {
				const skippedReason =
					result?.reason === 'too_short'
						? $i18n.t('Chat is too short to compact')
						: result?.reason === 'empty'
							? $i18n.t('No chat to compact')
							: result?.reason === 'disabled'
								? $i18n.t('Context compaction is disabled')
								: $i18n.t('Nothing to compact');
				toast.message(skippedReason, { id: toastId });
			} else {
				toast.success($i18n.t('Context compacted'), { id: toastId });
			}
			if ($chatId !== compactChatId) return;

			serverContextUsage = result?.context_usage ?? serverContextUsage;
			await loadChat();
		} catch (error) {
			toast.error(String(error?.detail ?? error?.message ?? $i18n.t('Context compaction failed')), {
				id: toastId
			});
		} finally {
			compacting = false;
			messageInput?.focus({ preventScroll: true });
		}
	};

	const handleStatusCommand = () => {
		messageInput?.showStatus();
		messageInput?.focus({ preventScroll: true });
	};

	const handleModelCommand = (modelId = '') => {
		if (!modelId) {
			const currentModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
				Boolean
			);
			toast.message(
				currentModels.length
					? `Current model: ${currentModels.join(', ')}`
					: $i18n.t('Model not selected')
			);
			messageInput?.setText('');
			prompt = '';
			messageInput?.focus({ preventScroll: true });
			return;
		}

		const model = ($models ?? []).find((model) => model.id === modelId);
		if (!model) {
			toast.error(`Model not found: ${modelId}`);
			messageInput?.setText('');
			prompt = '';
			messageInput?.focus({ preventScroll: true });
			return;
		}

		atSelectedModel = undefined;
		selectedModels = [model.id];
		saveControls(selectedModels);
		saveSessionSelectedModels();
		toast.success(`Model switched to: ${model.id}`);
		messageInput?.setText('');
		prompt = '';
		messageInput?.focus({ preventScroll: true });
	};

	const handleForkChat = async (messageId: string | null = null) => {
		if (!$chatId || $temporaryChat || !history?.currentId) {
			toast.message($i18n.t('No chat to fork'));
			return;
		}
		if (!($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true))) {
			toast.error($i18n.t('Access prohibited'));
			return;
		}

		const forkedMessage = history.messages?.[messageId ?? history.currentId];
		if (
			generating ||
			taskIds?.length ||
			(forkedMessage?.role === 'assistant' && !forkedMessage.done)
		) {
			toast.warning($i18n.t('Wait for the current response to finish before forking.'));
			return;
		}

		const toastId = toast.loading($i18n.t('Forking chat...'));

		try {
			const result = await forkChatById(
				localStorage.token,
				$chatId,
				messageId ?? history.currentId
			);

			if (result?.id) {
				if (!embedded) {
					await goto(`/c/${result.id}`);
					await refreshChatList(localStorage.token, { refreshPinned: true });
				} else if (tabbed) {
					await onSelectEmbeddedChat?.(result.id);
					await refreshChatList(localStorage.token, { refreshPinned: true });
				}
				toast.success($i18n.t('Chat forked'), { id: toastId });
			} else {
				toast.error($i18n.t('Failed to fork chat'), { id: toastId });
			}
		} catch (error) {
			toast.error(`${error}`, { id: toastId });
		} finally {
			messageInput?.focus({ preventScroll: true });
		}
	};

	const clearCommandInput = () => {
		messageInput?.setText('');
		prompt = '';
	};

	let tabs: Tabs;
	let fullWidthTabs = false;
	let mainChatActive = false;
	let mainChatStyle = '';
	let mainChatGroupId = '';
	export let tabTitleEditor: import('svelte').Snippet | undefined = undefined;
	let editingTitle = false;
	let titleDraft = '';
	let titleInput: HTMLInputElement;
	let generatingTitle = false;
	let titleEditChatId = '';
	// Folder owners can rename chats others made in their folders.
	$: canRename =
		!isShared ||
		(!!chat?.folder_id &&
			$_folders.find((folder) => folder.id === chat.folder_id)?.user_id === $user?.id);
	$: if (loading || !canRename || $temporaryChat || $chatId !== titleEditChatId)
		editingTitle = false;
	$: tabTitleEditor = editingTitle ? renderTitleEditor : undefined;
	/** A chat's actions on its tab: the Navbar's for the main chat, the chat menu for a side chat. */
	export let tabActions: import('svelte').Snippet | undefined = undefined;
	let showShareModal = false;
	$: showChatMenu =
		!loading &&
		!!$chatId &&
		!!history.currentId &&
		(!isNearTop ||
			(!isShared && !$temporaryChat) ||
			$user?.role === 'admin' ||
			($user?.permissions?.chat?.export ?? true));
	// Renaming hides the menu, like the tab's close button.
	$: chatMenu = showChatMenu && !editingTitle ? renderChatMenu : undefined;
	$: if (embedded && tabbed) tabActions = chatMenu;

	export const getOverview = () => ({ history, chatUser: chatOwner, showMessage });

	export const startRename = async () => {
		if (
			loading ||
			!canRename ||
			!$chatId ||
			$temporaryChat ||
			isTemporaryChatId($chatId) ||
			generatingTitle
		)
			return;
		titleEditChatId = $chatId;
		titleDraft = $chatTitle;
		editingTitle = true;
		await tick();
		setTimeout(() => {
			titleInput?.focus();
			titleInput?.select();
		}, 0);
	};

	const editChatTitle = async () => {
		// Generating a title disables and blurs the field; wait for the generated value.
		if (!editingTitle || generatingTitle) return;
		editingTitle = false;
		const title = titleDraft.trim();
		if (title === $chatTitle) return;
		if (!title) {
			toast.error($i18n.t('Title cannot be an empty string.'));
			return;
		}
		const id = $chatId;
		try {
			const updated = await updateChatById(localStorage.token, id, { title });
			if (!updated) return;
			setChatTitle(id, title);
			if ($chatId === id) {
				chatTitle.set(title);
				if (embedded) await onEmbeddedChatTitle?.(id, title);
			}
			await refreshChatList(localStorage.token, { refreshPinned: true });
			await refreshFolderChatLists();
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const generateChatTitle = async () => {
		const id = $chatId;
		generatingTitle = true;
		titleDraft = '';
		const branch = createMessagesList(history, history.currentId);
		const messages = branch.map((message) => ({
			role: message.role,
			content: getOutputText(message.output) || message.content || ''
		}));
		const modelId = selectedModels.find((modelId: string) => modelId) ?? '';
		const responseMessage = branch
			.filter((message) => message.role === 'assistant' && message.model === modelId)
			.at(-1);
		const generatedTitle = await generateTitle(
			localStorage.token,
			responseMessage?.selectedModelId ?? modelId,
			messages
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		generatingTitle = false;
		if ($chatId !== id || !editingTitle) return;
		titleDraft = generatedTitle || $chatTitle;
		await editChatTitle();
	};

	let folderTabActions: import('svelte').Snippet | undefined;

	// Renaming the folder from its tab saves like the Edit Folder modal.
	const renameFolder = async (folderId: string, name: string) => {
		try {
			const updated = await updateFolderById(localStorage.token, folderId, { name });
			if (!updated) return;
			updateFolderDetails(folderId, updated);
			selectedFolder.update((current) =>
				current?.id === folderId ? { ...current, ...updated } : current
			);
			await Promise.all([refreshChatList(localStorage.token), refreshFolderChatLists(null)]);
		} catch (error) {
			toast.error(String(error));
		}
	};

	let tabBarActions: import('svelte').Snippet | undefined;

	let initializedMachineChatId: string | null = null;
	const initializeMachineDirectory = async (id: string, context: MachineContext | null) => {
		if (initializedMachineChatId === id) return;
		if (!$config?.features?.enable_tool_servers || !context?.currentDirectory) return;
		const userSettings: any = $settings;
		const target = resolveMachineTarget(context.machineId, $machines ?? [], localStorage.token, {
			chatId: id,
			modelId: selectedModels[0] ?? null
		});
		if (!target) throw new Error($i18n.t('Machine Not Found'));
		const result = await setCwd(target, context.currentDirectory);
		if (!result?.cwd)
			throw new Error($i18n.t('Working directory is unavailable. Check the machine and path.'));
		initializedMachineChatId = id;
	};

	const getChatId = async (_history: typeof history, inputFiles = files) => {
		let _chatId = $chatId;
		const machineId =
			machineIdOf(inputFiles.find((file) => file.type === 'filesystem')) ?? $selectedMachineId;
		const context =
			$config?.features?.enable_tool_servers &&
			!Object.values(_history.messages).some((message) => message.role === 'assistant') &&
			machineContext &&
			machineContext.machineId === machineId
				? machineContext
				: null;
		// Empty embedded drafts create their backing chat only when the first message is sent.
		if (!_chatId) {
			if (embedded && onCreateEmbeddedChat && !$temporaryChat) {
				const createdChat = await onCreateEmbeddedChat({
					models: selectedModels,
					params,
					variables: chatVariables
				});
				if (!createdChat?.id) {
					toast.error($i18n.t('Failed to create chat'));
					return null;
				}
				if (history !== _history) return null;

				chat = createdChat;
				_chatId = createdChat.id;
				loadedChatIdProp = _chatId;
				await chatId.set(_chatId);
				await chatTitle.set(createdChat?.chat?.title ?? createdChat?.title ?? $i18n.t('Chat'));

				params = structuredClone(createdChat?.chat?.params ?? {});
				delete params.note_id;
				chatFiles = mergeFiles(chatFiles, createdChat?.chat?.files ?? []);
				await onSelectEmbeddedChat?.(_chatId);
			} else if ($temporaryChat) {
				_chatId = createTemporaryChatId($socket?.id);
				await chatId.set(_chatId);
			}
			if (!_chatId && (tabbed || context?.currentDirectory || tabs?.hasTerminalTabs())) {
				_chatId = await initChatHandler(_history);
			}
			await tick();
		}
		if (history !== _history) return null;
		if (_chatId) await tabs?.attachChatViewTo(_chatId);
		if (history !== _history || $chatId !== _chatId) return null;
		// Also covers temporary/embedded chats and retries after a failed initialization.
		if (_chatId) await initializeMachineDirectory(_chatId, context);
		if (history !== _history || $chatId !== _chatId) return null;
		return _chatId;
	};

	const submitHandler = async (
		userPrompt: string,
		{
			_raw = false,
			bridge: bridgeRequest = null
		}: { _raw?: boolean; bridge?: { userMessageId: string; modelId: string } | null } = {}
	): Promise<BridgeSubmission> => {
		if (embedded && onBeforeNoteSubmit) {
			try {
				await onBeforeNoteSubmit();
			} catch (error) {
				toast.error(String(error));
				return { status: 'rejected' };
			}
		}
		if (processing === 'uploading') return { status: 'deferred' };
		if ($models === null) return { status: 'deferred' };
		emitTyping(false);
		if (bridgeRequest && (selectedModelIds.length !== 1 || !bridgeRequest.modelId))
			return { status: 'rejected' };

		const _selectedModels = selectedModels.map((modelId) =>
			modelId.startsWith('agent:') || ($models ?? []).map((m) => m.id).includes(modelId)
				? modelId
				: ''
		);

		if (!equal(selectedModels, _selectedModels)) {
			selectedModels = _selectedModels;
		}

		if (String(userPrompt).trim() === '/compact') {
			clearCommandInput();
			await handleManualCompact();
			return { status: 'rejected' };
		}
		if (String(userPrompt).trim() === '/status') {
			clearCommandInput();
			handleStatusCommand();
			return { status: 'rejected' };
		}
		if (String(userPrompt).trim() === '/comments') {
			clearCommandInput();
			messageInput?.openComments();
			return { status: 'rejected' };
		}
		const chatTabCommand = String(userPrompt)
			.trim()
			.match(/^\/(?:side|btw)(?:\s+([\s\S]*))?$/i);
		if (chatTabCommand && !canOpenChatTab) {
			toast.error($i18n.t('You do not have permission to use side chat.'));
			return { status: 'rejected' };
		}
		if (chatTabCommand && !embedded && $chatId && history.currentId) {
			if (selectedModels.length !== 1 || !selectedModelIds[0]) {
				toast.error($i18n.t('Select only one model to open a side chat.'));
				return { status: 'rejected' };
			}
			clearCommandInput();
			chatTabRequest.set({ parentChatId: $chatId, prompt: chatTabCommand[1] ?? '' });
			showTabs.set('chat');
			return { status: 'rejected' };
		}
		if (String(userPrompt).trim() === '/fork') {
			clearCommandInput();
			await handleForkChat();
			return { status: 'rejected' };
		}
		const modelCommandMatch = String(userPrompt)
			.trim()
			.match(/^\/model(?:\s+([\s\S]+))?$/);
		if (modelCommandMatch) {
			handleModelCommand(modelCommandMatch[1]?.trim() ?? '');
			return { status: 'rejected' };
		}

		if (pendingOAuthTools.some((tool) => !isSystemOAuthTool(tool.id))) {
			toast.warning($i18n.t('Please connect all required integrations before sending a message'));
			return { status: 'rejected' };
		}
		if (userPrompt === '' && files.length === 0) {
			toast.error($i18n.t('Please enter a prompt'));
			return { status: 'rejected' };
		}
		if (selectedModels.includes('')) {
			toast.error($i18n.t('Model not selected'));
			return { status: 'rejected' };
		}
		const form = getChatVariablesForm(selectedModelIds, chatVariables, $models ?? []);
		if (form.conflicts.length > 0) {
			showChatVariablesModal = true;
			toast.error($i18n.t('Chat Variables have conflicting model definitions'));
			return { status: 'rejected' };
		}
		if (form.missing || form.empty) {
			showChatVariablesModal = true;
			return { status: 'deferred' };
		}

		if (
			($config?.file?.max_count ?? null) !== null &&
			files.length + chatFiles.length > $config?.file?.max_count
		) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount: $config?.file?.max_count
				})
			);
			return { status: 'rejected' };
		}

		const openingFolderTab = $selectedFolder && !$chatId && !bridgeRequest;
		if (
			!openingFolderTab &&
			$config?.features?.enable_web_search_confirmation &&
			webSearchActive &&
			!webSearchConfirmed
		) {
			pendingWebSearchPrompt = bridgeRequest ? null : (userPrompt ?? '');
			openWebSearchConfirm();
			return { status: 'deferred' };
		}

		// Uploads need the chat first. Otherwise the message shows at once and submitPrompt sets
		// up the chat, which can take several round trips (e.g. a folder's working directory).
		if (
			!openingFolderTab &&
			files.some((file) => file.status === 'pending' && file.file instanceof File)
		) {
			const currentHistory = history;
			processing = 'uploading';
			try {
				const _chatId = await getChatId(currentHistory);
				if (_chatId === null || history !== currentHistory) return { status: 'rejected' };
				if (!(await messageInput?.uploadPendingFiles(_chatId || (await initChatHandler(history)))))
					return { status: 'rejected' };
				if (history !== currentHistory) return { status: 'rejected' };
			} catch (error) {
				toast.error(`${error}`);
				return { status: 'rejected' };
			} finally {
				processing = '';
			}
		}

		if (
			($chatRequestQueues[$chatId] ?? []).some((m) =>
				(m.files ?? []).some((file) => ['uploading', 'error'].includes(file.status))
			) ||
			(files.length > 0 && files.some((file) => ['uploading', 'error'].includes(file.status)))
		) {
			if (bridgeRequest) return { status: 'deferred' };
			chatRequestQueues.update((q) => ({
				...q,
				[$chatId]: [...(q[$chatId] ?? []), { id: uuidv4(), prompt: userPrompt, files }]
			}));
			messageInput?.setText('');
			prompt = '';
			files = [];
			return { status: 'rejected' };
		}

		// Check if the assistant is still generating the main response
		// (don't block on background tasks like title gen, follow-ups, tags)
		const lastMessage = history.currentId ? history.messages[history.currentId] : null;
		const isGenerating = bridgeRequest
			? createMessagesList(history, bridgeRequest.userMessageId).some(
					(message) => message.role === 'assistant' && !message.done
				)
			: lastMessage && lastMessage.role === 'assistant' && !lastMessage.done;

		if (isGenerating && (bridgeRequest || !usesBackendQueue(files))) {
			if (bridgeRequest) return { status: 'deferred' };
			if ($settings?.enableMessageQueue ?? true) {
				// Enqueue the request
				const _files = structuredClone(files);
				chatRequestQueues.update((q) => ({
					...q,
					[$chatId]: [...(q[$chatId] ?? []), { id: uuidv4(), prompt: userPrompt, files: _files }]
				}));
				// Clear input
				messageInput?.setText('');
				prompt = '';
				files = [];
				return { status: 'rejected' };
			} else {
				// Interrupt: stop current generation and proceed
				await stopResponse();
				await tick();
			}
		}

		// Clear input and submit
		messageInput?.setText('');
		prompt = '';
		const _files = structuredClone(files);
		files = [];
		messageInput?.setText('');

		return (
			(await submitPrompt(userPrompt, _files, bridgeRequest)) ?? {
				status: 'rejected'
			}
		);
	};

	const sendMessage = async (
		_history,
		parentId: string,
		{
			messages = null,
			modelId = null,
			modelIdx = null,
			regenerationPrompt = null,
			regenerationMessageId = null
		}: {
			messages?: any[] | null;
			modelId?: string | null;
			modelIdx?: number | null;
			regenerationPrompt?: string | null;
			regenerationMessageId?: string | null;
		} = {}
	) => {
		const parent = _history.messages[parentId];
		if (parent?.files?.some((file: any) => file.type === 'filesystem')) {
			const attached = parent.files.filter((file: any) => file.type === 'filesystem');
			const machine = machineIdOf(attached.find((file: any) => machineIdOf(file)));
			if (
				attached.some(
					(file: any) =>
						(machineIdOf(file) && machineIdOf(file) !== machine) ||
						(file.session_id && file.session_id !== $chatId)
				)
			)
				throw new Error('Attached files must belong to this chat and the same machine.');
			if (machine && !isMachineAvailable(machine))
				throw new Error('The attached file’s machine is unavailable.');
		}
		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = JSON.parse(JSON.stringify($chatId));
		_history = structuredClone(_history);

		const responseMessageIds: Record<PropertyKey, string> = {};
		if (!modelId && atSelectedModel) {
			selectedModels = [atSelectedModel.id];
			atSelectedModel = undefined;
		}
		const selectedModelIds = modelId ? [modelId] : selectedModels;
		if (!modelId && history.messages[parentId]) {
			history.messages[parentId].models = [...selectedModelIds];
		}

		// A queued message gets no reply on screen unless the backend answers it now.
		const queued = history.messages[parentId]?.meta?.status === 'pending';
		const target = queued ? structuredClone(history) : history;

		// Use a message_ids array with modelIdx to preserve separate columns for duplicate models.
		const messageIdsList: Array<{ model_id: string; message_id: string; modelIdx: number }> = [];
		for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
			const model = ($models ?? []).filter((m) => m.id === modelId).at(0);

			if (model) {
				let responseMessageId = uuidv4();
				let responseMessage = {
					parentId: parentId,
					id: responseMessageId,
					childrenIds: [],
					role: 'assistant',
					user_id: $user?.id,
					content: '',
					done: false,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: modelIdx ? modelIdx : _modelIdx,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				// Add message to history and Set currentId to messageId
				target.messages[responseMessageId] = responseMessage;
				target.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null && target.messages[parentId]) {
					target.messages[parentId].childrenIds = [
						...target.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
				messageIdsList.push({
					model_id: modelId,
					message_id: responseMessageId,
					modelIdx: modelIdx ? modelIdx : _modelIdx
				});
			}
		}
		history = history;

		await tick();

		// Re-clone history so sendMessageSocket gets the response messages we just added
		_history = structuredClone(target);

		// Vision capability check
		for (const mid of selectedModelIds) {
			const model = ($models ?? []).filter((m) => m.id === mid).at(0);
			if (model) {
				const hasImages = createMessagesList(_history, parentId).some((message) =>
					message.files?.some(
						(file) => file.type === 'image' || isRasterImageContentType(file?.content_type)
					)
				);

				if (
					hasImages &&
					!(model.info?.meta?.capabilities?.vision ?? true) &&
					!imageGenerationEnabled &&
					!videoGenerationEnabled
				) {
					toast.error(
						$i18n.t('Model {{modelName}} is not vision capable', {
							modelName: model.name ?? model.id
						})
					);
				}
			}
		}

		// Single request — backend fans out to all models
		const primaryModelId = selectedModelIds[0];
		const primaryModel = ($models ?? []).filter((m) => m.id === primaryModelId).at(0);
		const primaryResponseMessageId = messageIdsList[0]?.message_id;
		let submittedTaskIds: string[] = [];

		if (primaryModel && primaryResponseMessageId) {
			const chatEventEmitter = await getChatEventEmitter(primaryModel.id, _chatId);

			try {
				scrollToBottom();
				const completion = await sendMessageSocket(
					primaryModel,
					messages && messages.length > 0
						? messages
						: createMessagesList(_history, primaryResponseMessageId),
					_history,
					primaryResponseMessageId,
					_chatId,
					{
						// Send message_ids even for single-column regenerations to preserve modelIdx on reload.
						messageIdsList: messageIdsList.length > 0 ? messageIdsList : undefined,
						regenerationPrompt,
						regenerationMessageId
					}
				);
				submittedTaskIds =
					completion?.task_ids ?? (completion?.task_id ? [completion.task_id] : []);
			} finally {
				if (chatEventEmitter) clearInterval(chatEventEmitter);
			}
		}
		return {
			status: 'submitted' as const,
			chatId: $chatId,
			userMessageId: parentId,
			assistantMessageId: primaryResponseMessageId,
			taskIds: submittedTaskIds
		};
	};

	const getFeatures = () => {
		let features = {};

		if ($config?.features)
			features = {
				voice: ($voiceCall && callMode === 'current') || !!bridge?.connected,
				// A picked image model rides on the flag; plain true leaves the choice to the server.
				image_generation:
					$config?.features?.enable_image_generation &&
					($user?.role === 'admin' || $user?.permissions?.features?.image_generation) &&
					imageGenerationEnabled
						? selectedImageModelId
							? { model: selectedImageModelId }
							: true
						: false,
				video_generation:
					$config?.features?.enable_video_generation &&
					($user?.role === 'admin' || $user?.permissions?.features?.video_generation) &&
					videoGenerationEnabled
						? selectedVideoModelId
							? { model: selectedVideoModelId }
							: true
						: false,
				code_interpreter:
					$config?.features?.enable_code_interpreter &&
					($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter)
						? codeInterpreterEnabled
						: false,
				web_search: webSearchActive
			};

		if ($settings?.memory ?? $config?.features?.enable_memories ?? false) {
			features = { ...features, memory: true };
		}

		return features;
	};

	const getStopTokens = () => {
		const stop = params?.stop ?? $settings?.params?.stop;
		if (!stop) return undefined;

		const tokens = Array.isArray(stop) ? stop : stop.split(',').map((s) => s.trim());

		return tokens.filter(Boolean).map((token) => {
			try {
				return decodeURIComponent(JSON.parse(`"${token.replace(/"/g, '\\"')}"`));
			} catch {
				return token;
			}
		});
	};

	const sendMessageSocket = async (
		model,
		_messages,
		_history,
		responseMessageId,
		_chatId,
		{
			messageIdsList,
			regenerationPrompt,
			regenerationMessageId,
			continueResponse = false
		}: {
			messageIdsList?: Array<{ model_id: string; message_id: string }>;
			regenerationPrompt?: string | null;
			regenerationMessageId?: string | null;
			continueResponse?: boolean;
		} = {}
	) => {
		const responseMessage = _history.messages[responseMessageId];
		const userMessage = _history.messages[responseMessage.parentId];
		const filesystemAttachment = userMessage?.files?.find(
			(file: any) => file.type === 'filesystem'
		);
		const requestMachineId = machineIdOf(filesystemAttachment) ?? $selectedMachineId;
		const requestMachineCwd =
			machineContext && machineContext.machineId === requestMachineId
				? machineContext.currentDirectory
				: undefined;

		const chatMessageFiles = _messages
			.filter((message) => message.files)
			.flatMap((message) => message.files);

		// Filter chatFiles to only include files that are in the chatMessageFiles
		chatFiles = chatFiles.filter((item) => {
			const fileExists = chatMessageFiles.some((messageFile) => messageFile.id === item.id);
			return fileExists;
		});

		let files = structuredClone(chatFiles);
		files.push(
			...(userMessage?.files ?? []).filter(
				(item) =>
					['doc', 'text', 'note', 'chat', 'collection', 'folder'].includes(item.type) ||
					(item.type === 'file' && !isRasterImageContentType(item?.content_type))
			)
		);
		// One copy per attachment; the model does not need an encore.
		files = files.filter((item, index, array) => array.findIndex((i) => equal(i, item)) === index);

		scrollToBottom();
		eventTarget.dispatchEvent(
			new CustomEvent('chat:start', {
				detail: {
					id: responseMessageId
				}
			})
		);
		await tick();

		let userLocation;
		if ($settings?.userLocation) {
			userLocation = await getAndUpdateUserLocation(localStorage.token).catch((err) => {
				console.error(err);
				return undefined;
			});
		}

		const stream =
			model?.info?.params?.stream_response ??
			params?.stream_response ??
			$settings?.params?.stream_response ??
			true;
		// Always include system prompt — backend extracts it and prepends to DB messages.
		// Only temp chats need conversation messages (persisted chats load from DB).
		let messages: any[] = [
			params?.system || $settings.system
				? { role: 'system', content: `${params?.system || $settings?.system || ''}` }
				: undefined
		].filter(Boolean);

		if ($temporaryChat) {
			messages = [
				...messages,
				..._messages.map((message) => ({
					...message,
					...(message.output && message.role === 'assistant'
						? { output: message.output }
						: { content: processDetails(message.content) })
				}))
			].filter((message) => message);

			messages = messages
				.map((message) => {
					const imageFiles = (message?.files ?? []).filter(
						(file) => file.type === 'image' || isRasterImageContentType(file?.content_type)
					);

					if (message.output && message.role === 'assistant') {
						return {
							role: message.role,
							model: message.model,
							output: message.output,
							meta: message.meta
						};
					}

					if (message.role === 'user' && imageFiles.length > 0) {
						return {
							id: message.id,
							role: message.role,
							contextSummary: message?.contextSummary,
							content: [
								{
									type: 'text',
									text: message?.merged?.content ?? message.content
								},
								...imageFiles.map((file) => ({
									type: 'image_url',
									image_url: {
										url: file.url
									}
								}))
							]
						};
					}

					return {
						id: message.id,
						role: message.role,
						contextSummary: message?.contextSummary,
						content: message?.merged?.content ?? message.content,
						model: message.model,
						meta: message.meta
					};
				})
				.filter(
					(message) =>
						message?.role === 'user' || message?.content?.trim() || message?.output?.length
				);
		}

		const toolIds = [...selectedToolIds];

		// The backend applies the skill loading setting to menu-selected skills.
		// Keep mentions in the message so the backend can resolve them.
		const skillIds = [...selectedSkillIds];

		// Only send machine_id if the model has the machine capability enabled
		const machineEnabled =
			$config?.features?.enable_tool_servers && (model.info?.meta?.capabilities?.terminal ?? true);
		const useChatVariablesFallback = !_chatId || $temporaryChat || isTemporaryChatId(_chatId);

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				stream: stream,
				model: model.id,
				...(messages.length > 0 ? { messages } : {}),
				params: {
					...$settings?.params,
					...Object.fromEntries(Object.entries(params).filter(([, value]) => value !== null)),
					model_controls: $settings?.params?.model_controls ?? {},
					stop: getStopTokens()
				},

				files: embedded
					? [...(files ?? []), ...noteFiles]
					: (files?.length ?? 0) > 0
						? files
						: undefined,

				filter_ids:
					$config?.features?.enable_functions && selectedFilterIds.length > 0
						? selectedFilterIds
						: undefined,
				tool_ids: toolIds.filter((id) =>
					id.startsWith('server:')
						? $config?.features?.enable_tool_servers
						: $config?.features?.enable_tools
				),
				skill_ids: skillIds.length > 0 ? skillIds : undefined,
				machine_id: machineEnabled && requestMachineId ? requestMachineId : null,
				machine_cwd: !_chatId ? requestMachineCwd : undefined,
				features: getFeatures(),
				variables: {
					...getPromptVariables(
						$user?.name,
						$settings?.userLocation ? userLocation : undefined,
						$user?.email
					)
				},
				...(useChatVariablesFallback ? { chat_variables: chatVariables } : {}),

				session_id: $socket?.id,
				chat_id: _chatId || undefined,
				folder_id:
					$selectedFolder?.id ?? ($temporaryChat && draftFolderId ? draftFolderId : undefined),

				id: responseMessageId,
				...(messageIdsList ? { message_ids: messageIdsList } : {}),
				parent_id: userMessage?.parentId ?? null,
				...(userMessage?.meta?.status === 'pending' ? { queue: true } : {}),
				// Whether a message is queued is the backend's call, not a status the browser sends.
				user_message:
					userMessage?.meta?.status === 'pending'
						? { ...userMessage, meta: { ...userMessage.meta, status: undefined } }
						: userMessage,
				...(regenerationPrompt ? { regeneration_prompt: regenerationPrompt } : {}),
				...(regenerationMessageId ? { regeneration_message_id: regenerationMessageId } : {}),
				...(continueResponse ? { assistant_message_id: responseMessageId } : {}),

				background_tasks: {
					...(!$temporaryChat &&
					(!_chatId ||
						((userMessage?.parentId ?? null) === null &&
							createMessagesList(_history, responseMessageId).length === 2) ||
						(branchPointMessageId && userMessage?.parentId === branchPointMessageId))
						? {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						: {}),
					follow_up_generation: $settings?.autoFollowUps ?? true
				}
			},
			`${WEBUI_BASE_URL}/api`
		).catch(async (error) => {
			console.log(error);

			let errorMessage = error;
			if (error?.error?.message) {
				errorMessage = error.error.message;
			} else if (error?.message) {
				errorMessage = error.message;
			}

			if (typeof errorMessage === 'object') {
				errorMessage = $i18n.t(`Uh-oh! There was an issue with the response.`);
			}

			toast.error(`${errorMessage}`);
			responseMessage.error = {
				content: error
			};

			responseMessage.done = true;

			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			return null;
		});

		if (filesystemAttachment && (!res || res.error))
			throw new Error('File request failed. Retry from the message or queue.');
		const placeholderIds = (messageIdsList ?? [{ message_id: responseMessageId }]).map(
			({ message_id }) => message_id
		);
		const sentMessage = history.messages[userMessage.id];
		if (res?.queued && sentMessage) {
			// Queued for the running reply, which ends at its next step; the answer arrives with a chat reload.
			for (const id of placeholderIds) delete history.messages[id];
			sentMessage.childrenIds = sentMessage.childrenIds.filter(
				(id: string) => !placeholderIds.includes(id)
			);
			sentMessage.meta = { ...(sentMessage.meta ?? {}), status: 'pending' };
			if (placeholderIds.includes(history.currentId)) history.currentId = sentMessage.parentId;
			history = history;
			return res;
		}
		if (res && !res.error && sentMessage?.meta?.status === 'pending') {
			// The reply had already finished, so the backend answered it as a normal turn.
			sentMessage.meta = { ...sentMessage.meta, status: undefined };
			for (const id of placeholderIds) {
				if (!_history.messages[id]) continue;
				history.messages[id] = _history.messages[id];
				if (!sentMessage.childrenIds.includes(id)) sentMessage.childrenIds.push(id);
			}
			history.currentId = responseMessageId;
			history = history;
		}
		if (res) {
			if (res.error) {
				await handleOpenAIError(res.error, responseMessage);
			} else {
				// An early completion event may have already finished these replies.
				if (
					(messageIdsList ?? [{ message_id: responseMessageId }]).some(
						({ message_id }) => history.messages[message_id]?.done === false
					)
				) {
					onToolCallResolved(res);
				}

				// Finish new-chat setup only if navigation has not changed the active chat during the request.
				if (
					res.chat_id &&
					history.messages[responseMessageId] &&
					res.chat_id !== _chatId &&
					($chatId === _chatId || $chatId === res.chat_id)
				) {
					chatRequestQueues.update((q) => {
						if (!q[_chatId]?.length) return q;

						const { [_chatId]: pendingQueue, ...rest } = q;
						return {
							...rest,
							[res.chat_id]: [
								...pendingQueue.map((entry) => ({
									...entry,
									files: entry.files.map((file) =>
										file.type === 'filesystem' && file.session_id == null
											? { ...file, session_id: res.chat_id }
											: file
									)
								})),
								...(rest[res.chat_id] ?? [])
							]
						};
					});
					for (const file of userMessage?.files ?? [])
						if (file.type === 'filesystem' && file.session_id == null)
							file.session_id = res.chat_id;
					for (const file of history.messages[userMessage.id]?.files ?? [])
						if (file.type === 'filesystem' && file.session_id == null)
							file.session_id = res.chat_id;
					await chatId.set(res.chat_id);
					if (!$temporaryChat && !embedded) {
						// Carry the picks made on the new-chat page over to this chat
						saveDraft(getChatInputDraft(), res.chat_id, false);
						if (!initialPage)
							window.history.replaceState(window.history.state, '', `/c/${res.chat_id}`);
						await refreshChatList(localStorage.token);

						// Save chat params omitted from the completion request; the backend already saves files.
						if (Object.keys(params).length > 0) {
							await updateChatParams(localStorage.token, res.chat_id, params);
						}
					}
					await processNextInQueue(res.chat_id);
				}
			}
		}

		await tick();
		if (shouldAutoScrollResponse()) {
			scrollToBottom();
		}
		return res;
	};

	const handleOpenAIError = (error, responseMessage) => {
		const responseFailed = responseMessage.done && responseMessage.error;
		const errorMessage = getErrorMessage(error, $i18n.t('Server connection failed'));
		responseMessage.error = { content: errorMessage };
		responseMessage.done = true;
		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status) => status.action !== 'knowledge_search'
			);
		}
		history.messages[responseMessage.id] = responseMessage;
		if (!responseFailed) toast.error(errorMessage);
	};

	const stopResponse = async (processQueue = true, messageId = history.currentId) => {
		const responseMessage = messageId ? history.messages[messageId] : null;
		if (responseMessage && (responseMessage.user_id ?? chat?.user_id ?? $user?.id) !== $user?.id)
			return;
		eventTarget.dispatchEvent(new CustomEvent('voice:cancel_animation'));
		cancelBrowserInteractions();
		if (bridge?.connected && responseMessage) responseMessage.bridgeStopping = true;
		const hasTaskIds = (taskIds?.length ?? 0) > 0;
		const hasPendingAssistantResponse =
			!!$chatId &&
			(hasTaskIds || (responseMessage?.role === 'assistant' && responseMessage?.done !== true));

		if (hasTaskIds || hasPendingAssistantResponse) {
			if ($chatId) {
				await stopTasksByChatId(localStorage.token, $chatId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			} else {
				for (const taskId of taskIds) {
					const res = await stopTask(localStorage.token, taskId).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}
			}

			taskIds = null;

			// Set all response messages to done
			if (responseMessage?.parentId && history.messages[responseMessage.parentId]) {
				for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
					history.messages[messageId].done = true;
				}
			}

			if (shouldAutoScrollResponse()) {
				scrollToBottom();
			}
		}

		if (generating) {
			generating = false;
			generationController?.abort();
			generationController = null;
		}

		if (processQueue) {
			await processNextInQueue($chatId);
		}
	};

	const submitMessage = async (parentId, prompt) => {
		if (selectedModels.includes('')) {
			toast.error($i18n.t('Model not selected'));
			return;
		}
		let userPrompt = prompt;
		let userMessageId = uuidv4();

		let userMessage = {
			id: userMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'user',
			user_id: $user?.id,
			user: { id: $user?.id, name: $user?.name },
			content: userPrompt,
			models: selectedModels,
			timestamp: Math.floor(Date.now() / 1000) // Unix epoch
		};

		if (parentId !== null) {
			history.messages[parentId].childrenIds = [
				...history.messages[parentId].childrenIds,
				userMessageId
			];
		}

		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		await sendMessage(history, userMessageId);
	};

	const regenerateResponse = async (message, suggestionPrompt = null) => {
		console.log('regenerateResponse');

		if (history.currentId) {
			let userMessage = history.messages[message.parentId];

			if (!userMessage) {
				toast.error($i18n.t('Parent message not found'));
				return;
			}

			if (autoScroll) {
				scrollToBottom();
			}

			const currentModels = atSelectedModel ? [atSelectedModel.id] : selectedModels;
			const options = {
				...(suggestionPrompt
					? {
							messages: createMessagesList(history, message.id),
							regenerationPrompt: suggestionPrompt,
							regenerationMessageId: message.id
						}
					: {}),
				...((userMessage.models ?? currentModels).length > 1 && currentModels.length > 1
					? {
							// Regenerate the selected column with its current model.
							modelId: currentModels[message.modelIdx ?? 0] ?? message.model,
							modelIdx: message.modelIdx
						}
					: {})
			};
			userMessage.models = [...currentModels];
			await sendMessage(history, userMessage.id, options);
		}
	};

	const continueResponse = async (message) => {
		console.log('continueResponse');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.messages[message.id].done == true) {
			const responseMessage = history.messages[message.id];
			responseMessage.done = false;
			responseMessage.error = null;
			await tick();

			const model = ($models ?? [])
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				await sendMessageSocket(
					model,
					createMessagesList(history, responseMessage.id),
					history,
					responseMessage.id,
					_chatId,
					{ continueResponse: true }
				);
			}
		}
	};

	const mergeResponses = async (messageId, responses, _chatId) => {
		console.log('mergeResponses', messageId, responses);
		const message = history.messages[messageId];
		const mergedResponse = {
			status: true,
			content: ''
		};
		message.merged = mergedResponse;
		history.messages[messageId] = message;

		try {
			generating = true;
			const [res, controller] = await generateMoACompletion(
				localStorage.token,
				message.model ?? '',
				message.parentId ? history.messages[message.parentId].content : '',
				responses
			);

			if (res && res.ok && res.body && generating) {
				generationController = controller as AbortController;
				const textStream = await createOpenAITextStream(
					res.body,
					Boolean($settings?.splitLargeChunks ?? false)
				);
				for await (const update of textStream) {
					const { value, done, sources, error, usage } = update;
					if (error || done) {
						generating = false;
						generationController = null;
						break;
					}

					if (mergedResponse.content == '' && value == '\n') {
						continue;
					} else {
						mergedResponse.content += value;
						history.messages[messageId] = message;
					}

					autoScrollToBottom();
				}

				await saveChatHandler(_chatId, history);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		} finally {
			generating = false;
			generationController = null;
		}
	};

	const initChatHandler = async (_history: typeof history) => {
		let _chatId = $chatId;
		const selectedFolderId = $selectedFolder?.id ?? draftFolderId;
		const context = machineContext;

		if (!$temporaryChat) {
			const createdChat = await createNewChat(
				localStorage.token,
				{
					id: _chatId,
					title: draftTitle || $i18n.t('New Chat'),
					...(parentChatId && { originalChatId: parentChatId, branchPointMessageId }),
					models: selectedModels,
					machine_id: $selectedMachineId,
					working_directory:
						context?.machineId === $selectedMachineId ? context.currentDirectory : '',
					system: $settings.system ?? undefined,
					params: params,
					history: _history,
					files: chatFiles,
					messages: createMessagesList(_history, _history.currentId),
					tags: [],
					timestamp: Date.now()
				},
				selectedFolderId,
				chatVariables
			);

			if (!createdChat?.id) throw new Error($i18n.t('Failed to create chat'));
			if (!Object.values(_history.messages).some((message) => message.role === 'assistant')) {
				// A refused first message leaves no chat behind.
				await initializeMachineDirectory(createdChat.id, context).catch(async (error) => {
					if (await deleteChatById(localStorage.token, createdChat.id).catch(() => null))
						throw error;
				});
			}
			if (history !== _history || $chatId !== _chatId) return '';
			chat = createdChat;
			if (selectedFolderId) updateFolderChatLists(createdChat, selectedFolderId);
			_chatId = chat.id;
			await chatId.set(_chatId);
			if (tabbed) {
				loadedChatIdProp = _chatId;
				chatTitle.set(createdChat.chat?.title ?? createdChat.title);
				await onSelectEmbeddedChat?.(_chatId);
			}

			if (!embedded) {
				saveDraft(getChatInputDraft(), _chatId, false);
				if (!initialPage) window.history.replaceState(window.history.state, '', `/c/${_chatId}`);
			}

			await tick();

			// The sidebar catches up on its own; the reply does not wait for it.
			void refreshChatList(localStorage.token);
			if (selectedFolderId) void refreshFolderChatLists(selectedFolderId, chat);

			if ($chatId === _chatId && $selectedFolder?.id === selectedFolderId) selectedFolder.set(null);
		} else {
			_chatId = isTemporaryChatId(_chatId) ? _chatId : createTemporaryChatId($socket?.id);
			await chatId.set(_chatId);
		}
		await initializeMachineDirectory(_chatId, context);
		await tick();

		return _chatId;
	};

	const saveChatHandler = async (_chatId, history) => {
		if (isShared) return;
		if ($chatId == _chatId) {
			if (!$temporaryChat) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					files: chatFiles
				});
			}
		}
	};

	const saveParam = async (key: string, value: unknown) => {
		if (isShared || !$chatId || $temporaryChat || isTemporaryChatId($chatId)) return;
		await updateChatParams(localStorage.token, $chatId, { [key]: value }).catch((error) => {
			toast.error(`${error}`);
		});
	};

	const saveControls = async (models: string[] | null = null) => {
		if (isShared && !chat?.write_access) return;
		if (!$chatId || $temporaryChat || chat?.id !== $chatId) return;
		// Model choices are passed explicitly; automatic fallbacks must not be saved.
		if (!models?.length || !models.every(Boolean)) models = null;
		if (isShared && !models) return;
		if (!models && equal(chatFiles, chat.chat?.files ?? [])) return;
		const id = $chatId;

		const res = await updateChatById(localStorage.token, id, {
			...(!isShared ? { files: chatFiles } : {}),
			...(models ? { models } : {})
		}).catch((err) => {
			console.error('[controls autosave]', err);
			return null;
		});
		// Refresh the dedupe baseline so a later revert still saves.
		if (res && $chatId === id) chat = res;
	};

	const MAX_DRAFT_LENGTH = 5000;
	let saveDraftTimeout: ReturnType<typeof setTimeout> | null = null;
	// chatIdProp is empty for chats started from the home page (URL set via replaceState)
	const getDraftChatId = () => chatIdProp || $chatId || embeddedDraftKey || null;
	const getChatInputKey = (chatId: string | null = null) => {
		if (chatId) return `chat-input-${chatId}`;
		// Use the displayed pane: selectedFolder may already point to the destination.
		const folderId = !embedded && mainChatHref.match(/^\/folders\/([^/?#]+)/)?.[1];
		return folderId ? `chat-input-folder-${folderId}` : 'chat-input';
	};

	const getEmbeddedDraft = (text?: string, inputFiles: any[] = []) =>
		structuredClone({
			selectedModels: atSelectedModel ? [atSelectedModel.id] : selectedModels,
			params,
			history,
			chatFiles,
			chatVariables,
			temporary: $temporaryChat,
			machineId: $selectedMachineId,
			machineContext,
			controls: getChatInputControls(),
			prompt: text ?? '',
			files: inputFiles,
			submit: text !== undefined
		});

	const getChatInputControls = () => ({
		selectedToolIds,
		selectedSkillIds,
		selectedFilterIds,
		imageGenerationEnabled,
		selectedImageModelId,
		videoGenerationEnabled,
		selectedVideoModelId,
		webSearchEnabled,
		codeInterpreterEnabled
	});

	const getChatInputDraft = () => ({
		prompt,
		files: files
			.filter((file) => file.type !== 'image' && !(file.file instanceof File))
			.map((file) => ({
				...file,
				user: undefined,
				access_grants: undefined
			})),
		...getChatInputControls()
	});

	const saveDraft = async (draft: any, chatId: string | null = null, debounce = true) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}

		if (draft.prompt !== null && draft.prompt.length < MAX_DRAFT_LENGTH) {
			const key = getChatInputKey(chatId);
			const write = () => sessionStorage.setItem(key, JSON.stringify(draft));
			if (debounce) {
				saveDraftTimeout = setTimeout(write, 500);
			} else {
				write();
			}
		} else {
			sessionStorage.removeItem(getChatInputKey(chatId));
		}
	};

	const oauthRedirectHandler = async (
		tool: {
			id: string;
			serverId: string;
			authType?: string | null;
		},
		draft = getChatInputDraft()
	) => {
		if (tabbed) return;
		await tick();
		saveSessionSelectedModels();
		await saveDraft(draft, null, false);
		if (isSystemOAuthTool(tool.id)) {
			sessionStorage.setItem('pendingOAuthToolId', tool.id);
			localStorage.removeItem('token');
			window.location.href = '/auth?state=logout&form=signin';
			return;
		}
		initiateOAuthRedirect(tool);
	};

	const clearDraft = async (chatId: string | null = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}
		await sessionStorage.removeItem(getChatInputKey(chatId));
	};

	const moveChatHandler = async (chatId, folderId) => {
		if (chatId && folderId) {
			const res = await updateChatFolderIdById(localStorage.token, chatId, folderId).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				updateFolderChatLists(res, folderId);
				await refreshChatList(localStorage.token, { refreshPinned: true });
				await refreshFolderChatLists();

				toast.success($i18n.t('Chat moved successfully'));
			}
		} else {
			toast.error($i18n.t('Failed to move chat'));
		}
	};

	const archiveChatHandler = async (id: string) => {
		try {
			const res = await archiveChatById(localStorage.token, id);
			updateFolderChatLists({ id }, undefined, true);
			if (embedded) {
				if (chat) chat.archived = !!res?.archived;
				if (res?.archived) closeChatTabs(id);
			} else {
				initNewChat();
				await goto('/');
			}
			await refreshChatList(localStorage.token, { refreshPinned: true });
			await refreshFolderChatLists();
			toast.success(res?.archived ? $i18n.t('Chat archived.') : $i18n.t('Chat unarchived.'));
		} catch (error) {
			console.error('Error archiving chat:', error);
			toast.error($i18n.t('Failed to archive chat.'));
		}
	};

	let showDeleteConfirm = false;

	const confirmWebSearch = async () => {
		const userPrompt = pendingWebSearchPrompt;
		pendingWebSearchPrompt = null;
		webSearchConfirmed = true;

		if (userPrompt !== null) {
			await submitHandler(userPrompt);
		} else {
			webSearchEnabled = true;
		}
	};

	const deleteChatHandler = async (id: string) => {
		showDeleteConfirm = true;
	};

	const confirmDeleteChat = async () => {
		const id = $chatId;
		if (!id) return;

		try {
			const res = await deleteChatById(localStorage.token, id);
			if (res) {
				updateFolderChatLists({ id }, undefined, true);
				closeChatTabs(id);
				if (!embedded) {
					initNewChat();
					await goto('/');
				}
				await refreshChatList(localStorage.token, { refreshPinned: true });
				await refreshFolderChatLists();
				allTags.set(await getAllTags(localStorage.token));
				toast.success($i18n.t('Chat deleted.'));
			}
		} catch (error) {
			console.error('Error deleting chat:', error);
			toast.error(`${error}`);
		}
	};
</script>

{#snippet renderChatMenu()}
	<ChatMenu
		chat={{
			id: $chatId,
			archived: chat?.archived ?? false,
			folder_id: chat?.folder_id,
			meta: chat?.meta,
			chat: {
				title: $chatTitle,
				models: selectedModels,
				system: $settings.system ?? undefined,
				params: params,
				history: history,
				timestamp: Date.now()
			}
		}}
		shareEnabled={!!history.currentId}
		readOnly={isShared}
		temporary={$temporaryChat}
		scrollToTop={!isNearTop ? scrollToTop : null}
		shareHandler={() => (showShareModal = true)}
		renameHandler={startRename}
		archiveChatHandler={() => archiveChatHandler($chatId)}
		deleteChatHandler={() => deleteChatHandler($chatId)}
		{moveChatHandler}
	>
		<button
			type="button"
			class="flex shrink-0 cursor-pointer items-center justify-center {tabbed || fullWidthTabs
				? 'size-4 rounded text-base-400 hover:bg-base-200 hover:text-base-700 dark:hover:bg-base-0/10 dark:hover:text-base-0'
				: 'size-6 rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200'}"
			id={embedded ? undefined : 'chat-context-menu-button'}
			aria-label={$i18n.t('Chat actions')}
		>
			<EllipsisHorizontal
				className={tabbed || fullWidthTabs ? 'size-3' : 'size-4.5'}
				strokeWidth="1.5"
			/>
		</button>
	</ChatMenu>
{/snippet}

{#snippet renderTitleEditor()}
	<input
		bind:this={titleInput}
		bind:value={titleDraft}
		class="min-w-0 flex-1 bg-transparent {tabbed || fullWidthTabs
			? 'text-sm'
			: 'md:py-1 text-[0.9375rem]'} font-normal text-base-700 outline-hidden dark:text-base-300"
		aria-label={$i18n.t('Title')}
		placeholder={generatingTitle ? $i18n.t('Generating...') : ''}
		disabled={generatingTitle}
		on:click|stopPropagation
		on:keydown={(e) => {
			if (e.isComposing || e.keyCode === 229) return;

			if (e.key === 'Enter') {
				e.preventDefault();
				editChatTitle();
			} else if (e.key === 'Escape') {
				e.preventDefault();
				editingTitle = false;
			}
		}}
		on:blur={editChatTitle}
	/>

	<Tooltip content={$i18n.t('Generate')}>
		<button
			class="flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-lg text-base-500 transition hover:bg-base-50/40 hover:text-base-700 disabled:cursor-not-allowed dark:text-base-400 dark:hover:bg-base-800/40 dark:hover:text-base-200"
			aria-label={$i18n.t('Generate')}
			disabled={generatingTitle}
			on:mousedown={(e) => e.preventDefault()}
			on:click|stopPropagation={() => {
				generateChatTitle();
			}}
		>
			<Sparkles className={tabbed || fullWidthTabs ? 'size-3.5' : 'size-4'} strokeWidth="1.5" />
		</button>
	</Tooltip>
{/snippet}

<audio bind:this={audioElement} style="display: none;"></audio>

{#if getChatVariablesForm(selectedModelIds, chatVariables, $models ?? []).conflicts.length > 0}
	<Modal ariaLabel={$i18n.t('Chat Variables')} bind:show={showChatVariablesModal} size="md">
		<div>
			<div class="flex justify-between px-4 pt-3 pb-1 dark:text-base-300">
				<div class="self-center text-sm font-medium">{$i18n.t('Chat Variables')}</div>
				<button
					aria-label={$i18n.t('Close')}
					class="self-center rounded-lg py-1 text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 px-0"
					on:click={() => {
						showChatVariablesModal = false;
					}}
				>
					<XMark className="size-4" />
				</button>
			</div>

			<div class="px-5 pb-4 text-sm text-base-600 dark:text-base-300">
				<div class="mb-2 text-xs text-base-500 dark:text-base-400">
					{$i18n.t('Selected models define incompatible Chat Variables.')}
				</div>
				<div class="flex flex-col gap-1">
					{#each getChatVariablesForm(selectedModelIds, chatVariables, $models ?? []).conflicts as conflict}
						<div class="rounded-lg border border-red-200 px-3 py-2 text-xs dark:border-red-900/60">
							<div class="font-medium text-red-600 dark:text-red-400">{conflict.key}</div>
							<div class="mt-1 text-base-500 dark:text-base-400">
								{conflict.modelIds.join(', ')}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	</Modal>
{:else}
	<InputVariablesModal
		bind:show={showChatVariablesModal}
		title={$i18n.t('Chat Variables')}
		variables={getChatVariablesForm(selectedModelIds, chatVariables, $models ?? []).variables}
		onSave={saveChatVariables}
	/>
{/if}

<EventConfirmDialog
	show={pendingUrlActions !== null}
	title={$i18n.t('Open link')}
	on:confirm={async () => {
		const actions = pendingUrlActions;
		const url = $page.url.href;
		pendingUrlActions = null;
		if (!actions) return;
		for (const source of actions.urls) {
			if ($page.url.href !== url) return;
			await uploadWeb(source);
		}
		if (actions.call && $page.url.href === url) openCallOverlay();
	}}
	on:cancel={() => (pendingUrlActions = null)}
>
	<div class="text-sm text-base-500 space-y-2 max-h-60 overflow-auto break-words">
		{#if pendingUrlActions?.urls.length}
			<p>{$i18n.t('Load content from these URLs?')}</p>
			{#each pendingUrlActions.urls as url}
				<p>{url}</p>
			{/each}
		{/if}
		{#if pendingUrlActions?.call}
			<p>{$i18n.t('Start a voice call using your microphone?')}</p>
		{/if}
	</div>
</EventConfirmDialog>

<WebSearchConfirmDialog
	bind:show={showWebSearchConfirm}
	title={$i18n.t('Use Web Search?')}
	message={($config?.features?.web_search_confirmation_content ?? '').trim() !== ''
		? ($config?.features?.web_search_confirmation_content ?? '')
		: $i18n.t('Your query will be sent to the configured web search provider.')}
	confirmLabel={$i18n.t('Continue')}
	cancelLabel={$i18n.t('Cancel')}
	on:confirm={confirmWebSearch}
	on:cancel={() => {
		if (pendingWebSearchPrompt === null) {
			webSearchEnabled = false;
		}
		pendingWebSearchPrompt = null;
	}}
/>

<ShareChatModal bind:show={showShareModal} chatId={$chatId} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		confirmDeleteChat();
	}}
>
	<div class=" text-sm text-base-500 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="  font-normal">{$chatTitle}</span>.
	</div>
</DeleteConfirmDialog>

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	inputType={eventConfirmationInputType}
	inputOptions={eventConfirmationInputOptions}
	on:confirm={(e) => {
		if (eventConfirmationInput) {
			eventCallback(e.detail);
		} else if (e.detail) {
			eventCallback(e.detail);
		} else {
			eventCallback(true);
		}
	}}
	on:cancel={() => {
		eventCallback(false);
	}}
/>

{#if browserInteraction?.type === 'request:elicitation'}
	{#key browserInteraction.id}
		{@const interaction = browserInteraction}
		<ElicitationDialog
			data={interaction.data}
			onResponse={(value) => resolveBrowserInteraction(interaction, value)}
		/>
	{/key}
{/if}

{#if browserInteraction?.data?.tool_call}
	{#key browserInteraction.id}
		{@const interaction = browserInteraction}
		<EventConfirmDialog
			show={true}
			title={$i18n.t('Tool Permissions')}
			confirmLabel={$i18n.t('Allow')}
			cancelLabel={$i18n.t('Deny')}
			on:confirm={() => resolveBrowserInteraction(interaction, true)}
			on:cancel={() => resolveBrowserInteraction(interaction, false)}
		>
			<div class="text-sm text-base-500">
				<div class="font-medium break-all">{interaction.data.tool_call.name}</div>
				<pre class="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(
						interaction.data.tool_call.arguments,
						null,
						2
					)}</pre>
			</div>
		</EventConfirmDialog>
	{/key}
{/if}

<div
	class="{embedded
		? 'h-full'
		: 'h-screen max-h-[100dvh]'} transition-width duration-200 ease-in-out {$showSidebar &&
	!embedded
		? '  md:max-w-[calc(100%-var(--sidebar-width))]'
		: ' '} w-full max-w-full min-w-0 flex flex-col"
	id={chatContainerId}
	data-chat={embedded ? instanceId : 'main'}
	role="presentation"
	on:dragover|capture={(event) => tabs?.handleChatDragOver(event)}
	on:drop|capture={(event) => tabs?.handleChatDrop(event)}
	on:dragleave={(event) => tabs?.handleChatDragLeave(event)}
>
	<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
		{#if backgroundImage}
			<div
				class="pointer-events-none absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
				style="background-image: url({backgroundImage})"
			/>
			<div
				class="pointer-events-none absolute top-0 left-0 w-full h-full bg-linear-to-t from-base-0/90 to-base-0/55 dark:from-base-900/90 dark:to-base-900/65 z-0"
			></div>
		{/if}

		<div class="relative w-full h-full min-h-0 flex">
			<div
				class="h-full flex relative max-w-full min-w-0 min-h-0 flex-1 flex-col col-start-1 row-start-2"
				class:hidden={fullWidthTabs && !mainChatActive}
				style={fullWidthTabs ? mainChatStyle : undefined}
				data-main-chat-pane
				data-chat-id={$chatId}
				data-panel-group={fullWidthTabs ? mainChatGroupId : undefined}
				on:focusin={() => fullWidthTabs && tabs?.focusMainChat()}
				on:pointerdown={() => fullWidthTabs && tabs?.focusMainChat()}
				id={fullWidthTabs ? 'chat-panel-main-chat-view' : undefined}
				role={fullWidthTabs ? 'tabpanel' : undefined}
				aria-labelledby={fullWidthTabs ? 'chat-panel-main-chat' : undefined}
			>
				<!-- An empty new chat keeps its input on screen while it sets itself up. -->
				{#if loading && (embedded || $page.url.pathname !== '/' || history.currentId)}
					{#if !fullWidthTabs && !embeddedCollapsed}
						<div class="flex items-center justify-center h-full w-full">
							<Spinner className="size-5" />
						</div>
					{/if}
				{:else}
					<FilesOverlay show={dragged} />
					{#if embedded && !tabbed && !embeddedCollapsed}
						<div
							class="h-8 shrink-0 flex items-center justify-between gap-2 border-b border-base-50/80 pb-1 text-base-700 dark:border-base-850/40 dark:text-base-200 {embeddedInset
								? 'px-4'
								: 'px-3'}"
						>
							<div class="flex min-w-0 items-center gap-2">
								<EmbeddedChatHistoryDropdown
									title={embeddedHeaderTitle}
									chats={embeddedChats}
									canCreateNew={!!onNewEmbeddedChat &&
										Object.keys(history?.messages ?? {}).length > 0}
									{loading}
									onNewChat={onNewEmbeddedChat}
									onSelectChat={onSelectEmbeddedChat}
									onDeleteChat={onDeleteEmbeddedChat}
								/>
							</div>
							{#if onCollapseEmbedded}<Tooltip content={$i18n.t('Collapse')} placement="bottom">
									<button
										type="button"
										class="rounded-md py-1 text-base-500 transition hover:text-base-900 dark:hover:text-base-0 px-0"
										on:click={() => onCollapseEmbedded?.()}
										aria-label={$i18n.t('Collapse')}
									>
										<ChevronDown className="size-4" strokeWidth="2" />
									</button>
								</Tooltip>{/if}
							{#if onCloseEmbedded}<Tooltip content={$i18n.t('Close')} placement="bottom">
									<button
										type="button"
										class="rounded-md py-1 text-base-500 transition hover:text-base-900 dark:hover:text-base-0 px-0"
										on:click={() => onCloseEmbedded?.()}
										aria-label={$i18n.t('Close')}
									>
										<XMark className="size-4" strokeWidth="2" />
									</button>
								</Tooltip>{/if}
						</div>
					{:else if !embedded}
						<Navbar
							tabbed={fullWidthTabs}
							{tabTitleEditor}
							{chatMenu}
							bind:tabActions
							bind:tabBarActions
							{liveParticipants}
							chat={{
								id: $chatId,
								archived: chat?.archived ?? false,
								folder_id: chat?.folder_id,
								chat: {
									title: $chatTitle,
									models: selectedModels,
									system: $settings.system ?? undefined,
									params: params,
									history: history,
									timestamp: Date.now()
								}
							}}
							{history}
							title={$chatTitle}
							{initNewChat}
							{onTemporaryChange}
							{deleteChatHandler}
							onSaveTempChat={async () => {
								try {
									if (!history?.currentId || !Object.keys(history.messages).length) {
										toast.error($i18n.t('No conversation to save'));
										return;
									}
									const messages = createMessagesList(history, history.currentId);
									const title =
										messages.find((m) => m.role === 'user')?.content ?? $i18n.t('New Chat');

									const savedChat = await createNewChat(
										localStorage.token,
										{
											id: uuidv4(),
											title: title.length > 50 ? `${title.slice(0, 50)}...` : title,
											models: selectedModels,
											machine_id: $selectedMachineId,
											working_directory:
												machineContext?.machineId === $selectedMachineId
													? machineContext.currentDirectory
													: '',
											params: params,
											history: history,
											messages: messages,
											timestamp: Date.now()
										},
										null,
										chatVariables
									);

									if (savedChat) {
										temporaryChat.set(false);
										chatId.set(savedChat.id);
										await refreshChatList(localStorage.token);

										await goto(`/c/${savedChat.id}`);
										toast.success($i18n.t('Conversation saved successfully'));
									}
								} catch (error) {
									console.error('Failed to save temporary chat:', error);
									toast.error($i18n.t('Failed to save conversation'));
								}
							}}
						/>
					{/if}
					<div
						id="chat-pane"
						class="flex min-h-0 flex-col flex-auto z-10 w-full @container {embeddedCollapsed
							? 'overflow-visible'
							: 'overflow-auto'}"
					>
						<div class="sr-only" aria-live="polite" aria-atomic="true">{liveStatus}</div>
						{#if (!tabbed && $settings?.landingPageMode === 'chat' && !$selectedFolder) || (!contextOnly && createMessagesList(history, history.currentId).length > 0)}
							<div
								class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
								class:hidden={embeddedCollapsed}
								class:px-2={embeddedInset}
								id={messagesContainerId}
								bind:this={messagesContainerElement}
								on:scroll={(e) => {
									if (!messagesContainerElement) return;
									const { scrollTop, scrollHeight, clientHeight } = messagesContainerElement;
									// Content growing below the viewport must not stop following.
									autoScroll =
										scrollHeight - scrollTop <= clientHeight + 5 ||
										(autoScroll && scrollTop >= lastScrollTop);
									lastScrollTop = scrollTop;
								}}
							>
								<div class=" h-full w-full flex flex-col">
									<Messages
										{messagesContainerId}
										{branchPointMessageId}
										bind:this={messagesRef}
										chatId={$chatId}
										user={chatOwner ?? (chat ? { id: chat.user_id } : $user)}
										readOnly={isShared}
										writeAccess={!!chat?.write_access}
										bind:history
										bind:autoScroll
										bind:prompt
										setInputText={(text) => {
											messageInput?.setTextHandler(text);
										}}
										bind:selectedModels
										{atSelectedModel}
										className={embedded || fullWidthTabs ? 'h-full flex pt-4' : 'h-full flex pt-18'}
										{sendMessage}
										{showMessage}
										{submitMessage}
										{continueResponse}
										{regenerateResponse}
										{mergeResponses}
										{chatActionHandler}
										{addMessages}
										{onToolCallResolved}
										allowDelete={!(generating || taskIds?.length)}
										forkHandler={$temporaryChat ? null : handleForkChat}
										topPadding={!embedded && !fullWidthTabs}
										bottomPadding={files.length > 0}
										{onSelect}
										{onInsertToNote}
										onOpenArtifacts={canOpenArtifacts ? openArtifacts : null}
									/>
								</div>
							</div>

							{#if isShared && !chat?.write_access}
								{#if canClone}
									<div
										class="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center gap-2 bg-linear-to-t from-base-0 dark:from-base-900 to-transparent pb-5 pt-10"
									>
										<button
											class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0 pointer-events-auto"
											disabled={cloning}
											on:click={cloneSharedChat}
										>
											{$i18n.t('Clone Chat')}
										</button>
									</div>
								{/if}
							{:else}
								<div
									id={embedded ? messageInputDropzoneId : undefined}
									class=" pb-2 {dragged ? 'z-0' : 'z-10'}"
								>
									<MessageInput
										{selectedMachineId}
										{machineSkills}
										{messagesContainerId}
										{inputId}
										{onTemporaryChange}
										bind:machineContext
										{typingUsers}
										on:typing={(event) => emitTyping(event.detail)}
										callActive={!!(bridge?.connected || bridge?.connecting)}
										callEnabled={!isShared}
										bind:this={messageInput}
										history={inputHistory}
										{taskIds}
										bind:selectedModels
										onModelSelect={saveControls}
										bind:chatFiles
										bind:params
										onParamChange={saveParam}
										bind:files
										bind:prompt
										bind:autoScroll
										bind:selectedToolIds
										bind:selectedSkillIds
										bind:selectedFilterIds
										bind:imageGenerationEnabled
										bind:selectedImageModelId
										bind:videoGenerationEnabled
										bind:selectedVideoModelId
										bind:codeInterpreterEnabled
										{pendingOAuthTools}
										{oauthRedirectHandler}
										bind:webSearchEnabled
										bind:atSelectedModel
										bind:showCommands
										bind:dragged
										{dropzoneId}
										chatId={$chatId}
										{contextUsage}
										{contextCompactionEnabled}
										{embedded}
										autofocus={!embeddedCollapsed}
										{onRecordedAudio}
										compactHandler={handleManualCompact}
										statusHandler={handleStatusCommand}
										forkHandler={handleForkChat}
										{toolApprovalMode}
										onToolApprovalModeChange={handleToolApprovalModeChange}
										{generating}
										{stopResponse}
										{createMessagePair}
										{onUpload}
										{onUpdate}
										{messageQueue}
										{chatTasks}
										askUser={savedAskUserPrompt ?? socketAskUserPrompt}
										onQueueSendNow={sendQueuedMessageNow}
										onQueueEdit={editQueuedMessage}
										onQueueDelete={deleteQueuedMessage}
										onChange={(data: any) => {
											if (!loading && !$temporaryChat) {
												saveDraft(data, getDraftChatId());
											}
										}}
										onWebSearchToggle={handleWebSearchToggle}
										on:chatVariables={() => {
											showChatVariablesModal = true;
										}}
										on:submit={async (e) => {
											clearDraft(getDraftChatId());
											if (e.detail || files.length > 0) {
												await tick();

												submitHandler(withSelectedText(e.detail));
											}
										}}
									/>

									<div
										class="absolute bottom-1 text-xs text-base-500 text-center line-clamp-1 right-0 left-0"
									>
										<!-- {$i18n.t('LLMs can make mistakes. Verify important information.')} -->
									</div>
								</div>
							{/if}
						{:else if embedded}
							<div class="flex h-full min-h-0 flex-col justify-end">
								{#if tabbed}
									<div class="flex flex-1 items-center justify-center px-6">
										<div class="max-w-56 text-center">
											<p class="text-sm font-normal text-base-600 dark:text-base-300">
												{$temporaryChat ? $i18n.t('Temporary chat') : $i18n.t('New Chat')}
											</p>
											<p class="mt-1.5 text-xs leading-relaxed text-base-400 dark:text-base-500">
												{$temporaryChat
													? $i18n.t('Messages disappear when you close this tab.')
													: $i18n.t('Messages are saved to your chats.')}
											</p>
										</div>
									</div>
									{#if modelSuggestionPrompts?.length}
										<div class="mx-auto w-full max-w-2xl px-5 pb-3">
											<Suggestions
												suggestionPrompts={modelSuggestionPrompts}
												inputValue={prompt}
												{onSelect}
											/>
										</div>
									{/if}
								{:else if suggestedPrompts.length > 0 && !embeddedCollapsed}
									<div class="flex flex-1 items-end px-5 pb-8">
										<div class="w-full">
											<div class="mb-2 text-[0.75rem] text-base-300 dark:text-base-700">
												{$i18n.t('Suggested prompts')}
											</div>
											<div class="flex flex-col">
												{#each suggestedPrompts as suggestion}
													<button
														type="button"
														class="flex min-h-8 w-full items-center justify-between py-1 text-left text-[0.8125rem] leading-5 text-base-500 transition hover:text-base-700 dark:text-base-500 dark:hover:text-base-300"
														on:click={async () => {
															await tick();
															await submitHandler(withSelectedText(suggestion));
														}}
													>
														<span class="min-w-0 truncate">{suggestion}</span>
													</button>
												{/each}
											</div>
										</div>
									</div>
								{/if}
								<div id={embedded ? messageInputDropzoneId : undefined} class="pb-2 z-10">
									<MessageInput
										{selectedMachineId}
										{machineSkills}
										{messagesContainerId}
										{inputId}
										{onTemporaryChange}
										bind:machineContext
										{typingUsers}
										on:typing={(event) => emitTyping(event.detail)}
										callActive={!!(bridge?.connected || bridge?.connecting)}
										callEnabled={!isShared}
										bind:this={messageInput}
										history={inputHistory}
										{taskIds}
										bind:selectedModels
										onModelSelect={saveControls}
										bind:chatFiles
										bind:params
										onParamChange={saveParam}
										bind:files
										bind:prompt
										bind:autoScroll
										bind:selectedToolIds
										bind:selectedSkillIds
										bind:selectedFilterIds
										bind:imageGenerationEnabled
										bind:selectedImageModelId
										bind:videoGenerationEnabled
										bind:selectedVideoModelId
										bind:codeInterpreterEnabled
										{pendingOAuthTools}
										{oauthRedirectHandler}
										bind:webSearchEnabled
										bind:atSelectedModel
										bind:showCommands
										bind:dragged
										{dropzoneId}
										chatId={$chatId}
										{contextUsage}
										{contextCompactionEnabled}
										{embedded}
										autofocus={!embeddedCollapsed}
										{onRecordedAudio}
										compactHandler={handleManualCompact}
										statusHandler={handleStatusCommand}
										forkHandler={handleForkChat}
										{toolApprovalMode}
										onToolApprovalModeChange={handleToolApprovalModeChange}
										{generating}
										{stopResponse}
										{createMessagePair}
										{onUpload}
										{onUpdate}
										{messageQueue}
										{chatTasks}
										askUser={savedAskUserPrompt ?? socketAskUserPrompt}
										onQueueSendNow={sendQueuedMessageNow}
										onQueueEdit={editQueuedMessage}
										onQueueDelete={deleteQueuedMessage}
										onChange={(data: any) => {
											if (!loading && !$temporaryChat) {
												saveDraft(data, getDraftChatId());
											}
										}}
										onWebSearchToggle={handleWebSearchToggle}
										on:chatVariables={() => {
											showChatVariablesModal = true;
										}}
										on:submit={async (e) => {
											clearDraft(getDraftChatId());
											if (e.detail || files.length > 0) {
												await tick();
												submitHandler(withSelectedText(e.detail));
											}
										}}
									/>
								</div>
							</div>
						{:else}
							<div
								class="flex h-full {$selectedFolder
									? 'min-h-0 flex-1 overflow-hidden'
									: 'items-center'}"
							>
								<Placeholder
									onNewFolderChat={() => tabs?.openFeatureTab('chat')}
									bind:folderTabActions
									{selectedMachineId}
									{machineSkills}
									chatId={$chatId}
									{onTemporaryChange}
									bind:machineContext
									callActive={!!(bridge?.connected || bridge?.connecting)}
									callEnabled={!isShared}
									bind:selectedModelIdx
									{history}
									bind:selectedModels
									onModelSelect={saveControls}
									bind:chatFiles
									bind:params
									onParamChange={saveParam}
									bind:messageInput
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedSkillIds
									bind:selectedFilterIds
									bind:imageGenerationEnabled
									bind:selectedImageModelId
									bind:videoGenerationEnabled
									bind:selectedVideoModelId
									bind:codeInterpreterEnabled
									bind:webSearchEnabled
									bind:atSelectedModel
									bind:showCommands
									bind:dragged
									{toolApprovalMode}
									onToolApprovalModeChange={handleToolApprovalModeChange}
									{pendingOAuthTools}
									{oauthRedirectHandler}
									{stopResponse}
									{createMessagePair}
									{onSelect}
									{onUpload}
									{onUpdate}
									{messageQueue}
									askUser={savedAskUserPrompt ?? socketAskUserPrompt}
									onQueueSendNow={sendQueuedMessageNow}
									onQueueEdit={editQueuedMessage}
									onQueueDelete={deleteQueuedMessage}
									onWebSearchToggle={handleWebSearchToggle}
									on:chatVariables={() => {
										showChatVariablesModal = true;
									}}
									onChange={(data: any) => {
										if (!loading && !$temporaryChat) {
											saveDraft(data, getDraftChatId());
										}
									}}
									on:submit={async (e) => {
										clearDraft(getDraftChatId());
										if (e.detail || files.length > 0) {
											await tick();
											submitHandler(withSelectedText(e.detail));
										}
									}}
								/>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Restored tabs resolve their machines on mount, so they wait for the lists. -->
			{#if !embedded && $models !== null}
				<Tabs
					{mainChatHref}
					{getEmbeddedDraft}
					chatLoading={loading}
					chatStreaming={streaming}
					bind:fullWidth={fullWidthTabs}
					bind:mainChatActive
					bind:mainChatStyle
					bind:mainChatGroupId
					title={$chatTitle || $i18n.t('New Chat')}
					mainTabFolder={!$chatId && $selectedFolder
						? {
								id: $selectedFolder.id,
								name: $selectedFolder.name,
								icon: $selectedFolder.meta?.icon,
								canEdit:
									$user?.role === 'admin' ||
									$selectedFolder.user_id === $user?.id ||
									$selectedFolder.write_access
							}
						: null}
					tabTitleEditor={loading ? undefined : tabTitleEditor}
					onRenameMainTab={startRename}
					onRenameFolder={renameFolder}
					tabActions={loading
						? undefined
						: !$chatId && $selectedFolder
							? folderTabActions
							: tabActions}
					tabBarActions={loading ? undefined : tabBarActions}
					{machineContext}
					bind:chatHistory={history}
					bind:files
					chatId={$chatId}
					mainArtifacts={artifacts}
					bind:this={tabs}
					folderId={chat ? (chat.folder_id ?? null) : ($selectedFolder?.id ?? null)}
					chatUser={chatOwner}
					modelId={selectedModelIds?.at(0) ?? null}
					{canOpenChatTab}
					systemPrompt={params?.system || $settings.system || ''}
					submitPrompt={submitHandler}
					onAskFile={askFile}
					onDraftPrompt={draftPrompt}
					{stopResponse}
					{bridge}
					bind:callMode
					{showMessage}
					{eventTarget}
					{codeInterpreterEnabled}
				/>
			{/if}
		</div>
	</div>
</div>

<style>
	:global(:where(html:not(.native-scrollbars))) ::-webkit-scrollbar {
		height: 0.5rem;
		width: 0.5rem;
	}
</style>
