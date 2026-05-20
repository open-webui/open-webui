<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';
	import { decode } from 'html-entities';

	import { getContext, onDestroy, onMount, tick } from 'svelte';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { get, type Unsubscriber, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { throttle, debounce } from 'throttle-debounce';
	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL } from '$lib/constants';

	import {
		chatId,
		chats,
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
		showControls,
		showCallOverlay,
		currentChatPage,
		temporaryChatEnabled,
		mobile,
		showOverview,
		chatTitle,
		showArtifacts,
		tools,
		toolServers,
		functions,
		selectedFolder,
		pinnedChats,
		showEmbeds,
		chatTokenStatsRefreshTrigger,
		subagentLiveStates
	} from '$lib/stores';
	import {
		convertMessagesToHistory,
		copyToClipboard,
		getMessageContentParts,
		createMessagesList,
		getPromptVariables,
		processDetails,
		removeDetails,
		removeAllDetails,
		renderPdfToImageDataUrls
	} from '$lib/utils';

	import {
		createNewChat,
		getAllTags,
		getChatById,
		getChatList,
		getPinnedChatList,
		getTagsById,
		updateChatById,
		updateChatFolderIdById
	} from '$lib/apis/chats';
	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { processWeb, processWebSearch, processYoutubeVideo } from '$lib/apis/retrieval';
	import { getAndUpdateUserLocation, updateUserSettings } from '$lib/apis/users';
	import {
		chatCompleted,
		generateQueries,
		chatAction,
		generateMoACompletion,
		stopTask,
		getTaskIdsByChatId
	} from '$lib/apis';
	import type { ReasoningEffort } from '$lib/apis';
	import {
		BASE_REASONING_EFFORTS,
		EXTRA_REASONING_EFFORTS,
		orderReasoningEfforts
	} from '$lib/constants/reasoning';
	import { getTools } from '$lib/apis/tools';
	import { uploadFile, getFileContentById } from '$lib/apis/files';
	import { createOpenAITextStream } from '$lib/apis/streaming';

	import { fade } from 'svelte/transition';

	import Banner from '../common/Banner.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import ChatControls from './ChatControls.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import NotificationToast from '../NotificationToast.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import { getFunctions } from '$lib/apis/functions';
	import Image from '../common/Image.svelte';
	import { updateFolderById } from '$lib/apis/folders';
	import { dispatchWidgetRender } from '$lib/utils/dataVizRegistry';

	export let chatIdProp = '';
	export let preloadedData = null;
	export let preloadedDataPromise: Promise<any> | null = null;

	let loading = true;
	let navigateGeneration = 0; // Incremented on each navigation; stale loadChat calls abort before touching state

	const eventTarget = new EventTarget();
	let controlPane;
	let controlPaneComponent;

	let messageInput;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	let navbarElement;

	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventCallback = null;

	let chatIdUnsubscriber: Unsubscriber | undefined;

	let selectedModels = [''];
	let atSelectedModel: Model | undefined;
	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	let selectedToolIds = [];
	let selectedFilterIds = [];
	let imageGenerationEnabled = false;
	let webSearchEnabled = false;
	let lastPersistedWebSearchEnabled: boolean | null = null;
	let studyModeEnabled = false;
	let lastPersistedStudyModeEnabled: boolean | null = null;
	let dataVizEnabled = false;
	let lastPersistedDataVizEnabled: boolean | null = null;
	let subagentsEnabled = false;
	let lastPersistedSubagentsEnabled: boolean | null = null;
	let codeInterpreterEnabled = false;

	// Auto-save tool preferences when they change
	let toolSaveTimeout;
	$: if (selectedToolIds && selectedToolIds.length > 0 && !loading) {
		// Only save when tools are actually selected (not during reset/init)
		// Debounce to avoid excessive API calls
		clearTimeout(toolSaveTimeout);
		toolSaveTimeout = setTimeout(async () => {
			try {
				await updateUserSettings(localStorage.token, {
					ui: {
						...$settings,
						defaultToolIds: selectedToolIds
					}
				});
			} catch (error) {
				console.error('Failed to save tool preferences:', error);
			}
		}, 1000); // Wait 1 second after last change before saving
	}

	// Keep the in-memory chat params in sync with the current per-chat web search state.
	$: if (webSearchEnabled !== params.webSearchEnabled) {
		params = { ...params, webSearchEnabled };
	}

	// Persist per-chat web search changes immediately so they survive reloads and other devices.
	$: if (
		activeChatId &&
		!loading &&
		!$temporaryChatEnabled &&
		lastPersistedWebSearchEnabled !== null &&
		webSearchEnabled !== lastPersistedWebSearchEnabled
	) {
		const nextParams = { ...params, webSearchEnabled };
		const chatIdToPersist = activeChatId;

		params = nextParams;
		lastPersistedWebSearchEnabled = webSearchEnabled;

		void saveChatHandler(chatIdToPersist, history, nextParams);
	}

	// Same pattern for studyModeEnabled — persist per-chat so reloads remember.
	$: if (studyModeEnabled !== params.studyModeEnabled) {
		params = { ...params, studyModeEnabled };
	}
	$: if (
		activeChatId &&
		!loading &&
		!$temporaryChatEnabled &&
		lastPersistedStudyModeEnabled !== null &&
		studyModeEnabled !== lastPersistedStudyModeEnabled
	) {
		const nextParams = { ...params, studyModeEnabled };
		const chatIdToPersist = activeChatId;

		params = nextParams;
		lastPersistedStudyModeEnabled = studyModeEnabled;

		void saveChatHandler(chatIdToPersist, history, nextParams);
	}

	// Same pattern for dataVizEnabled.
	$: if (dataVizEnabled !== params.dataVizEnabled) {
		params = { ...params, dataVizEnabled };
	}
	$: if (
		activeChatId &&
		!loading &&
		!$temporaryChatEnabled &&
		lastPersistedDataVizEnabled !== null &&
		dataVizEnabled !== lastPersistedDataVizEnabled
	) {
		const nextParams = { ...params, dataVizEnabled };
		const chatIdToPersist = activeChatId;

		params = nextParams;
		lastPersistedDataVizEnabled = dataVizEnabled;

		void saveChatHandler(chatIdToPersist, history, nextParams);
	}

	// Same pattern for subagentsEnabled — per-chat toggle, persisted so it
	// survives reloads and other devices.
	$: if (subagentsEnabled !== params.subagentsEnabled) {
		params = { ...params, subagentsEnabled };
	}
	$: if (
		activeChatId &&
		!loading &&
		!$temporaryChatEnabled &&
		lastPersistedSubagentsEnabled !== null &&
		subagentsEnabled !== lastPersistedSubagentsEnabled
	) {
		const nextParams = { ...params, subagentsEnabled };
		const chatIdToPersist = activeChatId;

		params = nextParams;
		lastPersistedSubagentsEnabled = subagentsEnabled;

		void saveChatHandler(chatIdToPersist, history, nextParams);
	}

	let showCommands = false;

	let generating = false;
	// Tagged with the response message id it belongs to so stale event handlers
	// can avoid clobbering an in-flight request's controller. The pre-tagged
	// version was a single AbortController shared component-wide; if a delayed
	// `chat:completion done` for a previous message fired during a follow-up
	// request, the previous message's cleanup would null this out and the
	// follow-up's stream would silently break.
	let generationController: { id: string; controller: AbortController } | null = null;
	let suppressErrorToast = false;
	// Set inside stopResponse() so the stream-side aborted handler can tell the
	// difference between user-clicked-stop (graceful) and a stray abort.
	let userInitiatedStop = false;

	// Clear `generationController` only if the event/handler claiming the clear
	// matches the in-flight controller's owner — stale events for prior messages
	// must not stomp on the current request's controller.
	const clearGenerationControllerIfOwned = (ownerId: string | null | undefined) => {
		if (!ownerId) return false;
		if (generationController?.id === ownerId) {
			generationController = null;
			return true;
		}
		return false;
	};

	// Gated debug logger. Flip on in DevTools with `localStorage.chatStreamDebug = '1'`
	// to surface every controller-state mutation and handleOpenAIError invocation —
	// useful for tracking down stray "operation was aborted" errors without leaving
	// noise in production.
	const chatStreamDebug = (...args: unknown[]) => {
		try {
			if (typeof localStorage !== 'undefined' && localStorage.chatStreamDebug === '1') {
				console.debug(...args);
			}
		} catch {
			// localStorage access can throw in some contexts (e.g. disabled cookies)
		}
	};

	const skipRemainingRetriesSet = new Set();
	const markSkipRemainingRetries = (messageId) => {
		if (messageId) skipRemainingRetriesSet.add(messageId);
	};

	let chat = null;
	let tags = [];

	let history = {
		messages: {},
		currentId: null
	};

	let taskIds = null;

	// Chat Input
	let prompt = '';
	let chatFiles = [];
	let files = [];
	let params = {};

	// Token usage tracking
	let tokenUsageGroups = {};
	let usagePollingInterval = null;
	let resetTimeouts: Map<string, ReturnType<typeof setTimeout>> = new Map(); // Per-group reset timeouts
	let resetTrigger = 0; // Increment to force Svelte reactivity when reset times pass

	/**
	 * Compute effective usage for a group, considering if reset time has passed client-side.
	 * This provides instant UI feedback when reset occurs, even before server confirms.
	 */
	const getEffectiveUsage = (groupData: any): { in: number; out: number; total: number } => {
		const now = Math.floor(Date.now() / 1000);
		const nextReset = groupData?.next_reset_at;

		// If we're past the reset time, show 0 optimistically while waiting for server confirmation
		if (nextReset && now >= nextReset) {
			return { in: 0, out: 0, total: 0 };
		}

		return groupData?.usage || { in: 0, out: 0, total: 0 };
	};

	// Reasoning effort tracking
	let reasoning = { effort: 'medium' };

	// Service tier tracking. Value is provider-specific (OpenAI: default/flex/
	// priority; Gemini: standard/flex/priority; etc.) so we keep it as `string`
	// rather than a fixed union — the per-model allowed list lives on
	// `meta.service_tier.values` and is enforced in MessageInput.svelte.
	let serviceTier: string = 'default';

	// Baseline so we only push a service-tier change to active task(s) when the
	// user actually flips it mid-run (and not when it's first set at task start).
	// Reset to null when no active task is running.
	let _serviceTierBaseline: typeof serviceTier | null = null;
	$: {
		if (taskIds && taskIds.length > 0) {
			if (_serviceTierBaseline === null) {
				_serviceTierBaseline = serviceTier;
			} else if (serviceTier !== _serviceTierBaseline) {
				const cid = getVisibleChatId();
				if (cid && $socket) {
					for (const tid of taskIds) {
						$socket.emit('service-tier-switch', {
							chat_id: cid,
							task_id: tid,
							service_tier: serviceTier
						});
					}
				}
				_serviceTierBaseline = serviceTier;
			}
		} else {
			_serviceTierBaseline = null;
		}
	}

	const getModelReasoningConfig = (modelId: string) => {
		const model = $models.find((m) => m.id === modelId);
		const reasoningConfig = model?.info?.meta?.reasoning;

		return {
			enabled: reasoningConfig?.enabled ?? true,
			extraEfforts: (reasoningConfig?.extra_efforts ?? []).filter((e) => typeof e === 'string' && e)
		};
	};

	const getAllowedReasoningEffortsForModel = (modelId: string) => {
		const { enabled, extraEfforts } = getModelReasoningConfig(modelId);
		if (!enabled) return [];
		return orderReasoningEfforts(Array.from(new Set([...BASE_REASONING_EFFORTS, ...extraEfforts])));
	};

	const clampEffortToAllowed = (effort: string, allowed: string[]) => {
		if (!allowed || allowed.length === 0) return null;
		if (allowed.includes(effort)) return effort;
		return allowed.includes('medium') ? 'medium' : allowed[0];
	};

	const getEffectiveReasoningForModel = (modelId: string, desired: { effort: string } | null) => {
		const allowed = getAllowedReasoningEffortsForModel(modelId);
		if (allowed.length === 0) return null;
		const desiredEffort = desired?.effort;
		if (!desiredEffort) return null;
		const clamped = clampEffortToAllowed(desiredEffort, allowed);
		return clamped ? { effort: clamped } : null;
	};

	/**
	 * Schedule per-group timeouts that fire exactly when each group's reset time arrives.
	 * When a reset time is reached:
	 * 1. Immediately increment resetTrigger to force UI update (shows 0 via getEffectiveUsage)
	 * 2. Fetch fresh data from server to get the new next_reset_at
	 */
	const scheduleGroupResetChecks = () => {
		const now = Math.floor(Date.now() / 1000);

		for (const [groupName, groupData] of Object.entries(tokenUsageGroups)) {
			const nextReset = (groupData as any).next_reset_at;

			// Clear any existing timeout for this group
			const existingTimeout = resetTimeouts.get(groupName);
			if (existingTimeout) {
				clearTimeout(existingTimeout);
				resetTimeouts.delete(groupName);
			}

			if (nextReset && nextReset > now) {
				// Calculate ms until reset (no buffer - we want instant UI update)
				const msUntilReset = (nextReset - now) * 1000;

				// Don't schedule if more than 24 hours away (will be recalculated on next poll)
				if (msUntilReset > 0 && msUntilReset < 24 * 60 * 60 * 1000) {
					const timeout = setTimeout(async () => {
						console.log(
							`Token usage: reset time reached for "${groupName}", triggering UI update...`
						);

						// Increment trigger to force Svelte reactivity - UI will immediately show 0
						// because getEffectiveUsage() checks if now >= next_reset_at
						resetTrigger++;

						// Clean up this timeout from the map
						resetTimeouts.delete(groupName);

						// Fetch fresh data from server (includes new next_reset_at for rolling windows)
						// Small delay to ensure server has processed the reset
						setTimeout(async () => {
							await fetchTokenUsage();
						}, 500);
					}, msUntilReset);

					resetTimeouts.set(groupName, timeout);
				}
			}
		}
	};

	/**
	 * Clear all scheduled reset timeouts
	 */
	const clearAllResetTimeouts = () => {
		for (const [groupName, timeout] of resetTimeouts) {
			clearTimeout(timeout);
		}
		resetTimeouts.clear();
	};

	const fetchTokenUsage = async () => {
		try {
			const response = await fetch(`${WEBUI_BASE_URL}/api/usage/groups`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				}
			});

			if (response.ok) {
				const data = await response.json();
				tokenUsageGroups = data.groups || {};

				// Schedule per-group timeouts based on returned next_reset_at values
				scheduleGroupResetChecks();
			}
		} catch (error) {
			console.error('Error fetching token usage:', error);
		}
	};

	// Get relevant groups for currently selected models
	// The resetTrigger dependency forces re-evaluation when reset times pass
	$: relevantGroups = (() => {
		// Reference resetTrigger to make this reactive to reset events
		const _ = resetTrigger;

		return Object.entries(tokenUsageGroups)
			.filter(([groupName, groupData]) => {
				const modelList = (groupData as any).models || [];
				return selectedModelIds.some((modelId) => modelList.includes(modelId));
			})
			.map(([groupName, groupData]) => {
				// Compute effective usage (0 if past reset time)
				const effectiveUsage = getEffectiveUsage(groupData);
				return [groupName, { ...groupData, effectiveUsage }] as [string, any];
			});
	})();

	const FAST_POLL_MS = 3000;
	const SLOW_POLL_MS = 30000;

	const startUsagePolling = (intervalMs = FAST_POLL_MS) => {
		if (usagePollingInterval) clearInterval(usagePollingInterval);
		usagePollingInterval = setInterval(fetchTokenUsage, intervalMs);
	};

	const stopUsagePolling = () => {
		if (usagePollingInterval) {
			clearInterval(usagePollingInterval);
			usagePollingInterval = null;
		}
		// Clear all per-group reset timeouts
		clearAllResetTimeouts();
	};

	$: if (chatIdProp) {
		navigateHandler();
	}

	onMount(() => {
		// Fetch immediately, then poll slowly to keep rate limits fresh
		fetchTokenUsage();
		startUsagePolling(SLOW_POLL_MS);
	});

	onDestroy(() => {
		stopUsagePolling();
	});

	const navigateHandler = async () => {
		const myGeneration = ++navigateGeneration;
		loading = true;
		lastPersistedWebSearchEnabled = null;
		lastPersistedStudyModeEnabled = null;
		lastPersistedDataVizEnabled = null;
		lastPersistedSubagentsEnabled = null;

		prompt = '';
		messageInput?.setText('');

		files = [];
		// Load default tools from user settings (use already-loaded store)
		selectedToolIds = $settings?.defaultToolIds || [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		subagentsEnabled = false;
		imageGenerationEnabled = false;

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		if (chatIdProp && (await loadChat(myGeneration))) {
			await tick();
			loading = false;

			// Wait for messages DOM to render, then force scroll to bottom
			await tick();
			if (messagesContainerElement) {
				messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
			}
			// Belt-and-suspenders: also schedule a delayed scroll for late-rendering content
			window.setTimeout(() => {
				if (messagesContainerElement) {
					messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
				}
			}, 50);
			window.setTimeout(() => {
				if (messagesContainerElement) {
					messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
				}
			}, 200);

			await tick();

			if (storageChatInput) {
				try {
					const input = JSON.parse(storageChatInput);

					if (!$temporaryChatEnabled) {
						messageInput?.setText(input.prompt);
						files = input.files;
						// Only use sessionStorage tools if they exist, otherwise keep saved defaults
						if (input.selectedToolIds && input.selectedToolIds.length > 0) {
							selectedToolIds = input.selectedToolIds;
						}
						selectedFilterIds = input.selectedFilterIds;
						imageGenerationEnabled = input.imageGenerationEnabled;
						codeInterpreterEnabled = input.codeInterpreterEnabled;
						studyModeEnabled = input.studyModeEnabled ?? false;
						dataVizEnabled = input.dataVizEnabled ?? false;
					}
				} catch (e) {}
			}

			if (!$mobile) {
				const chatInput = document.getElementById('chat-input');
				chatInput?.focus();
			}
		} else {
			await goto('/');
		}
	};

	const onSelect = async (e) => {
		const { type, data } = e;

		if (type === 'prompt') {
			// Handle prompt selection
			messageInput?.setText(data, async () => {
				if (!($settings?.insertSuggestionPrompt ?? false)) {
					await tick();
					submitPrompt(prompt);
				}
			});
		}
	};

	$: if (selectedModels && chatIdProp !== '') {
		saveSessionSelectedModels();
	}

	// When models load after initNewChat ran with an empty $models list,
	// apply the saved default (or first available) if nothing is selected yet.
	$: if ($models.length > 0 && !chatIdProp && (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === ''))) {
		const _availableModels = $models.filter((m) => !(m?.info?.meta?.hidden ?? false)).map((m) => m.id);
		if ($settings?.models) {
			const filtered = $settings.models.filter((id) => _availableModels.includes(id));
			if (filtered.length > 0) {
				selectedModels = filtered;
			} else {
				selectedModels = [_availableModels[0] ?? ''];
			}
		} else if ($config?.default_models) {
			const filtered = $config.default_models.split(',').filter((id) => _availableModels.includes(id));
			if (filtered.length > 0) {
				selectedModels = filtered;
			} else {
				selectedModels = [_availableModels[0] ?? ''];
			}
		} else {
			selectedModels = [_availableModels[0] ?? ''];
		}
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

	const arraysEqual = (a: string[], b: string[]) =>
		a.length === b.length && a.every((v, i) => v === b[i]);

	let oldSelectedModelIds = [''];
	$: if (!arraysEqual(selectedModelIds, oldSelectedModelIds)) {
		onSelectedModelIdsChange();
	}

	const onSelectedModelIdsChange = () => {
		if (oldSelectedModelIds.filter((id) => id).length > 0) {
			const _webSearchEnabled = webSearchEnabled;
			resetInput();

			if (_webSearchEnabled) {
				const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
				if (model?.info?.meta?.capabilities?.web_search ?? true) {
					webSearchEnabled = true;
				}
			}
		}
		oldSelectedModelIds = selectedModelIds;
	};

	const resetInput = () => {
		selectedToolIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;
		studyModeEnabled = false;
		dataVizEnabled = false;
		subagentsEnabled = false;
		imageGenerationEnabled = false;
		codeInterpreterEnabled = false;

		setDefaults();
	};

	const setDefaults = async () => {
		if (!$tools) {
			tools.set(await getTools(localStorage.token));
		}
		if (!$functions) {
			functions.set(await getFunctions(localStorage.token));
		}
		if (selectedModels.length !== 1 && !atSelectedModel) {
			return;
		}

		const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
		if (model) {
			// Set Default Tools
			if (model?.info?.meta?.toolIds) {
				selectedToolIds = [
					...new Set(
						[...(model?.info?.meta?.toolIds ?? [])].filter((id) => $tools.find((t) => t.id === id))
					)
				];
			}

			// Set Default Filters (Toggleable only)
			if (model?.info?.meta?.defaultFilterIds) {
				selectedFilterIds = model.info.meta.defaultFilterIds.filter((id) =>
					model?.filters?.find((f) => f.id === id)
				);
			}

			// Set Default Features
			if (model?.info?.meta?.defaultFeatureIds) {
				if (model.info?.meta?.capabilities?.['image_generation']) {
					imageGenerationEnabled = model.info.meta.defaultFeatureIds.includes('image_generation');
				}

				if (model.info?.meta?.capabilities?.['web_search']) {
					webSearchEnabled = model.info.meta.defaultFeatureIds.includes('web_search');
				}

				if (model.info?.meta?.capabilities?.['code_interpreter']) {
					codeInterpreterEnabled = model.info.meta.defaultFeatureIds.includes('code_interpreter');
				}
			}
		}
	};

	const parseChatIdFromPath = (pathname = '') => {
		const match = pathname.match(/^\/c\/([^/?#]+)/);
		return match?.[1] ? decodeURIComponent(match[1]) : '';
	};

	const resolveRouteChatId = () => {
		const fromPage = parseChatIdFromPath($page.url.pathname);
		if (fromPage) return fromPage;
		const browserPathname = typeof window !== 'undefined' ? window.location.pathname : '';
		return parseChatIdFromPath(browserPathname) || chatIdProp || '';
	};

	const isPersistentChatView = () => {
		const browserPathname = typeof window !== 'undefined' ? window.location.pathname : '';
		return browserPathname.includes('/c/') || $page.url.pathname.includes('/c/');
	};

	let routeChatId = '';
	let activeChatId = '';

	$: routeChatId = resolveRouteChatId();
	// Explicitly read $page and chatIdProp here so Svelte still re-evaluates
	// activeChatId when SvelteKit navigates (the `resolveRouteChatId()` call
	// below also reads them, but Svelte's compiler doesn't trace through
	// function calls when computing reactive dependencies).
	$: activeChatId = (() => {
		void $page;
		void chatIdProp;
		// Re-resolve at evaluation time. `routeChatId` is reactive on $page and
		// chatIdProp, but not on `window.location.pathname` — which can be
		// updated out-of-band via `history.replaceState` (e.g. when persisting a
		// brand-new chat in `initChatHandler`). Without a fresh resolution here,
		// activeChatId can be momentarily empty after a new chat is created,
		// hiding the Navbar's persistent-chat UI (token-stats box, etc.) until
		// the user navigates explicitly.
		const currentRouteChatId = resolveRouteChatId();
		if (currentRouteChatId) {
			return currentRouteChatId;
		}

		const currentChatId = $chatId ?? '';
		if ($temporaryChatEnabled || currentChatId.startsWith('local:') || isPersistentChatView()) {
			return currentChatId;
		}

		return '';
	})();

	$: if (routeChatId && routeChatId !== $chatId) {
		chatId.set(routeChatId);
	}

	const getVisibleChatId = () => {
		const currentRouteChatId = resolveRouteChatId();
		if (currentRouteChatId) {
			return currentRouteChatId;
		}

		const currentChatId = $chatId ?? '';
		return $temporaryChatEnabled || currentChatId.startsWith('local:') || isPersistentChatView()
			? currentChatId
			: '';
	};

	const getDraftChatId = () => getVisibleChatId() || null;

	const isVisibleChatEvent = (eventChatId) => {
		if (!eventChatId) {
			return false;
		}

		return getVisibleChatId() === eventChatId;
	};

	const getPendingAssistantMessageIds = () => {
		return Object.entries(history.messages)
			.filter(([, message]) => message.role === 'assistant' && message.done !== true)
			.map(([messageId]) => messageId);
	};

	const resolveChatEventMessageId = (eventMessageId) => {
		if (eventMessageId && history.messages[eventMessageId]) {
			return eventMessageId;
		}

		// If the event explicitly named a message id that we don't have, it's a
		// stale event from a previous request — DON'T retarget it to the current
		// pending message. That retargeting was the source of multiple latent
		// bugs where a delayed cancel/error from the prior turn would stomp on
		// the in-flight follow-up.
		if (eventMessageId) {
			chatStreamDebug('[chat-stream] dropping stale event with unmatched message_id', {
				eventMessageId
			});
			return null;
		}

		// Event has no message_id (legacy/back-compat behavior); fall back to
		// the only pending assistant message if there's exactly one.
		const pendingAssistantMessageIds = getPendingAssistantMessageIds();

		return pendingAssistantMessageIds.length === 1 ? pendingAssistantMessageIds[0] : null;
	};

	const markPendingAssistantMessagesDone = () => {
		const pendingAssistantMessageIds = getPendingAssistantMessageIds();

		for (const messageId of pendingAssistantMessageIds) {
			history.messages[messageId] = {
				...history.messages[messageId],
				done: true
			};
		}

		if (pendingAssistantMessageIds.length > 0) {
			history = { ...history };
		}
	};

	const showMessage = async (message, ignoreSettings = false) => {
		await tick();

		const _chatId = getVisibleChatId();
		let _messageId = message.id;

		let messageChildrenIds = [];
		if (_messageId === null) {
			messageChildrenIds = Object.keys(history.messages).filter(
				(id) => history.messages[id].parentId === null
			);
		} else {
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		while (messageChildrenIds.length !== 0) {
			_messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[_messageId].childrenIds;
		}

		history.currentId = _messageId;

		await tick();
		await tick();
		await tick();

		if (($settings?.scrollOnBranchChange ?? true) || ignoreSettings) {
			const messageElement = document.getElementById(`message-${message.id}`);
			if (messageElement) {
				messageElement.scrollIntoView({ behavior: 'smooth' });
			}
		}

		await tick();
		saveChatHandler(_chatId, history);
	};

	const chatEventHandler = async (event, cb) => {
		if (!isVisibleChatEvent(event.chat_id)) {
			console.log('❌ Chat ID mismatch - event ignored', {
				eventChatId: event.chat_id,
				visibleChatId: getVisibleChatId()
			});
			return;
		}

		await tick();

		const visibleChatId = getVisibleChatId();
		const type = event?.data?.type ?? null;
		const data = event?.data?.data ?? null;

		if (type === 'chat:title') {
			chatTitle.set(data);
			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			return;
		}

		if (type === 'chat:tags') {
			chat = await getChatById(localStorage.token, visibleChatId);
			allTags.set(await getAllTags(localStorage.token));
			return;
		}

		if (type === 'notification') {
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

			return;
		}

		if (type === 'confirmation') {
			eventCallback = cb;

			eventConfirmationInput = false;
			showEventConfirmation = true;

			eventConfirmationTitle = data.title;
			eventConfirmationMessage = data.message;
			return;
		}

		if (type === 'execute') {
			eventCallback = cb;

			try {
				// Use Function constructor to evaluate code in a safer way
				const asyncFunction = new Function(`return (async () => { ${data.code} })()`);
				const result = await asyncFunction();

				if (cb) {
					cb(result);
				}
			} catch (error) {
				console.error('Error executing code:', error);
			}

			return;
		}

		if (type === 'data_viz:render') {
			// Backend's show_widget tool is awaiting a render result.
			// dispatchWidgetRender finds the DataVizWidget by message_id+override_key,
			// asks it to render the (possibly repaired) widget_code, and resolves
			// with `{status, error_message?, error_stack?}` once the iframe either
			// succeeds or throws.
			const result = await dispatchWidgetRender(event.message_id, data);
			if (cb) cb(result);
			return;
		}

		if (type === 'input') {
			eventCallback = cb;

			eventConfirmationInput = true;
			showEventConfirmation = true;

			eventConfirmationTitle = data.title;
			eventConfirmationMessage = data.message;
			eventConfirmationInputPlaceholder = data.placeholder;
			eventConfirmationInputValue = data?.value ?? '';
			return;
		}

		// Subagent lifecycle events. The runner in `utils/subagent.py` emits
		// `chat:subagent:start` once when a subagent run begins, and
		// `chat:subagent:update` wrapping each forwarded inner-pipeline event
		// (chat:completion, status, errors) so the parent UI's collapsible
		// block under the parent assistant message can render live progress.
		//
		// Both events are keyed on `tool_call_id` (the parent's tool_call_id
		// that triggered this subagent) — that's the same key
		// `serialize_content_blocks` stamps onto the `<details
		// type="subagent_launch">` placeholder, so the SubagentBlock
		// component can look up state without any prop drilling.
		if (type === 'chat:subagent:start') {
			const sd = data ?? {};
			const key = sd.tool_call_id || sd.subagent_id;
			if (key) {
				const now = Math.floor(Date.now() / 1000);
				subagentLiveStates.update((s) => ({
					...s,
					[key]: {
						...(s[key] ?? {}),
						subagent_id: sd.subagent_id,
						parent_message_id: sd.parent_message_id,
						tool_call_id: sd.tool_call_id,
						num: sd.num,
						name: sd.name,
						chat_id: sd.chat_id ?? sd.subagent_id,
						continuation: sd.continuation === true,
						status: 'running',
						started_at: (s[key] && s[key].started_at) || now
					}
				}));
			}
			return;
		}

		if (type === 'chat:subagent:update') {
			const sd = data ?? {};
			const key = sd.tool_call_id || sd.subagent_id;
			if (!key) return;
			const innerEvent = sd.inner_event ?? {};
			const innerType = innerEvent?.type;
			const innerData = innerEvent?.data ?? {};
			subagentLiveStates.update((s) => {
				const cur = {
					...(s[key] ?? {
						subagent_id: sd.subagent_id,
						parent_message_id: sd.parent_message_id,
						tool_call_id: sd.tool_call_id,
						num: sd.num,
						name: sd.name,
						chat_id: sd.chat_id ?? sd.subagent_id,
						status: 'running'
					})
				};
				if (innerType === 'chat:completion') {
					if (Array.isArray(innerData.content_blocks)) {
						cur.content_blocks = innerData.content_blocks;
					}
					if (typeof innerData.content === 'string') {
						cur.content = innerData.content;
					}
					if (innerData.done === true) {
						cur.status = 'done';
						cur.ended_at = Math.floor(Date.now() / 1000);
					}
				} else if (innerType === 'chat:message:error') {
					cur.status = 'error';
					cur.error = innerData?.error ?? innerData;
					cur.ended_at = Math.floor(Date.now() / 1000);
				} else if (innerType === 'chat:tasks:cancel') {
					cur.status = 'cancelled';
					cur.ended_at = Math.floor(Date.now() / 1000);
				} else if (innerType === 'status') {
					const sh = cur.statusHistory ?? [];
					cur.statusHistory = [...sh, innerData];
				}
				return { ...s, [key]: cur };
			});
			return;
		}

		const resolvedMessageId = resolveChatEventMessageId(event.message_id);
		let message = resolvedMessageId ? history.messages[resolvedMessageId] : null;

		if (!message) {
			// CRITICAL: with the tightened resolveChatEventMessageId, an event
			// reaches this "no message" branch only when it (a) had no
			// message_id, or (b) named a message id we don't have. Case (b) is
			// almost always a stale event from a previous turn — clearing
			// generationController/generating here would kill the in-flight
			// follow-up. So: clear these only if no controller is currently in
			// flight, OR if the controller's owner matches a non-pending message
			// (i.e. the in-flight request really is the one this event is about).
			const hasInFlight = generationController != null;

			if (type === 'chat:tasks:cancel') {
				chatStreamDebug('[chat-stream] no-message chat:tasks:cancel', {
					eventMessageId: event.message_id,
					eventChatId: event.chat_id,
					hasInFlight
				});
				taskIds = null;
				if (!hasInFlight) {
					generating = false;
					generationController = null;
					markPendingAssistantMessagesDone();
				}
				return;
			}

			if (type === 'chat:message:error') {
				chatStreamDebug('[chat-stream] no-message chat:message:error', {
					eventMessageId: event.message_id,
					error: data?.error,
					hasInFlight
				});
				if (!hasInFlight) {
					taskIds = null;
					generating = false;
					generationController = null;

					if (visibleChatId && !$temporaryChatEnabled) {
						await loadChat();
						return;
					}
				}
			}

			if (type === 'chat:completion' && data?.done && visibleChatId && !$temporaryChatEnabled) {
				chatStreamDebug('[chat-stream] no-message chat:completion done', {
					eventMessageId: event.message_id,
					hasInFlight
				});
				if (!hasInFlight) {
					taskIds = null;
					generating = false;
					generationController = null;
					await loadChat();
				}
				return;
			}

			console.warn('Unable to resolve live chat message for current chat event', event);
			return;
		}

		// Stale-event guard: while we're in a retry countdown, any state
		// mutation from the just-failed attempt (chat:completion done=true,
		// chat:message:error, chat:tasks:cancel, content deltas, etc.) would
		// corrupt the retry — flipping done=true, clearing generating, or
		// stuffing in old content. Drop everything except the trailing
		// stop-by-error guard below.
		if (message.retrying) {
			return;
		}

		if (type === 'status') {
			if (message?.statusHistory) {
				message.statusHistory.push(data);
			} else {
				message.statusHistory = [data];
			}
		} else if (type === 'chat:completion') {
			await chatCompletionEventHandler(data, message, event.chat_id);
			// chatCompletionEventHandler manages history.messages updates internally via
			// spread objects. Do NOT fall through to the store-back at the end of this
			// function — it holds a reference to the pre-spread message object which
			// would overwrite the done=true state set inside chatCompletionEventHandler.
			return;
		} else if (type === 'chat:tasks:cancel') {
			chatStreamDebug('[chat-stream] resolved chat:tasks:cancel — clearing controller', {
				resolvedMessageId,
				ownedByThisMessage: generationController?.id === resolvedMessageId
			});
			taskIds = null;
			generating = false;
			clearGenerationControllerIfOwned(resolvedMessageId);

			const responseMessage = history.messages[history.currentId] ?? message;
			if (responseMessage?.parentId !== null && history.messages[responseMessage?.parentId]) {
				for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
					if (history.messages[messageId]) {
						history.messages[messageId].done = true;
					}
				}
			} else {
				message.done = true;
			}

			history = { ...history };
		} else if (type === 'chat:message:delta' || type === 'message') {
			message.content += data.content;
			history.messages[resolvedMessageId] = message;
			history = { ...history };
		} else if (type === 'chat:message' || type === 'replace') {
			message.content = data.content;
			history.messages[resolvedMessageId] = message;
			history = { ...history };
		} else if (type === 'chat:message:files' || type === 'files') {
			message.files = data.files;
		} else if (type === 'chat:message:embeds' || type === 'embeds') {
			message.embeds = data.embeds;
		} else if (type === 'data_viz:override') {
			// Backend's show_widget tool just persisted a corrected widget_code.
			// Merge into the in-memory message so the soon-to-mount DataVizWidget
			// (or any already-mounted one) picks it up without waiting for reload.
			if (data?.key && typeof data.widget_code === 'string') {
				const existing =
					message.dataVizOverrides && typeof message.dataVizOverrides === 'object'
						? message.dataVizOverrides
						: {};
				message.dataVizOverrides = { ...existing, [data.key]: data.widget_code };
				history.messages[resolvedMessageId] = message;
				history = { ...history };
			}
		} else if (type === 'chat:message:error') {
			chatStreamDebug('[chat-stream] resolved chat:message:error — clearing controller', {
				resolvedMessageId,
				error: data?.error,
				ownedByThisMessage: generationController?.id === resolvedMessageId
			});
			message.error = data.error;
			message.done = true;
			taskIds = null;
			generating = false;
			clearGenerationControllerIfOwned(resolvedMessageId);
		} else if (type === 'chat:message:follow_ups') {
			message.followUps = data.follow_ups;

			if (autoScroll) {
				scrollToBottom('smooth');
			}
		} else if (type === 'model-switch:pending') {
			// Model switch has been queued
			message.pendingSwitchModel = data.model_id;
			toast.info(
				$i18n.t('Model switch to {{model}} queued for next iteration', { model: data.model_id })
			);
		} else if (type === 'model-switch:applied') {
			// Model switch was applied
			message.model = data.new_model_id;
			message.modelName =
				$models.find((m) => m.id === data.new_model_id)?.name ?? data.new_model_id;
			message.pendingSwitchModel = null;
			toast.success($i18n.t('Switched to model: {{model}}', { model: message.modelName }));
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
		} else {
			console.log('Unknown message type', data);
		}

		history.messages[resolvedMessageId] = message;
	};

	const onMessageHandler = async (event: {
		origin: string;
		data: { type: string; text: string };
	}) => {
		if (event.origin !== window.origin) {
			return;
		}

		if (event.data.type === 'action:submit') {
			console.debug(event.data.text);

			if (prompt !== '') {
				await tick();
				submitPrompt(prompt);
			}
		}

		// Replace with your iframe's origin
		if (event.data.type === 'input:prompt') {
			console.debug(event.data.text);

			const inputElement = document.getElementById('chat-input');

			if (inputElement) {
				messageInput?.setText(event.data.text);
				inputElement.focus();
			}
		}

		if (event.data.type === 'input:prompt:submit') {
			console.debug(event.data.text);

			if (event.data.text !== '') {
				await tick();
				submitPrompt(event.data.text);
			}
		}
	};

	const savedModelIds = async () => {
		if (
			$selectedFolder &&
			selectedModels.filter((modelId) => modelId !== '').length > 0 &&
			!arraysEqual($selectedFolder?.data?.model_ids ?? [], selectedModels)
		) {
			const res = await updateFolderById(localStorage.token, $selectedFolder.id, {
				data: {
					model_ids: selectedModels
				}
			});
		}
	};

	$: if (selectedModels !== null) {
		savedModelIds();
	}

	let pageSubscribe = null;
	let showControlsSubscribe = null;
	let selectedFolderSubscribe = null;
	let socketSubscribe = null;

	// Cmd/Ctrl+S inside a temporary chat saves it instead of triggering the
	// browser's "Save Page" dialog. Skip when an editable element is focused so
	// it doesn't intercept normal text-input shortcuts.
	const onSaveChatShortcut = (event: KeyboardEvent) => {
		const isSaveCombo = (event.metaKey || event.ctrlKey) && event.key?.toLowerCase() === 's';
		if (!isSaveCombo) return;
		if (!$temporaryChatEnabled) return;

		const target = event.target as HTMLElement | null;
		const tag = target?.tagName?.toLowerCase();
		if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return;

		if (!history?.currentId || !Object.keys(history.messages ?? {}).length) return;

		event.preventDefault();
		saveTempChatHandler();
	};

	onMount(async () => {
		loading = true;

		window.addEventListener('message', onMessageHandler);
		window.addEventListener('keydown', onSaveChatShortcut);

		// Register socket event handler reactively
		socketSubscribe = socket.subscribe((_socket) => {
			if (_socket) {
				// Remove old listener if any
				_socket.off('events', chatEventHandler);
				// Register new listener
				_socket.on('events', chatEventHandler);

				// Reload chat if we reconnect while generating to catch missed completion events
				const connectHandler = async () => {
					if (generating || taskIds) {
						console.log('Socket reconnected while generating. Checking task status...');
						const visibleChatId = getVisibleChatId();

						if (visibleChatId && !$temporaryChatEnabled) {
							try {
								const taskRes = await getTaskIdsByChatId(localStorage.token, visibleChatId);
								if (!taskRes || !taskRes.task_ids || taskRes.task_ids.length === 0) {
									console.log('Task finished while disconnected. Reloading chat...');
									chatStreamDebug('[chat-stream] reconnect: task finished — clearing controller');
									taskIds = null;
									generating = false;
									generationController = null;
									await loadChat();
								} else {
									console.log('Task is still running on the backend. Resuming stream...');
								}
							} catch (e) {
								console.error('Failed to check task status on reconnect', e);
							}
						}
					}
				};
				_socket.off('connect', connectHandler);
				_socket.on('connect', connectHandler);
			}
		});

		pageSubscribe = page.subscribe(async (p) => {
			if (p.url.pathname === '/') {
				await tick();
				initNewChat();
			}
		});

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		if (!chatIdProp) {
			loading = false;
			await tick();
		}

		if (storageChatInput) {
			prompt = '';
			messageInput?.setText('');

			files = [];
			selectedToolIds = [];
			selectedFilterIds = [];
			webSearchEnabled = false;
			studyModeEnabled = false;
			dataVizEnabled = false;
			imageGenerationEnabled = false;
			codeInterpreterEnabled = false;

			try {
				const input = JSON.parse(storageChatInput);

				if (!$temporaryChatEnabled) {
					messageInput?.setText(input.prompt);
					files = input.files;
					// Only use sessionStorage tools if they exist, otherwise keep saved defaults
					if (input.selectedToolIds && input.selectedToolIds.length > 0) {
						selectedToolIds = input.selectedToolIds;
					}
					selectedFilterIds = input.selectedFilterIds;
					if (!chatIdProp) {
						webSearchEnabled = input.webSearchEnabled;
					}
					imageGenerationEnabled = input.imageGenerationEnabled;
					codeInterpreterEnabled = input.codeInterpreterEnabled;
					studyModeEnabled = input.studyModeEnabled ?? false;
					dataVizEnabled = input.dataVizEnabled ?? false;
				}
			} catch (e) {}
		}

		showControlsSubscribe = showControls.subscribe(async (value) => {
			if (controlPane && !$mobile) {
				try {
					if (value) {
						controlPaneComponent.openPane();
					} else {
						controlPane.collapse();
					}
				} catch (e) {
					// ignore
				}
			}

			if (!value) {
				showCallOverlay.set(false);
				showOverview.set(false);
				showArtifacts.set(false);
				showEmbeds.set(false);
			}
		});

		selectedFolderSubscribe = selectedFolder.subscribe(async (folder) => {
			if (folder?.data?.model_ids && !arraysEqual(selectedModels, folder.data.model_ids)) {
				selectedModels = folder.data.model_ids;

				console.log('Set selectedModels from folder data:', selectedModels);
			}
		});

		if (!$mobile) {
			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		}
	});

	onDestroy(() => {
		try {
			pageSubscribe();
			showControlsSubscribe();
			selectedFolderSubscribe();
			socketSubscribe?.();
			chatIdUnsubscriber?.();
			window.removeEventListener('message', onMessageHandler);
			window.removeEventListener('keydown', onSaveChatShortcut);
			$socket?.off('events', chatEventHandler);
		} catch (e) {
			console.error(e);
		}
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
			fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

			files = files;
			toast.success($i18n.t('File uploaded successfully'));
		} catch (e) {
			console.error('Error uploading file:', e);
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error(
				$i18n.t('Error uploading file: {{error}}', {
					error: e.message || 'Unknown error'
				})
			);
		}
	};

	const uploadWeb = async (url) => {
		console.log(url);

		const fileItem = {
			type: 'text',
			name: url,
			status: 'uploading',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processWeb(localStorage.token, '', url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.file = {
					...res.file,
					...fileItem.file
				};

				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(JSON.stringify(e));
		}
	};

	const uploadYoutubeTranscription = async (url) => {
		console.log(url);

		const fileItem = {
			type: 'text',
			name: url,
			status: 'uploading',
			context: 'full',
			url: url,
			error: ''
		};

		try {
			files = [...files, fileItem];
			const res = await processYoutubeVideo(localStorage.token, url);

			if (res) {
				fileItem.status = 'uploaded';
				fileItem.file = {
					...res.file,
					...fileItem.file
				};
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(`${e}`);
		}
	};

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
		console.log('initNewChat');
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

		const availableModels = $models
			.filter((m) => !(m?.info?.meta?.hidden ?? false))
			.map((m) => m.id);

		if ($page.url.searchParams.get('models') || $page.url.searchParams.get('model')) {
			const urlModels = (
				$page.url.searchParams.get('models') ||
				$page.url.searchParams.get('model') ||
				''
			)?.split(',');

			if (urlModels.length === 1) {
				const m = $models.find((m) => m.id === urlModels[0]);
				if (!m) {
					const modelSelectorButton = document.getElementById('model-selector-0-button');
					if (modelSelectorButton) {
						modelSelectorButton.click();
						await tick();

						const modelSelectorInput = document.getElementById('model-search-input');
						if (modelSelectorInput) {
							modelSelectorInput.focus();
							modelSelectorInput.value = urlModels[0];
							modelSelectorInput.dispatchEvent(new Event('input'));
						}
					}
				} else {
					selectedModels = urlModels;
				}
			} else {
				selectedModels = urlModels;
			}

			selectedModels = selectedModels.filter((modelId) =>
				$models.map((m) => m.id).includes(modelId)
			);
		} else {
			if ($selectedFolder?.data?.model_ids) {
				selectedModels = $selectedFolder?.data?.model_ids;
			} else {
				if (sessionStorage.selectedModels) {
					selectedModels = JSON.parse(sessionStorage.selectedModels);
					sessionStorage.removeItem('selectedModels');
				} else {
					if ($settings?.models) {
						selectedModels = $settings?.models;
					} else if ($config?.default_models) {
						console.log($config?.default_models.split(',') ?? '');
						selectedModels = $config?.default_models.split(',');
					}
				}
			}

			if (availableModels.length > 0) {
				selectedModels = selectedModels.filter((modelId) => availableModels.includes(modelId));
			}
		}

		if (availableModels.length > 0 && (selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === ''))) {
			selectedModels = [availableModels?.at(0) ?? ''];
		}

		await showControls.set(false);
		await showCallOverlay.set(false);
		await showOverview.set(false);
		await showArtifacts.set(false);

		if ($page.url.pathname.includes('/c/')) {
			window.history.replaceState(history.state, '', `/`);
		}

		autoScroll = true;

		// Check if we should preserve state (from temp chat toggle)
		const preserveState = sessionStorage.getItem('tempChatPreserveState');
		const preservedWebSearch = preserveState ? webSearchEnabled : false;
		if (preserveState) {
			sessionStorage.removeItem('tempChatPreserveState');
		}

		resetInput();
		await chatId.set('');
		await chatTitle.set('');

		history = {
			messages: {},
			currentId: null
		};

		chatFiles = [];
		params = {};

		if ($page.url.searchParams.get('youtube')) {
			uploadYoutubeTranscription(
				`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`
			);
		}

		if ($page.url.searchParams.get('load-url')) {
			await uploadWeb($page.url.searchParams.get('load-url'));
		}

		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		if ($page.url.searchParams.get('image-generation') === 'true') {
			imageGenerationEnabled = true;
		}

		if ($page.url.searchParams.get('code-interpreter') === 'true') {
			codeInterpreterEnabled = true;
		}

		if ($page.url.searchParams.get('reasoning')) {
			const reasoningParam = $page.url.searchParams.get('reasoning')?.toLowerCase();
			if ([...BASE_REASONING_EFFORTS, ...EXTRA_REASONING_EFFORTS].includes(reasoningParam)) {
				reasoning.effort = reasoningParam;
			}
		}

		if ($page.url.searchParams.get('tools')) {
			selectedToolIds = $page.url.searchParams
				.get('tools')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		} else if ($page.url.searchParams.get('tool-ids')) {
			selectedToolIds = $page.url.searchParams
				.get('tool-ids')
				?.split(',')
				.map((id) => id.trim())
				.filter((id) => id);
		}

		if ($page.url.searchParams.get('call') === 'true') {
			showCallOverlay.set(true);
			showControls.set(true);
		}

		if ($page.url.searchParams.get('q')) {
			const q = $page.url.searchParams.get('q') ?? '';
			messageInput?.setText(q);

			if (q) {
				if (($page.url.searchParams.get('submit') ?? 'true') === 'true') {
					await tick();
					submitPrompt(q);
				}
			}
		}

		selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		// Load persistent tool preferences from already-loaded settings store
		if ($settings?.defaultToolIds) {
			selectedToolIds = $settings.defaultToolIds;
		}

		// Restore preserved state from temp chat toggle
		if (preserveState && preservedWebSearch) {
			const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
			if (model?.info?.meta?.capabilities?.web_search ?? true) {
				webSearchEnabled = true;
			}
		}

		if (!$mobile) {
			const chatInput = document.getElementById('chat-input');
			setTimeout(() => chatInput?.focus(), 0);
		}
	};

	const loadChat = async (generation: number = navigateGeneration) => {
		const currentChatId = chatIdProp || getVisibleChatId();

		if (!currentChatId) {
			return false;
		}

		chatId.set(currentChatId);

		if ($temporaryChatEnabled) {
			temporaryChatEnabled.set(false);
		}

		let _chat, _taskRes;

		if (preloadedDataPromise) {
			const resolved = await preloadedDataPromise;
			preloadedDataPromise = null;
			if (resolved && resolved.chatId === currentChatId && resolved.chat) {
				_chat = resolved.chat;
				_taskRes = resolved.taskRes;
			} else {
				[_chat, _taskRes] = await Promise.all([
					getChatById(localStorage.token, currentChatId).catch(async (error) => {
						await goto('/');
						return null;
					}),
					getTaskIdsByChatId(localStorage.token, currentChatId).catch((error) => {
						return null;
					})
				]);
			}
		} else if (preloadedData && preloadedData.chatId === currentChatId && preloadedData.chat) {
			_chat = preloadedData.chat;
			_taskRes = preloadedData.taskRes;
			preloadedData = null;
		} else {
			[_chat, _taskRes] = await Promise.all([
				getChatById(localStorage.token, currentChatId).catch(async (error) => {
					await goto('/');
					return null;
				}),
				getTaskIdsByChatId(localStorage.token, currentChatId).catch((error) => {
					return null;
				})
			]);
		}

		// Abort if a newer navigation started while we were fetching
		if (generation !== navigateGeneration) {
			return false;
		}

		chat = _chat;

		if (!chat) {
			return null;
		}

		// Load tags asynchronously — they're cosmetic and shouldn't block rendering
		getTagsById(localStorage.token, currentChatId)
			.then((_tags) => {
				tags = _tags;
			})
			.catch(() => {
				tags = [];
			});

		const chatContent = chat.chat;

		if (!chatContent) {
			return null;
		}

		selectedModels =
			(chatContent?.models ?? undefined) !== undefined
				? chatContent.models
				: [chatContent.models ?? ''];

		if (!($user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true))) {
			selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
		}

		oldSelectedModelIds = selectedModels;

		// Build history and pre-process done states BEFORE assigning to avoid multiple reactive triggers
		const loadedHistory =
			(chatContent?.history ?? undefined) !== undefined
				? chatContent.history
				: convertMessagesToHistory(chatContent.messages);

		if (loadedHistory.currentId) {
			for (const message of Object.values(loadedHistory.messages)) {
				if (message.role === 'assistant') {
					message.done = true;
				}
			}
		}

		history = loadedHistory;

		chatTitle.set(chatContent.title);

		params = chatContent?.params ?? {};
		chatFiles = chatContent?.files ?? [];

		// Restore webSearchEnabled from saved params
		if (params.webSearchEnabled !== undefined) {
			const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
			if (model?.info?.meta?.capabilities?.web_search ?? true) {
				webSearchEnabled = params.webSearchEnabled;
			}
		}

		lastPersistedWebSearchEnabled = webSearchEnabled;

		// Restore study mode + data viz toggles from saved params (feature-flag gated
		// at submit time, so restoring true here is safe even if the global flag flips).
		if (params.studyModeEnabled !== undefined) {
			studyModeEnabled = params.studyModeEnabled;
		}
		lastPersistedStudyModeEnabled = studyModeEnabled;

		if (params.dataVizEnabled !== undefined) {
			dataVizEnabled = params.dataVizEnabled;
		}
		lastPersistedDataVizEnabled = dataVizEnabled;

		if (params.subagentsEnabled !== undefined) {
			subagentsEnabled = params.subagentsEnabled;
		}
		lastPersistedSubagentsEnabled = subagentsEnabled;

		// Hydrate the subagent live-state store with anything persisted on
		// this chat's messages. Each message's `subagent_runs` is a
		// {key -> SubagentRun} dict (key is usually `subagent_id`, or
		// `subagent_id#tool_call_id` for continues). Seed the store keyed by
		// tool_call_id when present so the SubagentBlock renderer can look up
		// state by the `tool_call_id` attribute on the markdown placeholder.
		try {
			const seeded: Record<string, any> = {};
			for (const msg of Object.values(history.messages ?? {})) {
				const runs = (msg as any)?.subagent_runs;
				if (runs && typeof runs === 'object') {
					for (const [, run] of Object.entries(runs)) {
						const r = run as any;
						const key = r?.tool_call_id || r?.subagent_id;
						if (key) {
							seeded[key] = {
								...r,
								parent_message_id: (msg as any).id
							};
						}
					}
				}
			}
			if (Object.keys(seeded).length > 0) {
				subagentLiveStates.update((s) => ({ ...s, ...seeded }));
			}
		} catch (e) {
			console.warn('Failed to hydrate subagentLiveStates:', e);
		}

		autoScroll = true;

		taskIds = _taskRes?.task_ids ?? null;

		await tick();

		return true;
	};

	const scrollToBottom = debounce(100, async (behavior = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});
		}
	});

	const onScroll = throttle(100, (e) => {
		autoScroll =
			messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
			messagesContainerElement.clientHeight + 5;
	});

	onDestroy(() => {
		onScroll.cancel();
		scrollToBottom.cancel();
	});
	let _completedMessageIds = new Set<string>();

	const chatCompletedHandler = async (chatId, modelId, responseMessageId, messages) => {
		// Guard against duplicate completion for the same message (e.g. socket + direct stream race)
		if (_completedMessageIds.has(responseMessageId)) {
			return;
		}
		_completedMessageIds.add(responseMessageId);

		try {
			const res = await chatCompleted(localStorage.token, {
				model: modelId,
				messages: messages.map((m) => ({
					id: m.id,
					role: m.role,
					content: m.content,
					info: m.info ? m.info : undefined,
					timestamp: m.timestamp,
					...(m.usage ? { usage: m.usage } : {}),
					...(m.sources ? { sources: m.sources } : {}),
					...(m.reasoning_details ? { reasoning_details: m.reasoning_details } : {}),
					...(m.reasoning_details_per_round
						? { reasoning_details_per_round: m.reasoning_details_per_round }
						: {})
				})),
				filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
				model_item: $models.find((m) => m.id === modelId),
				chat_id: chatId,
				session_id: $socket?.id,
				id: responseMessageId
			}).catch((error) => {
				toast.error(`${error}`);
				messages.at(-1).error = { content: error };

				return null;
			});

			if (res !== null && res.messages) {
				// Update chat history with the new messages
				for (const message of res.messages) {
					if (message?.id) {
						// Add null check for message and message.id
						history.messages[message.id] = {
							...history.messages[message.id],
							...(history.messages[message.id].content !== message.content
								? { originalContent: history.messages[message.id].content }
								: {}),
							...message,
							...(message.role === 'assistant' ? { done: true } : {})
						};
					}
				}
			}

			await tick();

			if (isVisibleChatEvent(chatId)) {
				if (!$temporaryChatEnabled) {
					chat = await updateChatById(localStorage.token, chatId, {
						models: selectedModels,
						messages: messages,
						history: history,
						params: params,
						reasoning: reasoning,
						files: chatFiles
					});

					currentChatPage.set(1);
					await chats.set(await getChatList(localStorage.token, $currentChatPage));
				}
			}
		} finally {
			const owned = generationController?.id === responseMessageId;
			chatStreamDebug('[chat-stream] chatCompletedHandler finally — clearing controller', {
				responseMessageId,
				ownedByThisMessage: owned
			});
			// Ensure the response message is definitively marked as done
			if (history.messages[responseMessageId]) {
				history.messages[responseMessageId].done = true;
			}

			taskIds = null;
			generating = false;
			clearGenerationControllerIfOwned(responseMessageId);

			// Force a reactive history update so Svelte picks up all in-place mutations
			// that may have occurred during the async HTTP calls above
			history = { ...history };
		}
	};

	const chatActionHandler = async (chatId, actionId, modelId, responseMessageId, event = null) => {
		try {
			const messages = createMessagesList(history, responseMessageId);

			const res = await chatAction(localStorage.token, actionId, {
				model: modelId,
				messages: messages.map((m) => ({
					id: m.id,
					role: m.role,
					content: m.content,
					info: m.info ? m.info : undefined,
					timestamp: m.timestamp,
					...(m.sources ? { sources: m.sources } : {}),
					...(m.reasoning_details ? { reasoning_details: m.reasoning_details } : {}),
					...(m.reasoning_details_per_round
						? { reasoning_details_per_round: m.reasoning_details_per_round }
						: {})
				})),
				...(event ? { event: event } : {}),
				model_item: $models.find((m) => m.id === modelId),
				chat_id: chatId,
				session_id: $socket?.id,
				id: responseMessageId
			}).catch((error) => {
				toast.error(`${error}`);
				messages.at(-1).error = { content: error };
				return null;
			});

			if (res !== null && res.messages) {
				// Update chat history with the new messages
				for (const message of res.messages) {
					history.messages[message.id] = {
						...history.messages[message.id],
						...(history.messages[message.id].content !== message.content
							? { originalContent: history.messages[message.id].content }
							: {}),
						...message
					};
				}
			}

			if (isVisibleChatEvent(chatId)) {
				if (!$temporaryChatEnabled) {
					chat = await updateChatById(localStorage.token, chatId, {
						models: selectedModels,
						messages: messages,
						history: history,
						params: params,
						files: chatFiles
					});

					currentChatPage.set(1);
					await chats.set(await getChatList(localStorage.token, $currentChatPage));
				}
			}
		} finally {
			chatStreamDebug('[chat-stream] chatActionHandler finally — clearing taskIds/generating', {
				responseMessageId
			});
			taskIds = null;
			generating = false;
			// chatActionHandler doesn't own a chat-stream controller (it's for
			// rate/feedback-style actions). Only clear if this action's message
			// id happens to match the in-flight controller — defensive but
			// shouldn't normally apply.
			clearGenerationControllerIfOwned(responseMessageId);
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
		messageInput?.setText('');
		if (selectedModels.length === 0) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const modelId = selectedModels[0];
			const model = $models.filter((m) => m.id === modelId).at(0);

			const messages = createMessagesList(history, history.currentId);
			const parentMessage = messages.length !== 0 ? messages.at(-1) : null;

			const userMessageId = uuidv4();
			const responseMessageId = uuidv4();

			const userMessage = {
				id: userMessageId,
				parentId: parentMessage ? parentMessage.id : null,
				childrenIds: [responseMessageId],
				role: 'user',
				content: userPrompt ? userPrompt : `[PROMPT] ${userMessageId}`,
				timestamp: Math.floor(Date.now() / 1000)
			};

			const responseMessage = {
				id: responseMessageId,
				parentId: userMessageId,
				childrenIds: [],
				role: 'assistant',
				content: `[RESPONSE] ${responseMessageId}`,
				done: true,

				model: modelId,
				modelName: model.name ?? model.id,
				modelIdx: 0,
				timestamp: Math.floor(Date.now() / 1000)
			};

			if (parentMessage) {
				parentMessage.childrenIds.push(userMessageId);
				history.messages[parentMessage.id] = parentMessage;
			}
			history.messages[userMessageId] = userMessage;
			history.messages[responseMessageId] = responseMessage;

			history.currentId = responseMessageId;

			await tick();

			if (autoScroll) {
				scrollToBottom();
			}

			if (messages.length === 0) {
				await initChatHandler(history);
			} else {
				await saveChatHandler(getVisibleChatId(), history);
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
			await saveChatHandler(getVisibleChatId(), history);
		}
	};

	const chatCompletionEventHandler = async (data, message, chatId) => {
		const {
			id,
			done,
			choices,
			content,
			content_blocks,
			sources,
			selected_model_id,
			error,
			usage,
			reasoning_details,
			reasoning_details_per_round
		} = data;

		if (error) {
			await handleOpenAIError(error, message, 'chatCompletionEventHandler:data.error');
			// Error takes priority — do NOT fall through to the `done`
			// handler which would finalize the message as completed and
			// prevent the automatic retry mechanism from triggering.
			return;
		}

		// Emit usage event for token tracking if usage data is available
		if (usage && selected_model_id && $socket) {
			$socket.emit('usage', {
				model: selected_model_id,
				usage: usage,
				chat_id: chatId
			});
		}

		if (sources && !message?.sources) {
			message.sources = sources;
		}

		if (choices) {
			if (choices[0]?.message?.content) {
				// Non-stream response
				message.content += choices[0]?.message?.content;

				if (choices[0]?.message?.reasoning_details) {
					message.reasoning_details = choices[0].message.reasoning_details;
				}
			} else {
				// Stream response
				if (choices[0]?.delta?.reasoning_details) {
					if (!Array.isArray(message.reasoning_details)) {
						message.reasoning_details = [];
					}

					// Merge streaming reasoning_details deltas. Match by (id, type)
					// with a (type, index) fallback for id-less chunks; concat
					// text/data/summary across fragments. Mirrors the backend
					// merger in middleware.py — the two MUST stay in lockstep
					// because the frontend's locally captured copy gets POSTed
					// back to the server via chatCompleted and overwrites the
					// backend's clean copy if they diverge.
					//
					// See backend/open_webui/utils/REASONING_DETAILS.md §2 (the
					// wire protocol) and §9 (why frontend + backend must match).
					for (const detail of choices[0].delta.reasoning_details) {
						const detailId = detail.id ?? null;
						const detailType = detail.type ?? null;
						const detailIdx = detail.index ?? 0;

						let existing = null;
						if (detailId !== null) {
							existing = message.reasoning_details.find(
								(d) => d.id === detailId && d.type === detailType
							);
							if (!existing) {
								existing = message.reasoning_details.find(
									(d) => d.id == null && d.type === detailType && d.index === detailIdx
								);
							}
						} else {
							existing = message.reasoning_details.find(
								(d) => d.type === detailType && d.index === detailIdx
							);
						}

						if (existing) {
							if (detail.text) existing.text = (existing.text || '') + detail.text;
							if (detail.data) existing.data = (existing.data || '') + detail.data;
							if (detail.summary) existing.summary = (existing.summary || '') + detail.summary;
							// `type` is matched on, so it can't have changed; never overwrite.
							if (detail.id) existing.id = detail.id;
							if (detail.signature) existing.signature = detail.signature;
							if (detail.format) existing.format = detail.format;
							if (detail.index != null) existing.index = detail.index;
						} else {
							message.reasoning_details.push({ ...detail });
						}
					}
				}

				let value = choices[0]?.delta?.content ?? '';
				if (!(message.content == '' && value == '\n')) {
					message.content += value;
					message = { ...message };
					history.messages[message.id] = message;
					history = { ...history };

					if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
						navigator.vibrate(5);
					}

					// Emit chat event for TTS
					const messageContentParts = getMessageContentParts(
						removeAllDetails(message.content),
						$config?.audio?.tts?.split_on ?? 'punctuation'
					);
					messageContentParts.pop();

					// dispatch only last sentence and make sure it hasn't been dispatched before
					if (
						messageContentParts.length > 0 &&
						messageContentParts[messageContentParts.length - 1] !== message.lastSentence
					) {
						message.lastSentence = messageContentParts[messageContentParts.length - 1];
						eventTarget.dispatchEvent(
							new CustomEvent('chat', {
								detail: {
									id: message.id,
									content: messageContentParts[messageContentParts.length - 1]
								}
							})
						);
					}
				}
			}
		}

		// Some backends may only attach final `reasoning_details` on the done event (no `choices` deltas).
		if (Array.isArray(reasoning_details)) {
			if (reasoning_details.length > 0) {
				message.reasoning_details = reasoning_details;
			}
		} else if (reasoning_details) {
			message.reasoning_details = reasoning_details;
		}

		// Per-round reasoning_details (one array per stream round / tool-call
		// round) lets the chat replay attach the correct round's reasoning to
		// each tool_calls assistant message in multi-turn follow-ups. Without
		// this, only the last round's reasoning survives in `reasoning_details`.
		if (
			Array.isArray(reasoning_details_per_round) &&
			reasoning_details_per_round.length > 0
		) {
			message.reasoning_details_per_round = reasoning_details_per_round;
		}

		if (Array.isArray(content_blocks)) {
			// Structured content blocks are the canonical replay form. They travel
			// alongside the legacy `content` HTML projection for backwards compat
			// and keep the API replay byte-stable with the live tool-call loop.
			message.content_blocks = content_blocks;
		}

		if (content) {
			// REALTIME_CHAT_SAVE is disabled
			message.content = content;
			message = { ...message };
			history.messages[message.id] = message;
			history = { ...history };

			if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
				navigator.vibrate(5);
			}

			// Emit chat event for TTS
			const messageContentParts = getMessageContentParts(
				removeAllDetails(message.content),
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);
			messageContentParts.pop();

			// dispatch only last sentence and make sure it hasn't been dispatched before
			if (
				messageContentParts.length > 0 &&
				messageContentParts[messageContentParts.length - 1] !== message.lastSentence
			) {
				message.lastSentence = messageContentParts[messageContentParts.length - 1];
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: {
							id: message.id,
							content: messageContentParts[messageContentParts.length - 1]
						}
					})
				);
			}
		}

		if (selected_model_id) {
			message.selectedModelId = selected_model_id;
			message.arena = true;
		}

		if (usage) {
			message.usage = usage;
		}

		message = { ...message };
		history.messages[message.id] = message;
		history = { ...history };

		if (done) {
			message.done = true;
			message = { ...message };

			if ($settings.responseAutoCopy) {
				copyToClipboard(message.content);
			}

			if ($settings.responseAutoPlayback && !$showCallOverlay) {
				await tick();
				document.getElementById(`speak-button-${message.id}`)?.click();
			}

			// Emit chat event for TTS
			let lastMessageContentPart =
				getMessageContentParts(
					removeAllDetails(message.content),
					$config?.audio?.tts?.split_on ?? 'punctuation'
				)?.at(-1) ?? '';
			if (lastMessageContentPart) {
				eventTarget.dispatchEvent(
					new CustomEvent('chat', {
						detail: { id: message.id, content: lastMessageContentPart }
					})
				);
			}
			eventTarget.dispatchEvent(
				new CustomEvent('chat:finish', {
					detail: {
						id: message.id,
						content: message.content
					}
				})
			);

			history.messages[message.id] = message;
			history = { ...history };

			await tick();
			if (autoScroll) {
				scrollToBottom();
			}

			await chatCompletedHandler(
				chatId,
				message.model,
				message.id,
				createMessagesList(history, message.id)
			);

			// Trigger token stats refresh if this message had usage data
			if (message.usage) {
				chatTokenStatsRefreshTrigger.update((n) => n + 1);
			}
		}

		await tick();

		if (autoScroll) {
			scrollToBottom();
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (userPrompt, { _raw = false } = {}) => {
		console.log('submitPrompt', userPrompt, getVisibleChatId());

		const _selectedModels = selectedModels.map((modelId) =>
			$models.map((m) => m.id).includes(modelId) ? modelId : ''
		);

		if (!arraysEqual(selectedModels, _selectedModels)) {
			selectedModels = _selectedModels;
		}

		if (userPrompt === '' && files.length === 0) {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}
		if (selectedModels.includes('')) {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		if (
			files.length > 0 &&
			files.filter((file) => file.status === 'uploading' || file.status === 'processing')
				.length > 0
		) {
			const inFlightFiles = files.filter(
				(file) => file.status === 'uploading' || file.status === 'processing'
			);
			const uploadingFiles = inFlightFiles.filter((file) => file.status === 'uploading');
			const processingFiles = inFlightFiles.filter((file) => file.status === 'processing');
			const allSentWaitingForServer = uploadingFiles.every(
				(file) => typeof file?.progress === 'number' && file.progress >= 99
			);

			toast.error(
				processingFiles.length > 0
					? $i18n.t(
							`Open WebUI is still extracting content from {{count}} file(s). Please wait.`,
							{ count: processingFiles.length }
						)
					: allSentWaitingForServer
						? $i18n.t(
								`Uploads have finished sending ({{count}} file(s)); waiting for the server to finish processing.`,
								{ count: uploadingFiles.length }
							)
						: $i18n.t(
								`Oops! There are files still uploading. Please wait for the upload to complete.`
							)
			);
			return;
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
			return;
		}

		if (history?.currentId) {
			const lastMessage = history.messages[history.currentId];
			if (lastMessage.done != true) {
				// Response not done
				return;
			}

			if (lastMessage.error && !lastMessage.content) {
				// Error in response
				toast.error($i18n.t(`Oops! There was an error in the previous response.`));
				return;
			}
		}

		messageInput?.setText('');
		prompt = '';

		const messages = createMessagesList(history, history.currentId);
		const _files = structuredClone(files);

		chatFiles.push(
			..._files.filter((item) =>
				['doc', 'text', 'file', 'note', 'chat', 'folder', 'collection'].includes(item.type)
			)
		);
		chatFiles = chatFiles.filter(
			// Remove duplicates
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

		files = [];
		messageInput?.setText('');

		// Create user message
		let userMessageId = uuidv4();
		let userMessage = {
			id: userMessageId,
			parentId: messages.length !== 0 ? messages.at(-1).id : null,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			files: _files.length > 0 ? _files : undefined,
			timestamp: Math.floor(Date.now() / 1000), // Unix epoch
			models: selectedModels
		};

		// Add message to history and Set currentId to messageId
		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		// Append messageId to childrenIds of parent message
		if (messages.length !== 0) {
			history.messages[messages.at(-1).id].childrenIds.push(userMessageId);
		}

		const chatInput = document.getElementById('chat-input');
		if ($mobile) {
			chatInput?.blur();
		} else {
			chatInput?.focus();
		}

		saveSessionSelectedModels();

		await sendMessage(history, userMessageId, { newChat: true });
	};

	const sendMessage = async (
		_history,
		parentId: string,
		{
			messages = null,
			modelId = null,
			modelIdx = null,
			newChat = false
		}: {
			messages?: any[] | null;
			modelId?: string | null;
			modelIdx?: number | null;
			newChat?: boolean;
		} = {}
	) => {
		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = getVisibleChatId();
		_history = structuredClone(_history);

		const syncHistorySnapshot = () => {
			history = structuredClone(_history);
		};
		syncHistorySnapshot();
		generating = true;
		// Note: do NOT clear _completedMessageIds here. The set's purpose is to
		// dedupe completion-handler invocations per message id; uuids never
		// collide, so clearing it just creates a window where a delayed
		// completion event for a previous message can re-trigger
		// chatCompletedHandler and clobber the in-flight request's state.

		const mirrorHistoryMessage = (messageId) => {
			const nextMessage = _history.messages[messageId];
			if (!nextMessage) {
				return;
			}
			history.messages[messageId] = structuredClone(nextMessage);
			history = { ...history };
		};

		const responseMessageIds: Record<PropertyKey, string> = {};
		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: selectedModels;

		// Create response messages for each selected model
		for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
			const model = $models.filter((m) => m.id === modelId).at(0);

			if (model) {
				let responseMessageId = uuidv4();
				let responseMessage = {
					parentId: parentId,
					id: responseMessageId,
					childrenIds: [],
					role: 'assistant',
					content: '',
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
					// Add null check before accessing childrenIds
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
			}
		}
		history = history;

		// Create new chat if newChat is true and first user message
		if (newChat && _history.messages[_history.currentId].parentId === null) {
			_chatId = await initChatHandler(_history);
		}

		await tick();

		// Skip the structuredClone of `history` — saveChatHandler only reads it
		// to serialize a request body, and the LLM request is fired in parallel
		// below, so the save no longer gates the upstream call.
		_history = history;
		void saveChatHandler(_chatId, _history).catch((err) => {
			console.error('saveChatHandler failed:', err);
		});

		try {
			if (!generating) {
				return;
			}

			await Promise.all(
				selectedModelIds.map(async (modelId, _modelIdx) => {
					console.log('modelId', modelId);
					const model = $models.filter((m) => m.id === modelId).at(0);

					if (model) {
						// If there are image files, check if model is vision capable
						const hasImages = createMessagesList(_history, parentId).some((message) =>
							message.files?.some((file) => file.type === 'image')
						);

						const hasNativeVision = model.info?.meta?.capabilities?.vision ?? true;
						const hasPreprocessor = !!model.info?.meta?.vision_preprocessor_model_id;

						if (hasImages && !hasNativeVision && !hasPreprocessor) {
							toast.error(
								$i18n.t('Model {{modelName}} is not vision capable', {
									modelName: model.name ?? model.id
								})
							);
						}

						let responseMessageId =
							responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`];

						if (hasImages && !hasNativeVision && hasPreprocessor) {
							const preprocessorId = model.info.meta.vision_preprocessor_model_id;
							const preprocessorModel = $models.find((m) => m.id === preprocessorId);
							if (!preprocessorModel) {
								toast.error(`Vision preprocessor model not found: ${preprocessorId}`);
							} else {
								const userMessage = _history.messages[parentId];
								const userImages = userMessage.files?.filter((f) => f.type === 'image') || [];

								if (userImages.length > 0) {
									let responseMessage = _history.messages[responseMessageId];
									responseMessage.statusHistory = responseMessage.statusHistory || [];
									responseMessage.statusHistory.push({
										done: false,
										action: '🖼️',
										description: 'Preprocessing images with vision model...'
									});
									_history.messages[responseMessageId] = responseMessage;
									history.messages[responseMessageId] = responseMessage;
									history = { ...history };

									const userContent = userMessage.content;

									const visionPrompt = (
										model.info.meta.vision_preprocessor_prompt ||
										'Perform OCR on this image and describe its contents in the context of the user query: {query}'
									).replace('{query}', userContent);
									const visionMessages = [
										{ role: 'system', content: visionPrompt },
										{
											role: 'user',
											content: [
												{ type: 'text', text: userContent },
												...userImages.map((f) => ({
													type: 'image_url',
													image_url: { url: f.url }
												}))
											]
										}
									];

									try {
										const visionRes = await generateOpenAIChatCompletion(
											localStorage.token,
											{
												model: preprocessorModel.id,
												messages: visionMessages,
												stream: false,
												params: { max_tokens: 2048 }
											},
											`${WEBUI_BASE_URL}/api`
										);

										const visionResponse = visionRes.choices[0].message.content;

										responseMessage = _history.messages[responseMessageId];
										responseMessage.statusHistory.push({
											done: true,
											action: '🖼️',
											description: 'Vision analysis complete',
											vision_prompt: visionPrompt,
											vision_response: visionResponse
										});
										_history.messages[responseMessageId] = responseMessage;
										history.messages[responseMessageId] = responseMessage;

										// Prepend FULL analysis to user content
										userMessage.content = `[Vision Analysis:\n${visionResponse}\n]\n\n${userMessage.content}`;
										userMessage.vision_processed = true;

										_history.messages[parentId] = userMessage;
										history.messages[parentId] = userMessage;
										history = { ...history };

										await saveChatHandler(_chatId, _history);
									} catch (visionError) {
										console.error('Vision preprocessing failed:', visionError);
										toast.error('Vision preprocessing failed. Sending without analysis.');

										responseMessage = _history.messages[responseMessageId];
										responseMessage.statusHistory.push({
											done: true,
											action: '🖼️❌',
											description: 'Vision preprocessing failed (text-only mode)'
										});
										_history.messages[responseMessageId] = responseMessage;
										history.messages[responseMessageId] = responseMessage;

										userMessage.vision_processed = false; // Don't strip if failed
										_history.messages[parentId] = userMessage;
										history.messages[parentId] = userMessage;
										history = { ...history };
									}
								}
							}
						}

						// PDF Preprocessing for non-vision models
						const hasPdfs = createMessagesList(_history, parentId).some((message) =>
							message.files?.some(
								(file) =>
									file.type === 'file' &&
									(file.name?.toLowerCase().endsWith('.pdf') ||
										file.file?.filename?.toLowerCase().endsWith('.pdf'))
							)
						);

						if (hasPdfs && !hasNativeVision && hasPreprocessor) {
							const preprocessorId = model.info.meta.vision_preprocessor_model_id;
							const preprocessorModel = $models.find((m) => m.id === preprocessorId);
							if (!preprocessorModel) {
								toast.error(`Vision preprocessor model not found: ${preprocessorId}`);
							} else {
								const userMessage = _history.messages[parentId];
								const userPdfs =
									userMessage.files?.filter(
										(f) =>
											f.type === 'file' &&
											(f.name?.toLowerCase().endsWith('.pdf') ||
												f.file?.filename?.toLowerCase().endsWith('.pdf'))
									) || [];

								if (userPdfs.length > 0) {
									let responseMessage = _history.messages[responseMessageId];
									responseMessage.statusHistory = responseMessage.statusHistory || [];
									responseMessage.statusHistory.push({
										done: false,
										action: '📄',
										description: 'Preprocessing PDF with vision model...'
									});
									_history.messages[responseMessageId] = responseMessage;
									history.messages[responseMessageId] = responseMessage;
									history = { ...history };

									try {
										// Convert all PDFs to images
										let allPdfImages = [];
										for (const pdfFile of userPdfs) {
											const pdfUrl =
												pdfFile.url || `${WEBUI_API_BASE_URL}/files/${pdfFile.id}/content`;
											try {
												const pdfImages = await renderPdfToImageDataUrls(pdfUrl);
												allPdfImages.push(
													...pdfImages.map((url, idx) => ({
														url,
														filename: `${pdfFile.name || pdfFile.file?.filename || 'document'}_page_${idx + 1}`
													}))
												);
											} catch (pdfError) {
												console.error(`Failed to render PDF ${pdfFile.name}:`, pdfError);
												throw new Error(`Failed to render PDF: ${pdfFile.name || 'unknown'}`);
											}
										}

										if (allPdfImages.length === 0) {
											throw new Error('No pages could be extracted from PDF(s)');
										}

										const userContent = userMessage.content;
										const visionPrompt = (
											model.info.meta.vision_preprocessor_prompt ||
											'Perform OCR on this image and describe its contents in the context of the user query: {query}'
										).replace('{query}', userContent);

										const visionMessages = [
											{ role: 'system', content: visionPrompt },
											{
												role: 'user',
												content: [
													{
														type: 'text',
														text: `I have uploaded ${allPdfImages.length} page(s) from PDF document(s). Please analyze them:\n\n${userContent}`
													},
													...allPdfImages.map((img) => ({
														type: 'image_url',
														image_url: { url: img.url }
													}))
												]
											}
										];

										const visionRes = await generateOpenAIChatCompletion(
											localStorage.token,
											{
												model: preprocessorModel.id,
												messages: visionMessages,
												stream: false,
												params: { max_tokens: 4096 }
											},
											`${WEBUI_BASE_URL}/api`
										);

										const visionResponse = visionRes.choices[0].message.content;

										responseMessage = _history.messages[responseMessageId];
										responseMessage.statusHistory.push({
											done: true,
											action: '📄',
											description: `PDF analysis complete (${allPdfImages.length} pages)`,
											vision_prompt: visionPrompt,
											vision_response: visionResponse
										});
										_history.messages[responseMessageId] = responseMessage;
										history.messages[responseMessageId] = responseMessage;

										// Prepend PDF analysis to user content
										userMessage.content = `[PDF Analysis (${allPdfImages.length} pages):\n${visionResponse}\n]\n\n${userMessage.content}`;
										userMessage.pdf_processed = true;

										_history.messages[parentId] = userMessage;
										history.messages[parentId] = userMessage;
										history = { ...history };

										await saveChatHandler(_chatId, _history);
									} catch (pdfError) {
										console.error('PDF preprocessing failed:', pdfError);

										// Block message and show error
										responseMessage = _history.messages[responseMessageId];
										responseMessage.statusHistory.push({
											done: true,
											action: '📄❌',
											description: `PDF preprocessing failed: ${pdfError.message}`
										});
										responseMessage.error = {
											content: `PDF preprocessing failed: ${pdfError.message}\n\nThe selected model does not support vision natively, and PDF preprocessing could not be completed.`
										};
										responseMessage.done = true;
										_history.messages[responseMessageId] = responseMessage;
										history.messages[responseMessageId] = responseMessage;
										history = { ...history };

										await saveChatHandler(_chatId, _history);
										return; // Stop processing this model
									}
								}
							}
						}

						const chatEventEmitter = await getChatEventEmitter(model.id, _chatId);
						startUsagePolling(FAST_POLL_MS);
						scrollToBottom();

						const MAX_RETRIES = 5;
						let retryCancelled = false;
						let savedToolContent = null;
						let savedReasoningDetails = null;
						let savedReasoningDetailsPerRound = null;

						for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
							let responseMessage = _history.messages[responseMessageId];

							if (attempt > 1) {
								// Re-enable generating for retry (socket error handler sets it false)
								generating = true;

								// Preserve tool context so retry continues from where it left off
								if (savedToolContent) {
									responseMessage.content = savedToolContent;
									responseMessage.preservedToolContext = true;
									if (savedReasoningDetails) {
										responseMessage.reasoning_details = savedReasoningDetails;
									}
									if (savedReasoningDetailsPerRound) {
										responseMessage.reasoning_details_per_round =
											savedReasoningDetailsPerRound;
									}
								} else {
									responseMessage.content = '';
								}

								responseMessage.error = null;
								responseMessage.done = false;
								responseMessage.retrying = null;
								_history.messages[responseMessageId] = responseMessage;
								mirrorHistoryMessage(responseMessageId);
							}

							suppressErrorToast = attempt < MAX_RETRIES;

							await sendMessageSocket(
								model,
								messages && messages.length > 0
									? messages
									: createMessagesList(_history, responseMessageId),
								_history,
								responseMessageId,
								_chatId
							);

							// Wait for response to actually complete (handles socket-based delivery
							// where sendMessageSocket returns before the response arrives)
							{
								const msg = history.messages[responseMessageId];
								if (!msg?.done && !msg?.error) {
									while (true) {
										await new Promise((r) => setTimeout(r, 100));
										const m = history.messages[responseMessageId];
										if (m?.done || m?.error) break;
									}
								}
							}

							suppressErrorToast = false;

							// Sync from reactive history back to _history (socket handler writes to history, not _history)
							const completedMsg = history.messages[responseMessageId];
							if (completedMsg) {
								_history.messages[responseMessageId] = structuredClone(completedMsg);
							}
							responseMessage = _history.messages[responseMessageId];

							if (!responseMessage.error) break;

							// Save tool context from failed attempt for next retry
							const failedToolContext = getRetryableToolContext(responseMessage.content);
							if (failedToolContext?.hasCompletedToolCall) {
								savedToolContent = failedToolContext.content;
								savedReasoningDetails = responseMessage.reasoning_details || null;
								savedReasoningDetailsPerRound =
									responseMessage.reasoning_details_per_round || null;
							}

							if (attempt < MAX_RETRIES && !skipRemainingRetriesSet.has(responseMessageId)) {
								const waitSeconds = attempt * 2;

								// Re-enable generating for countdown UI
								generating = true;

								responseMessage.error = null;
								responseMessage.done = false;
								responseMessage.content = '';
								responseMessage.retrying = {
									attempt,
									maxAttempts: MAX_RETRIES,
									countdown: waitSeconds
								};
								_history.messages[responseMessageId] = responseMessage;
								mirrorHistoryMessage(responseMessageId);

								await new Promise((resolve) => {
									let remaining = waitSeconds;
									const ticker = setInterval(() => {
										remaining--;
										if (!generating || remaining <= 0) {
											clearInterval(ticker);
											resolve();
											return;
										}
										responseMessage.retrying = {
											attempt,
											maxAttempts: MAX_RETRIES,
											countdown: remaining
										};
										_history.messages[responseMessageId] = responseMessage;
										mirrorHistoryMessage(responseMessageId);
									}, 1000);
								});

								if (!generating) {
									retryCancelled = true;
									break;
								}
								continue;
							}

							// All retries exhausted — restore tool context so manual retry can use it
							if (savedToolContent) {
								responseMessage.content = savedToolContent;
								responseMessage.preservedToolContext = true;
								if (savedReasoningDetails) {
									responseMessage.reasoning_details = savedReasoningDetails;
								}
								if (savedReasoningDetailsPerRound) {
									responseMessage.reasoning_details_per_round =
										savedReasoningDetailsPerRound;
								}
							}

							// Check for provider restrictions
							const hasProviderRestrictions = !!(
								model?.info?.params?.custom_params?.provider?.only?.length ||
								model?.info?.params?.custom_params?.provider?.order?.length
							);
							if (hasProviderRestrictions) {
								responseMessage.providerFailed = true;
							}
							_history.messages[responseMessageId] = responseMessage;
							mirrorHistoryMessage(responseMessageId);
							break;
						}

						skipRemainingRetriesSet.delete(responseMessageId);

						// Defensive cleanup: ensure the "Retrying in Xs..." UI never
						// outlives the retry loop, even if state got corrupted by a
						// stale socket event mid-countdown.
						{
							const finalMsg = _history.messages[responseMessageId];
							if (finalMsg?.retrying) {
								finalMsg.retrying = null;
								_history.messages[responseMessageId] = finalMsg;
								mirrorHistoryMessage(responseMessageId);
							}
						}

						if (chatEventEmitter) clearInterval(chatEventEmitter);
						startUsagePolling(SLOW_POLL_MS);
					} else {
						toast.error($i18n.t(`Model {{modelId}} not found`, { modelId }));
					}
				})
			);

			currentChatPage.set(1);
			chats.set(await getChatList(localStorage.token, $currentChatPage));
		} finally {
			chatStreamDebug('[chat-stream] sendMessage finally — clearing controller');
			generating = false;
			generationController = null;
		}
	};

	const getFeatures = () => {
		let features = {};

		if ($config?.features)
			features = {
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
				web_search:
					$config?.features?.enable_web_search &&
					($user?.role === 'admin' || $user?.permissions?.features?.web_search)
						? webSearchEnabled
						: false,
				study_mode: $config?.features?.enable_study_mode ? studyModeEnabled : false,
				data_viz: $config?.features?.enable_data_viz ? dataVizEnabled : false,
				subagents:
					$config?.features?.enable_subagents &&
					($user?.role === 'admin' || $user?.permissions?.features?.subagents)
						? subagentsEnabled
						: false
			};

		const currentModels = atSelectedModel?.id ? [atSelectedModel.id] : selectedModels;
		if (
			currentModels.filter(
				(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
			).length === currentModels.length
		) {
			if ($config?.features?.enable_web_search && ($settings?.webSearch ?? false) === 'always') {
				features = { ...features, web_search: true };
			}
		}

		if ($settings?.memory ?? false) {
			features = { ...features, memory: true };
		}

		return features;
	};

	const sendMessageSocket = async (model, _messages, _history, responseMessageId, _chatId, opts = {}) => {
		const responseMessage = _history.messages[responseMessageId];
		const userMessage = _history.messages[responseMessage.parentId];

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
			...(userMessage?.files ?? []).filter((item) =>
				['doc', 'text', 'file', 'note', 'chat', 'collection'].includes(item.type)
			)
		);
		// Remove duplicates
		files = files.filter(
			(item, index, array) =>
				array.findIndex((i) => JSON.stringify(i) === JSON.stringify(item)) === index
		);

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
			$settings?.params?.stream_response ??
			params?.stream_response ??
			true;

		let messages = [
			params?.system || $settings.system
				? {
						role: 'system',
						content: `${params?.system ?? $settings?.system ?? ''}`
					}
				: undefined,
			...expandMessagesForToolResumption(_messages).map((message) => ({
				...message,
				content:
					typeof message.content === 'string' ? processDetails(message.content) : message.content
			}))
		].filter((message) => message);

		const TEXT_FILE_EXTS = new Set([
			'txt', 'md', 'markdown', 'rst', 'csv', 'tsv', 'json', 'jsonl', 'ndjson',
			'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf', 'env', 'log', 'xml', 'svg',
			'py', 'pyi', 'ipynb', 'js', 'mjs', 'cjs', 'ts', 'tsx', 'jsx', 'vue',
			'svelte', 'java', 'kt', 'kts', 'scala', 'groovy', 'c', 'cc', 'cpp',
			'cxx', 'h', 'hpp', 'hxx', 'rs', 'go', 'rb', 'php', 'pl', 'pm', 'lua',
			'r', 'jl', 'dart', 'swift', 'm', 'mm', 'cs', 'fs', 'fsx', 'ex', 'exs',
			'erl', 'hs', 'ml', 'mli', 'clj', 'cljs', 'sh', 'bash', 'zsh', 'fish',
			'ps1', 'bat', 'cmd', 'sql', 'graphql', 'gql', 'proto', 'css', 'scss',
			'sass', 'less', 'tex', 'bib', 'srt', 'vtt', 'patch', 'diff',
			'gitignore', 'dockerignore', 'editorconfig'
		]);

		const isTextFile = (file) => {
			if (file?.type !== 'file') return false;
			const name = (file.name || file.file?.filename || '').toLowerCase();
			if (name.endsWith('.pdf')) return false;
			const dot = name.lastIndexOf('.');
			const ext = dot >= 0 ? name.slice(dot + 1) : name;
			if (ext && TEXT_FILE_EXTS.has(ext)) return true;
			const ct = (
				file.content_type ||
				file.file?.meta?.content_type ||
				''
			).toLowerCase();
			if (ct.startsWith('text/') && !ct.includes('html')) return true;
			return false;
		};

		// Files that don't read as plain text but the backend can extract from:
		// office formats, html, epub, etc. These travel as `type: "file"` content
		// parts with a `processing_mode` and get materialised on the server
		// (openai.py file-part loop: text mode → <document> text part;
		// pdf mode → LibreOffice → existing PDF + file-parser plugin path).
		const EXTRACTABLE_EXTS = new Set([
			'docx', 'doc', 'odt', 'rtf',
			'pptx', 'ppt',
			'xlsx', 'xls',
			'html', 'htm',
			'epub'
		]);

		const isExtractableFile = (file) => {
			if (file?.type !== 'file') return false;
			const name = (file.name || file.file?.filename || '').toLowerCase();
			if (name.endsWith('.pdf')) return false;
			const dot = name.lastIndexOf('.');
			const ext = dot >= 0 ? name.slice(dot + 1) : '';
			return EXTRACTABLE_EXTS.has(ext);
		};

		const fetchTextFileContent = async (file) => {
			if (typeof file._inlinedText === 'string') return file._inlinedText;
			try {
				const blob = await getFileContentById(file.id);
				const text = blob ? await blob.text() : '';
				file._inlinedText = text;
				return text;
			} catch (e) {
				console.error('Failed to read text file content:', e);
				file._inlinedText = '';
				return '';
			}
		};

		const escapeXmlAttr = (s) =>
			String(s)
				.replace(/&/g, '&amp;')
				.replace(/</g, '&lt;')
				.replace(/>/g, '&gt;')
				.replace(/"/g, '&quot;');

		const buildTextFileBlocks = async (files) => {
			const textFiles = (files ?? []).filter(isTextFile);
			if (!textFiles.length) return '';
			const blocks = await Promise.all(
				textFiles.map(async (f) => {
					const name = f.name || f.file?.filename || 'file';
					const text = await fetchTextFileContent(f);
					return `<document filename="${escapeXmlAttr(name)}">\n${text}\n</document>`;
				})
			);
			return blocks.join('\n\n') + '\n\n';
		};

		messages = (
			await Promise.all(
				messages.map(async (message) => {
					// Structured content_blocks travel through to the backend untouched —
					// `blocks_to_api_messages` on the server is the single source of truth
					// for the internal-message → API-message conversion.
					if (
						message?.role === 'assistant' &&
						Array.isArray(message?.content_blocks) &&
						message.content_blocks.length > 0
					) {
						return {
							role: 'assistant',
							content_blocks: message.content_blocks,
							...(message.reasoning_details_per_round
								? { reasoning_details_per_round: message.reasoning_details_per_round }
								: {}),
							...(message.reasoning_details
								? { reasoning_details: message.reasoning_details }
								: {})
						};
					}

					if (message.role === 'tool') {
						return {
							role: 'tool',
							content: message.content ?? '',
							...(message.tool_call_id ? { tool_call_id: message.tool_call_id } : {})
						};
					}

					if (message.tool_calls) {
						if (Array.isArray(message.reasoning_details)) {
							const signatureDetail = message.reasoning_details.find(
								(d) => d.type === 'reasoning.encrypted' && d.data
							);

							if (signatureDetail) {
								message.tool_calls = message.tool_calls.map((tc) => ({
									...tc,
									extra_content: { google: { thought_signature: signatureDetail.data } }
								}));
							}
						}

						return {
							role: 'assistant',
							content: (message?.merged?.content ?? message.content) || null,
							tool_calls: message.tool_calls,
							// OpenAI Responses API (and Anthropic) require the reasoning that
							// led to a function_call to be preserved on the assistant message
							// in follow-up requests. Dropping it breaks the reasoning chain on
							// multi-turn tool-call conversations.
							...(message.reasoning_details
								? { reasoning_details: message.reasoning_details }
								: {})
						};
					}

					const hasImages = message.files?.some((file) => file.type === 'image');
					const isUser = message.role === 'user';
					const modelSupportsVision = model?.info?.meta?.capabilities?.vision ?? true;

					// Check if message has PDF files
					const hasPdfFiles = message.files?.some(
						(file) =>
							file.type === 'file' &&
							(file.name?.toLowerCase().endsWith('.pdf') ||
								file.file?.filename?.toLowerCase().endsWith('.pdf'))
					);

					// docx/xlsx/pptx/etc. — always sent as file parts so the backend
					// can text-extract (or PDF-convert per processing_mode). Unlike
					// images/PDFs these don't gate on vision capability — extracted
					// text works on every model.
					const hasExtractableFiles = message.files?.some(isExtractableFile);

					const textPrefix = isUser ? await buildTextFileBlocks(message.files) : '';
					const baseText = message?.merged?.content ?? message.content ?? '';

					if (
						isUser &&
						(((hasImages || hasPdfFiles) && modelSupportsVision) || hasExtractableFiles)
					) {
						return {
							role: message.role,
							content: [
								{
									type: 'text',
									text: textPrefix + baseText
								},
								// Add image content parts (vision-capable models only).
								...(modelSupportsVision
									? message.files
											.filter((file) => file.type === 'image')
											.map((file) => ({
												type: 'image_url',
												image_url: {
													url: file.url
												}
											}))
									: []),
								// PDF file parts for OpenRouter's file-parser plugin
								// (vision-capable models only; existing behavior).
								...(modelSupportsVision
									? message.files
											.filter(
												(file) =>
													file.type === 'file' &&
													(file.name?.toLowerCase().endsWith('.pdf') ||
														file.file?.filename?.toLowerCase().endsWith('.pdf'))
											)
											.map((file) => ({
												type: 'file',
												file: {
													filename: file.name || file.file?.filename || 'document.pdf',
													file_data:
														file.url || `${WEBUI_API_BASE_URL}/files/${file.id}/content`
												}
											}))
									: []),
								// docx/xlsx/pptx/etc. — backend extracts on receipt and
								// replaces this part with either a <document> text part
								// (mode == 'text') or a PDF binary part routed through
								// the file-parser plugin (mode == 'pdf').
								...message.files.filter(isExtractableFile).map((file) => ({
									type: 'file',
									file: {
										filename: file.name || file.file?.filename || 'document',
										file_data: file.url || `${WEBUI_API_BASE_URL}/files/${file.id}/content`,
										processing_mode: (file.processing_mode === 'pdf' ? 'pdf' : 'text')
									}
								}))
							]
						};
					}

					return {
						role: message.role,
						content: isUser ? textPrefix + baseText : baseText,
						...(message.reasoning_details ? { reasoning_details: message.reasoning_details } : {})
					};
				})
			)
		).filter(
			(message) =>
				message?.role === 'user' ||
				message?.role === 'tool' ||
				hasMessageContent(message?.content) ||
				message?.reasoning_details ||
				message?.tool_calls?.length ||
				(Array.isArray(message?.content_blocks) && message.content_blocks.length > 0)
		);

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

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				stream: stream,
				model: model.id,
				messages: messages,
				params: {
					...$settings?.params,
					...params,
					stop:
						(params?.stop ?? $settings?.params?.stop ?? undefined)
							? (params?.stop.split(',').map((token) => token.trim()) ?? $settings.params.stop).map(
									(str) => decodeURIComponent(JSON.parse('"' + str.replace(/\"/g, '\\"') + '"'))
								)
							: undefined
				},

				files: (files?.length ?? 0) > 0 ? files : undefined,

				filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
				tool_ids: toolIds.length > 0 ? toolIds : undefined,
				tool_servers: ($toolServers ?? []).filter(
					(server, idx) => toolServerIds.includes(idx) || toolServerIds.includes(server?.id)
				),
				features: getFeatures(),
				variables: {
					...getPromptVariables($user?.name, $settings?.userLocation ? userLocation : undefined)
				},
				model_item: $models.find((m) => m.id === model.id),

				session_id: $socket?.id,
				chat_id: _chatId,
				id: responseMessageId,

				// Lets the backend stamp `Current Date: YYYY-MM-DD (TZ)` in the
				// system prompt using the user's local time, not the server's UTC.
				timezone: Intl?.DateTimeFormat?.()?.resolvedOptions?.()?.timeZone,

				background_tasks: {
					...(!$temporaryChatEnabled &&
					(messages.length == 1 ||
						(messages.length == 2 &&
							messages.at(0)?.role === 'system' &&
							messages.at(1)?.role === 'user')) &&
					(selectedModels[0] === model.id || atSelectedModel !== undefined)
						? {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						: {}),
					follow_up_generation: $settings?.autoFollowUps ?? true
				},

				...(stream && (model.info?.meta?.capabilities?.usage ?? false)
					? {
							stream_options: {
								include_usage: true
							}
						}
					: {}),

				// Include reasoning effort parameter
				reasoning: reasoning,

				// Include service tier for OpenRouter / OpenAI-compatible APIs.
				// Skip the field entirely when the selected model has service_tier
				// disabled in its meta — some providers (e.g. Gemini via OpenRouter)
				// don't support it and including a stale value from localStorage
				// can confuse them.
				...(((model?.info?.meta as any)?.service_tier?.enabled === false)
					? {}
					: { service_tier: serviceTier }),

				...(opts.stripProvider ? { strip_provider: true } : {})
			},
			`${WEBUI_BASE_URL}/api`
		).catch(async (error) => {
			console.log(error);
			chatStreamDebug('[chat-stream] chatCompletion .catch fired', {
				responseMessageId,
				name: error?.name,
				message: error?.message,
				stack: error?.stack
			});

			let errorMessage = error;
			if (error?.error?.message) {
				errorMessage = error.error.message;
			} else if (error?.message) {
				errorMessage = error.message;
			}

			if (typeof errorMessage === 'object') {
				errorMessage = $i18n.t(`Uh-oh! There was an issue with the response.`);
			}

			if (!suppressErrorToast) toast.error(`${errorMessage}`);
			responseMessage.error = {
				content: error
			};

			responseMessage.done = true;

			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			return null;
		});

		generationController = controller ? { id: responseMessageId, controller } : null;
		chatStreamDebug('[chat-stream] generationController assigned', {
			responseMessageId,
			hasController: !!controller
		});
		// Reset the user-stop flag for this new request lifecycle.
		userInitiatedStop = false;

		if (res) {
			if (stream) {
				if (!res.ok) {
					let errorPayload = null;
					try {
						errorPayload = await res.json();
					} catch {
						errorPayload = { message: `HTTP ${res.status}` };
					}
					chatStreamDebug('[chat-stream] HTTP non-OK', {
						responseMessageId,
						status: res.status,
						errorPayload
					});
					await handleOpenAIError(errorPayload, responseMessage, `http-${res.status}`);
				} else if (res.body) {
					responseMessage.done = false;
					history.messages[responseMessageId] = responseMessage;
					history = { ...history };

					const contentType = res.headers.get('content-type') ?? '';
					const isEventStream = contentType.includes('text/event-stream');
					const shouldUseDirectStream = isEventStream || !($socket?.connected && $socket?.id);

					if (shouldUseDirectStream) {
						const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
						try {
							for await (const update of textStream) {
								const { value, done, sources, error, usage, selectedModelId, aborted } = update;

								// Handle aborts FIRST (before any early-exit check) so a
								// user-driven stopResponse() flow — which nulls
								// generationController — still finalizes the message
								// instead of silently breaking out.
								if (aborted) {
									chatStreamDebug('[chat-stream] direct stream aborted', {
										responseMessageId,
										contentLen: responseMessage.content?.length ?? 0,
										userInitiatedStop
									});
									responseMessage.done = true;
									history.messages[responseMessageId] = responseMessage;
									history = { ...history };
									break;
								}

								// Bail if THIS stream's controller has been swapped out for a
								// different message's controller (concurrent request).
								if (
									generationController != null &&
									generationController.id !== responseMessageId
								) {
									chatStreamDebug('[chat-stream] for-await bailing — controller owner changed', {
										responseMessageId,
										currentOwner: generationController?.id
									});
									break;
								}

								if (error) {
									chatStreamDebug('[chat-stream] direct stream error', { responseMessageId, error });
									await handleOpenAIError(error, responseMessage, 'direct-stream-error');
									break;
								}

								if (sources && !responseMessage?.sources) {
									responseMessage.sources = sources;
								}

								if (selectedModelId) {
									responseMessage.selectedModelId = selectedModelId;
									responseMessage.arena = true;
								}

								if (usage) {
									responseMessage.usage = usage;
								}

								if (done) {
									responseMessage.done = true;
									history.messages[responseMessageId] = responseMessage;
									history = { ...history };

									// We must save the chat here for direct streams, as there is no backend socket event to do it for us
									if (!$temporaryChatEnabled && isVisibleChatEvent(_chatId)) {
										await chatCompletedHandler(
											_chatId,
											model.id,
											responseMessageId,
											createMessagesList(history, responseMessageId)
										);
									}
									break;
								}

								if (!(responseMessage.content == '' && value == '\n')) {
									responseMessage.content += value;
									history.messages[responseMessageId] = responseMessage;
									history = { ...history };

									if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
										navigator.vibrate(5);
									}
								}

								await tick();

								if (autoScroll) {
									scrollToBottom();
								}
							}
						} catch (e: any) {
							// Defense in depth: openAIStreamToIterator already converts thrown
							// errors into in-band updates, so this should rarely fire. If it
							// does, route through the same error path so the message finalizes.
							chatStreamDebug('[chat-stream] for-await threw', {
								responseMessageId,
								name: e?.name,
								message: e?.message
							});
							if (e?.name === 'AbortError') {
								responseMessage.done = true;
								history.messages[responseMessageId] = responseMessage;
								history = { ...history };
							} else {
								await handleOpenAIError(
									{ message: e?.message ?? String(e) },
									responseMessage,
									'for-await-throw'
								);
							}
						}
					} else {
						let payload = null;
						try {
							payload = await res.json();
						} catch (error) {
							console.error('Error parsing async chat task response', error);
						}

						if (payload?.error) {
							chatStreamDebug('[chat-stream] async-task payload.error', {
								responseMessageId,
								error: payload.error
							});
							await handleOpenAIError(payload.error, responseMessage, 'async-task-payload-error');
						} else if (payload?.task_id) {
							const currentMessage = history.messages[responseMessageId];
							if (currentMessage && !currentMessage.done) {
								if (taskIds) {
									taskIds = [...taskIds, payload.task_id];
								} else {
									taskIds = [payload.task_id];
								}
							}
						}
					}
				} else {
					await handleOpenAIError(
						{ message: 'Streaming response body is missing.' },
						responseMessage,
						'res-body-missing'
					);
				}
			} else {
				const data = await res.json();
				if (data.error) {
					chatStreamDebug('[chat-stream] non-streaming data.error', {
						responseMessageId,
						error: data.error
					});
					await handleOpenAIError(data.error, responseMessage, 'non-streaming-data-error');
				} else {
					const currentMessage = history.messages[responseMessageId];
					if (currentMessage && !currentMessage.done) {
						if (taskIds) {
							taskIds = [...taskIds, data.task_id];
						} else {
							taskIds = [data.task_id];
						}
					}
				}
			}
		}

		await tick();
		scrollToBottom();
	};

	const handleOpenAIError = async (error, responseMessage, source: string = 'unknown') => {
		let errorMessage = '';
		let innerError;

		if (error) {
			innerError = error;
		}

		console.error(innerError);
		chatStreamDebug('[chat-stream] handleOpenAIError', {
			source,
			responseMessageId: responseMessage?.id,
			errorShape: innerError && typeof innerError === 'object' ? Object.keys(innerError) : typeof innerError,
			error: innerError
		});

		if ('detail' in innerError) {
			// FastAPI error
			if (!suppressErrorToast) toast.error(innerError.detail);
			errorMessage = innerError.detail;
		} else if ('error' in innerError) {
			// OpenAI error
			if ('message' in innerError.error) {
				if (!suppressErrorToast) toast.error(innerError.error.message);
				errorMessage = innerError.error.message;
			} else {
				if (!suppressErrorToast) toast.error(innerError.error);
				errorMessage = innerError.error;
			}
		} else if ('message' in innerError) {
			// OpenAI error
			if (!suppressErrorToast) toast.error(innerError.message);
			errorMessage = innerError.message;
		}

		// OpenRouter docs: errors arrive as either the WRAPPED pre-stream shape
		// `{error: {code, message, metadata: {error_type, provider_name, raw}}}`
		// or the UNWRAPPED mid-stream shape where those fields sit at the top of
		// the chunk alongside `choices`. Read both.
		// Ref: https://openrouter.ai/docs/api/reference/errors
		const orError =
			innerError && typeof innerError === 'object' && 'error' in innerError && innerError.error
				? innerError.error
				: innerError;
		const code = orError?.code ?? innerError?.code;
		const meta = orError?.metadata ?? innerError?.metadata ?? {};
		const errorType = meta?.error_type;
		const providerName = meta?.provider_name;
		const rawText = meta?.raw;

		// Friendly labels for the documented OpenRouter HTTP codes so users can
		// tell at a glance whether to retry, switch model, or top up credits.
		// 408/502/503 are documented; 504 + the timeout error_type also occur in
		// practice (OpenRouter's own gateway timeout — not in the public table).
		const codeLabel = (() => {
			switch (Number(code)) {
				case 400:
					return 'Bad request';
				case 401:
					return 'Auth failed';
				case 402:
					return 'Out of credits';
				case 403:
					return 'Moderation block';
				case 408:
					return 'Request timeout';
				case 429:
					return 'Rate limited';
				case 502:
					return 'Provider down / bad response';
				case 503:
					return 'No available provider';
				case 504:
					return 'Gateway timeout';
				default:
					return null;
			}
		})();

		let displayMessage =
			typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage);

		if (code || errorType || providerName) {
			const parts: string[] = [];
			if (code) parts.push(codeLabel ? `${codeLabel} (${code})` : `HTTP ${code}`);
			if (errorType && errorType !== codeLabel?.toLowerCase()) parts.push(String(errorType));
			if (providerName) parts.push(`via ${providerName}`);
			displayMessage = `${parts.join(' · ')}: ${displayMessage || '(no message)'}`;
		}
		// Append the raw upstream error if present and short — useful for
		// timeouts where `raw` often holds the actual provider response.
		if (typeof rawText === 'string' && rawText.length > 0 && rawText.length < 800) {
			displayMessage += `\n\n${rawText}`;
		} else if (rawText && typeof rawText === 'object') {
			try {
				const j = JSON.stringify(rawText);
				if (j.length < 800) displayMessage += `\n\n${j}`;
			} catch {
				// non-serializable, ignore
			}
		}

		const fallback = $i18n.t(`Uh-oh! There was an issue with the response.`);

		responseMessage.error = {
			content: displayMessage || fallback
		};
		responseMessage.done = true;

		history.messages[responseMessage.id] = responseMessage;
	};

	const stopResponse = async () => {
		if (taskIds) {
			for (const taskId of taskIds) {
				const res = await stopTask(localStorage.token, taskId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}

			taskIds = null;
		}

		const responseMessage = history.messages[history.currentId];
		if (responseMessage) {
			// Mark current response(s) as done immediately so the UI can finish.
			if (responseMessage.parentId !== null && history.messages[responseMessage.parentId]) {
				for (const messageId of history.messages[responseMessage.parentId].childrenIds) {
					if (history.messages[messageId]) {
						history.messages[messageId].done = true;
						history.messages[messageId] = { ...history.messages[messageId] };
					}
				}
			} else {
				responseMessage.done = true;
				history.messages[history.currentId] = { ...responseMessage };
			}
			history = { ...history };
		}

		chatStreamDebug('[chat-stream] stopResponse — user clicked stop, aborting controller');
		userInitiatedStop = true;
		generating = false;
		generationController?.controller.abort();
		generationController = null;

		if (autoScroll) {
			scrollToBottom();
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

	const retryWithoutProviderRestrictions = async (message) => {
		if (!history.currentId) return;

		const userMessage = history.messages[message.parentId];
		if (!userMessage) return;

		const model = $models.find((m) => m.id === (message.selectedModelId ?? message.model));
		if (!model) return;

		// Preserve tool context from the failed message so retry continues from where it left off
		const originalToolContext = getRetryableToolContext(message?.content ?? '');
		let savedToolContent = null;
		let savedReasoningDetails = null;
		let savedReasoningDetailsPerRound = null;
		if (originalToolContext?.hasCompletedToolCall) {
			savedToolContent = originalToolContext.content;
			savedReasoningDetails = message.reasoning_details || null;
			savedReasoningDetailsPerRound = message.reasoning_details_per_round || null;
			message.content = savedToolContent;
			message.preservedToolContext = true;
		} else {
			message.content = '';
		}

		message.error = null;
		message.providerFailed = false;
		message.done = false;
		history.messages[message.id] = message;
		history = { ...history };

		generating = true;

		try {
			const MAX_RETRIES = 5;
			const _history = structuredClone(history);

			for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
				let responseMessage = _history.messages[message.id];

				if (attempt > 1) {
					// Preserve tool context so retry continues from where it left off
					if (savedToolContent) {
						responseMessage.content = savedToolContent;
						responseMessage.preservedToolContext = true;
						if (savedReasoningDetails) {
							responseMessage.reasoning_details = savedReasoningDetails;
						}
						if (savedReasoningDetailsPerRound) {
							responseMessage.reasoning_details_per_round =
								savedReasoningDetailsPerRound;
						}
					} else {
						responseMessage.content = '';
					}
					responseMessage.error = null;
					responseMessage.done = false;
					responseMessage.retrying = null;
					_history.messages[message.id] = responseMessage;
					history.messages[message.id] = structuredClone(responseMessage);
					history = { ...history };
				}

				suppressErrorToast = attempt < MAX_RETRIES;

				await sendMessageSocket(
					model,
					createMessagesList(_history, message.id),
					_history,
					message.id,
					getVisibleChatId(),
					{ stripProvider: true }
				);

				// Wait for response to actually complete (socket-based delivery)
				{
					const msg = history.messages[message.id];
					if (!msg?.done && !msg?.error) {
						while (true) {
							await new Promise((r) => setTimeout(r, 100));
							const m = history.messages[message.id];
							if (m?.done || m?.error) break;
						}
					}
				}

				suppressErrorToast = false;

				// Sync from reactive history back to _history
				const completedMsg = history.messages[message.id];
				if (completedMsg) {
					_history.messages[message.id] = structuredClone(completedMsg);
				}
				responseMessage = _history.messages[message.id];

				if (!responseMessage.error) break;

				// Save tool context from failed attempt for next retry
				const failedToolContext = getRetryableToolContext(responseMessage.content);
				if (failedToolContext?.hasCompletedToolCall) {
					savedToolContent = failedToolContext.content;
					savedReasoningDetails = responseMessage.reasoning_details || null;
					savedReasoningDetailsPerRound =
						responseMessage.reasoning_details_per_round || null;
				}

				if (attempt < MAX_RETRIES && !skipRemainingRetriesSet.has(message.id)) {
					generating = true;
					const waitSeconds = attempt * 2;
					responseMessage.error = null;
					responseMessage.done = false;
					responseMessage.content = '';
					responseMessage.retrying = {
						attempt,
						maxAttempts: MAX_RETRIES,
						countdown: waitSeconds
					};
					_history.messages[message.id] = responseMessage;
					history.messages[message.id] = structuredClone(responseMessage);
					history = { ...history };

					await new Promise((resolve) => {
						let remaining = waitSeconds;
						const ticker = setInterval(() => {
							remaining--;
							if (!generating || remaining <= 0) {
								clearInterval(ticker);
								resolve();
								return;
							}
							responseMessage.retrying = {
								attempt,
								maxAttempts: MAX_RETRIES,
								countdown: remaining
							};
							_history.messages[message.id] = responseMessage;
							history.messages[message.id] = structuredClone(responseMessage);
							history = { ...history };
						}, 1000);
					});

					if (!generating) break;
					continue;
				}
				break;
			}
			skipRemainingRetriesSet.delete(message.id);

			// Defensive cleanup mirrors the primary retry loop: never leave
			// `retrying` set on the message after the loop exits.
			{
				const finalMsg = _history.messages[message.id];
				if (finalMsg?.retrying) {
					finalMsg.retrying = null;
					_history.messages[message.id] = finalMsg;
					history.messages[message.id] = structuredClone(finalMsg);
					history = { ...history };
				}
			}
		} finally {
			chatStreamDebug('[chat-stream] retryWithoutProviderRestrictions finally — clearing controller', {
				messageId: message?.id
			});
			generating = false;
			clearGenerationControllerIfOwned(message?.id);
		}
	};

	const regenerateResponse = async (message, suggestionPrompt = null) => {
		console.log('regenerateResponse');

		if (history.currentId) {
			let userMessage = history.messages[message.parentId];

			if (autoScroll) {
				scrollToBottom();
			}

			await sendMessage(history, userMessage.id, {
				...(suggestionPrompt
					? {
							messages: [
								...createMessagesList(history, message.id),
								{
									role: 'user',
									content: suggestionPrompt
								}
							]
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

	const getRetryableToolContext = (content = '') => {
		content = getStringMessageContent(content);

		const toolCallsRegex = /<details\s+type="tool_calls"[^>]*>[\s\S]*?<\/details>/gi;
		const toolCallMatches = [...content.matchAll(toolCallsRegex)];

		if (toolCallMatches.length === 0) {
			return null;
		}

		const completedToolCallMatch =
			[...toolCallMatches].reverse().find((match) => /\bdone="true"/i.test(match[0])) ?? null;

		if (completedToolCallMatch) {
			const endIndex = (completedToolCallMatch.index ?? 0) + completedToolCallMatch[0].length;

			return {
				content: content.substring(0, endIndex).trim(),
				endIndex,
				hasCompletedToolCall: true
			};
		}

		const firstToolCallMatch = toolCallMatches[0];
		const endIndex = firstToolCallMatch.index ?? 0;
		const preservedContent = content.substring(0, endIndex).trim();

		if (!preservedContent) {
			return null;
		}

		return {
			content: preservedContent,
			endIndex,
			hasCompletedToolCall: false
		};
	};

	const shouldContinueFromLastToolRequest = (message) => {
		const content = getStringMessageContent(message?.content);
		const toolContext = getRetryableToolContext(content);
		if (!toolContext?.hasCompletedToolCall) {
			return false;
		}

		const trailingContent = removeAllDetails(content.slice(toolContext.endIndex)).trim();

		return trailingContent.length === 0;
	};

	const normalizeToolCallArguments = (value = '') => {
		const decodedValue = decode(value);

		try {
			const parsedValue = JSON.parse(decodedValue);
			return typeof parsedValue === 'string' ? parsedValue : JSON.stringify(parsedValue);
		} catch (error) {
			return decodedValue;
		}
	};

	const normalizeToolResultContent = (value = '') => {
		const decodedValue = decode(value);

		try {
			const parsedValue = JSON.parse(decodedValue);
			return typeof parsedValue === 'string' ? parsedValue : JSON.stringify(parsedValue);
		} catch (error) {
			return decodedValue;
		}
	};

	const getStringMessageContent = (value) => {
		if (typeof value === 'string') {
			return value;
		}

		if (Array.isArray(value)) {
			return value
				.map((part) => {
					if (typeof part === 'string') {
						return part;
					}

					if (part?.type === 'text' && typeof part.text === 'string') {
						return part.text;
					}

					return '';
				})
				.join('\n');
		}

		return '';
	};

	const hasMessageContent = (value) => {
		if (typeof value === 'string') {
			return value.trim().length > 0;
		}

		if (Array.isArray(value)) {
			return value.length > 0;
		}

		return value != null;
	};

	const normalizePreservedAssistantContent = (value = '') => {
		const normalizedValue = getStringMessageContent(value);
		return removeDetails(normalizedValue, ['reasoning', 'code_interpreter']).trim();
	};

	const expandPreservedToolContextMessage = (message) => {
		if (!message?.preservedToolContext) {
			return [message];
		}

		const content = getStringMessageContent(message.content);
		const toolCallsRegex = /<details\s+type="tool_calls"([^>]*)>[\s\S]*?<\/details>/gi;
		const matches = [...content.matchAll(toolCallsRegex)];

		if (matches.length === 0) {
			return [message];
		}

		// Parse all completed tool calls with their positions
		const parsedToolCalls = [];
		for (const match of matches) {
			const matchStart = match.index ?? 0;
			const matchEnd = matchStart + match[0].length;

			const attributes = {};
			const attributeRegex = /(\w+)="([^"]*)"/g;
			let attributeMatch;
			while ((attributeMatch = attributeRegex.exec(match[1] ?? '')) !== null) {
				attributes[attributeMatch[1]] = attributeMatch[2];
			}

			if (attributes.done === 'true' && attributes.id && attributes.name) {
				parsedToolCalls.push({
					matchStart,
					matchEnd,
					id: attributes.id,
					name: attributes.name,
					arguments: attributes.arguments ?? '',
					result: attributes.result ?? ''
				});
			}
		}

		if (parsedToolCalls.length === 0) {
			return [message];
		}

		// Group consecutive tool calls (no meaningful text between them = parallel calls from same turn)
		const groups = [{ toolCalls: [parsedToolCalls[0]], textBeforeStart: 0 }];

		for (let i = 1; i < parsedToolCalls.length; i++) {
			const prevEnd = parsedToolCalls[i - 1].matchEnd;
			const currStart = parsedToolCalls[i].matchStart;
			const textBetween = normalizePreservedAssistantContent(content.slice(prevEnd, currStart));

			if (textBetween) {
				// Meaningful text between — new group (separate model turn)
				groups.push({ toolCalls: [parsedToolCalls[i]], textBeforeStart: prevEnd });
			} else {
				// No text between — same group (parallel calls from one turn)
				groups[groups.length - 1].toolCalls.push(parsedToolCalls[i]);
			}
		}

		// Compute trailing text (content after the last tool call)
		const lastParsedTc = parsedToolCalls[parsedToolCalls.length - 1];
		const trailingText = normalizePreservedAssistantContent(content.slice(lastParsedTc.matchEnd));
		const hasTrailingText = !!trailingText;

		// Where do reasoning_details belong?
		//
		// Newer messages have `reasoning_details_per_round` — one entry per stream
		// round (tool-call round or the trailing text round). When present, attach
		// per-round entries to the matching tool_calls group (and any final entry
		// to the trailing text). This preserves multi-round reasoning continuity
		// for OpenAI's Responses API.
		//
		// Older messages only have a flat `message.reasoning_details` (the last
		// round's reasoning, since earlier rounds were overwritten by index). Fall
		// back to the legacy heuristic for those:
		// - No trailing text (retry): attach to last group.
		// - Has trailing text: attach only to the trailing text message.

		const reasoningPerRound = Array.isArray(message.reasoning_details_per_round)
			? message.reasoning_details_per_round
			: null;

		const expandedMessages = [];

		for (let groupIdx = 0; groupIdx < groups.length; groupIdx++) {
			const group = groups[groupIdx];
			const isLastGroup = groupIdx === groups.length - 1;
			const firstTc = group.toolCalls[0];
			const textBefore = normalizePreservedAssistantContent(
				content.slice(group.textBeforeStart, firstTc.matchStart)
			);

			let groupReasoningDetails;
			if (reasoningPerRound && reasoningPerRound[groupIdx] !== undefined) {
				groupReasoningDetails = reasoningPerRound[groupIdx];
			} else if (isLastGroup && !hasTrailingText) {
				// Legacy: attach the (single) reasoning_details to the last group
				// when there's no trailing text.
				groupReasoningDetails = message.reasoning_details;
			} else {
				groupReasoningDetails = undefined;
			}

			expandedMessages.push({
				...message,
				role: 'assistant',
				content: textBefore,
				tool_calls: group.toolCalls.map((tc) => ({
					id: tc.id,
					type: 'function',
					function: {
						name: tc.name,
						arguments: normalizeToolCallArguments(tc.arguments)
					}
				})),
				preservedToolContext: undefined,
				reasoning_details: groupReasoningDetails
			});

			// Individual tool result messages
			for (const tc of group.toolCalls) {
				expandedMessages.push({
					role: 'tool',
					tool_call_id: tc.id,
					content: normalizeToolResultContent(tc.result)
				});
			}
		}

		// Trailing text = model's final response after all tool calls completed.
		// Per-round: anything beyond `groups.length` is the final round's reasoning.
		// Legacy: keep `message.reasoning_details` (the spread already includes it).
		if (hasTrailingText) {
			let trailingReasoning;
			if (reasoningPerRound && reasoningPerRound.length > groups.length) {
				trailingReasoning = reasoningPerRound[reasoningPerRound.length - 1];
			} else if (!reasoningPerRound) {
				trailingReasoning = message.reasoning_details;
			} else {
				trailingReasoning = undefined;
			}

			expandedMessages.push({
				...message,
				content: trailingText,
				preservedToolContext: undefined,
				tool_calls: undefined,
				reasoning_details: trailingReasoning
			});
		}

		return expandedMessages;
	};

	const expandMessagesForToolResumption = (messages = []) => {
		return messages.flatMap((message) => {
			// Preferred path: assistant messages that carry structured content_blocks
			// pass through as-is. The backend's blocks_to_api_messages converts them
			// to OpenAI shape — the same function the live tool loop uses, so live
			// and replay produce byte-identical messages and prompt caching holds.
			if (
				message?.role === 'assistant' &&
				Array.isArray(message?.content_blocks) &&
				message.content_blocks.length > 0
			) {
				return [message];
			}

			if (message?.preservedToolContext) {
				return expandPreservedToolContextMessage(message);
			}

			// Legacy fallback: assistant messages stored before the content_blocks
			// migration only have tool-call HTML in their content string. Recover
			// tool_calls by parsing the HTML — drift-prone, hence the migration.
			if (message?.role === 'assistant' && !message?.tool_calls) {
				const content = getStringMessageContent(message.content ?? '');
				if (/<details\s+type="tool_calls"[^>]+done="true"/.test(content)) {
					return expandPreservedToolContextMessage({ ...message, preservedToolContext: true });
				}
			}

			return [message];
		});
	};

	const retryFromLastRequest = async (message, modelId = null) => {
		if (!history.currentId) {
			return false;
		}

		const targetModelId = modelId ?? message?.selectedModelId ?? message?.model;
		const model = $models.find((m) => m.id === targetModelId);
		if (!model) {
			toast.error($i18n.t(`Model {{modelId}} not found`, { modelId: targetModelId }));
			return false;
		}

		const toolContext = getRetryableToolContext(message?.content ?? '');
		if (!toolContext?.content) {
			return false;
		}

		const responseMessageId = uuidv4();
		const responseMessage = {
			parentId: message.parentId,
			id: responseMessageId,
			childrenIds: [],
			role: 'assistant',
			content: `${toolContext.content}\n\n`,
			model: targetModelId,
			modelName: model.name ?? targetModelId,
			modelIdx: message.modelIdx ?? 0,
			timestamp: Math.floor(Date.now() / 1000),
			preservedToolContext: true,
			...(message.reasoning_details ? { reasoning_details: message.reasoning_details } : {}),
			...(message.reasoning_details_per_round
				? { reasoning_details_per_round: message.reasoning_details_per_round }
				: {})
		};

		history.messages[responseMessageId] = responseMessage;
		history.currentId = responseMessageId;

		if (message.parentId !== null && history.messages[message.parentId]) {
			history.messages[message.parentId].childrenIds = [
				...history.messages[message.parentId].childrenIds,
				responseMessageId
			];
		}

		history = history;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		const messages = createMessagesList(history, responseMessageId);
		const _chatId = getVisibleChatId();
		const chatEventEmitter = await getChatEventEmitter(targetModelId, _chatId);
		startUsagePolling(FAST_POLL_MS);

		await sendMessageSocket(model, messages, history, responseMessageId, _chatId);

		if (chatEventEmitter) {
			clearInterval(chatEventEmitter);
		}
		startUsagePolling(SLOW_POLL_MS);

		return true;
	};

	const regenerateWithModel = async (message, newModelId, preserveToolContext = false) => {
		console.log('regenerateWithModel', message, newModelId, preserveToolContext);

		if (!history.currentId) {
			return;
		}

		let userMessage = history.messages[message.parentId];

		if (preserveToolContext) {
			const retried = await retryFromLastRequest(message, newModelId);
			if (retried) {
				return;
			}
		}

		if (autoScroll) {
			scrollToBottom();
		}

		await sendMessage(history, userMessage.id, {
			modelId: newModelId,
			modelIdx: message.modelIdx
		});
	};

	const continueResponse = async () => {
		console.log('continueResponse');
		const _chatId = getVisibleChatId();

		if (history.currentId && history.messages[history.currentId].done == true) {
			const responseMessage = history.messages[history.currentId];

			if (shouldContinueFromLastToolRequest(responseMessage)) {
				await retryFromLastRequest(responseMessage);
				return;
			}

			responseMessage.done = false;
			await tick();

			const model = $models
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				startUsagePolling(FAST_POLL_MS);
				await sendMessageSocket(
					model,
					createMessagesList(history, responseMessage.id),
					history,
					responseMessage.id,
					_chatId
				);
				startUsagePolling(SLOW_POLL_MS);
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
				message.model,
				history.messages[message.parentId].content,
				responses
			);

			if (res && res.ok && res.body && generating) {
				generationController = { id: messageId, controller: controller as AbortController };
				const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
				for await (const update of textStream) {
					const { value, done, sources, error, usage } = update;
					if (error || done) {
						break;
					}

					if (mergedResponse.content == '' && value == '\n') {
						continue;
					} else {
						mergedResponse.content += value;
						history.messages[messageId] = message;
					}

					if (autoScroll) {
						scrollToBottom();
					}
				}

				await saveChatHandler(_chatId, history);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		} finally {
			chatStreamDebug('[chat-stream] MoA generation finally — clearing controller', {
				messageId
			});
			generating = false;
			clearGenerationControllerIfOwned(messageId);
		}
	};

	const initChatHandler = async (history) => {
		let _chatId = getVisibleChatId();

		if (!$temporaryChatEnabled) {
			chat = await createNewChat(
				localStorage.token,
				{
					id: _chatId,
					title: $i18n.t('New Chat'),
					models: selectedModels,
					system: $settings.system ?? undefined,
					params: params,
					history: history,
					messages: createMessagesList(history, history.currentId),
					tags: [],
					timestamp: Date.now()
				},
				$selectedFolder?.id
			);

			_chatId = chat.id;

			// Order matters here: update the URL FIRST, then $chatId. The
			// `activeChatId` reactive falls back to `isPersistentChatView()`
			// (which reads `window.location.pathname`, untracked by Svelte) when
			// `routeChatId` is stale. If we set $chatId first, the reactive
			// flushes on the next microtask while pathname is still `/`,
			// computes `activeChatId = ''`, and Navbar mounts with no chat —
			// hiding the token-stats box (and any other persistent-chat-only UI)
			// until the user navigates again. Doing replaceState first means the
			// reactive sees the new pathname and resolves activeChatId
			// correctly on the same flush.
			window.history.replaceState(history.state, '', `/c/${_chatId}`);
			chatId.set(_chatId);

			await tick();

			// Refresh the sidebar list in the background — this is purely cosmetic
			// and was previously gating the entire send pipeline on a network round-trip.
			currentChatPage.set(1);
			getChatList(localStorage.token, $currentChatPage)
				.then((list) => chats.set(list))
				.catch((err) => console.error('getChatList refresh failed:', err));

			selectedFolder.set(null);
		} else {
			_chatId = `local:${$socket?.id}`; // Use socket id for temporary chat
			await chatId.set(_chatId);
		}
		await tick();
		lastPersistedWebSearchEnabled = webSearchEnabled;
		lastPersistedStudyModeEnabled = studyModeEnabled;
		lastPersistedDataVizEnabled = dataVizEnabled;

		return _chatId;
	};

	const saveChatHandler = async (_chatId, history, nextParams = params) => {
		if (isVisibleChatEvent(_chatId)) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					params: nextParams,
					files: chatFiles
				});
				currentChatPage.set(1);
				// Refresh sidebar list in background — purely cosmetic, never gates the LLM request.
				getChatList(localStorage.token, $currentChatPage)
					.then((list) => chats.set(list))
					.catch((err) => console.error('getChatList refresh failed:', err));
			}
		}
	};

	const MAX_DRAFT_LENGTH = 5000;
	let saveDraftTimeout = null;

	const saveDraft = async (draft, chatId = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}

		if (draft.prompt !== null && draft.prompt.length < MAX_DRAFT_LENGTH) {
			saveDraftTimeout = setTimeout(async () => {
				await sessionStorage.setItem(
					`chat-input${chatId ? `-${chatId}` : ''}`,
					JSON.stringify(draft)
				);
			}, 500);
		} else {
			sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
		}
	};

	const clearDraft = async (chatId = null) => {
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
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
				await pinnedChats.set(await getPinnedChatList(localStorage.token));

				toast.success($i18n.t('Chat moved successfully'));
			}
		} else {
			toast.error($i18n.t('Failed to move chat'));
		}
	};

	// Promote the in-memory temporary chat into a permanent saved chat. Triggered
	// from both the navbar button and the Cmd/Ctrl+S keyboard shortcut. The earlier
	// implementation passed the user's first-message `content` directly as the
	// title, which fails when the content is a multimodal list (image/file/etc.) —
	// the API rejects the non-string title and the user sees a vague generic
	// "Failed to save conversation" toast. Coerce to text first, fall back when
	// empty, and surface real error messages so the user can act on them.
	const saveTempChatHandler = async () => {
		try {
			if (!history?.currentId || !Object.keys(history.messages).length) {
				toast.error($i18n.t('No conversation to save'));
				return;
			}

			const messagesList = createMessagesList(history, history.currentId);
			const firstUserContent = messagesList.find((m) => m.role === 'user')?.content;
			let title = getStringMessageContent(firstUserContent ?? '').trim();
			if (!title) {
				title = $i18n.t('New Chat');
			}
			if (title.length > 50) {
				title = `${title.slice(0, 50)}...`;
			}

			const savedChat = await createNewChat(
				localStorage.token,
				{
					id: uuidv4(),
					title,
					models: selectedModels,
					params: params,
					history: history,
					messages: messagesList,
					timestamp: Date.now()
				},
				null
			);

			if (!savedChat) {
				toast.error($i18n.t('Failed to save conversation'));
				return;
			}

			temporaryChatEnabled.set(false);
			chatId.set(savedChat.id);
			chats.set(await getChatList(localStorage.token, $currentChatPage));

			await goto(`/c/${savedChat.id}`);
			toast.success($i18n.t('Conversation saved successfully'));
		} catch (error) {
			console.error('Error saving conversation:', error);
			const detail =
				(error && (error.detail || error.message)) ||
				(typeof error === 'string' ? error : null);
			toast.error(
				detail
					? `${$i18n.t('Failed to save conversation')}: ${detail}`
					: $i18n.t('Failed to save conversation')
			);
		}
	};
</script>

<svelte:head>
	<title>
		{$settings.showChatTitleInTab !== false && $chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<audio id="audioElement" src="" style="display: none;" />

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	on:confirm={(e) => {
		if (e.detail) {
			eventCallback(e.detail);
		} else {
			eventCallback(true);
		}
	}}
	on:cancel={() => {
		eventCallback(false);
	}}
/>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? '  md:max-w-[calc(100%-260px)]'
		: ' '} w-full max-w-full flex flex-col"
	id="chat-container"
>
	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			{#if $selectedFolder && $selectedFolder?.meta?.background_image_url}
				<div
					class="absolute {$showSidebar
						? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
						: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$selectedFolder?.meta?.background_image_url})  "
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{:else if $settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url ?? null}
				<div
					class="absolute {$showSidebar
						? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
						: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$settings?.backgroundImageUrl ??
						$config?.license_metadata?.background_image_url})  "
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{/if}

			<PaneGroup direction="horizontal" class="w-full h-full">
				<Pane defaultSize={50} minSize={30} class="h-full flex relative max-w-full flex-col">
					<Navbar
						bind:this={navbarElement}
						chat={{
							id: activeChatId,
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
						bind:selectedModels
						shareEnabled={!!history.currentId}
						{initNewChat}
						archiveChatHandler={() => {}}
						{moveChatHandler}
						onSaveTempChat={saveTempChatHandler}
					/>

					<div class="flex flex-col flex-auto z-10 w-full @container overflow-auto">
						{#if ($settings?.landingPageMode === 'chat' && !$selectedFolder) || history.currentId !== null}
							<div
								class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
								id="messages-container"
								bind:this={messagesContainerElement}
								on:scroll={onScroll}
							>
								<div class=" h-full w-full flex flex-col">
									<Messages
										chatId={activeChatId}
										bind:history
										bind:autoScroll
										bind:prompt
										setInputText={(text) => {
											messageInput?.setText(text);
										}}
										{selectedModels}
										{atSelectedModel}
										{sendMessage}
										{showMessage}
										{submitMessage}
										{continueResponse}
										{regenerateResponse}
										{retryWithoutProviderRestrictions}
										{markSkipRemainingRetries}
										{regenerateWithModel}
										{mergeResponses}
										{chatActionHandler}
										{addMessages}
										topPadding={true}
										bottomPadding={files.length > 0}
										{onSelect}
									/>
								</div>
							</div>

							<!-- Token Usage Display -->
							{#if relevantGroups.length > 0}
								<div class="mx-auto inset-x-0 flex justify-center w-full">
									<div class="px-3 pb-2 w-full {($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-6xl'}">
										<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-3 text-xs">
										{#each relevantGroups as [groupName, groupData]}
											{@const effectiveUsage = groupData.effectiveUsage}
											{@const isOverLimit =
												groupData.limit && effectiveUsage.total > groupData.limit}
											<div class="flex items-center justify-between mb-1 last:mb-0">
												<span
													class="font-medium {isOverLimit
														? 'text-red-600 dark:text-red-400'
														: 'text-gray-700 dark:text-gray-300'}">{groupName}</span
												>
												<div
													class="flex items-center space-x-2 {isOverLimit
														? 'text-red-600 dark:text-red-400'
														: 'text-gray-600 dark:text-gray-400'}"
												>
													<span>{effectiveUsage.in.toLocaleString()} IN</span>
													<span>·</span>
													<span>{effectiveUsage.out.toLocaleString()} OUT</span>
													<span>·</span>
													<span>{effectiveUsage.total.toLocaleString()} TOTAL</span>
													{#if groupData.limit}
														<span>/ {groupData.limit.toLocaleString()}</span>
													{/if}
												</div>
											</div>
										{/each}
									</div>
								</div>
							</div>
							{/if}

							<div class=" pb-safe">
								<MessageInput
									bind:this={messageInput}
									{history}
									{taskIds}
									{selectedModels}
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedFilterIds
									bind:imageGenerationEnabled
									bind:codeInterpreterEnabled
									bind:webSearchEnabled
									bind:studyModeEnabled
									bind:dataVizEnabled
									bind:subagentsEnabled
									bind:serviceTier
									bind:atSelectedModel
									bind:showCommands
									toolServers={$toolServers}
									{generating}
									{stopResponse}
									{createMessagePair}
									onChange={(data) => {
										if (!$temporaryChatEnabled) {
											saveDraft(data, getDraftChatId());
										}
										// Capture reasoning effort from MessageInput (only if changed to prevent infinite loop)
										if (data.reasoning && data.reasoning.effort !== reasoning.effort) {
											reasoning = data.reasoning;
										}
									}}
									on:upload={async (e) => {
										const { type, data } = e.detail;

										if (type === 'web') {
											await uploadWeb(data);
										} else if (type === 'youtube') {
											await uploadYoutubeTranscription(data);
										} else if (type === 'google-drive') {
											await uploadGoogleDriveFile(data);
										}
									}}
									on:submit={async (e) => {
										clearDraft(getDraftChatId());
										if (e.detail || files.length > 0) {
											await tick();

											submitPrompt(e.detail.replaceAll('\n\n', '\n'));
										}
									}}
								/>

								<div
									class="absolute bottom-1 text-xs text-gray-500 text-center line-clamp-1 right-0 left-0"
								>
									<!-- {$i18n.t('LLMs can make mistakes. Verify important information.')} -->
								</div>
							</div>
						{:else}
							<div class="flex items-center h-full">
								<Placeholder
									{relevantGroups}
									{history}
									{selectedModels}
									bind:messageInput
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedFilterIds
									bind:imageGenerationEnabled
									bind:codeInterpreterEnabled
									bind:webSearchEnabled
									bind:studyModeEnabled
									bind:dataVizEnabled
									bind:subagentsEnabled
									bind:serviceTier
									bind:atSelectedModel
									bind:showCommands
									toolServers={$toolServers}
									{stopResponse}
									{createMessagePair}
									{onSelect}
									onChange={(data) => {
										if (!$temporaryChatEnabled) {
											saveDraft(data, getDraftChatId());
										}
									}}
									on:upload={async (e) => {
										const { type, data } = e.detail;

										if (type === 'web') {
											await uploadWeb(data);
										} else if (type === 'youtube') {
											await uploadYoutubeTranscription(data);
										}
									}}
									on:submit={async (e) => {
										clearDraft(getDraftChatId());
										if (e.detail || files.length > 0) {
											await tick();
											submitPrompt(e.detail.replaceAll('\n\n', '\n'));
										}
									}}
								/>
							</div>
						{/if}
					</div>
				</Pane>

				<ChatControls
					bind:this={controlPaneComponent}
					bind:history
					bind:chatFiles
					bind:params
					bind:files
					bind:pane={controlPane}
					chatId={activeChatId}
					modelId={selectedModelIds?.at(0) ?? null}
					models={selectedModelIds.reduce((a, e, i, arr) => {
						const model = $models.find((m) => m.id === e);
						if (model) {
							return [...a, model];
						}
						return a;
					}, [])}
					{submitPrompt}
					{stopResponse}
					{showMessage}
					{eventTarget}
				/>
			</PaneGroup>
		</div>
	{:else if loading}
		<div class="flex flex-col h-full w-full">
			<div class="flex items-center w-full px-4 h-12">
				<div class="h-5 w-48 bg-gray-200 dark:bg-gray-800 rounded animate-pulse mx-auto"></div>
			</div>
			<div class="flex flex-col flex-1 overflow-hidden px-6 pt-4 gap-6">
				{#each Array(3) as _, i}
					<div class="flex gap-3 {i % 2 === 1 ? 'justify-end' : ''}">
						{#if i % 2 === 0}
							<div class="size-7 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse flex-shrink-0"></div>
						{/if}
						<div class="flex flex-col gap-1.5 {i % 2 === 1 ? 'items-end' : ''}" style="max-width: 65%;">
							<div class="h-3.5 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" style="width: {120 + i * 40}px"></div>
							<div class="h-3.5 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" style="width: {180 + i * 20}px"></div>
						</div>
					</div>
				{/each}
			</div>
			<div class="px-4 pb-4">
				<div class="h-12 rounded-xl bg-gray-200 dark:bg-gray-800 animate-pulse"></div>
			</div>
		</div>
	{/if}
</div>
