<script lang="ts">
	import type { TerminalContext } from '$lib/types';
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { getContext, setContext, onDestroy, onMount, tick } from 'svelte';
	import { fade } from 'svelte/transition';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { goto, beforeNavigate } from '$app/navigation';
	import { page } from '$app/stores';

	import { get, writable, type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import equal from 'fast-deep-equal';

	import {
		chatId,
		config,
		type Model,
		models,
		tags as allTags,
		settings,
		showSidebar,
		WEBUI_NAME,
		banners,
		user,
		socket,
		audioQueue,
		showControls,
		showCallOverlay,
		temporaryChatEnabled,
		mobile,
		chatTitle,
		showArtifacts,
		artifactContents,
		tools,
		skills,
		terminalSkills,
		toolServers,
		terminalServers,
		functions,
		selectedFolder,
		showEmbeds,
		selectedTerminalId,
		showFileNavPath,
		showFileNavDir,
		chatRequestQueues,
		desktopEvent
	} from '$lib/stores';
	import { refreshChatList, refreshFolderChatLists } from '$lib/stores/chatList';

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
	import { createTemporaryChatId, isTemporaryChatId } from '$lib/utils/chatId';
	import {
		applyResponseStreamEvent,
		getOutputText,
		setOutputText
	} from './Messages/structuredOutput';

	import {
		addTagById,
		archiveChatById,
		compactChatById,
		createNewChat,
		deleteChatById,
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
	import type { FilesystemFile } from '$lib/apis/terminal';
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
	import ChatControls from './ChatControls.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import ElicitationDialog from './ElicitationDialog.svelte';
	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import WebSearchConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
	import NotificationToast from '../NotificationToast.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Modal from '../common/Modal.svelte';
	import { isEmbedWindow } from '../common/FullHeightIframe.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import Image from '../common/Image.svelte';
	import XMark from '../icons/XMark.svelte';
	import EmbeddedChatHistoryDropdown from './EmbeddedChatHistoryDropdown.svelte';
	import InputVariablesModal from './MessageInput/InputVariablesModal.svelte';

	export let chatIdProp = '';
	export let embedded = false;
	export let embeddedTitle = '';
	export let embeddedChats = [];
	export let embeddedDraftKey = '';
	export let suggestedPrompts = [];
	export let selectedText = '';
	export let onInsertToNote: ((content: string) => void) | null = null;
	export let onCloseEmbedded: (() => void) | null = null;
	export let onNewEmbeddedChat: (() => void | Promise<void>) | null = null;
	export let onCreateEmbeddedChat: (() => any | Promise<any>) | null = null;
	export let onSelectEmbeddedChat: ((chatId: string) => void | Promise<void>) | null = null;
	export let onDeleteEmbeddedChat: ((chatId: string) => void | Promise<void>) | null = null;
	export let onEmbeddedChatTitle: ((chatId: string, title: string) => void | Promise<void>) | null =
		null;

	let loading = true;
	$: chatContainerId = embedded ? 'note-chat-container' : 'chat-container';
	$: messageInputDropzoneId = embedded ? 'note-chat-input-dropzone' : 'chat-pane';

	const eventTarget = new EventTarget();

	let messageInput: MessageInput | undefined;
	let messagesRef: Messages | undefined;

	let autoScroll = true;
	let lastScrollTop = 0;
	let isNearTop = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	let navbarElement;

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
			$models.find((model) => model.id === selectedModels[selectedModelIdx])?.info?.meta
				?.background_image_url ||
			($settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url);

	let atSelectedModel: Model | undefined;
	let selectedModelIds: string[] = [];
	$: if (atSelectedModel !== undefined) {
		selectedModelIds = [atSelectedModel.id];
	} else {
		selectedModelIds = selectedModels;
	}
	let serverContextUsage = null;
	let contextUsage = null;

	const normalizeSelectedModels = (modelIds: string[] = []) => {
		const selected = resolveDefaultModelIds(
			$models,
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
			$models.length > 0 &&
			!selectedModels?.some((modelId) => modelId) &&
			!modelSearchParam
		) {
			const fallbackModels = normalizeSelectedModels(selectedModels);
			if (!equal(fallbackModels, selectedModels)) {
				selectedModels = fallbackModels;
			}
		}
	}

	const estimateTokens = (value) => {
		if (value === null || value === undefined || value === '') {
			return 0;
		}
		if (typeof value !== 'string') {
			try {
				value = JSON.stringify(value);
			} catch {
				value = String(value);
			}
		}
		return Math.max(1, Math.floor(value.length / 4));
	};

	const estimateMessagesTokens = (messages) =>
		messages.reduce((total, message) => {
			let next = total + 4 + estimateTokens(message.content);
			next += estimateTokens(message.output);
			next += estimateTokens(message.tool_calls);
			if (message.files?.length) {
				next += estimateTokens(
					JSON.stringify(message.files).replace(/data:[\w/+.;=%-]*;base64,[A-Za-z0-9+/=]*/g, '')
				);
			}
			return next;
		}, 0);

	$: contextCompactionEnabled = Boolean($config?.features?.enable_context_compaction);

	const getContextThreshold = () => {
		const modelId = atSelectedModel?.id ?? selectedModels.find((id) => id);
		const model = $models.find((item) => item.id === modelId);
		const threshold = Number(
			model?.info?.params?.compact_token_threshold ?? params?.compact_token_threshold
		);
		return Number.isFinite(threshold) && threshold > 0 ? threshold : null;
	};

	const getContextUsage = () => {
		if (!history?.currentId) {
			return null;
		}

		const messages = createMessagesList(history, history.currentId);
		const threshold = contextCompactionEnabled
			? (getContextThreshold() ?? serverContextUsage?.threshold ?? null)
			: null;
		const systemTokens = estimateTokens($settings?.system ?? '');
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
				estimatedTokens = usageTokens + estimateMessagesTokens(activeMessages.slice(idx + 1));
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

	$: contextUsage = getContextUsage() ?? (contextCompactionEnabled ? serverContextUsage : null);
	$: embeddedHeaderTitle = embeddedTitle || $chatTitle || $i18n.t('Chat');

	let selectedToolIds: string[] = [];
	let selectedSkillIds: string[] = [];
	let selectedFilterIds: string[] = [];
	let pendingOAuthTools = [];

	let imageGenerationEnabled = false;
	let webSearchEnabled = false;
	let codeInterpreterEnabled = false;
	let webSearchActive = false;
	let showWebSearchConfirm = false;
	let pendingWebSearchPrompt: string | null = null;
	let webSearchConfirmed = false;

	$: {
		const currentModels = atSelectedModel?.id ? [atSelectedModel.id] : selectedModels;
		const allModelsSupportWebSearch =
			currentModels.filter(
				(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
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
	const contextCompactions = writable<Record<string, 'in_progress' | { error: string }>>({});
	setContext('contextCompactions', contextCompactions);
	let compactionChatId = '';
	$: if (compactionChatId !== $chatId) {
		contextCompactions.set({});
		compactionChatId = $chatId;
	}

	let chat: any = null;
	let tags = [];

	// Non-owners may reply when the sharing mode allows it, but cannot save chat edits.
	$: isShared = chat != null && chat.user_id !== $user?.id;
	$: if (isShared && $showCallOverlay) showCallOverlay.set(false);
	$: canClone = isShared && ($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true));
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
				await goto(`/c/${copy.id}`);
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

	let taskIds = null;
	let liveStatus = '';

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
	let prompt = '';
	let chatFiles = [];
	let files: any[] = [];
	let terminalContext: TerminalContext | null = null;
	const askFile = async (instruction: string, file: FilesystemFile) => {
		const attachments = [structuredClone(file)];
		const last = history.currentId ? history.messages[history.currentId] : null;
		if (last?.role === 'assistant' && !last.done) {
			chatRequestQueues.update((queues) => ({
				...queues,
				[$chatId]: [
					...(queues[$chatId] ?? []),
					{ id: uuidv4(), prompt: instruction, files: attachments }
				]
			}));
		} else await submitPrompt(instruction, attachments);
	};

	let params = {};
	let chatVariables = {};
	let showChatVariablesModal = false;
	let loadedChatIdProp = '';
	let currentDraftKey = '';

	// Chat parameters own the approval mode; chats without an override use the user default.
	$: toolApprovalMode =
		(params?.tool_approval_mode ?? $settings?.params?.tool_approval_mode) === 'ask'
			? 'ask'
			: 'full';

	const handleToolApprovalModeChange = async (mode: string) => {
		const tool_approval_mode = mode === 'ask' ? 'ask' : 'full';
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

	const parseToolArguments = (args) => {
		if (!args) {
			return {};
		}
		let value = args;
		while (typeof value === 'string') {
			try {
				value = JSON.parse(value);
			} catch {
				break;
			}
		}
		return typeof value === 'object' && value !== null && !Array.isArray(value) ? value : {};
	};

	const getPendingAskUserFromMessage = (message) => {
		if (message?.role !== 'assistant' || !Array.isArray(message.output)) {
			return null;
		}

		const call = message.output.find(
			(item) =>
				item?.type === 'function_call' &&
				item?.name === 'ask_user' &&
				item?.status === 'pending' &&
				(item?.call_id || item?.id)
		);

		if (call) {
			return { message, call, args: parseToolArguments(call.arguments) };
		}

		return null;
	};

	const findPendingAskUser = (chatHistory) => {
		if (!chatHistory?.messages) {
			return null;
		}
		const messages = chatHistory.currentId
			? createMessagesList(chatHistory, chatHistory.currentId)
			: Object.values(chatHistory.messages);
		for (const message of [...messages].reverse()) {
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

		if ($chatId && !$temporaryChatEnabled && !isTemporaryChatId($chatId)) {
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

	let oldSelectedModelIds = [''];
	$: if (!equal(selectedModelIds, oldSelectedModelIds)) {
		onSelectedModelIdsChange();
	}

	const onSelectedModelIdsChange = () => {
		resetInput();
		oldSelectedModelIds = structuredClone(selectedModelIds);
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

	const restoreChatInput = async (storageChatInput: string | null) => {
		if (!storageChatInput || $temporaryChatEnabled) {
			return false;
		}

		try {
			const input = JSON.parse(storageChatInput);
			prompt = input.prompt ?? '';
			messageInput?.setText(prompt);
			files = input.files ?? [];
			selectedToolIds = input.selectedToolIds ?? [];
			selectedSkillIds = input.selectedSkillIds ?? [];
			selectedFilterIds = input.selectedFilterIds ?? [];
			webSearchEnabled = input.webSearchEnabled ?? false;
			imageGenerationEnabled = input.imageGenerationEnabled ?? false;
			codeInterpreterEnabled = input.codeInterpreterEnabled ?? false;
			// Ignore approval modes in older drafts. Restoring input must not overwrite chat
			// parameters or invoke the change handler, which can save settings and approve tools.
			return true;
		} catch (e) {
			return false;
		}
	};

	const withSelectedText = (text: string) =>
		embedded && selectedText?.trim()
			? `${text}\n\nSelected note text for replace_note_content operations:\n${selectedText.trim()}`
			: text;
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
		currentDraftKey = embeddedDraftKey;
		initEmbeddedDraft();
	}

	let saveControlsTimer;
	$: if (!loading && !$temporaryChatEnabled && $chatId && chatFiles) {
		clearTimeout(saveControlsTimer);
		saveControlsTimer = setTimeout(saveControls, 400);
	}

	const navigateHandler = async () => {
		cancelBrowserInteractions();
		bridge?.end();
		noteChatDebug('navigateHandler start');
		// Mark the outgoing chat as read before loading the new one.
		// $chatId still holds the previous chat here — loadChat() updates it.
		if ($chatId && $chatId !== chatIdProp && !$temporaryChatEnabled) {
			noteChatDebug('marking outgoing chat read', { outgoingChatId: $chatId });
			updateLastReadAt($chatId);
		}

		clearTimeout(saveControlsTimer);
		await saveControls();
		loading = true;

		prompt = '';
		messageInput?.setText('');

		files = [];
		selectedToolIds = [];
		selectedSkillIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		const loaded = chatIdProp ? await loadChat() : false;
		noteChatDebug('loadChat completed inside navigateHandler', { loaded });
		if (loaded) {
			await tick();
			loading = false;
			noteChatDebug('embedded chat loading false');
			if (!$page.url.searchParams.has('message')) window.setTimeout(() => scrollToBottom(), 0);

			await tick();

			// Mark chat read when initially loading it
			if (chatIdProp && !$temporaryChatEnabled) {
				updateLastReadAt(chatIdProp);
			}

			// Process any queued requests if the chat is idle
			const lastMessage = history.currentId ? history.messages[history.currentId] : null;
			const isIdle = !lastMessage || lastMessage.role !== 'assistant' || lastMessage.done;
			if (isIdle) {
				await processNextInQueue(chatIdProp);
			}

			if (!(await restoreChatInput(storageChatInput))) {
				await setDefaults();
			}

			messageInput?.focus({ preventScroll: true });
		} else if (!embedded) {
			await goto('/');
		} else {
			loading = false;
			console.warn('[note-chat] embedded load failed; clearing spinner', {
				chatIdProp,
				activeChatId: $chatId
			});
		}
	};

	const initEmbeddedDraft = async () => {
		terminalContext = null;
		clearTimeout(saveControlsTimer);
		await saveControls();

		if ($chatId && !$temporaryChatEnabled) {
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
		prompt = '';
		messageInput?.setText('');
		await chatId.set('');
		await chatTitle.set('');

		await setDefaults();
		loading = false;
		await tick();
		messageInput?.focus({ preventScroll: true });
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
			selectedModels.length === 0 ||
			(selectedModels.length === 1 && selectedModels[0] === '') ||
			sessionStorage.selectedModels === selectedModelsString
		) {
			return;
		}
		sessionStorage.selectedModels = selectedModelsString;
		console.log('saveSessionSelectedModels', selectedModels, sessionStorage.selectedModels);
	};

	const continueOAuthRedirect = async () => {
		if (pendingOAuthTools.length === 0) {
			sessionStorage.removeItem('oauthRedirectInProgressToolId');
			return;
		}

		if (chatIdProp) {
			return;
		}

		const nextTool = pendingOAuthTools[0];
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

		if (selectedModelIds.filter((id) => id).length > 0) {
			await setDefaults();
		}
	};

	/** Check whether a terminal ID references an available system or direct terminal. */
	const isTerminalAvailable = (tid: string): boolean => {
		return (
			$config?.features?.enable_tool_servers === true &&
			(($terminalServers ?? []).some((t) => t.id && t.id === tid) ||
				($settings?.terminalServers ?? []).some((s) => s.url === tid))
		);
	};

	$: if (
		$terminalServers !== null &&
		$selectedTerminalId &&
		!isTerminalAvailable($selectedTerminalId)
	) {
		selectedTerminalId.set(null);
	}

	let lastTerminalSkillSelector: string | null = null;
	$: if ($selectedTerminalId !== lastTerminalSkillSelector) {
		terminalContext = null;
		selectedSkillIds = selectedSkillIds.filter((id) => !id.startsWith('terminal:'));
		terminalSkills.set([]);
		lastTerminalSkillSelector = $selectedTerminalId;
	}

	let settingDefaults: Promise<void> | null = null;
	const setDefaults = async () => {
		// Concurrent callers must wait, or the earlier run overwrites what they write afterwards
		if (settingDefaults) return settingDefaults;
		let resolveDefaults = () => {};
		settingDefaults = new Promise<void>((resolve) => (resolveDefaults = resolve));

		try {
			if (!$tools) {
				tools.set(await getTools(localStorage.token));
			}
			if (!$functions) {
				functions.set(await getFunctions(localStorage.token));
			}
			if (!$skills) {
				skills.set(await getSkills(localStorage.token));
			}
			if (selectedModels.length !== 1 && !atSelectedModel) {
				const comparedModels = selectedModels
					.filter((id) => id)
					.map((id) => $models.find((m) => m.id === id));
				const isSharedDefaultFeature = (feature) =>
					comparedModels.length > 0 &&
					comparedModels.every(
						(model) =>
							model?.info?.meta?.capabilities?.[feature] &&
							model?.info?.meta?.defaultFeatureIds?.includes(feature)
					);

				if (
					isSharedDefaultFeature('image_generation') &&
					$config?.features?.enable_image_generation &&
					($user?.role === 'admin' || $user?.permissions?.features?.image_generation)
				) {
					imageGenerationEnabled = true;
				}

				if (
					isSharedDefaultFeature('web_search') &&
					$config?.features?.enable_web_search &&
					($user?.role === 'admin' || $user?.permissions?.features?.web_search)
				) {
					webSearchEnabled = true;
				}

				if (
					isSharedDefaultFeature('code_interpreter') &&
					$config?.features?.enable_code_interpreter &&
					($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter)
				) {
					codeInterpreterEnabled = true;
				}

				return;
			}

			const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
			if (model) {
				// Set Default Tools
				if (model?.info?.meta?.toolIds) {
					const defaultIds = [
						...new Set(
							[...(model?.info?.meta?.toolIds ?? [])].filter((id) =>
								$tools.find((t) => t.id === id)
							)
						)
					];

					// Separate unauthenticated OAuth tools
					const unauthed = [];
					const authed = [];
					for (const id of defaultIds) {
						const tool = $tools.find((t) => t.id === id);
						if (tool && tool.authenticated === false) {
							const parts = id.split(':');
							const serverId = parts.at(-1) ?? id;
							const authType =
								parts.length > 1 ? (parts[0] === 'server' ? parts[1] : parts[0]) : null;
							unauthed.push({ id, name: tool.name ?? id, serverId, authType });
						} else {
							authed.push(id);
						}
					}
					selectedToolIds = authed;
					pendingOAuthTools = unauthed;
					await continueOAuthRedirect();
				} else if ($settings?.tools) {
					selectedToolIds = $settings.tools;
				} else {
					selectedToolIds = selectedToolIds.filter((id) => !id.startsWith('direct_server:'));
				}

				// Set Default Skills
				if (model?.info?.meta?.skillIds) {
					selectedSkillIds = [
						...new Set(
							[...(model?.info?.meta?.skillIds ?? [])].filter((id) =>
								($skills ?? []).find((s) => s.id === id && s.is_active)
							)
						)
					];
				} else {
					selectedSkillIds = [];
				}

				// Set Default Filters (Toggleable only)
				if (model?.info?.meta?.defaultFilterIds) {
					selectedFilterIds = model.info.meta.defaultFilterIds.filter((id) =>
						model?.filters?.find((f) => f.id === id)
					);
				}

				// Set Default Features
				if (model?.info?.meta?.defaultFeatureIds) {
					if (
						model.info?.meta?.capabilities?.['image_generation'] &&
						$config?.features?.enable_image_generation &&
						($user?.role === 'admin' || $user?.permissions?.features?.image_generation)
					) {
						imageGenerationEnabled = model.info.meta.defaultFeatureIds.includes('image_generation');
					}

					if (
						model.info?.meta?.capabilities?.['web_search'] &&
						$config?.features?.enable_web_search &&
						($user?.role === 'admin' || $user?.permissions?.features?.web_search)
					) {
						webSearchEnabled = model.info.meta.defaultFeatureIds.includes('web_search');
					}

					if (
						model.info?.meta?.capabilities?.['code_interpreter'] &&
						$config?.features?.enable_code_interpreter &&
						($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter)
					) {
						codeInterpreterEnabled = model.info.meta.defaultFeatureIds.includes('code_interpreter');
					}
				}

				// Set Default Terminal — only if the referenced terminal actually exists
				if (model?.info?.meta?.terminalId) {
					const tid = model.info.meta.terminalId;
					if (isTerminalAvailable(tid)) {
						selectedTerminalId.set(tid);
					}
				}
			}
		} finally {
			settingDefaults = null;
			resolveDefaults();
		}
	};

	let revealedSearchMessage = '';
	$: if (!embedded && !loading && messagesRef && chat && chat.id === $page.params.id) {
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

	const terminalEventHandler = (type: string, data: any, message: any) => {
		const attachment = history.messages[message?.parentId]?.files?.find(
			(file: any) => file.type === 'filesystem'
		);
		if (attachment) {
			if (attachment.terminal_id && attachment.terminal_id !== $selectedTerminalId) return;
			if (type === 'terminal:display_file' && terminalContext?.file?.path === data.path)
				showFileNavDir.set(data.path);
			return;
		}
		if (type === 'terminal:display_file') {
			if (!data?.path) return;
			if ($settings?.terminalFileDisplay === 'inline') return;
			displayFileHandler(data.path, { showControls, showFileNavPath }, { page: data?.page });
		} else if (type === 'terminal:write_file' || type === 'terminal:replace_file_content') {
			if (!data?.path) return;
			showFileNavDir.set(data.path);
		} else if (type === 'terminal:run_command' && !terminalContext?.file) {
			showFileNavDir.set('/');
		}
	};

	const clearContextCompaction = (messageId: string) => {
		const next = { ...$contextCompactions };
		delete next[messageId];
		contextCompactions.set(next);
	};

	const handleContextCompactionStatus = (status, messageId: string) => {
		if (status?.action !== 'context_compaction') return;
		if (status.done && !status.error) {
			clearContextCompaction(messageId);
		} else {
			$contextCompactions = {
				...$contextCompactions,
				[messageId]: status.error ? { error: $i18n.t('Context compaction failed') } : 'in_progress'
			};
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
		if (typing && (joinedChatId !== $chatId || (isShared && chat?.chat?.share_mode !== 'continue')))
			return;
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
		if (!id || $temporaryChatEnabled) return Promise.resolve();
		if (chatRefresh?.id === id) return chatRefresh.promise;
		const baseline = { ...history.messages };
		const promise = (async () => {
			try {
				const fresh = await getChatById(localStorage.token, id);
				if ($chatId !== id || joinedChatId !== id) return;
				chat = fresh;
				mergeChatMessages(fresh.chat.history, baseline);
			} catch (error) {
				if ($chatId === id && joinedChatId === id) {
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
	$: syncChatRoom($socket, $chatId, $temporaryChatEnabled);

	const chatEventHandler = async (event, cb) => {
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
					active: $showCallOverlay && callMode === 'current' && selectedModelIds.length === 1,
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
		if (!$chatId && event.chat_id && history.messages[event.message_id]) {
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
				if (
					!sender?.id ||
					sender.id === $user?.id ||
					(isShared && chat?.chat?.share_mode !== 'continue')
				)
					return;
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
					handleContextCompactionStatus(data, event.message_id);
					autoScrollToBottom();
				} else if (type === 'chat:active') {
					if (!data?.active) {
						taskIds = null;
						if (
							$chatId &&
							!$temporaryChatEnabled &&
							hasPendingAssistantLeaf(event?.message_id ?? null)
						) {
							await loadChat();
						}
						if ($chatId && !$temporaryChatEnabled) {
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
					clearContextCompaction(event.message_id);
					if (data?.output) {
						message.output = data.output;
					}
					if (!event.shared && event.message_id === history.currentId) {
						taskIds = null;
						// Set all response messages to done
						for (const messageId of history.messages[message.parentId].childrenIds) {
							history.messages[messageId].done = true;
							clearContextCompaction(messageId);
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
						clearContextCompaction(message.id);
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
				} else if (type.startsWith('terminal:')) {
					terminalEventHandler(type, data, message);
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

			const inputElement = document.getElementById('chat-input');

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
		if (!$chatId || $temporaryChatEnabled) return;
		joinedChatId = '';
		syncChatRoom($socket, $chatId, $temporaryChatEnabled);
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
		window.addEventListener('message', onMessageHandler);
		$socket?.on('events', chatEventHandler);
		$socket?.on('connect', handleSocketConnect);
		$socket?.on('disconnect', clearTyping);
		$socket?.on('disconnect', clearPresence);
		$socket?.on('disconnect', cancelBrowserInteractions);

		$audioQueue?.destroy();

		const audioQueueInstance = new AudioQueue(document.getElementById('audioElement'));
		audioQueue.set(audioQueueInstance);

		// Restore direct terminal enabled states based on persisted selectedTerminalId
		if ($settings?.terminalServers?.length) {
			settings.set({
				...$settings,
				terminalServers: ($settings.terminalServers ?? []).map((s) => ({
					...s,
					enabled: $selectedTerminalId !== null && s.url === $selectedTerminalId
				}))
			});
		}

		const pageSubscribe = page.subscribe(async (p) => {
			if (p.url.pathname === '/' || p.url.pathname.startsWith('/folders/')) {
				await tick();
				initNewChat();
			}

			stopAudio();
		});

		const showControlsSubscribe = showControls.subscribe((value) => {
			if (!value) {
				showCallOverlay.set(false);
				showArtifacts.set(false);
				showEmbeds.set(false);
			}
		});

		// the artifacts pane reads this list when it opens, which can be before the debounced rebuild
		const showArtifactsSubscribe = showArtifacts.subscribe((value) => {
			if (value) getContents();
		});

		const selectedFolderSubscribe = selectedFolder.subscribe(async (folder) => {
			await tick();
			// Folder default models apply to new chats only.
			if (!history.currentId && folder) {
				const folderModels = normalizeSelectedModels(folder.data?.model_ids ?? []);
				if (!equal(selectedModels, folderModels)) {
					selectedModels = folderModels;
				}
			}
		});

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
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

				await restoreChatInput(storageChatInput);
			}

			messageInput?.focus({ preventScroll: true });
		};
		init();

		return () => {
			try {
				cancelBrowserInteractions();
				clearTimeout(saveControlsTimer);
				saveControls();
				if (chatIdProp && !$temporaryChatEnabled) {
					updateLastReadAt(chatIdProp);
				}
				pageSubscribe();
				showControlsSubscribe();
				showArtifactsSubscribe();
				selectedFolderSubscribe();

				// Clear the selected chat when leaving the chat surface (e.g. navigating
				// to the admin panel), otherwise the previously-viewed chat stays selected
				// in the sidebar and deleting/archiving it wrongly navigates away.
				clearTyping();
				clearPresence();
				if (joinedChatId && $socket?.connected)
					$socket.emit('events:chat', { chat_id: joinedChatId, data: { type: 'leave' } });
				joinedChatId = '';
				chatId.set('');
				chatTitle.set('');

				window.removeEventListener('message', onMessageHandler);
				$socket?.off('events', chatEventHandler);
				$socket?.off('connect', handleSocketConnect);
				$socket?.off('disconnect', clearTyping);
				$socket?.off('disconnect', clearPresence);
				$socket?.off('disconnect', cancelBrowserInteractions);
				contextCompactions.set({});
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
			artifactContents.set([]);
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
		($showCallOverlay && callMode === 'current') || !!(bridge?.connected || bridge?.connecting);
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
			if (_chatId && !$temporaryChatEnabled) {
				// Realtime replies need no chat completion; start metadata work at chat creation.
				void generateVoiceChatMetadata(_chatId, modelId, content, chat.title).catch((error) => {
					console.error('Could not save voice chat metadata', error);
				});
			}
		} else if (!$temporaryChatEnabled) {
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
		if ($chatId && !$temporaryChatEnabled) {
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
						? $models.find((model) => model.id === selectedModelIds[0])
						: null;
				return {
					chatId: isTemporaryChatId($chatId) ? undefined : $chatId || undefined,
					modelId: model && !('direct' in model && model.direct) ? model.id : '',
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
	beforeNavigate(() => {
		bridge?.end();
		pendingUrlActions = null;
	});
	$: if (!$user && (bridge?.connected || bridge?.connecting)) bridge.end();
	$: if (selectedModelIds && $models && $config) bridge?.syncModel();

	const dispatchCallOverlayAudio = (message, final = false) => {
		if (message.error || !$showCallOverlay || callMode !== 'current') {
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
		let contents = [];
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

		artifactContents.set(contents);
	};

	//////////////////////////
	// Web functions
	//////////////////////////

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

		showCallOverlay.set(true);
		showControls.set(true);
	};

	const initNewChat = async () => {
		if ($chatId) terminalContext = null;
		cancelBrowserInteractions();
		bridge?.end();
		console.log('initNewChat');
		resetWebSearchConfirmation();

		// Mark the outgoing chat as read before resetting; in-place created chats
		// keep chatIdProp undefined, so navigateHandler never marks them read.
		if ($chatId && !$temporaryChatEnabled) {
			updateLastReadAt($chatId);
		}

		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		}

		if ($settings?.temporaryChatByDefault ?? false) {
			if ($temporaryChatEnabled === false) {
				await temporaryChatEnabled.set(true);
			} else if ($temporaryChatEnabled === null) {
				// if set to null set to false; refer to temp chat toggle click handler
				await temporaryChatEnabled.set(false);
			}
		}

		if ($page.url.searchParams.get('temporary-chat') === 'true') {
			await temporaryChatEnabled.set(true);
		}

		if ($user?.role !== 'admin' && !$user?.permissions?.chat?.temporary) {
			await temporaryChatEnabled.set(false);
		}

		const availableModels = $models
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

		const defaultModels = normalizeSelectedModels();

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

		if ($page.url.searchParams.get('models') || $page.url.searchParams.get('model')) {
			const urlModels = (
				$page.url.searchParams.get('models') ||
				$page.url.searchParams.get('model') ||
				''
			)?.split(',');

			if (urlModels.length === 1) {
				if (!$models.find((m) => m.id === urlModels[0])) {
					// Model not found; open model selector and prefill
					await openModelSelectorWithSearch(urlModels[0]);
				} else {
					// Model found; set it as selected
					selectedModels = urlModels;
				}
			} else {
				// Multiple models; set as selected
				selectedModels = urlModels;
			}

			// Unavailable models filtering
			selectedModels = selectedModels.filter((modelId) =>
				$models.map((m) => m.id).includes(modelId)
			);
		} else {
			if ($selectedFolder) {
				// Folder defaults are explicit; never inherit a previous chat's selection.
				selectedModels = normalizeSelectedModels($selectedFolder.data?.model_ids ?? []);
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
			await showControls.set(false);
		}
		await showCallOverlay.set(false);
		await showArtifacts.set(false);

		if (!embedded && $page.url.pathname.includes('/c/')) {
			window.history.replaceState(window.history.state, '', `/`);
		}

		autoScroll = true;

		// resetInput() must stay last: the selected model's defaults override the draft's selection.
		await restoreChatInput(sessionStorage.getItem('chat-input'));
		const previousChatId = $chatId;
		const previousMessageId = history.currentId;
		await resetInput();
		// A chat opened or a message sent in the meantime keeps its id and history
		if (($chatId && $chatId !== previousChatId) || history.currentId !== previousMessageId) return;
		await chatId.set('');
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

		const youtube = $page.url.searchParams.get('youtube');
		const loadUrl = $page.url.searchParams.get('load-url');
		const urls = [
			...(youtube ? [`https://www.youtube.com/watch?v=${youtube}`] : []),
			...(loadUrl ? [loadUrl] : [])
		];
		const call =
			$page.url.searchParams.get('call') === 'true' ||
			$page.url.searchParams.get('voice') === 'true';
		pendingUrlActions = urls.length || call ? { urls, call } : null;

		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		if ($page.url.searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

		if ($page.url.searchParams.get('code-interpreter') === 'true') {
			codeInterpreterEnabled = true;
		}

		if ($page.url.searchParams.get('tools')) {
			selectedToolIds = $page.url.searchParams
				.get('tools')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id && ($tools ?? []).find((t) => t.id === id));
		} else if ($page.url.searchParams.get('tool-ids')) {
			selectedToolIds = $page.url.searchParams
				.get('tool-ids')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id && ($tools ?? []).find((t) => t.id === id));
		}

		// Restore tool selection after OAuth redirect
		const pendingToolId = sessionStorage.getItem('pendingOAuthToolId');
		if (pendingToolId) {
			sessionStorage.removeItem('pendingOAuthToolId');
			if (!selectedToolIds.includes(pendingToolId)) {
				selectedToolIds = [...selectedToolIds, pendingToolId];
			}
		}

		// Consume one-shot desktop event (e.g. Spotlight query, call shortcut)
		if ($desktopEvent) {
			const event = $desktopEvent;
			desktopEvent.set(null);

			if (event.type === 'call') {
				openCallOverlay();
			} else if (event.type === 'query') {
				const query = event.data?.query;
				const eventFiles = event.data?.files;

				// Attach screenshot images from desktop (e.g. Spotlight region capture)
				if (eventFiles?.length) {
					for (const ef of eventFiles) {
						files = [
							...files,
							{
								type: 'image',
								url: ef.dataUrl,
								name: ef.name
							}
						];
					}
				}

				if (query) {
					messageInput?.setTextHandler(query, () => submitHandler(prompt));
				} else if (eventFiles?.length) {
					await tick();
					submitHandler('');
				}
			}
		} else if ($page.url.searchParams.get('q')) {
			const q = $page.url.searchParams.get('q') ?? '';

			messageInput?.setTextHandler(q);
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		await tick();
		messageInput?.focus({ preventScroll: true });
	};

	const loadChat = async () => {
		if (chatIdProp && chatIdProp !== $chatId) {
			terminalContext = null;
			history = { messages: {}, currentId: null };
		}
		const initialHistory = { ...history, messages: { ...history.messages } };
		noteChatDebug('loadChat start');
		// chatIdProp is empty for chats started from the home page (URL set via replaceState)
		chatId.set(chatIdProp || $chatId);
		noteChatDebug('loadChat set active chat id');

		if ($temporaryChatEnabled) {
			noteChatDebug('loadChat disabling temporary chat');
			temporaryChatEnabled.set(false);
		}

		chat = await getChatById(localStorage.token, $chatId).catch(async (error) => {
			console.error('[note-chat] getChatById failed', {
				chatIdProp,
				activeChatId: $chatId,
				error
			});
			if (!embedded) {
				await goto('/');
			}
			return null;
		});
		noteChatDebug('getChatById completed', {
			found: !!chat,
			chatId: chat?.id,
			hasChatPayload: !!chat?.chat,
			title: chat?.title
		});

		if (chat) {
			tags = await getTagsById(localStorage.token, $chatId).catch(async (error) => {
				console.warn('[note-chat] getTagsById failed; continuing without tags', {
					chatIdProp,
					activeChatId: $chatId,
					error
				});
				return [];
			});
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

				// An empty model list is not evidence that the chat's models are gone.
				if ($models.length > 0) {
					selectedModels = selectedModels.filter((modelId) =>
						$models.map((m) => m.id).includes(modelId)
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

				oldSelectedModelIds = structuredClone(selectedModels);

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

				params = structuredClone(chatContent?.params ?? {});
				delete params.note_id;
				chatFiles = structuredClone(chatContent?.files ?? []);

				// Load tasks from chat-level DB field
				chatTasks = chat?.tasks ?? [];
				serverContextUsage = chat?.context_usage ?? null;

				autoScroll = true;
				await tick();

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
				const currentMessage = history.currentId ? history.messages[history.currentId] : null;
				const pendingTaskIds = await getTaskIdsByChatId(localStorage.token, $chatId)
					.then((res) => res?.task_ids ?? [])
					.catch((error) => {
						console.warn('[note-chat] getTaskIdsByChatId failed; continuing without tasks', {
							chatIdProp,
							activeChatId: $chatId,
							error
						});
						return [];
					});
				noteChatDebug('task reconciliation completed', {
					pendingTaskCount: pendingTaskIds.length,
					hasCurrentMessage: !!currentMessage
				});
				if (taskIds !== activeTaskIds) {
					noteChatDebug('task ids changed during load; aborting stale load');
					return;
				}
				const responseComplete = currentMessage?.role === 'assistant' && currentMessage?.done;

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
								!messageHasPendingAskUser(message)
							) {
								message.done = true;
								history = history;
							}
						}
					}
				}

				await tick();

				return true;
			} else {
				console.warn('[note-chat] chat response missing chat payload', {
					chatIdProp,
					activeChatId: $chatId,
					chat
				});
				return null;
			}
		}
		console.warn('[note-chat] no chat returned from getChatById', {
			chatIdProp,
			activeChatId: $chatId
		});
	};

	const scrollToBottom = async (behavior = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});
			lastScrollTop = messagesContainerElement.scrollTop;

			// content-visibility: auto causes the initial scrollHeight to be based on
			// estimated sizes (contain-intrinsic-size). After we scroll, previously
			// off-screen messages become visible and the browser resolves their actual
			// heights, which shifts scrollHeight. Re-layouts can cascade across frames
			// (new sizes reveal more content, triggering further size resolution), so
			// we re-scroll across two animation frames to land at the true bottom.
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
			(lastMessage && lastMessage.role === 'assistant' && !lastMessage.done) ||
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
			boundary === 0 ? queue.slice(0, 1) : boundary < 0 ? [...queue] : queue.slice(0, boundary);
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

	const sendQueuedMessageNow = async (id) => {
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
		const queue = $chatRequestQueues[$chatId] ?? [];
		chatRequestQueues.update((q) => ({
			...q,
			[$chatId]: queue.filter((m) => m.id !== id)
		}));

		await processNextInQueue($chatId);
	};

	const chatCompletedHandler = async (_chatId, modelId, responseMessageId, messages) => {
		// Backend handles outlet filters and persistence inline.
		// Just refresh the sidebar chat list.
		if ($chatId == _chatId && !$temporaryChatEnabled) {
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
			model_item: $models.find((m) => m.id === modelId),
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

		if (changed && !$temporaryChatEnabled) {
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
				const model = $models.filter((m) => m.id === modelId).at(0);

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

			if (messages.length === 0) {
				await initChatHandler(history);
			} else {
				await saveChatHandler($chatId, history);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }) => {
		const model = $models.filter((m) => m.id === modelId).at(0);

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

		if (messages.length === 0) {
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
		const { id, done, choices, content, output, sources, selected_model_id, error, usage } = data;

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
			message.arena = true;
		}

		if (usage) {
			message.usage = usage;
		}

		history.messages[message.id] = message;
		history = history;

		if (done) {
			message.done = true;
			if ($contextCompactions[message.id] === 'in_progress') clearContextCompaction(message.id);
			if (shared) return;
			if (message.error) {
				clearContextCompaction(message.id);
				bridge?.update();
				await processNextInQueue(chatId);
				return;
			}
			const visibleContent =
				getOutputText(message?.output) || removeAllDetails(message?.content ?? '');

			if ($settings.responseAutoCopy) {
				copyToClipboard(visibleContent);
			}

			if ($settings.responseAutoPlayback && !$showCallOverlay && !bridge?.connected) {
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

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (
		inputContent: string,
		inputFiles: any[],
		bridgeRequest: { userMessageId: string; modelId: string } | null = null
	) => {
		const _files = structuredClone(inputFiles);

		chatFiles.push(
			..._files.filter(
				(item) =>
					['doc', 'text', 'note', 'chat', 'folder', 'collection'].includes(item.type) ||
					(item.type === 'file' && !isRasterImageContentType(item?.content_type))
			)
		);
		chatFiles = chatFiles.filter(
			// Remove duplicates
			(item, index, array) => array.findIndex((i) => equal(i, item)) === index
		);

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
			models: selectedModels
		};

		// A transcribed Bridge message already exists in the same history.
		const existingUserMessage = history.messages[userMessageId];
		if (existingUserMessage) userMessage = { ...existingUserMessage, files: userMessage.files };
		history.messages[userMessageId] = userMessage;

		// Append messageId to childrenIds of parent message
		if (!existingUserMessage && history.currentId !== null) {
			history.messages[history.currentId].childrenIds.push(userMessageId);
		}

		history.currentId = userMessageId;

		// focus on chat input (skip during voice call to avoid triggering mobile keyboard)
		if (!$showCallOverlay) {
			messageInput?.focus({ preventScroll: true });
		}

		saveSessionSelectedModels();

		return await sendMessage(history, userMessageId, {
			modelId: bridgeRequest?.modelId ?? null
		});
	};

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

		const model = atSelectedModel?.id ?? selectedModels.find((modelId) => modelId);
		// Preserve the former toast translation for i18n extraction.
		// const toastId = toast.loading($i18n.t('Compacting context...'));
		const compactChatId = $chatId;
		const compactMessageId = history.currentId;
		if ($contextCompactions[compactMessageId] === 'in_progress') return;
		$contextCompactions = { ...$contextCompactions, [compactMessageId]: 'in_progress' };

		try {
			const result = await compactChatById(localStorage.token, compactChatId, model);
			if ($chatId !== compactChatId) return;
			serverContextUsage = result?.context_usage ?? serverContextUsage;

			if (!result?.compacted) {
				const skippedReason =
					result?.reason === 'too_short'
						? $i18n.t('Chat is too short to compact')
						: result?.reason === 'empty'
							? $i18n.t('No chat to compact')
							: result?.reason === 'disabled'
								? $i18n.t('Context compaction is disabled')
								: $i18n.t('Nothing to compact');
				toast.message(skippedReason);
			}

			await loadChat();
			clearContextCompaction(compactMessageId);
		} catch (error) {
			if ($chatId === compactChatId) {
				$contextCompactions = {
					...$contextCompactions,
					[compactMessageId]: {
						error: String(error?.detail ?? error?.message ?? $i18n.t('Context compaction failed'))
					}
				};
			}
		} finally {
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

		const model = $models.find((model) => model.id === modelId);
		if (!model) {
			toast.error(`Model not found: ${modelId}`);
			messageInput?.setText('');
			prompt = '';
			messageInput?.focus({ preventScroll: true });
			return;
		}

		atSelectedModel = undefined;
		selectedModels = [model.id];
		saveSessionSelectedModels();
		toast.success(`Model switched to: ${model.id}`);
		messageInput?.setText('');
		prompt = '';
		messageInput?.focus({ preventScroll: true });
	};

	const handleForkChat = async (messageId: string | null = null) => {
		if (!$chatId || $temporaryChatEnabled || !history?.currentId) {
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

	const getChatId = async (_history: typeof history) => {
		let _chatId = $chatId;
		// Empty embedded drafts create their backing chat only when the first message is sent.
		if (!_chatId) {
			if (embedded && onCreateEmbeddedChat) {
				const createdChat = await onCreateEmbeddedChat();
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
			} else if ($temporaryChatEnabled) {
				_chatId = createTemporaryChatId($socket?.id);
				await chatId.set(_chatId);
			}
			await tick();
		}
		return _chatId;
	};

	const submitHandler = async (
		userPrompt: string,
		{
			_raw = false,
			bridge: bridgeRequest = null
		}: { _raw?: boolean; bridge?: { userMessageId: string; modelId: string } | null } = {}
	): Promise<BridgeSubmission> => {
		if (processing === 'uploading') return { status: 'deferred' };
		emitTyping(false);
		if (bridgeRequest && (selectedModelIds.length !== 1 || !bridgeRequest.modelId))
			return { status: 'rejected' };

		const _selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
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

		if (pendingOAuthTools.length > 0) {
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
		const form = getChatVariablesForm(selectedModelIds, chatVariables, $models);
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

		if (
			$config?.features?.enable_web_search_confirmation &&
			webSearchActive &&
			!webSearchConfirmed
		) {
			pendingWebSearchPrompt = bridgeRequest ? null : (userPrompt ?? '');
			openWebSearchConfirm();
			return { status: 'deferred' };
		}

		const currentHistory = history;
		processing = 'uploading';
		try {
			const _chatId = await getChatId(currentHistory);
			if (_chatId === null) return { status: 'rejected' };

			if (history !== currentHistory) return { status: 'rejected' };
			if (
				files.some((file) => file.status === 'pending' && file.file instanceof File) &&
				!(await messageInput?.uploadPendingFiles(_chatId || (await initChatHandler(history))))
			)
				return { status: 'rejected' };
			if (history !== currentHistory) return { status: 'rejected' };
		} catch (error) {
			toast.error(`${error}`);
			return { status: 'rejected' };
		} finally {
			processing = '';
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

		if (isGenerating) {
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
			const terminal = attached.find((file: any) => file.terminal_id)?.terminal_id;
			if (
				attached.some(
					(file: any) =>
						(file.terminal_id && file.terminal_id !== terminal) ||
						(file.session_id && file.session_id !== $chatId)
				)
			)
				throw new Error('Attached files must belong to this chat and the same terminal.');
			if (terminal && !isTerminalAvailable(terminal))
				throw new Error('The attached file’s terminal is unavailable.');
		}
		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = JSON.parse(JSON.stringify($chatId));
		_history = structuredClone(_history);

		const responseMessageIds: Record<PropertyKey, string> = {};
		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: selectedModels;
		if (!modelId && history.messages[parentId]) {
			history.messages[parentId].models = [...selectedModelIds];
		}

		// Create response messages for each selected model
		// Build message_ids list: [{model_id, message_id, modelIdx}, ...]
		// Uses an array instead of a dict to support duplicate model IDs in side-by-side chat.
		// modelIdx identifies each side-by-side column so the backend can persist it; without
		// it, duplicate models collapse into one another when the chat is reloaded.
		const messageIdsList: Array<{ model_id: string; message_id: string; modelIdx: number }> = [];
		for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
			const model = $models.filter((m) => m.id === modelId).at(0);

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
				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null && history.messages[parentId]) {
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
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
		_history = structuredClone(history);

		// Vision capability check
		for (const mid of selectedModelIds) {
			const model = $models.filter((m) => m.id === mid).at(0);
			if (model) {
				const hasImages = createMessagesList(_history, parentId).some((message) =>
					message.files?.some(
						(file) => file.type === 'image' || isRasterImageContentType(file?.content_type)
					)
				);

				if (
					hasImages &&
					!(model.info?.meta?.capabilities?.vision ?? true) &&
					!imageGenerationEnabled
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
		const primaryModel = $models.filter((m) => m.id === primaryModelId).at(0);
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
						// Always forward the message_ids list (not just for multi-model sends) so the
						// backend persists each response's modelIdx — including single-column
						// regenerations in a duplicate-model chat, which would otherwise lose their
						// column identity and collapse on reload.
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
				voice: ($showCallOverlay && callMode === 'current') || !!bridge?.connected,
				image_generation:
					$config?.features?.enable_image_generation &&
					($user?.role === 'admin' || $user?.permissions?.features?.image_generation)
						? imageGenerationEnabled
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
		const requestTerminalId = filesystemAttachment?.terminal_id ?? $selectedTerminalId;

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
		// Remove duplicates
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

		if ($temporaryChatEnabled) {
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

		const toolIds = [];
		const toolServerIds = [];

		for (const toolId of selectedToolIds) {
			if (toolId.startsWith('direct_server:')) {
				let serverId = toolId.replace('direct_server:', '');
				// Check if serverId is a number
				if (!isNaN(parseInt(serverId))) {
					toolServerIds.push(parseInt(serverId));
				} else {
					toolServerIds.push(serverId);
				}
			} else {
				toolIds.push(toolId);
			}
		}

		// The backend applies the skill loading setting to menu-selected skills.
		// Keep mentions in the message so the backend can resolve them.
		const skillIds = [...selectedSkillIds];

		// Only send terminal_id if the model has terminal capability enabled
		const terminalEnabled =
			$config?.features?.enable_tool_servers && (model.info?.meta?.capabilities?.terminal ?? true);
		const useChatVariablesFallback =
			!_chatId || $temporaryChatEnabled || isTemporaryChatId(_chatId);

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

				files: (files?.length ?? 0) > 0 ? files : undefined,

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
				terminal_id: terminalEnabled && requestTerminalId ? requestTerminalId : undefined,
				tool_servers: $config?.features?.enable_tool_servers
					? [
							...($toolServers ?? []).filter(
								(server, idx) => toolServerIds.includes(idx) || toolServerIds.includes(server?.id)
							),
							// Direct terminal servers — always included when enabled (not routed through selectedToolIds)
							...(terminalEnabled
								? ($terminalServers ?? [])
										.filter(
											(server) =>
												!server.id && (!filesystemAttachment || server.url === requestTerminalId)
										)
										.map((server) => ({ ...server, is_terminal: true }))
								: [])
						]
					: [],
				features: getFeatures(),
				variables: {
					...getPromptVariables(
						$user?.name,
						$settings?.userLocation ? userLocation : undefined,
						$user?.email
					)
				},
				...(useChatVariablesFallback ? { chat_variables: chatVariables } : {}),
				model_item: $models.find((m) => m.id === model.id),

				session_id: $socket?.id,
				chat_id: _chatId || undefined,
				folder_id: $selectedFolder?.id ?? undefined,

				id: responseMessageId,
				...(messageIdsList ? { message_ids: messageIdsList } : {}),
				parent_id: userMessage?.parentId ?? null,
				user_message: userMessage,
				...(regenerationPrompt ? { regeneration_prompt: regenerationPrompt } : {}),
				...(regenerationMessageId ? { regeneration_message_id: regenerationMessageId } : {}),
				...(continueResponse ? { assistant_message_id: responseMessageId } : {}),

				background_tasks: {
					...(!$temporaryChatEnabled &&
					(!_chatId ||
						((userMessage?.parentId ?? null) === null &&
							createMessagesList(_history, responseMessageId).length === 2))
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

				// Finish new-chat setup even if an event already supplied the chat id.
				// Only update if the user hasn't navigated to a different chat
				// while the request was in flight (prevents overwriting $chatId
				// and causing spurious toast notifications / state duplication).
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
					if (!$temporaryChatEnabled && !embedded) {
						// Carry the picks made on the new-chat page over to this chat
						saveDraft(getChatInputDraft(), res.chat_id, false);
						window.history.replaceState(window.history.state, '', `/c/${res.chat_id}`);
						await refreshChatList(localStorage.token);

						// Persist chat-level params (system prompt, advanced
						// params) that the backend doesn't receive in the
						// chat completion request.  Files are now persisted
						// by the backend at chat creation time.
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
					clearContextCompaction(messageId);
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

			await sendMessage(history, userMessage.id, {
				...(suggestionPrompt
					? {
							messages: createMessagesList(history, message.id),
							regenerationPrompt: suggestionPrompt,
							regenerationMessageId: message.id
						}
					: {}),
				...((userMessage?.models ?? [...selectedModels]).length > 1
					? {
							// If multiple models are selected, use the model from the message
							modelId: message.model,
							modelIdx: message.modelIdx
						}
					: {})
			});
		}
	};

	const continueResponse = async (message) => {
		console.log('continueResponse');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.messages[message.id].done == true) {
			const responseMessage = history.messages[message.id];
			responseMessage.done = false;
			await tick();

			const model = $models
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
		}
	};

	const initChatHandler = async (_history: typeof history) => {
		let _chatId = $chatId;
		const selectedFolderId = $selectedFolder?.id;

		if (!$temporaryChatEnabled) {
			const createdChat = await createNewChat(
				localStorage.token,
				{
					id: _chatId,
					title: $i18n.t('New Chat'),
					models: selectedModels,
					system: $settings.system ?? undefined,
					params: params,
					history: _history,
					messages: createMessagesList(_history, _history.currentId),
					tags: [],
					timestamp: Date.now()
				},
				$selectedFolder?.id,
				chatVariables
			);

			if (!createdChat?.id) throw new Error($i18n.t('Failed to create chat'));
			if (history !== _history || $chatId !== _chatId) return '';
			chat = createdChat;
			_chatId = chat.id;
			await chatId.set(_chatId);

			if (!embedded) {
				saveDraft(getChatInputDraft(), _chatId, false);
				window.history.replaceState(window.history.state, '', `/c/${_chatId}`);
			}

			await tick();

			if (!embedded) {
				await refreshChatList(localStorage.token);
			}

			if (selectedFolderId) {
				await refreshFolderChatLists(selectedFolderId, chat);
			}

			selectedFolder.set(null);
		} else {
			_chatId = createTemporaryChatId($socket?.id);
			await chatId.set(_chatId);
		}
		await tick();

		return _chatId;
	};

	const saveChatHandler = async (_chatId, history) => {
		if (isShared) return;
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
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
		if (isShared || !$chatId || $temporaryChatEnabled || isTemporaryChatId($chatId)) return;
		await updateChatParams(localStorage.token, $chatId, { [key]: value }).catch((error) => {
			toast.error(`${error}`);
		});
	};

	const saveControls = async () => {
		if (isShared) return;
		if (!$chatId || $temporaryChatEnabled) return;
		const loaded = chat?.chat ?? {};
		if (equal(chatFiles, loaded.files ?? [])) return;

		const res = await updateChatById(localStorage.token, $chatId, {
			files: chatFiles
		}).catch((err) => {
			console.error('[controls autosave]', err);
			return null;
		});
		// Refresh the dedupe baseline so a later revert still saves.
		if (res) chat = res;
	};

	const MAX_DRAFT_LENGTH = 5000;
	let saveDraftTimeout: ReturnType<typeof setTimeout> | null = null;
	// chatIdProp is empty for chats started from the home page (URL set via replaceState)
	const getDraftChatId = () => chatIdProp || $chatId || null;

	const getChatInputDraft = () => ({
		prompt,
		files: files
			.filter((file) => file.type !== 'image' && !(file.file instanceof File))
			.map((file) => ({
				...file,
				user: undefined,
				access_grants: undefined
			})),
		selectedToolIds,
		selectedSkillIds,
		selectedFilterIds,
		imageGenerationEnabled,
		webSearchEnabled,
		codeInterpreterEnabled
	});

	const saveDraft = async (draft: any, chatId: string | null = null, debounce = true) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}

		if (draft.prompt !== null && draft.prompt.length < MAX_DRAFT_LENGTH) {
			const key = `chat-input${chatId ? `-${chatId}` : ''}`;
			const write = () => sessionStorage.setItem(key, JSON.stringify(draft));
			if (debounce) {
				saveDraftTimeout = setTimeout(write, 500);
			} else {
				write();
			}
		} else {
			sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
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
		await tick();
		saveSessionSelectedModels();
		await saveDraft(draft, null, false);
		initiateOAuthRedirect(tool);
	};

	const clearDraft = async (chatId: string | null = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}
		await sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
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
			initNewChat();
			await goto('/');
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
				initNewChat();
				await goto('/');
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

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$settings.showChatTitleInTab !== false && $chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} / ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<audio id="audioElement" style="display: none;"></audio>

{#if getChatVariablesForm(selectedModelIds, chatVariables, $models).conflicts.length > 0}
	<Modal bind:show={showChatVariablesModal} size="md">
		<div>
			<div class="flex justify-between px-4 pt-3 pb-1 dark:text-gray-300">
				<div class="self-center text-sm font-medium">{$i18n.t('Chat Variables')}</div>
				<button
					aria-label={$i18n.t('Close')}
					class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					on:click={() => {
						showChatVariablesModal = false;
					}}
				>
					<XMark className="size-4" />
				</button>
			</div>

			<div class="px-5 pb-4 text-sm text-gray-600 dark:text-gray-300">
				<div class="mb-2 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Selected models define incompatible Chat Variables.')}
				</div>
				<div class="flex flex-col gap-1">
					{#each getChatVariablesForm(selectedModelIds, chatVariables, $models).conflicts as conflict}
						<div class="rounded-lg border border-red-200 px-3 py-2 text-xs dark:border-red-900/60">
							<div class="font-medium text-red-600 dark:text-red-400">{conflict.key}</div>
							<div class="mt-1 text-gray-500 dark:text-gray-400">
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
		variables={getChatVariablesForm(selectedModelIds, chatVariables, $models).variables}
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
	<div class="text-sm text-gray-500 space-y-2 max-h-60 overflow-auto break-words">
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

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		confirmDeleteChat();
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
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
			<div class="text-sm text-gray-500">
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
>
	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			{#if backgroundImage}
				<div
					class="pointer-events-none absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({backgroundImage})"
				/>
				<div
					class="pointer-events-none absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				></div>
			{/if}

			<div class="w-full h-full flex">
				<div class="h-full flex relative max-w-full min-w-0 flex-1 flex-col">
					<FilesOverlay show={dragged} />
					{#if embedded}
						<div
							class="h-10 shrink-0 flex items-center justify-between gap-2 border-b border-gray-50/80 px-3 text-gray-700 dark:border-gray-850/40 dark:text-gray-200"
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
							<Tooltip content={$i18n.t('Close')} placement="bottom">
								<button
									type="button"
									class="rounded-md p-1 text-gray-500 transition hover:text-gray-900 dark:hover:text-white"
									on:click={() => onCloseEmbedded?.()}
									aria-label={$i18n.t('Close')}
								>
									<XMark className="size-4" strokeWidth="2" />
								</button>
							</Tooltip>
						</div>
					{:else}
						<Navbar
							{liveParticipants}
							bind:this={navbarElement}
							readOnly={isShared}
							chat={{
								id: $chatId,
								archived: chat?.archived ?? false,
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
							shareEnabled={!!history.currentId}
							{initNewChat}
							scrollToTop={!isNearTop ? scrollToTop : null}
							{archiveChatHandler}
							{deleteChatHandler}
							{moveChatHandler}
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
											params: params,
											history: history,
											messages: messages,
											timestamp: Date.now()
										},
										null,
										chatVariables
									);

									if (savedChat) {
										temporaryChatEnabled.set(false);
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
					<div id="chat-pane" class="flex flex-col flex-auto z-10 w-full @container overflow-auto">
						<div class="sr-only" aria-live="polite" aria-atomic="true">{liveStatus}</div>
						{#if ($settings?.landingPageMode === 'chat' && !$selectedFolder) || createMessagesList(history, history.currentId).length > 0}
							<div
								class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
								id="messages-container"
								bind:this={messagesContainerElement}
								on:scroll={(e) => {
									if (!messagesContainerElement) return;
									const { scrollTop, scrollHeight, clientHeight } = messagesContainerElement;
									// Content growing below the viewport must not stop following.
									autoScroll =
										scrollHeight - scrollTop <= clientHeight + 5 ||
										(autoScroll && scrollTop >= lastScrollTop);
									lastScrollTop = scrollTop;
									isNearTop = scrollTop <= 100;
								}}
							>
								<div class=" h-full w-full flex flex-col">
									<Messages
										bind:this={messagesRef}
										chatId={$chatId}
										user={chatOwner ?? (chat ? { id: chat.user_id } : $user)}
										readOnly={isShared}
										shareMode={chat?.chat?.share_mode ?? null}
										bind:history
										bind:autoScroll
										bind:prompt
										setInputText={(text) => {
											messageInput?.setTextHandler(text);
										}}
										bind:selectedModels
										{atSelectedModel}
										className={embedded ? 'h-full flex pt-4' : 'h-full flex pt-18'}
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
										forkHandler={$temporaryChatEnabled ? null : handleForkChat}
										topPadding={!embedded}
										bottomPadding={files.length > 0}
										{onSelect}
										{onInsertToNote}
									/>
								</div>
							</div>

							{#if isShared && chat?.chat?.share_mode !== 'continue'}
								{#if canClone}
									<div
										class="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center gap-2 bg-linear-to-t from-white dark:from-gray-900 to-transparent pb-5 pt-10"
									>
										<button
											class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white pointer-events-auto"
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
										{terminalContext}
										{typingUsers}
										on:typing={(event) => emitTyping(event.detail)}
										callActive={!!(bridge?.connected || bridge?.connecting)}
										callEnabled={!isShared}
										bind:this={messageInput}
										{history}
										{taskIds}
										bind:selectedModels
										bind:files
										bind:prompt
										bind:autoScroll
										bind:selectedToolIds
										bind:selectedSkillIds
										bind:selectedFilterIds
										bind:imageGenerationEnabled
										bind:codeInterpreterEnabled
										{pendingOAuthTools}
										{oauthRedirectHandler}
										bind:webSearchEnabled
										bind:atSelectedModel
										bind:showCommands
										bind:dragged
										dropzoneId={messageInputDropzoneId}
										chatId={$chatId}
										{contextUsage}
										{contextCompactionEnabled}
										{embedded}
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
										messageQueue={$chatRequestQueues[$chatId] ?? []}
										{chatTasks}
										askUser={savedAskUserPrompt ?? socketAskUserPrompt}
										onQueueSendNow={sendQueuedMessageNow}
										onQueueEdit={editQueuedMessage}
										onQueueDelete={deleteQueuedMessage}
										onChange={(data: any) => {
											if (!$temporaryChatEnabled) {
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
										class="absolute bottom-1 text-xs text-gray-500 text-center line-clamp-1 right-0 left-0"
									>
										<!-- {$i18n.t('LLMs can make mistakes. Verify important information.')} -->
									</div>
								</div>
							{/if}
						{:else if embedded}
							<div class="flex h-full min-h-0 flex-col justify-end">
								{#if suggestedPrompts.length > 0}
									<div class="flex flex-1 items-end px-5 pb-8">
										<div class="w-full">
											<div class="mb-2 text-[0.75rem] text-gray-300 dark:text-gray-700">
												{$i18n.t('Suggested prompts')}
											</div>
											<div class="flex flex-col">
												{#each suggestedPrompts as suggestion}
													<button
														type="button"
														class="flex min-h-8 w-full items-center justify-between py-1 text-left text-[0.8125rem] leading-5 text-gray-500 transition hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
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
										{terminalContext}
										{typingUsers}
										on:typing={(event) => emitTyping(event.detail)}
										callActive={!!(bridge?.connected || bridge?.connecting)}
										callEnabled={!isShared}
										bind:this={messageInput}
										{history}
										{taskIds}
										bind:selectedModels
										bind:files
										bind:prompt
										bind:autoScroll
										bind:selectedToolIds
										bind:selectedSkillIds
										bind:selectedFilterIds
										bind:imageGenerationEnabled
										bind:codeInterpreterEnabled
										{pendingOAuthTools}
										{oauthRedirectHandler}
										bind:webSearchEnabled
										bind:atSelectedModel
										bind:showCommands
										bind:dragged
										dropzoneId={messageInputDropzoneId}
										chatId={$chatId}
										{contextUsage}
										{contextCompactionEnabled}
										{embedded}
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
										messageQueue={$chatRequestQueues[$chatId] ?? []}
										{chatTasks}
										askUser={savedAskUserPrompt ?? socketAskUserPrompt}
										onQueueSendNow={sendQueuedMessageNow}
										onQueueEdit={editQueuedMessage}
										onQueueDelete={deleteQueuedMessage}
										onChange={(data: any) => {
											if (!$temporaryChatEnabled) {
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
							<div class="flex items-center h-full">
								<Placeholder
									chatId={$chatId}
									{terminalContext}
									callActive={!!(bridge?.connected || bridge?.connecting)}
									callEnabled={!isShared}
									bind:selectedModelIdx
									{history}
									bind:selectedModels
									bind:messageInput
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedSkillIds
									bind:selectedFilterIds
									bind:imageGenerationEnabled
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
									messageQueue={$chatRequestQueues[$chatId] ?? []}
									askUser={savedAskUserPrompt ?? socketAskUserPrompt}
									onQueueSendNow={sendQueuedMessageNow}
									onQueueEdit={editQueuedMessage}
									onQueueDelete={deleteQueuedMessage}
									onWebSearchToggle={handleWebSearchToggle}
									on:chatVariables={() => {
										showChatVariablesModal = true;
									}}
									onChange={(data: any) => {
										if (!$temporaryChatEnabled) {
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
				</div>

				{#if !embedded}
					<ChatControls
						bind:terminalContext
						bind:history
						bind:chatFiles
						bind:params
						onParamChange={saveParam}
						bind:files
						chatId={$chatId}
						chatUser={chatOwner}
						modelId={selectedModelIds?.at(0) ?? null}
						models={selectedModelIds.reduce((a, e, i, arr) => {
							const model = $models.find((m) => m.id === e);
							if (model) {
								return [...a, model];
							}
							return a;
						}, [])}
						submitPrompt={submitHandler}
						onAskFile={askFile}
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
	{:else if loading}
		<div class=" flex items-center justify-center h-full w-full">
			<div class="m-auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}
</div>

<style>
	::-webkit-scrollbar {
		height: 0.5rem;
		width: 0.5rem;
	}
</style>
