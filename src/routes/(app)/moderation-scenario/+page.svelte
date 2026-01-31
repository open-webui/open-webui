<script lang="ts">
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { goto, afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar, user } from '$lib/stores';
	import { get } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import {
		applyModeration,
		generateFollowUpPrompt,
		type ModerationResponse,
		saveModerationSession,
		getModerationSessions,
		postSessionActivity,
		assignScenario,
		startScenario,
		completeScenario,
		skipScenario,
		abandonScenario,
		createHighlight,
		getHighlights,
		type ScenarioAssignResponse,
		getAssignmentsForChild,
		type AssignmentWithScenario
	} from '$lib/apis/moderation';
	import { getChildProfileById, getChildProfilesForUser } from '$lib/apis/child-profiles';
	import { finalizeModeration } from '$lib/apis/workflow';
	import { getAvailableScenarios, getCurrentSession } from '$lib/apis/prolific';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import {
		getQuestionsForCharacteristics,
		loadPersonalityDataFromJSON,
		generateScenariosFromJSON
	} from '$lib/data/personalityTraits';
	import { generateScenariosFromPersonalityData } from '$lib/data/personalityQuestions';
	import { getRandomScenarios, type QAPair } from '$lib/data/scenarioBank';
	import { getRandomAttentionCheck, type AttentionCheckQAPair } from '$lib/data/attentionCheckBank';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import AssignmentTimeTracker from '$lib/components/assignment/AssignmentTimeTracker.svelte';
	import VideoModal from '$lib/components/common/VideoModal.svelte';

	const i18n = getContext('i18n');

	// =================================================================================================
	// CONFIGURATION LEVERS
	// =================================================================================================
	//
	// SCENARIOS_PER_SESSION: Number of scenarios to randomly sample per session
	// This is a clear lever for adjusting the number of scenarios shown to users.
	// Change this value to modify how many scenarios are presented in each moderation session.
	//
	// =================================================================================================
	const SCENARIOS_PER_SESSION: number = 6;

	// Moderation options - grouped by category
	const moderationOptions = {
		'Refuse and Remove': [
			'Refuse Response and Explain',
			'Remove Harmful Phrases',
			'Omit Unprompted Suggestions',
			'Do Not Suggest Workarounds'
		],
		'Investigate and Empathize': ["Clarify Child's Intent", 'Emphasize Emotional Support'],
		'Correct their Understanding': [
			'Explain Problems in Prompt',
			'Emphasize Risk Awareness',
			'Redirect with Alternatives',
			'Remind Model is Not Human',
			'Encourage Introspection'
		],
		'Match their Age': ['Tailor to Age Group'],
		'Defer to Support': ['Defer to Parents', 'Defer to Resources'],
		'Attention Check': ['I read the instructions'],
		Custom: ['Custom']
	};

	// Convert to array for compatibility with existing code
	$: moderationOptionsArray = Object.values(moderationOptions).flat();

	// Tooltips for concern levels (Step 3)
	const concernTooltips: Record<number, string> = {
		1: "Not concerned — Appropriate for my child; I don't see meaningful risk.",
		2: 'Slightly concerned — Minor issues, but unlikely to cause harm.',
		3: 'Moderately concerned — Could confuse, mislead, or upset my child; I would prefer changes before they see it.',
		4: 'Very concerned — Likely to cause harm or encourage unsafe behavior; my child should not see it as-is.',
		5: 'Extremely concerned — Serious/urgent risk; must not be shown as-is.'
	};

	// Tooltips for each moderation strategy
	const moderationTooltips: Record<string, string> = {
		'Refuse Response and Explain':
			'Decline to provide an answer when the question is inappropriate or harmful, with a clear explanation why.',
		'Remove Harmful Phrases':
			'Identify and remove any language that could be damaging, triggering, or inappropriate for children.',
		'Omit Unprompted Suggestions':
			"Remove any advice or suggestions that weren't specifically requested by the child.",
		'Do Not Suggest Workarounds':
			'Avoid providing alternative ways to accomplish potentially harmful or inappropriate goals.',
		"Clarify Child's Intent":
			'Ask clarifying questions to better understand what the child is really asking for or trying to achieve.',
		'Emphasize Emotional Support':
			'Focus on validating feelings and providing emotional comfort before offering practical advice.',
		'Explain Problems in Prompt':
			"Point out any concerning or problematic aspects of the child's question itself.",
		'Emphasize Risk Awareness':
			'Highlight potential dangers, consequences, or things to be cautious about in the situation.',
		'Redirect with Alternatives':
			'Suggest safer, healthier, or more appropriate alternative actions or perspectives.',
		'Remind Model is Not Human':
			'Clarify that the AI is not a person and has limitations in understanding complex human situations.',
		'Encourage Introspection':
			'Prompt the child to think deeper about their feelings, motivations, or the situation.',
		'Tailor to Age Group':
			"Adjust language complexity, examples, and advice to be appropriate for the child's age level.",
		'Defer to Parents':
			'Suggest that the child discuss this matter with their parents or guardians for guidance.',
		'Defer to Resources':
			'Recommend professional resources, hotlines, or trusted adults who can provide specialized help.',
		Custom: 'Create your own moderation instruction tailored to this specific scenario.',
		'I read the instructions':
			'Only select this if you saw attention check instructions embedded in the scenario text. If you did not see any special instructions in the scenario, do not select this option.'
	};

	// Attention check marker and instruction suffix
	// Marker is embedded in response text to identify attention check scenarios.
	// Suffix contains 3-step instructions appended to attention check responses.
	const ATTENTION_CHECK_MARKER = '<!--ATTN-CHECK-->';
	const ATTENTION_CHECK_SUFFIX =
		'\n\nPlease moderate this question. Follow these steps:\n1) Step 1: Highlight anything in the response, then click "Continue".\n2) Step 2: In the "Explain why this content concerns you" field, enter "attention check", then click "Continue".\n3) Step 3: Select \'I read the instructions\' from the "Attention Check" dropdown under "Step 3: Moderate". ' +
		ATTENTION_CHECK_MARKER;

	// Custom scenario constant - always appears last
	const CUSTOM_SCENARIO_PROMPT = '[Create Your Own Scenario]';
	const CUSTOM_SCENARIO_PLACEHOLDER = 'Enter your custom child prompt here...';

	let selectedScenarioIndex: number = 0;
	let scenarioList: Array<[string, string]> = []; // Initialized empty - populated by personality-based scenarios
	let sessionNumber: number = 1; // Default session number for non-Prolific users

	// Track current session ID to detect changes
	let trackedSessionId: string | null = null;
	let trackedUrlSessionId: string | null = null;
	let isInitialMount: boolean = true;

	// Assignment time tracking (separate from moderation tracking)
	// Get session_number - prioritize localStorage (child-specific) over user object
	// This is important because enforceWorkflowNavigation increments localStorage session numbers
	// when a new Prolific session starts, but the user's session_number in DB may not be updated yet
	// Resolve session number as a function (not reactive) to avoid cyclical dependencies
	// Note: This function should only be called during component initialization (onMount)
	// to avoid accessing reactive stores outside component context
	function resolveSessionNumber() {
		try {
			if (typeof window === 'undefined' || !selectedChildId) {
				// Fallback: try to get from user object (only if in component context)
				try {
					const userObj = $user as any;
					const userSessionNumber = userObj?.session_number;
					if (userSessionNumber && Number.isFinite(userSessionNumber)) {
						sessionNumber = Number(userSessionNumber);
					} else {
						sessionNumber = 1;
					}
				} catch (e) {
					// Not in component context, use default
					sessionNumber = 1;
				}
				return;
			}

			let resolvedSessionNumber: number | null = null;

			// First, check localStorage for child-specific session number (most up-to-date)
			const sessionKey = `moderationSessionNumber_${selectedChildId}`;
			const storedSession = localStorage.getItem(sessionKey);
			if (storedSession) {
				const parsedSession = parseInt(storedSession);
				if (!isNaN(parsedSession) && parsedSession > 0) {
					resolvedSessionNumber = parsedSession;
				}
			}

			// Fallback: try to get from user object if localStorage didn't have a value
			if (resolvedSessionNumber === null) {
				try {
					const userObj = $user as any;
					const userSessionNumber = userObj?.session_number;
					if (userSessionNumber && Number.isFinite(userSessionNumber)) {
						resolvedSessionNumber = Number(userSessionNumber);
					}
				} catch (e) {
					// Not in component context, skip user object fallback
				}
			}

			// Final fallback
			if (resolvedSessionNumber === null || !Number.isFinite(resolvedSessionNumber)) {
				resolvedSessionNumber = 1;
			}

			sessionNumber = resolvedSessionNumber;
		} catch (e) {
			// If anything fails, use default
			console.warn('Error resolving session number, using default:', e);
			sessionNumber = 1;
		}
	}

	// Default characteristics to use as fallback when no scenarios are generated
	const DEFAULT_CHARACTERISTICS = [
		'Is curious about many different things',
		'Is compassionate, has a soft heart',
		'Is systematic, likes to keep things in order',
		'Is outgoing, sociable',
		'Can be tense'
	] as const;

	// Reactive block to detect URL parameter changes
	$: {
		const urlSessionId = $page.url.searchParams.get('SESSION_ID');
		if (urlSessionId && urlSessionId !== trackedUrlSessionId && !isInitialMount) {
			console.log('URL SESSION_ID changed:', trackedUrlSessionId, '->', urlSessionId);
			trackedUrlSessionId = urlSessionId;
			handleSessionChange(urlSessionId);
		}
	}

	// Listen for navigation events to catch session changes
	// Call afterNavigate at top level (not inside onMount) to avoid component initialization errors
	afterNavigate(() => {
		try {
			const pageValue = get($page);
			// Type-safe access to page URL - check if pageValue has url property
			if (!pageValue || typeof pageValue !== 'object' || !('url' in pageValue)) {
				console.warn('Page URL not available in afterNavigate');
				return;
			}

			const url = (pageValue as { url?: { searchParams?: URLSearchParams } }).url;
			if (!url || !url.searchParams) {
				console.warn('Page URL searchParams not available in afterNavigate');
				return;
			}

			const urlSessionId = url.searchParams.get('SESSION_ID') || '';
			const storageSessionId = localStorage.getItem('prolificSessionId') || '';

			console.log('Navigation detected, checking session:', {
				urlSessionId,
				storageSessionId,
				trackedUrlSessionId,
				trackedSessionId
			});

			// Trigger reactive updates if needed
			if (urlSessionId && urlSessionId !== trackedUrlSessionId) {
				trackedUrlSessionId = urlSessionId;
			}
			if (storageSessionId && storageSessionId !== trackedSessionId) {
				trackedSessionId = storageSessionId;
			}
		} catch (e) {
			// If we can't access page store, skip this check
			console.warn('Could not access page store in afterNavigate:', e);
		}
	});

	// Reactive block to detect localStorage changes
	$: {
		if (typeof window !== 'undefined' && !isInitialMount) {
			const storageSessionId = localStorage.getItem('prolificSessionId') || '';
			if (storageSessionId && storageSessionId !== trackedSessionId) {
				console.log(
					'localStorage prolificSessionId changed:',
					trackedSessionId,
					'->',
					storageSessionId
				);
				trackedSessionId = storageSessionId;
				handleSessionChange(storageSessionId);
			}
		}
	}

	function handleSessionChange(newSessionId: string) {
		const lastLoadedSessionId = localStorage.getItem('lastLoadedModerationSessionId') || '';

		if (newSessionId && newSessionId !== lastLoadedSessionId) {
			console.log('🔄 New session detected in moderation page, resetting state');
			resetAllScenarioStates();
			clearModerationLocalKeys();
			localStorage.setItem('lastLoadedModerationSessionId', newSessionId);

			// Reset scenario index to start fresh
			selectedScenarioIndex = 0;

			// Session number increment is handled by layout
			// Navigation to instructions is also handled by layout
		}
	}

	// Warm-up tutorial state
	let warmupCompleted: boolean = false;
	// FIX: Default showWarmup to true to prevent blank page when $user?.id is not available initially.
	// The reactive statement at line 327 will update this based on warmup completion status once $user is available.
	// If we defaulted to false, the template would try to render the regular UI before scenarios are loaded,
	// resulting in a blank page. Defaulting to true ensures the warmup tutorial displays by default.
	let showWarmup: boolean = true;
	let warmupStep: number = 0;
	let warmupSelectedStrategies: string[] = [];
	let warmupModeratedResponse: string = '';
	let warmupConfirmed: boolean = false;

	// =================================================================================================
	// WARMUP/LOAD INITIALIZATION FLOW DOCUMENTATION
	// =================================================================================================
	//
	// PURPOSE:
	// This reactive statement initializes `showWarmup` synchronously to prevent UI flashing
	// where the regular moderation UI briefly renders before switching to the tutorial.
	//
	// WHY SYNCHRONOUS (REACTIVE STATEMENT) VS ASYNCHRONOUS (onMount):
	// ------------------------------------------------------------------------------------------------
	// 1. Reactive statements execute during Svelte's initial render phase, before the template renders.
	//    This ensures `showWarmup` is set correctly BEFORE the template conditionally renders content.
	//
	// 2. If this check were in `onMount` (asynchronous), the sequence would be:
	//    a) Template renders with `showWarmup = false` (default) → Regular UI appears
	//    b) `onMount` executes → Checks localStorage → Sets `showWarmup = true`
	//    c) Template re-renders → Tutorial appears
	//    Result: Visible flash of regular UI before tutorial
	//
	// 3. With reactive statement (synchronous), the sequence is:
	//    a) Reactive statement executes when `$user?.id` becomes available
	//    b) Checks localStorage → Sets `showWarmup` immediately
	//    c) Template renders with correct `showWarmup` value → Correct UI from start
	//    Result: No flash, correct UI appears immediately
	//
	// INITIALIZATION ORDER:
	// ------------------------------------------------------------------------------------------------
	// 1. Component mounts → Reactive statement checks `$user?.id`
	// 2. When `$user?.id` is available → Reactive statement executes
	// 3. Reads `warmupCompleted` from localStorage → Sets `showWarmup = !warmupCompleted`
	// 4. Template renders based on `showWarmup` value
	// 5. `onMount` executes asynchronously → Handles child profiles, scenarios, state restoration
	//
	// RELATIONSHIP BETWEEN VARIABLES:
	// ------------------------------------------------------------------------------------------------
	// - `warmupCompleted`: Boolean flag stored in localStorage, indicates if user completed tutorial
	// - `showWarmup`: Controls template rendering - if true, shows tutorial; if false, shows regular UI
	// - Template uses: `{#if showWarmup}` to conditionally render tutorial vs regular moderation UI
	//
	// ERROR HANDLING:
	// ------------------------------------------------------------------------------------------------
	// If localStorage check fails, defaults to `showWarmup = true` (show tutorial) to ensure
	// new users always see the tutorial. This is safer than defaulting to false (which might
	// skip the tutorial for users who haven't completed it).
	//
	// =================================================================================================

	// TUTORIAL DISABLED: Tutorial feature has been disabled
	// Initialize showWarmup synchronously - always set to false to disable tutorial
	// This prevents the flash where regular UI renders before tutorial check completes
	$: if ($user?.id) {
		// Tutorial is disabled - always set showWarmup to false
		showWarmup = false;
		warmupCompleted = true; // Mark as completed so tutorial never shows
	}

	// Session-level lock to prevent re-ordering once restored/corrected
	let scenariosLockedForSession: boolean = false;
	let lastPolledChildId: string | number | null = null;
	let lastPolledSession: number | null = null;
	let currentFetchId: number = 0;
	let inFlightFetchId: number | null = null;
	let visibilityDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	// Session active time tracking
	let sessionActiveMs: number = 0;
	let lastActivityAt: number = Date.now();
	let activityInterval: ReturnType<typeof setInterval> | null = null;
	let syncInterval: ReturnType<typeof setInterval> | null = null;
	const IDLE_THRESHOLD_MS = 60_000; // 60s
	const SYNC_INTERVAL_MS = 30_000; // 30s

	function markActivity() {
		lastActivityAt = Date.now();
	}

	function isActiveWindow(): boolean {
		return typeof document !== 'undefined' && document.visibilityState === 'visible';
	}

	function activityKeyFor(childId: string | number, session: number) {
		return `moderationActiveMs_${childId}_${session}`;
	}

	async function startActivityTracking() {
		if (!selectedChildId || !Number.isFinite(sessionNumber)) return;
		try {
			const k = activityKeyFor(selectedChildId, sessionNumber);
			sessionActiveMs = Number(localStorage.getItem(k) || 0);
		} catch {}
		if (!activityInterval) {
			activityInterval = setInterval(() => {
				if (!isActiveWindow()) return;
				const now = Date.now();
				if (now - lastActivityAt <= IDLE_THRESHOLD_MS) {
					sessionActiveMs += 1000;
					try {
						localStorage.setItem(
							activityKeyFor(selectedChildId, sessionNumber),
							String(sessionActiveMs)
						);
					} catch {}
				}
			}, 1000);
		}
		if (!syncInterval) {
			syncInterval = setInterval(() => {
				void syncActivity();
			}, SYNC_INTERVAL_MS);
		}
		window.addEventListener('mousemove', markActivity);
		window.addEventListener('keydown', markActivity);
		window.addEventListener('click', markActivity);
		window.addEventListener('touchstart', markActivity);
		document.addEventListener('visibilitychange', markActivity);
		window.addEventListener('beforeunload', () => {
			try {
				const payload = JSON.stringify({
					user_id: $user?.id || 'unknown',
					child_id: selectedChildId,
					session_number: sessionNumber,
					active_ms_cumulative: sessionActiveMs
				});
				navigator.sendBeacon(`${WEBUI_API_BASE_URL}/moderation/session-activity`, payload);
			} catch {}
		});
	}

	async function syncActivity() {
		if (!selectedChildId || !Number.isFinite(sessionNumber)) return;
		try {
			await postSessionActivity(localStorage.token, {
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId,
				session_number: sessionNumber,
				active_ms_cumulative: sessionActiveMs
			});
		} catch (e) {
			console.warn('Activity sync failed', e);
		}
	}

	// Helper for current scenario key (still used for UI state)
	const currentKeyFor = (childId: string | number) => `moderationCurrentScenario_${childId}`;

	function shouldRepollScenarios(childId: string | number, session: number): boolean {
		if (!childId || !Number.isFinite(session)) return false;
		if (scenariosLockedForSession && lastPolledChildId === childId && lastPolledSession === session)
			return false;
		return true;
	}

	function beginScenarioFetch(): number {
		currentFetchId += 1;
		inFlightFetchId = currentFetchId;
		return currentFetchId;
	}

	function isFetchCurrent(fetchId: number): boolean {
		return inFlightFetchId === fetchId;
	}

	function endScenarioFetch(fetchId: number): void {
		if (inFlightFetchId === fetchId) inFlightFetchId = null;
	}

	/**
	 * Builds the final scenario list by loading one attention check from the attention check bank,
	 * appending instructions to it, shuffling it into the list (not at index 0 or last position),
	 * and ensuring the custom scenario is always last.
	 *
	 * @param basePairs - Base scenario Q&A pairs from the scenario bank
	 * @returns Promise resolving to the complete scenario list with attention check and custom scenario
	 */
	async function buildScenarioList(
		basePairs: Array<[string, string]>
	): Promise<Array<[string, string]>> {
		let list: Array<[string, string]> = basePairs.slice();

		// Load one attention check question from the database via API
		try {
			const token = localStorage.getItem('token');
			if (!token) {
				console.warn('⚠️ No authentication token available, skipping attention check');
			} else {
				const attentionCheck = await getRandomAttentionCheck(token);
				if (attentionCheck) {
					// Apply instruction suffix to the attention check question
					const attentionCheckResponse = attentionCheck.response + ATTENTION_CHECK_SUFFIX;
					const attentionCheckPair: [string, string] = [
						attentionCheck.question,
						attentionCheckResponse
					];

					// Shuffle attention check into the list (not at index 0, not at last position)
					list = shuffleAttentionCheckIntoList(list, attentionCheckPair);
				} else {
					console.warn(
						'⚠️ No attention check question available, proceeding without attention check'
					);
				}
			}
		} catch (error) {
			console.error('Error loading attention check:', error);
			// Continue without attention check if loading fails
		}

		// Ensure custom scenario is last
		const hasCustom = list.some(([q]) => q === CUSTOM_SCENARIO_PROMPT);
		if (!hasCustom) {
			list.push([CUSTOM_SCENARIO_PROMPT, CUSTOM_SCENARIO_PLACEHOLDER]);
		} else {
			// Move existing custom to the end
			list = list.filter(([q]) => q !== CUSTOM_SCENARIO_PROMPT);
			list.push([CUSTOM_SCENARIO_PROMPT, CUSTOM_SCENARIO_PLACEHOLDER]);
		}
		return list;
	}

	/**
	 * Shuffles an attention check question into the scenario list.
	 * The attention check will NOT be placed at index 0 (first scenario) or at the last position.
	 *
	 * @param list - The base scenario list
	 * @param attentionCheckPair - The attention check question/response pair with instructions already appended
	 * @returns The list with attention check shuffled in
	 */
	function shuffleAttentionCheckIntoList(
		list: Array<[string, string]>,
		attentionCheckPair: [string, string]
	): Array<[string, string]> {
		if (!Array.isArray(list) || list.length === 0) {
			// If list is empty, just add the attention check
			return [attentionCheckPair];
		}

		// Skip if attention check already exists in list
		if (list.some(([, res]) => (res || '').includes(ATTENTION_CHECK_MARKER))) {
			return list;
		}

		// Valid positions: 1 through list.length (not 0, not last)
		// After insertion, last position will be reserved for custom scenario
		const validPositions = [];
		for (let i = 1; i <= list.length; i++) {
			validPositions.push(i);
		}

		if (validPositions.length === 0) {
			// If no valid positions (shouldn't happen), just append
			return [...list, attentionCheckPair];
		}

		// Randomly select a position
		const randomPosition = validPositions[Math.floor(Math.random() * validPositions.length)];

		// Insert at the selected position
		const updated = [...list];
		updated.splice(randomPosition, 0, attentionCheckPair);

		return updated;
	}

	// Persist current scenario selection whenever it changes
	$: if (selectedChildId != null && typeof selectedScenarioIndex === 'number') {
		try {
			localStorage.setItem(currentKeyFor(selectedChildId), String(selectedScenarioIndex));
		} catch {}
	}

	// Custom scenario state
	let customScenarioPrompt: string = '';
	let customScenarioResponse: string = '';
	let customScenarioGenerating: boolean = false;
	let customScenarioGenerated: boolean = false;

	// Q&A Pair interface for personality-based scenarios
	interface QAPair {
		question: string;
		response: string;
	}

	// Reactive statement to get effective theme

	async function ensureSessionNumberForChild(childId: string) {
		try {
			const sessionKey = `moderationSessionNumber_${childId}`;
			const existing = localStorage.getItem(sessionKey);
			if (!existing) {
				const sessions = await getModerationSessions(localStorage.token, childId);
				const maxSession =
					Array.isArray(sessions) && sessions.length > 0
						? Math.max(...sessions.map((s: any) => Number(s.session_number || 0)))
						: 0;
				localStorage.setItem(sessionKey, String(maxSession + 1));
				// Prefer the freshly established session number immediately
				sessionNumber = maxSession + 1;
				console.log('✅ Started new session for child:', childId, 'session:', sessionNumber);
			}
		} catch (e) {
			console.warn('Failed to ensure session number for child', childId, e);
		}
	}

	// Ensure session number is initialized whenever selected child is set/changes
	// Note: Session number is resolved in the reactive statement above (line 116)
	// ensureSessionNumberForChild is called in onMount and when child changes to ensure
	// session numbers are properly initialized, avoiding cyclical dependency

	// Child profile and personality-based scenario generation
	let childProfiles: any[] = [];
	let selectedChildId: string = '';
	let previousChildId: string = ''; // Track previous child to detect changes
	let usePersonalityScenarios: boolean = true;
	let personalityJSONData: any = null;

	// Watch for child profile changes and reset state
	$: {
		// Get the current child ID from the service
		const currentChildId = childProfileSync.getCurrentChildId();

		if (currentChildId && previousChildId && currentChildId !== previousChildId) {
			console.log('🔄 Child profile changed from', previousChildId, 'to', currentChildId);
			const oldChildId = previousChildId;
			selectedChildId = currentChildId;

			// Reset all scenario state when switching child profiles
			resetAllScenarioStates();

			// Clear scenario list and lock to force fresh generation for new child
			scenarioList = [];
			scenariosLockedForSession = false;

			// Scenarios are now stored in backend, no localStorage cleanup needed
			console.log('Child profile changed, scenarios will be loaded from backend');

			// Update previous child ID
			previousChildId = currentChildId;

			// Regenerate scenarios for the new child (async, non-blocking)
			setTimeout(async () => {
				console.log('Generating scenarios for new child:', currentChildId);
				await loadRandomScenarios();
				console.log('Scenarios generated for new child. scenarioList.length:', scenarioList.length);
			}, 0);
		} else if (currentChildId && !previousChildId) {
			// First time initialization - don't regenerate (onMount handles it)
			selectedChildId = currentChildId;
			previousChildId = currentChildId;
			console.log('✅ Initial child ID set:', currentChildId);
		}
	}

	// =================================================================================================
	// RESET FLOW DOCUMENTATION
	// =================================================================================================
	//
	// PURPOSE:
	// Reset functions clear state when switching contexts (child profiles, sessions, scenarios).
	// They ensure clean state isolation so one scenario's data doesn't bleed into another.
	//
	// RESET FUNCTIONS OVERVIEW:
	// ------------------------------------------------------------------------------------------------
	// 1. `resetAllScenarioStates()` - Comprehensive reset for all scenarios
	//    - Called when: Switching child profiles, starting new session, session change detected
	//    - Clears: All scenario states, versions, highlights, decisions, localStorage
	//    - Purpose: Complete reset for new child/session context
	//
	// 2. `resetConversation()` - Reset current scenario only
	//    - Called when: User wants to start fresh on current scenario
	//    - Clears: Current scenario state only (highlights, versions, decisions)
	//    - Purpose: Allow re-moderation of same scenario without affecting others
	//
	// 3. `clearModerationLocalKeys()` - Clear localStorage keys
	//    - Called when: Session changes (Prolific users), workflow reset
	//    - Clears: Scenario-specific localStorage keys, workflow progress
	//    - Purpose: Remove stale cached data when context changes
	//
	// WHEN RESET FUNCTIONS ARE CALLED:
	// ------------------------------------------------------------------------------------------------
	// - `resetAllScenarioStates()`:
	//   * Child profile changes (reactive statement watching selectedChildId)
	//   * Session change detected (Prolific users)
	//   * Workflow reset (restart study button)
	//
	// - `resetConversation()`:
	//   * User clicks "Reset Conversation" button (if implemented)
	//   * User wants to start fresh on current scenario
	//
	// - `clearModerationLocalKeys()`:
	//   * Prolific session change detected
	//   * Workflow reset
	//
	// WHAT EACH RESET FUNCTION CLEARS:
	// ------------------------------------------------------------------------------------------------
	// `resetAllScenarioStates()` clears:
	//   - Scenario state map (all scenarios)
	//   - Versions, highlights, moderations, instructions
	//   - UI state (panels, views, comparisons)
	//   - Step completion flags (Step 1-4)
	//   - Custom scenario state
	//   - Scenario timers
	//   - Session locks
	//   - Child-specific localStorage keys
	//
	// `resetConversation()` clears:
	//   - Current scenario highlights
	//   - Current scenario versions
	//   - Current scenario decisions
	//   - Current scenario UI state
	//   - Step completion for current scenario
	//
	// `clearModerationLocalKeys()` clears:
	//   - Scenario-specific localStorage keys (pattern matching)
	//   - Workflow progress state
	//
	// RELATIONSHIP TO CHILD PROFILE CHANGES:
	// ------------------------------------------------------------------------------------------------
	// When a user switches child profiles:
	// 1. Reactive statement detects `selectedChildId` change
	// 2. Calls `resetAllScenarioStates()` to clear all state
	// 3. Clears child-specific localStorage keys
	// 4. Loads new child's scenarios and state
	// 5. Ensures complete isolation between children
	//
	// STATE ISOLATION PRINCIPLE:
	// ------------------------------------------------------------------------------------------------
	// Each scenario should have completely isolated state. When loading a scenario:
	// 1. All state variables are reset to defaults at start of `loadScenario()`
	// 2. State is then selectively restored from backend/localStorage
	// 3. This prevents previous scenario's state from affecting current scenario
	// 4. Reset functions ensure clean slate when switching contexts
	//
	// =================================================================================================

	// Function to reset all scenario states
	function resetAllScenarioStates() {
		console.log('Resetting all scenario states for new child profile');
		scenarioStates.clear();
		versions = [];
		currentVersionIndex = -1;
		confirmedVersionIndex = null;
		highlightedTexts1 = [];
		selectedModerations = new Set();
		customInstructions = [];
		showComparisonView = false;
		// showOriginal1 and moderationPanelVisible are now derived
		moderationPanelExpanded = false;
		expandedGroups.clear();
		attentionCheckSelected = false;
		attentionCheckPassed = false;
		attentionCheckProcessing = false;
		markedNotApplicable = false;
		// Reset unified initial decision flow state
		step1Completed = false;
		step2Completed = false;
		step3Completed = false;
		concernLevel = null;
		// showInitialDecisionPane is now derived
		// Reset custom scenario state
		customScenarioPrompt = '';
		customScenarioResponse = '';
		customScenarioGenerated = false;
		customScenarioGenerating = false;
		selectedScenarioIndex = 0;
		scenarioTimers.clear();
		// Reset scenario generation lock to allow fresh generation
		scenariosLockedForSession = false;
		lastPolledChildId = null;
		lastPolledSession = null;

		// Clear child-specific localStorage states
		try {
			if (selectedChildId) {
				const stateKey = `moderationScenarioStates_${selectedChildId}`;
				const timerKey = `moderationScenarioTimers_${selectedChildId}`;
				const currentKey = `moderationCurrentScenario_${selectedChildId}`;

				localStorage.removeItem(stateKey);
				localStorage.removeItem(timerKey);
				localStorage.removeItem(currentKey);
				console.log(`Cleared localStorage states for child: ${selectedChildId}`);
			}
		} catch (e) {
			console.error('Failed to clear scenario states from localStorage:', e);
		}
	}

	// Load child profiles and generate personality-based scenarios
	async function loadChildProfiles() {
		try {
			// Check if admin is viewing another user's quiz
			const adminUserId = $page.url.searchParams.get('user_id');
			if (adminUserId && $user?.role === 'admin') {
				// Load child profiles for the target user
				childProfiles = await getChildProfilesForUser(localStorage.token, adminUserId);
				console.log('Admin loaded child profiles for user:', adminUserId, childProfiles);
			} else {
				// Load child profiles for current user
				childProfiles = await childProfileSync.getChildProfiles();
				console.log('Loaded child profiles:', childProfiles);
			}

			if (childProfiles.length > 0) {
				// Get the current child ID from the service (set by sidebar/profile page)
				const currentChildId = childProfileSync.getCurrentChildId();
				if (currentChildId) {
					selectedChildId = currentChildId;
				} else {
					// Fallback to first child if none selected
					selectedChildId = childProfiles[0].id;
					await childProfileSync.setCurrentChildId(selectedChildId);
				}
				console.log('Set selectedChildId to:', selectedChildId);
			}

			// Load personality JSON data
			personalityJSONData = await loadPersonalityDataFromJSON();
			console.log('Loaded personality JSON data:', personalityJSONData);
		} catch (error) {
			console.error('Error loading child profiles:', error);
		}
	}

	// Helper: aggressively clear moderation-related localStorage keys
	function clearModerationLocalKeys() {
		const keysToRemove: string[] = [];
		for (let i = 0; i < localStorage.length; i++) {
			const k = localStorage.key(i) || '';
			if (
				k.startsWith('scenario_') ||
				k.startsWith('selection-') ||
				k.startsWith('input-panel-state-') ||
				k.startsWith('selection-dismissed-')
			) {
				keysToRemove.push(k);
			}
		}
		keysToRemove.forEach((k) => localStorage.removeItem(k));

		// Also reset workflow progress state for new session
		localStorage.removeItem('assignmentStep');
		localStorage.setItem('assignmentStep', '0');
	}

	/**
	 * Loads random scenarios from the scenario bank.
	 *
	 * Randomly samples SCENARIOS_PER_SESSION scenarios from the scenario bank,
	 * independent of child characteristics. Scenarios are sampled without replacement
	 * and exclude any scenarios already seen by the user/child.
	 *
	 * The scenario package is persisted to localStorage to prevent re-ordering
	 * within a session. Once locked for a session, scenarios don't regenerate.
	 *
	 * @returns {Promise<void>}
	 */
	async function loadRandomScenarios() {
		console.log('loadRandomScenarios called');
		console.log('selectedChildId:', selectedChildId);
		console.log('SCENARIOS_PER_SESSION:', SCENARIOS_PER_SESSION);

		if (!selectedChildId) {
			console.log('Early return: selectedChildId is not set');
			return;
		}

		const token = localStorage.getItem('token') || '';
		if (!token) {
			console.error('❌ No authentication token found');
			toast.error('Please log in to continue.');
			return;
		}

		// Get user ID from user store
		const userObj = $user as any;
		const participantId = userObj?.id;
		if (!participantId) {
			console.error('❌ No user ID found');
			toast.error('User information not available. Please refresh the page.');
			return;
		}

		try {
			// Get child profile from backend to get session_number
			const childProfile = await getChildProfileById(token, selectedChildId);
			if (childProfile && childProfile.session_number) {
				sessionNumber = childProfile.session_number;
				console.log(`✅ Got session_number ${sessionNumber} from child profile`);
			} else {
				console.warn('⚠️ Could not get session_number from child profile, using default 1');
				sessionNumber = 1;
			}

			// Check for existing assignments from backend
			let existingAssignments: AssignmentWithScenario[] = [];
			try {
				existingAssignments = await getAssignmentsForChild(token, selectedChildId);
				console.log(
					`Found ${existingAssignments.length} existing assignments for child ${selectedChildId}`
				);
			} catch (error) {
				console.log('No existing assignments found or error querying:', error);
			}

			// If we have existing assignments, use them
			if (existingAssignments.length > 0) {
				console.log('✅ Using existing assignments from backend');
				const basePairs: Array<[string, string]> = [];
				const assignmentMap: Map<number, { assignment_id: string; scenario_id: string }> =
					new Map();

				// Sort by assignment_position to maintain order
				existingAssignments.sort(
					(a, b) => (a.assignment_position || 0) - (b.assignment_position || 0)
				);

				for (const assignment of existingAssignments) {
					basePairs.push([assignment.prompt_text, assignment.response_text]);
					const position = assignment.assignment_position || 0;
					assignmentMap.set(position, {
						assignment_id: assignment.assignment_id,
						scenario_id: assignment.scenario_id
					});
				}

				console.log(`✅ Loaded ${basePairs.length} existing scenarios from backend`);

				// Build final list (loads attention check, shuffles it in, and adds custom scenario)
				scenarioList = await buildScenarioList(basePairs);

				// Store assignment IDs in scenario states
				assignmentMap.forEach((assignment, index) => {
					const existingState = scenarioStates.get(index) || {
						versions: [],
						currentVersionIndex: -1,
						confirmedVersionIndex: null,
						highlightedTexts1: [],
						selectedModerations: new Set(),
						customInstructions: [],
						showOriginal1: false,
						showComparisonView: false,
						attentionCheckSelected: false,
						attentionCheckPassed: false,
						markedNotApplicable: false,
						step1Completed: false,
						step2Completed: false,
						step3Completed: false,
						concernLevel: null,
						concernReason: '',
						satisfactionLevel: null,
						satisfactionReason: '',
						nextAction: null
					};
					existingState.assignment_id = assignment.assignment_id;
					existingState.scenario_id = assignment.scenario_id;
					scenarioStates.set(index, existingState);
				});

				if (scenarioList.length > 0) {
					scenariosLockedForSession = true;
					console.log('✅ Using existing assignments, scenarioList length:', scenarioList.length);

					// Load saved states for this child after scenarios are loaded
					loadSavedStates();

					// Load the first scenario to ensure UI is updated (force reload)
					await loadScenario(0, true);
				} else {
					console.warn('Built scenarioList is empty from existing assignments');
					scenariosLockedForSession = false;
				}
			} else {
				// No existing assignments found - create new ones
				console.log('No existing assignments found, creating new assignments...');

				// Assign scenarios one by one using weighted sampling
				const basePairs: Array<[string, string]> = [];
				const assignmentMap: Map<number, { assignment_id: string; scenario_id: string }> =
					new Map();

				for (let i = 0; i < SCENARIOS_PER_SESSION; i++) {
					try {
						const assignResponse = await assignScenario(token, {
							participant_id: participantId,
							child_profile_id: selectedChildId,
							assignment_position: i,
							alpha: 1.0 // Default alpha for weighted sampling
						});

						basePairs.push([assignResponse.prompt_text, assignResponse.response_text]);
						assignmentMap.set(i, {
							assignment_id: assignResponse.assignment_id,
							scenario_id: assignResponse.scenario_id
						});

						console.log(
							`✅ Assigned scenario ${i + 1}/${SCENARIOS_PER_SESSION}: ${assignResponse.scenario_id}`
						);
					} catch (error: any) {
						console.error(`Error assigning scenario ${i + 1}:`, error);
						// Continue with remaining scenarios even if one fails
						if (error?.detail?.includes('No eligible scenarios')) {
							console.warn(`⚠️ No eligible scenarios available for position ${i + 1}`);
							// If we have some scenarios, continue; otherwise show error
							if (basePairs.length === 0) {
								toast.error('No scenarios available. Please contact support.');
								return;
							}
						}
					}
				}

				if (basePairs.length === 0) {
					console.error('❌ No scenarios assigned from backend');
					toast.error(
						'Failed to load scenarios. Please refresh the page or contact support if the issue persists.'
					);
					return;
				}

				console.log(`✅ Created ${basePairs.length} new scenarios from backend`);

				// Build final list (loads attention check, shuffles it in, and adds custom scenario)
				scenarioList = await buildScenarioList(basePairs);

				// Store assignment IDs in scenario states
				assignmentMap.forEach((assignment, index) => {
					const existingState = scenarioStates.get(index) || {
						versions: [],
						currentVersionIndex: -1,
						confirmedVersionIndex: null,
						highlightedTexts1: [],
						selectedModerations: new Set(),
						customInstructions: [],
						showOriginal1: false,
						showComparisonView: false,
						attentionCheckSelected: false,
						attentionCheckPassed: false,
						markedNotApplicable: false,
						step1Completed: false,
						step2Completed: false,
						step3Completed: false,
						concernLevel: null,
						concernReason: '',
						satisfactionLevel: null,
						satisfactionReason: '',
						nextAction: null
					};
					existingState.assignment_id = assignment.assignment_id;
					existingState.scenario_id = assignment.scenario_id;
					scenarioStates.set(index, existingState);
				});

				if (scenarioList.length > 0) {
					scenariosLockedForSession = true;
					console.log('✅ Created new assignments, scenarioList length:', scenarioList.length);

					// Load saved states for this child after scenarios are loaded
					loadSavedStates();

					// Load the first scenario to ensure UI is updated (force reload)
					await loadScenario(0, true);
				} else {
					console.warn('Built scenarioList is empty, not locking session');
					scenariosLockedForSession = false;
				}
			}
		} catch (error) {
			console.error('Error loading scenarios from backend:', error);
			toast.error(
				'Failed to load scenarios. Please refresh the page or contact support if the issue persists.'
			);
		}
	}

	// Detects if current scenario is an attention check by checking for ATTENTION_CHECK_MARKER in response
	$: isAttentionCheckScenario = (scenarioList[selectedScenarioIndex]?.[1] || '').includes(
		ATTENTION_CHECK_MARKER
	);

	// Custom scenario helper - reactive variable (NOT a function!)
	$: isCustomScenario = scenarioList[selectedScenarioIndex]?.[0] === CUSTOM_SCENARIO_PROMPT;

	// Reactive debug logging
	$: {
		console.log('🎨 RENDER STATE:', {
			isCustomScenario,
			customScenarioGenerated,
			selectedScenarioIndex,
			currentPrompt: scenarioList[selectedScenarioIndex]?.[0],
			scenarioListLength: scenarioList.length
		});
	}

	// Generate response for custom scenario
	async function generateCustomScenarioResponse() {
		if (!customScenarioPrompt.trim() || customScenarioPrompt.trim().length < 10) {
			toast.error('Please enter a custom prompt (at least 10 characters)');
			return;
		}

		if (!$user) {
			toast.error('User not authenticated');
			return;
		}

		customScenarioGenerating = true;

		try {
			// Use the moderation API to generate a child-friendly response
			// We'll use empty moderation types to just get a basic response
			const result = await applyModeration(
				localStorage.getItem('token') || '',
				[], // No moderation strategies - just generate a response
				customScenarioPrompt.trim(),
				[], // No custom instructions
				undefined, // No original response
				[], // No highlighted texts
				undefined // No specific age
			);

			if (result) {
				customScenarioResponse = result.refactored_response;
				customScenarioGenerated = true;

				// Update the scenario list: keep CUSTOM_SCENARIO_PROMPT as the marker, store actual prompt in metadata
				// The response is the generated one
				scenarioList[selectedScenarioIndex] = [CUSTOM_SCENARIO_PROMPT, customScenarioResponse];

				// Custom scenarios are stored in memory, no persistence needed (backend assignments handle regular scenarios)

				// Update the current scenario data - treat this as the ORIGINAL response
				childPrompt1 = customScenarioPrompt.trim();
				originalResponse1 = customScenarioResponse;

				// Reset ALL state to treat this as a fresh, unmoderated scenario
				markedNotApplicable = false;
				versions = []; // No moderated versions yet
				currentVersionIndex = -1; // Not viewing any version
				confirmedVersionIndex = null; // Nothing confirmed
				highlightedTexts1 = []; // No highlights
				selectedModerations = new Set(); // No strategies selected
				customInstructions = []; // No custom instructions
				showComparisonView = false; // Not showing comparison view
				// showOriginal1 and moderationPanelVisible are now derived
				moderationPanelExpanded = false; // Panel collapsed
				attentionCheckSelected = false; // Not attention check

				// Initialize unified initial decision flow state for the custom scenario
				step1Completed = false; // Reset to step 1
				step1Completed = false;
				step2Completed = false;
				step3Completed = false;
				step3Completed = false;
				concernLevel = null;
				// showOriginal1 and showInitialDecisionPane are now derived

				// Wait for DOM to update, then scroll to top after custom scenario loads
				await tick();
				if (mainContentContainer) {
					mainContentContainer.scrollTo({ top: 0, behavior: 'smooth' });
				}

				// Force save the clean state (this will include customPrompt)
				saveCurrentScenarioState();

				// Ensure isLoadingScenario is false so reactive statements can evaluate
				isLoadingScenario = false;

				// Wait for reactive updates to complete
				await tick();

				console.log('✅ Custom scenario reset - treating as original response', {
					versions: versions.length,
					showOriginal1
				});

				toast.success('Custom scenario generated! Please review the response below.');
			}
		} catch (error) {
			console.error('Error generating custom scenario:', error);
			toast.error('Failed to generate response. Please try again.');
		} finally {
			customScenarioGenerating = false;
		}
	}

	/**
	 * Check if a scenario is completed.
	 *
	 * For attention check scenarios: completed when attentionCheckSelected AND attentionCheckPassed are both true.
	 * For regular scenarios: completed when markedNotApplicable OR confirmedVersionIndex is set.
	 *
	 * @param index - Scenario index to check
	 * @returns true if scenario is completed, false otherwise
	 */
	function isScenarioCompleted(index: number): boolean {
		const state = scenarioStates.get(index);
		const isAttentionCheck = (scenarioList[index]?.[1] || '').includes(ATTENTION_CHECK_MARKER);

		if (state) {
			// Check if this is an attention check scenario and if it's been passed
			if (isAttentionCheck && state.attentionCheckSelected && state.attentionCheckPassed) {
				return true;
			}
			// Completed if: marked not applicable or confirmed a moderated version
			const completed =
				state.markedNotApplicable ||
				(state.confirmedVersionIndex !== null && state.confirmedVersionIndex >= 0);
			return completed;
		}
		// Check current scenario
		if (index === selectedScenarioIndex) {
			// Check if this is an attention check scenario and if it's been passed
			if (isAttentionCheck && attentionCheckSelected && attentionCheckPassed) {
				return true;
			}
			// For current scenario, check if they've made a decision
			// Scenario is completed if: marked as not applicable OR a version has been confirmed
			const completed =
				markedNotApplicable || (confirmedVersionIndex !== null && confirmedVersionIndex >= 0);
			console.log('Current scenario completion check:', {
				index,
				markedNotApplicable,
				confirmedVersionIndex,
				isAttentionCheck,
				attentionCheckSelected,
				attentionCheckPassed,
				completed
			});
			return completed;
		}
		return false;
	}

	// Highlight information interface
	interface HighlightInfo {
		text: string;
		// Offsets removed - highlights now stored as HTML with <mark> elements
	}

	// Version management interfaces
	interface ModerationVersion {
		response: string;
		strategies: string[];
		customInstructions: Array<{ id: string; text: string }>;
		highlightedTexts: HighlightInfo[];
		moderationResult: ModerationResponse;
	}

	// Store moderation state for each scenario
	interface ScenarioState {
		versions: ModerationVersion[];
		currentVersionIndex: number;
		confirmedVersionIndex: number | null;
		highlightedTexts1: HighlightInfo[];
		selectedModerations: Set<string>;
		customInstructions: Array<{ id: string; text: string }>;
		showOriginal1: boolean;
		showComparisonView: boolean;
		// Attention check tracking: selected indicates user selected the option,
		// passed indicates the attention check scenario was successfully completed
		attentionCheckSelected: boolean;
		attentionCheckPassed: boolean;
		markedNotApplicable: boolean;
		customPrompt?: string; // Store actual custom prompt text for custom scenarios
		// Unified initial decision flow state (3-step flow)
		// Removed initialDecisionStep - now derived from completion flags
		step1Completed: boolean;
		step2Completed: boolean;
		step3Completed: boolean;
		// Removed step4Completed - now 3-step flow
		// Removed childAccomplish and assistantDoing - no longer collected in Step 2
		concernLevel: number | null; // Step 2 (Assess): Concern assessment (1-5)
		concernReason: string; // Step 2 (Assess): "Why?" explanation
		satisfactionLevel: number | null; // Step 3 (Update): Satisfaction level (1-5 Likert scale)
		satisfactionReason: string; // Step 3 (Update): "Why?" for satisfaction
		nextAction: 'try_again' | 'move_on' | null; // Step 3 (Update): Next action after satisfaction check
		// Assignment tracking (new system)
		assignment_id?: string; // Backend assignment ID for this scenario
		scenario_id?: string; // Backend scenario ID
		assignmentStarted?: boolean; // Whether /start endpoint has been called
		// HTML storage for highlights (Approach 3)
		responseHighlightedHTML?: string; // HTML with <mark> elements for response
		promptHighlightedHTML?: string; // HTML with <mark> elements for prompt
	}

	let scenarioStates: Map<number, ScenarioState> = new Map();

	// Reactive variable to trigger sidebar updates when scenario states change
	// This forces the sidebar to re-render when scenarios are completed
	$: scenarioStatesUpdateTrigger = (() => {
		// Access scenarioStates to make this reactive
		scenarioStates.forEach((state, index) => {
			// Just accessing the Map makes this reactive
		});
		return Date.now(); // Return timestamp to force update
	})();

	// Timer state - track time spent on each scenario
	let scenarioTimers: Map<number, number> = new Map(); // Store accumulated time in seconds
	let timerInterval: NodeJS.Timeout | null = null;
	let currentTimerStart: number | null = null;

	// Abandonment detection state
	let scenarioStartTimes: Map<number, number> = new Map(); // Track when each scenario was started
	let abandonmentTimeout: NodeJS.Timeout | null = null;
	const ABANDONMENT_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

	// Current scenario state
	let moderationLoading: boolean = false;
	let selectedModerations: Set<string> = new Set();
	let showCustomInput: boolean = false; // Show inline input instead of modal
	let customInstructionInput: string = '';
	let customInstructions: Array<{ id: string; text: string }> = [];
	// Attention check state: selected when user chooses "I read the instructions",
	// passed when attention check scenario is completed, processing during async save
	let attentionCheckSelected: boolean = false;
	let attentionCheckPassed: boolean = false;
	let attentionCheckProcessing: boolean = false;

	// Version management state
	let versions: ModerationVersion[] = [];
	let currentVersionIndex: number = -1;
	let confirmedVersionIndex: number | null = null;

	// Reactive computation for current scenario completion
	// Scenario is completed if: marked as not applicable OR a version has been confirmed OR attention check passed
	$: currentScenarioCompleted = (() => {
		const isAttentionCheck = (scenarioList[selectedScenarioIndex]?.[1] || '').includes(
			ATTENTION_CHECK_MARKER
		);
		const completed = isAttentionCheck
			? attentionCheckSelected && attentionCheckPassed
			: markedNotApplicable || (confirmedVersionIndex !== null && confirmedVersionIndex >= 0);
		console.log('Reactive: currentScenarioCompleted =', completed, {
			isAttentionCheck,
			attentionCheckSelected,
			attentionCheckPassed,
			markedNotApplicable,
			confirmedVersionIndex
		});
		return completed;
	})();

	// Reactive computation for completion count
	// This updates when scenarioStates changes (via scenarioStatesUpdateTrigger)
	$: completionCount = (() => {
		// Access scenarioStatesUpdateTrigger to make this reactive to scenario state changes
		const _ = scenarioStatesUpdateTrigger;

		// Count only completed scenarios in scenarioStates
		let completedInMap = 0;
		scenarioStates.forEach((state, index) => {
			if (isScenarioCompleted(index)) {
				completedInMap++;
			}
		});

		// Add current scenario if it's completed but not yet in scenarioStates
		const isCurrentAttentionCheck = (scenarioList[selectedScenarioIndex]?.[1] || '').includes(
			ATTENTION_CHECK_MARKER
		);
		const currentCompleted = isCurrentAttentionCheck
			? attentionCheckSelected && attentionCheckPassed
			: markedNotApplicable || (confirmedVersionIndex !== null && confirmedVersionIndex >= 0);
		const currentNotInMap = !scenarioStates.has(selectedScenarioIndex);
		const completedCount = completedInMap + (currentCompleted && currentNotInMap ? 1 : 0);

		return `${completedCount} of ${scenarioList.length} completed`;
	})();

	// Reactive array of completion statuses for all scenarios
	// This ensures the sidebar template is reactive to scenario state changes
	// Re-computes whenever scenarioStates or scenarioStatesUpdateTrigger changes
	//
	// IMPORTANT: The sidebar template uses this array (scenarioCompletionStatuses[index])
	// instead of calling isScenarioCompleted(index) directly. This is necessary because:
	// - Function calls in templates are not reactive to Map changes
	// - The reactive array recomputes when scenarioStates changes, triggering template updates
	// - This ensures completion indicators update immediately when scenarios are completed
	$: scenarioCompletionStatuses = (() => {
		// Access scenarioStatesUpdateTrigger to make this reactive to state changes
		const _ = scenarioStatesUpdateTrigger;
		return scenarioList.map((_, index) => isScenarioCompleted(index));
	})();

	// First pass data
	let childPrompt1: string = scenarioList.length > 0 && scenarioList[0] ? scenarioList[0][0] : '';
	let originalResponse1: string =
		scenarioList.length > 0 && scenarioList[0] ? scenarioList[0][1] : '';
	let highlightedTexts1: HighlightInfo[] = [];
	let childPromptHTML: string = '';

	// HTML storage for highlights (Approach 3)
	let responseHighlightedHTML: string = ''; // Store HTML with marks embedded for response
	let promptHighlightedHTML: string = ''; // Store HTML with marks embedded for prompt

	// Hydration guard to avoid DOM mutations before Svelte finishes hydrating
	let hasHydrated = false;

	// Text selection UI state
	let responseContainer1: HTMLElement;
	let promptContainer1: HTMLElement;
	let mainContentContainer: HTMLElement; // Main scrollable container
	let moderationPanelElement: HTMLElement; // Reference to moderation panel for scrolling
	let selectionButtonsVisible1: boolean = false;
	let selectionButtonsTop1: number = 0;
	let selectionButtonsLeft1: number = 0;
	let currentSelection1: string = '';
	let selectionInPrompt: boolean = false;

	// UI state
	let showComparisonView: boolean = false;
	let showHelpVideo: boolean = false;
	let showConfirmationModal: boolean = false;
	// Local restart removed; use global sidebar reset
	let showResetConfirmationModal: boolean = false; // keep for template compatibility, always false
	let moderationPanelExpanded: boolean = false;
	// showOriginal1 and showInitialDecisionPane are now derived via reactive statements above
	// moderationPanelVisible is set explicitly after state restoration to prevent flashing (see loadScenario)
	let moderationPanelVisible: boolean = false;
	// Loading flag to gate reactive updates during state restoration to prevent flashing
	let isLoadingScenario: boolean = false;
	let expandedGroups: Set<string> = new Set();
	let markedNotApplicable: boolean = false;

	// Unified initial decision flow state (3-step flow)
	// Removed initialDecisionStep - now derived from completion flags
	let step1Completed: boolean = false;
	let step2Completed: boolean = false;
	let step3Completed: boolean = false;
	// Removed step4Completed - now 3-step flow
	// Removed childAccomplish and assistantDoing - no longer collected
	let showInitialDecisionPane: boolean = false;

	// Derive current step from completion flags
	// Gate reactive updates during scenario loading to prevent flashing
	// SIMPLIFIED FLOW: Only Steps 1 and 2 are active (identification-only experiment)
	// Step 3 (moderation) is disabled - see UI block comment for restoration instructions
	$: initialDecisionStep = isLoadingScenario
		? 1
		: (() => {
				if (!step1Completed) return 1;
				if (!step2Completed) return 2;
				// SIMPLIFIED FLOW: Step 2 is now the final step
				// Original code for Step 3 (commented out for future restoration):
				// if (!step3Completed) return 3;
				// return 3; // Stay on step 3 even when completed (for viewing final state)
				return 2; // Stay on step 2 when completed (simplified flow ends here)
			})();

	// Step 2 (Assess): Concern assessment fields
	let concernLevel: number | null = null; // 1-5 (mapped from: 1=Not concerned at all, 2=Somewhat unconcerned, 3=Neutral, 4=Somewhat concerned, 5=Concerned)
	let concernReason: string = ''; // "Why?" field - required text explanation

	// Step 3 (Update): Satisfaction check fields (after version created)
	let satisfactionLevel: number | null = null; // 1-5 Likert scale (1=Very Dissatisfied, 5=Very Satisfied)
	let satisfactionReason: string = '';
	let nextAction: 'try_again' | 'move_on' | null = null;

	// Derived UI visibility states
	// SIMPLIFIED FLOW: Only show pane for Steps 1 and 2, close when scenario is complete
	// Gate reactive updates during scenario loading to prevent flashing
	$: showInitialDecisionPane = isLoadingScenario
		? false
		: initialDecisionStep >= 1 &&
			initialDecisionStep <= 2 &&
			!markedNotApplicable &&
			confirmedVersionIndex === null && // Close pane when scenario is complete
			(!isCustomScenario || customScenarioGenerated);
	// moderationPanelVisible is now set explicitly after state restoration to prevent flashing
	// See loadScenario() for explicit setting after all state is restored
	$: showOriginal1 = !showComparisonView || initialDecisionStep === 1;

	// Derived flag for drag-to-highlight feature visibility
	// Gate reactive updates during scenario loading to prevent flashing
	$: isHighlightingEnabled =
		!isLoadingScenario && initialDecisionStep === 1 && !markedNotApplicable;

	// DISABLED: Reactive statement that was causing panel to flash during state restoration
	// Panel visibility is now set explicitly in loadScenario after all state is restored
	// This prevents the panel from opening/closing during the async backend check
	// $: {
	// 	// Keep pane open for any step (1-4) as long as Step 4 is not completed and scenario is not marked as not applicable
	// 	const shouldShowPane = !step4Completed && !markedNotApplicable &&
	// 		(initialDecisionStep >= 1 && initialDecisionStep <= 4) &&
	// 		selectedScenarioIndex >= 0 &&
	// 		scenarioList.length > 0 &&
	// 		(!isCustomScenario || customScenarioGenerated);
	//
	// 	if (shouldShowPane && !showInitialDecisionPane) {
	// 		showInitialDecisionPane = true;
	// 		console.log('🔄 Reactive: Showing initial decision pane');
	// 	} else if (!shouldShowPane && showInitialDecisionPane) {
	// 		// showInitialDecisionPane is now derived
	// 	}
	// }
	// Mobile sidebar toggle for scenario list
	let sidebarOpen: boolean = true;
	// Request guard to prevent responses applying to wrong scenario
	let currentRequestId: number = 0;

	// =================================================================================================
	// DRAG-TO-HIGHLIGHT FEATURE DOCUMENTATION
	// =================================================================================================
	//
	// PURPOSE:
	// Allows users to drag over text in Step 1 to highlight concerns. The feature includes:
	// 1. Visual cursor feedback (cursor-text class with hover ring)
	// 2. Tooltip text ("Drag to highlight" arrows)
	// 3. Title attribute on hover ("Drag over text to highlight concerns")
	// 4. Functional text selection handler (handleTextSelection)
	//
	// ENABLING CONDITIONS:
	// ------------------------------------------------------------------------------------------------
	// All highlighting UI elements must check the same three conditions:
	// - `initialDecisionStep === 1`: Only enabled in Step 1 (highlighting step)
	// - `!markedNotApplicable`: Disabled if user marked scenario as "not applicable" (skip)
	//
	// CONSISTENCY REQUIREMENT:
	// ------------------------------------------------------------------------------------------------
	// The following elements MUST use identical conditions to prevent UI inconsistencies:
	// 1. cursor-text class (lines 4270, 4377): Visual cursor feedback
	// 2. title attribute (lines 4274, 4379): Hover tooltip text
	// 3. Tooltip visibility (lines 4276, 4381): "Drag to highlight" arrow indicators
	// 4. handleTextSelection guard (line 1351): Functional blocking
	//
	// If any condition is missing from one element, users will see inconsistent behavior:
	// - Tooltip text may remain visible when highlighting is disabled
	// - Cursor may change when highlighting is disabled
	// - Selection may work when UI suggests it's disabled
	//
	// STATE MANAGEMENT:
	// ------------------------------------------------------------------------------------------------
	// When `markNotApplicable()` is called:
	// - Sets `markedNotApplicable = true` immediately
	// - Clears `highlightedTexts1 = []` to remove existing highlights
	// - All highlighting UI should disappear immediately (not wait for navigation)
	//
	// Removed acceptOriginalResponse() - users can no longer accept original response
	//
	// =================================================================================================

	/**
	 * Handle text selection and auto-highlight on drag.
	 *
	 * **HIGHLIGHT SAVING BEHAVIOR:**
	 *
	 * Highlights are saved to TWO separate database tables:
	 *
	 * 1. **`selection` table** (immediate save):
	 *    - Saved immediately when user drags to select text
	 *    - Each highlight is saved as a separate row via `saveSelection()`
	 *    - Saved regardless of whether user later presses "Skip" or "Continue"
	 *    - Used for analytics and individual selection tracking
	 *    - Table: `selection` (backend model: `Selection`)
	 *
	 * 2. **`moderation_session` table** (batch save):
	 *    - Saved only when user presses "Continue" in Step 1 (via `completeStep1()`)
	 *    - All highlights saved together as JSON array in `highlighted_texts` column
	 *    - NOT saved if user presses "Skip" (sets `highlighted_texts: []`)
	 *    - Used for moderation session state and restoration
	 *    - Table: `moderation_session` (backend model: `ModerationSession`)
	 *
	 * HIGHLIGHTING IMPLEMENTATION (IN-PLACE TEXT WRAPPING)
	 *
	 * Historical context:
	 * - Earlier versions used offsets + string matching, which were brittle across markdown/rendering changes.
	 * - Then we tried DOM extraction (`range.extractContents()`), anchors, and block merging for cross-block
	 *   selections. This caused a long tail of bugs: duplicated highlights, reordered text, missing newlines,
	 *   highlights mysteriously appearing at the top or bottom of the response, and hydration issues.
	 *
	 * Current approach (Approach 3B - in-place wrapping):
	 * - We work directly on the rendered DOM and:
	 *   - Walk all text nodes in the active container (prompt or response).
	 *   - Find only those text nodes that intersect with the current selection range.
	 *   - For each such node, split it so the selected portion becomes its own `Text` node.
	 *   - Wrap that selected portion in a `<mark.selection-highlight>` element in-place.
	 * - We **never**:
	 *   - Call `extractContents()` or otherwise remove large fragments from the DOM.
	 *   - Move or recreate block elements (`<p>`, `<li>`, `<h2>`, etc.).
	 *   - Insert content relative to container roots.
	 *
	 * Benefits:
	 * - Works the same for single-block and cross-block selections.
	 * - Preserves exact visual order and whitespace/newlines.
	 * - Eliminates the class of bugs where highlights are duplicated or re-ordered.
	 *
	 * Data flow:
	 * - The DOM is treated as the source of truth for highlight placement.
	 * - After each mutation, we snapshot just the content HTML (prompt or response) into
	 *   `promptHighlightedHTML` / `responseHighlightedHTML`, which drives rendering and persistence.
	 *
	 * **IMPORTANT:** If user highlights text then presses "Skip":
	 * - Highlights remain in `selection` table (already saved)
	 * - `moderation_session.highlighted_texts` is set to empty array `[]`
	 * - This allows analytics to track what users highlighted even for skipped scenarios
	 */
	function handleTextSelection(event: MouseEvent) {
		// Only allow highlighting when explicitly enabled (step 1, not loading, not skipped)
		// This prevents saving to `selection` table during state restoration, after skip, or in steps 2-3
		if (!isHighlightingEnabled || !hasHydrated) return;
		const container = (event.currentTarget as HTMLElement) || responseContainer1;
		if (!container) return;

		// Capture the scenario index at the start to guard against navigation during async operations
		// This prevents race conditions where highlighting from scenario A overwrites scenario B's state
		const scenarioAtSelection = selectedScenarioIndex;

		setTimeout(() => {
			// Guard: If user navigated to a different scenario, don't proceed with highlighting
			if (selectedScenarioIndex !== scenarioAtSelection) {
				console.log('Skipping highlight: scenario changed during selection');
				return;
			}

			const selection = window.getSelection();
			const selectedText = selection?.toString().trim() || '';

			if (!selection || selectedText.length === 0 || selection.rangeCount === 0) {
				selectionButtonsVisible1 = false;
				currentSelection1 = '';
				return;
			}

			const range = selection.getRangeAt(0);

			/**
			 * PROMPT HIGHLIGHTING FIX
			 *
			 * Previously, activeContainer was set using: responseContainer1 || promptContainer1
			 * This always defaulted to responseContainer1 if it existed, even when the selection
			 * was in the prompt container. This caused prompt selections to fail the containment
			 * check and return early without creating highlights.
			 *
			 * Fix: Check which container actually contains the selection using contains() method,
			 * checking promptContainer1 first, then responseContainer1. This ensures the correct
			 * container is identified and highlighting works for both prompts and responses.
			 */
			// Determine which container actually contains the selection
			let activeContainer: HTMLElement | null = null;
			if (promptContainer1 && promptContainer1.contains(range.commonAncestorContainer)) {
				activeContainer = promptContainer1;
			} else if (responseContainer1 && responseContainer1.contains(range.commonAncestorContainer)) {
				activeContainer = responseContainer1;
			}

			if (!activeContainer || !activeContainer.contains(range.commonAncestorContainer)) {
				selectionButtonsVisible1 = false;
				currentSelection1 = '';
				return;
			}

			// Guard: if the selection is entirely inside an existing highlight, skip
			const startMark = range.startContainer.parentElement?.closest('mark.selection-highlight');
			const endMark = range.endContainer.parentElement?.closest('mark.selection-highlight');
			if (startMark && startMark === endMark) {
				const markRange = document.createRange();
				markRange.selectNodeContents(startMark);
				if (
					range.compareBoundaryPoints(Range.START_TO_START, markRange) >= 0 &&
					range.compareBoundaryPoints(Range.END_TO_END, markRange) <= 0
				) {
					selection.removeAllRanges();
					return;
				}
			}

			/**
			 * PREVENT RE-HIGHLIGHTING GUARD (cross-block)
			 *
			 * Clone the selection contents and check for existing marks. If any are present,
			 * skip highlighting to avoid deleting/altering already-highlighted content.
			 */
			try {
				const cloneRange = range.cloneRange();
				const cloneFragment = cloneRange.cloneContents(); // non-destructive
				const hasExistingMark = cloneFragment.querySelector('mark.selection-highlight');
				if (hasExistingMark) {
					selection.removeAllRanges();
					return;
				}
			} catch (e) {
				console.warn('Guard check failed when cloning selection:', e);
			}

			// Find content element (same logic as later in the function)
			let contentElement: HTMLElement | null = null;
			if (activeContainer === responseContainer1) {
				contentElement = activeContainer.querySelector('.response-text') as HTMLElement;
			} else if (activeContainer === promptContainer1) {
				contentElement = activeContainer.querySelector('p') as HTMLElement;
			}

			// Find all existing marks in the content element and unwrap any that overlap with the new selection
			if (contentElement) {
				const existingMarks = Array.from(
					contentElement.querySelectorAll('mark.selection-highlight')
				);
				const rangeClone = range.cloneRange();

				// Unwrap any marks that overlap with the new selection
				existingMarks.forEach((mark) => {
					try {
						if (rangeClone.intersectsNode(mark)) {
							// Unwrap: replace mark with its children using document fragment
							const parent = mark.parentNode;
							if (parent) {
								const fragment = document.createDocumentFragment();
								while (mark.firstChild) {
									fragment.appendChild(mark.firstChild);
								}
								parent.replaceChild(fragment, mark);
								parent.normalize();
							}
						}
					} catch (e) {
						// If intersectsNode fails (e.g., detached node), skip this mark
						console.warn('Error checking mark overlap:', e);
					}
				});
			}

			/**
			 * IN-PLACE TEXT NODE WRAPPING
			 *
			 * Instead of extracting and re-inserting content (which caused position/ordering bugs),
			 * we wrap text nodes IN PLACE without ever removing them from the DOM.
			 *
			 * This approach:
			 * - Never extracts content from the DOM
			 * - Never moves block elements
			 * - Works identically for single-block and cross-block selections
			 * - Preserves exact positions and document structure
			 */
			try {
				// The container to search within (use contentElement if available, else activeContainer)
				const searchRoot = contentElement || activeContainer;

				// Collect all text nodes that intersect with the selection range
				interface TextNodeInfo {
					node: Text;
					startOffset: number;
					endOffset: number;
				}
				const textNodesInRange: TextNodeInfo[] = [];

				const walker = document.createTreeWalker(searchRoot, NodeFilter.SHOW_TEXT, null);

				let textNode: Text | null;
				while ((textNode = walker.nextNode() as Text | null)) {
					// Skip empty text nodes
					if (!textNode.textContent || textNode.textContent.length === 0) {
						continue;
					}

					// Skip nodes inside existing marks
					if (textNode.parentElement?.closest('mark.selection-highlight')) {
						continue;
					}

					// Create a range for this text node to compare with selection
					const nodeRange = document.createRange();
					nodeRange.selectNodeContents(textNode);

					// Check if this text node intersects with the selection range
					// Node is entirely after selection - skip
					if (range.compareBoundaryPoints(Range.END_TO_START, nodeRange) >= 0) {
						continue;
					}
					// Node is entirely before selection - skip
					if (range.compareBoundaryPoints(Range.START_TO_END, nodeRange) <= 0) {
						continue;
					}

					// This node intersects - calculate the selected portion
					let startOffset = 0;
					let endOffset = textNode.length;

					// If selection starts within this node
					if (range.startContainer === textNode) {
						startOffset = range.startOffset;
					} else {
						// Check if selection starts after this node begins
						const startComparison = range.compareBoundaryPoints(Range.START_TO_START, nodeRange);
						if (startComparison > 0) {
							// Selection starts after node begins - but we need to find where
							// Since selection doesn't start in this node, use 0
							startOffset = 0;
						}
					}

					// If selection ends within this node
					if (range.endContainer === textNode) {
						endOffset = range.endOffset;
					} else {
						// Check if selection ends before this node ends
						const endComparison = range.compareBoundaryPoints(Range.END_TO_END, nodeRange);
						if (endComparison < 0) {
							// Selection ends before node ends - use full length
							endOffset = textNode.length;
						}
					}

					// Only include if there's actual content to highlight
					const selectedPortion = textNode.textContent.substring(startOffset, endOffset);
					if (startOffset < endOffset && selectedPortion.trim()) {
						textNodesInRange.push({ node: textNode, startOffset, endOffset });
					}
				}

				// If no text nodes found, nothing to highlight
				if (textNodesInRange.length === 0) {
					selection.removeAllRanges();
					return;
				}

				// Wrap each text node portion IN PLACE (no extraction)
				// Process in REVERSE order so that splitting earlier nodes doesn't
				// invalidate the offsets of later nodes
				for (let i = textNodesInRange.length - 1; i >= 0; i--) {
					const info = textNodesInRange[i];
					let targetNode: Text = info.node;
					const nodeLength = targetNode.length;

					// Validate offsets are still valid (in case DOM changed)
					if (info.startOffset >= nodeLength || info.endOffset > nodeLength) {
						continue;
					}

					// Split the text node to isolate the selected portion
					// Split off the end first (if not selecting to end)
					if (info.endOffset < nodeLength) {
						targetNode.splitText(info.endOffset);
						// targetNode now contains text from 0 to endOffset
					}

					// Split off the beginning (if not selecting from start)
					if (info.startOffset > 0) {
						targetNode = targetNode.splitText(info.startOffset);
						// targetNode now contains exactly the selected text
					}

					// Now targetNode contains exactly the selected text - wrap it in a mark
					const mark = document.createElement('mark');
					mark.className = 'selection-highlight bg-yellow-200 dark:bg-yellow-600';

					// Insert mark before the text node, then move text node into mark
					if (targetNode.parentNode) {
						targetNode.parentNode.insertBefore(mark, targetNode);
						mark.appendChild(targetNode);
					}
				}

				// Normalize the container to merge adjacent text nodes
				// This cleans up the splits we made
				if (searchRoot) {
					searchRoot.normalize();
				}
			} catch (error) {
				console.error('Error wrapping selection in mark:', error);
				selection.removeAllRanges();
				return;
			}

			// Defer reactive updates to avoid hydration conflicts
			// Use requestAnimationFrame to ensure DOM is stable before triggering Svelte updates
			requestAnimationFrame(() => {
				// Guard: If user navigated to a different scenario, don't save the highlight
				// This prevents race conditions where old scenario's HTML overwrites new scenario's state
				if (selectedScenarioIndex !== scenarioAtSelection) {
					console.log('Skipping highlight save: scenario changed');
					return;
				}

				// Store container's innerHTML after wrapping
				// Re-query the content element to ensure we have the latest DOM state after mark insertion
				if (activeContainer === responseContainer1) {
					// For response, find the div with class "response-text"
					contentElement = activeContainer.querySelector('.response-text') as HTMLElement;
				} else if (activeContainer === promptContainer1) {
					// For prompt, find the <p> tag
					contentElement = activeContainer.querySelector('p') as HTMLElement;
				}

				// Fallback to activeContainer if content element not found
				const elementToCapture = contentElement || activeContainer;
				const containerHTML = elementToCapture.innerHTML;

				// Use activeContainer instead of container to determine which HTML to store
				console.log(
					'🟠 Saving HTML - scenarioAtSelection:',
					scenarioAtSelection,
					'selectedScenarioIndex:',
					selectedScenarioIndex,
					'containerHTML length:',
					containerHTML.length
				);
				if (activeContainer === promptContainer1) {
					console.log('🟠 Setting promptHighlightedHTML');
					promptHighlightedHTML = containerHTML;
				} else {
					console.log('🟠 Setting responseHighlightedHTML');
					responseHighlightedHTML = containerHTML;
				}

				currentSelection1 = selectedText;
				selectionInPrompt = activeContainer === promptContainer1;

				// Automatically save the selection (stores HTML and saves to backend)
				saveSelection();

				// Clear the text selection after highlighting (visual cleanup)
				setTimeout(() => {
					selection.removeAllRanges();
				}, 100);
			});
		}, 10);
	}

	/**
	 * Save individual highlight to `selection` table immediately.
	 *
	 * This function is called automatically when user drags to select text.
	 * Each highlight is saved as a separate row in the `selection` table for:
	 * - Real-time analytics tracking
	 * - Individual selection history
	 * - Cross-scenario analysis
	 *
	 * **Save timing:** Immediate (on text selection, before "Continue" or "Skip")
	 * **Table:** `selection` (not `moderation_session`)
	 * **API endpoint:** POST `/api/v1/selections`
	 *
	 * Note: This is separate from the batch save to `moderation_session.highlighted_texts`
	 * which happens in `completeStep1()` when user presses "Continue".
	 */
	async function saveSelection() {
		const text = currentSelection1;

		if (!text) return;

		// Check if this highlight already exists (by text)
		const exists = highlightedTexts1.some((h) => h.text === text);
		if (!exists) {
			// Add to local state array (Approach 3: no offsets, just text)
			const highlightInfo: HighlightInfo = { text };
			highlightedTexts1 = [...highlightedTexts1, highlightInfo];

			// Save to new `/moderation/highlights` API (no offsets in Approach 3)
			try {
				const state = scenarioStates.get(selectedScenarioIndex);
				const assignmentId = state?.assignment_id;

				if (!assignmentId) {
					console.warn('No assignment_id found for scenario, skipping highlight save');
					// Fallback to old API for custom scenarios or scenarios without assignments
					const scenarioId = `scenario_${selectedScenarioIndex}`;
					const source = selectionInPrompt ? 'prompt' : 'response';
					const role = selectionInPrompt ? 'user' : 'assistant';
					const body = {
						chat_id: scenarioId,
						message_id: `${scenarioId}:${source}`,
						role,
						selected_text: text,
						child_id: selectedChildId || 'unknown',
						scenario_id: scenarioId,
						source,
						context: null,
						meta: {}
					};
					fetch(`${WEBUI_API_BASE_URL}/selections`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.token}`
						},
						body: JSON.stringify(body)
					});
					return;
				}

				// Save to new highlights API (no offsets in Approach 3)
				const highlightPayload = {
					assignment_id: assignmentId,
					selected_text: highlightInfo.text,
					source: (selectionInPrompt ? 'prompt' : 'response') as 'prompt' | 'response'
				};
				await createHighlight(localStorage.token, highlightPayload);
				console.log('✅ Highlight saved to new API:', { assignmentId, highlightInfo });
			} catch (e) {
				console.error('Failed to persist highlight to highlights API', e);
				// Fallback to old API on error
				try {
					const scenarioId = `scenario_${selectedScenarioIndex}`;
					const source = selectionInPrompt ? 'prompt' : 'response';
					const role = selectionInPrompt ? 'user' : 'assistant';
					const body = {
						chat_id: scenarioId,
						message_id: `${scenarioId}:${source}`,
						role,
						selected_text: text,
						child_id: selectedChildId || 'unknown',
						scenario_id: scenarioId,
						source,
						context: null,
						meta: {}
					};
					fetch(`${WEBUI_API_BASE_URL}/selections`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.token}`
						},
						body: JSON.stringify(body)
					});
				} catch (fallbackError) {
					console.error('Failed to persist selection via fallback API', fallbackError);
				}
			}
		}
		selectionButtonsVisible1 = false;
		currentSelection1 = '';

		const selection = window.getSelection();
		if (selection) {
			selection.removeAllRanges();
		}
	}

	/**
	 * Remove highlight from local state and delete from `selection` table.
	 *
	 * **Delete timing:** Debounced (250ms delay) to batch rapid removals
	 * **Table:** `selection` (deletes individual row)
	 * **API endpoint:** POST `/api/v1/selections/delete_by_text`
	 *
	 * Note: This only removes from `selection` table. If highlights were already
	 * saved to `moderation_session.highlighted_texts`, they remain there until
	 * the session is updated via `completeStep1()` or other save operations.
	 */
	function removeHighlight(highlight: HighlightInfo | string) {
		// Remove from local state array
		// Support both old string format (for backward compatibility) and new HighlightInfo format
		const textToRemove = typeof highlight === 'string' ? highlight : highlight.text;
		highlightedTexts1 = highlightedTexts1.filter((h) => h.text !== textToRemove);

		// Determine which container(s) to update
		// Since we don't know which container the highlight was in, update both if they have stored HTML
		const updates: Array<{
			htmlVar: 'response' | 'prompt';
			originalText: string;
			currentHTML: string;
		}> = [];

		if (responseHighlightedHTML && originalResponse1) {
			updates.push({
				htmlVar: 'response',
				originalText: originalResponse1,
				currentHTML: responseHighlightedHTML
			});
		}

		if (promptHighlightedHTML && childPrompt1) {
			updates.push({
				htmlVar: 'prompt',
				originalText: childPrompt1,
				currentHTML: promptHighlightedHTML
			});
		}

		// Rebuild HTML for each container
		for (const { htmlVar, originalText } of updates) {
			// Start with clean HTML (no marks)
			const cleanHTML = renderMarkdown(originalText);

			// Re-apply all remaining highlights
			const updatedHTML = applyHighlightsToHTML(cleanHTML, highlightedTexts1);

			// Update stored HTML
			if (htmlVar === 'prompt') {
				promptHighlightedHTML = updatedHTML;
			} else {
				responseHighlightedHTML = updatedHTML;
			}
		}

		// Delete from `selection` table (debounced to batch rapid removals)
		try {
			const scenarioId = `scenario_${selectedScenarioIndex}`;
			const role = 'assistant'; // Removal is text-only; role-agnostic on backend unless provided
			if (!window.__removeSelectionDebounce) {
				window.__removeSelectionDebounce = {};
			}
			const key = `${scenarioId}:${textToRemove}`;
			clearTimeout(window.__removeSelectionDebounce[key]);
			window.__removeSelectionDebounce[key] = setTimeout(() => {
				// POST to `/api/v1/selections/delete_by_text` - deletes from `selection` table
				fetch(`${WEBUI_API_BASE_URL}/selections/delete_by_text`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.token}`
					},
					body: JSON.stringify({ chat_id: scenarioId, selected_text: textToRemove, role })
				});
			}, 250);
		} catch (e) {
			console.error('Failed to schedule selection removal from selection table', e);
		}
	}

	/**
	 * Extract text from outermost <mark> elements in HTML (for backend data storage only)
	 * This function extracts text content from outermost marks, ignoring nested marks
	 */
	function extractTextFromHighlightedHTML(html: string): string[] {
		if (!html) return [];
		const tempDiv = document.createElement('div');
		tempDiv.innerHTML = html;
		const marks = Array.from(tempDiv.querySelectorAll('mark.selection-highlight'));
		const texts: string[] = [];
		marks.forEach((mark) => {
			// Ensure we only get text from outermost marks if there are nested ones
			if (!mark.parentElement?.closest('mark.selection-highlight')) {
				texts.push(mark.textContent || '');
			}
		});
		return texts;
	}

	/**
	 * Compute highlight offsets in original markdown text using multiple matching strategies
	 * @deprecated This function is no longer used in Approach 3 (HTML storage)
	 */
	function computeHighlightOffsets(
		highlightText: string,
		originalText: string
	): { startOffset: number; endOffset: number } | null {
		// Strategy 1: Exact match
		let startOffset = originalText.indexOf(highlightText);
		if (startOffset >= 0) {
			return { startOffset, endOffset: startOffset + highlightText.length };
		}

		// Strategy 2: Normalize whitespace (collapse multiple spaces/newlines)
		const normalizeWhitespace = (str: string) => str.replace(/\s+/g, ' ').trim();
		const normalizedText = normalizeWhitespace(highlightText);
		const normalizedOriginal = normalizeWhitespace(originalText);
		const normalizedStart = normalizedOriginal.indexOf(normalizedText);

		if (normalizedStart >= 0) {
			// Map back to original positions
			let originalPos = 0;
			let normalizedPos = 0;

			// Find start position
			while (originalPos < originalText.length && normalizedPos < normalizedStart) {
				if (!/\s/.test(originalText[originalPos])) {
					normalizedPos++;
				} else if (originalPos === 0 || !/\s/.test(originalText[originalPos - 1])) {
					normalizedPos++;
				}
				originalPos++;
			}
			const mappedStart = originalPos;

			// Find end position
			const targetEnd = normalizedStart + normalizedText.length;
			let endPos = originalPos;
			while (endPos < originalText.length && normalizedPos < targetEnd) {
				if (!/\s/.test(originalText[endPos])) {
					normalizedPos++;
				} else if (endPos === 0 || !/\s/.test(originalText[endPos - 1])) {
					normalizedPos++;
				}
				endPos++;
			}

			// Verify extracted text matches (allowing for whitespace differences)
			const extracted = normalizeWhitespace(originalText.substring(mappedStart, endPos));
			if (extracted === normalizedText) {
				return { startOffset: mappedStart, endOffset: endPos };
			}
		}

		// Strategy 3: Remove all whitespace (fuzzy match)
		const removeWhitespace = (str: string) => str.replace(/\s+/g, '');
		const textNoWS = removeWhitespace(highlightText);
		const originalNoWS = removeWhitespace(originalText);
		const fuzzyStart = originalNoWS.indexOf(textNoWS);

		if (fuzzyStart >= 0) {
			// Map back to original positions
			let originalPos = 0;
			let noWSPos = 0;

			// Find start
			while (originalPos < originalText.length && noWSPos < fuzzyStart) {
				if (!/\s/.test(originalText[originalPos])) {
					noWSPos++;
				}
				originalPos++;
			}
			const mappedStart = originalPos;

			// Find end
			const targetEnd = fuzzyStart + textNoWS.length;
			while (originalPos < originalText.length && noWSPos < targetEnd) {
				if (!/\s/.test(originalText[originalPos])) {
					noWSPos++;
				}
				originalPos++;
			}

			// Verify match is reasonable (not too long)
			if (originalPos - mappedStart <= highlightText.length * 2) {
				return { startOffset: mappedStart, endOffset: originalPos };
			}
		}

		return null; // Could not find match
	}

	/**
	 * Render markdown text to HTML (without highlights)
	 * Used for displaying markdown-formatted text in moderation responses
	 */
	function renderMarkdown(text: string): string {
		if (!text) return '';
		try {
			const html = marked.parse(text);
			return DOMPurify.sanitize(html);
		} catch (error) {
			console.error('Error rendering markdown:', error);
			return text; // Fallback to plain text on error
		}
	}

	/**
	 * Helper function to find text nodes containing a specific text using TreeWalker
	 * Returns array of text nodes that contain parts of the target text
	 */
	function findTextNodesInRange(root: Node, targetText: string): Text[] {
		const nodes: Text[] = [];
		const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
		let node: Text | null;
		let plainText = '';

		// First pass: collect all text nodes and build plain text map
		while ((node = walker.nextNode() as Text | null)) {
			if (node.parentElement?.closest('mark.selection-highlight')) {
				continue; // Skip nodes already inside highlights
			}
			plainText += node.textContent || '';
			nodes.push(node);
		}

		// Find target text in plain text
		const targetIndex = plainText.indexOf(targetText);
		if (targetIndex === -1) {
			return []; // Text not found
		}

		// Second pass: identify nodes that contain the target text
		const result: Text[] = [];
		let currentPos = 0;
		for (let i = 0; i < nodes.length; i++) {
			const node = nodes[i];
			const nodeText = node.textContent || '';
			const nodeStart = currentPos;
			const nodeEnd = currentPos + nodeText.length;
			currentPos = nodeEnd;

			// Check if this node overlaps with the target range
			if (nodeEnd > targetIndex && nodeStart < targetIndex + targetText.length) {
				result.push(node);
			}
		}

		return result;
	}

	/**
	 * Apply highlights to HTML by wrapping matching text in <mark> elements
	 * Uses TreeWalker pattern similar to existing selection logic
	 * @param html - HTML string to apply highlights to
	 * @param highlights - Array of highlight info objects containing text to highlight
	 * @returns HTML string with highlights applied
	 */
	function applyHighlightsToHTML(html: string, highlights: HighlightInfo[]): string {
		if (!html || highlights.length === 0) return html;

		// Parse HTML into temporary DOM
		const tempDiv = document.createElement('div');
		tempDiv.innerHTML = html;

		// Sort highlights by length (longest first) to avoid nested replacements
		const sortedHighlights = [...highlights].sort((a, b) => b.text.length - a.text.length);

		// Apply each highlight
		for (const highlight of sortedHighlights) {
			const targetText = highlight.text.trim();
			if (!targetText) continue;

			// Use TreeWalker to find text nodes (similar to findTextNodesInRange)
			const walker = document.createTreeWalker(tempDiv, NodeFilter.SHOW_TEXT, null);
			let node: Text | null;

			while ((node = walker.nextNode() as Text | null)) {
				// Skip nodes already inside marks
				if (node.parentElement?.closest('mark.selection-highlight')) {
					continue;
				}

				const nodeText = node.textContent || '';
				const idx = nodeText.indexOf(targetText);

				if (idx !== -1) {
					// Split text node and wrap target text with <mark> element
					// (similar to handleTextSelection logic)
					const mark = document.createElement('mark');
					mark.className = 'selection-highlight bg-yellow-200 dark:bg-yellow-600';
					mark.textContent = targetText;

					const before = node.splitText(idx);
					before.splitText(targetText.length);
					before.parentNode?.replaceChild(mark, before);

					// Normalize after modification
					tempDiv.normalize();
					break; // Only wrap first occurrence of each highlight
				}
			}
		}

		return tempDiv.innerHTML;
	}

	/**
	 * Render markdown text to HTML (simplified - highlights are now stored as HTML directly)
	 * @deprecated In Approach 3, highlights are stored as HTML directly, so this function just renders markdown.
	 * Use stored HTML (responseHighlightedHTML/promptHighlightedHTML) directly for display.
	 */
	function renderMarkdownWithHighlights(text: string, highlights: HighlightInfo[]): string {
		// Approach 3: Highlights are stored as HTML directly, so we just render markdown
		// The stored HTML (responseHighlightedHTML/promptHighlightedHTML) should be used directly for display
		return renderMarkdown(text);
	}

	/**
	 * Get highlighted HTML - Approach 3: Use stored HTML directly if available, otherwise render markdown
	 * @deprecated In Approach 3, use stored HTML (responseHighlightedHTML/promptHighlightedHTML) directly
	 */
	function getHighlightedHTML(text: string, highlights: HighlightInfo[]): string {
		// Approach 3: Just render markdown - highlights are stored as HTML directly
		return renderMarkdown(text);
	}

	// Reactive statement for response HTML - Approach 3: Use stored HTML directly
	$: response1HTML = (() => {
		console.log('🔴 response1HTML computing:', {
			selectedScenarioIndex,
			hasResponseHighlightedHTML: !!responseHighlightedHTML,
			responseHighlightedHTMLLength: responseHighlightedHTML?.length || 0,
			responseHighlightedHTMLPreview: responseHighlightedHTML?.substring(0, 100) || '',
			showInitialDecisionPane,
			initialDecisionStep,
			showOriginal1,
			currentVersionIndex,
			versionsLength: versions.length,
			originalResponse1Preview: originalResponse1?.substring(0, 50) || ''
		});

		// Use stored HTML if available (with marks already embedded)
		if (responseHighlightedHTML) {
			console.log('🔴 Using responseHighlightedHTML');
			return responseHighlightedHTML;
		}
		// Fall back to rendered markdown if no stored HTML
		// Always show original with highlights when in Step 1 of initial decision pane
		if (showInitialDecisionPane && initialDecisionStep === 1) {
			console.log('🔴 Using renderMarkdown (step 1)');
			return renderMarkdown(originalResponse1);
		}
		if (showOriginal1) {
			console.log('🔴 Using renderMarkdown (showOriginal1)');
			return renderMarkdown(originalResponse1);
		}
		if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
			console.log('🔴 Using versions[currentVersionIndex].response');
			return versions[currentVersionIndex].response;
		}
		console.log('🔴 Using renderMarkdown (default fallback)');
		return renderMarkdown(originalResponse1);
	})();

	// Ensure original is shown during Step 1 for highlighting
	// showOriginal1 is now derived via reactive statement above

	// Highlighted Prompt HTML - Approach 3: Use stored HTML directly
	$: childPromptHTML = (() => {
		console.log('🔵 childPromptHTML computing:', {
			selectedScenarioIndex,
			hasPromptHighlightedHTML: !!promptHighlightedHTML,
			promptHighlightedHTMLLength: promptHighlightedHTML?.length || 0,
			promptHighlightedHTMLPreview: promptHighlightedHTML?.substring(0, 100) || '',
			childPrompt1Preview: childPrompt1?.substring(0, 50) || ''
		});

		// Use stored HTML if available (with marks already embedded)
		if (promptHighlightedHTML) {
			console.log('🔵 Using promptHighlightedHTML');
			return promptHighlightedHTML;
		}
		// Fall back to rendered markdown if no stored HTML
		console.log('🔵 Using renderMarkdown (default fallback)');
		return renderMarkdown(childPrompt1);
	})();

	// Timer management functions
	function startTimer(scenarioIndex: number) {
		stopTimer(); // Stop any existing timer
		currentTimerStart = Date.now();

		// Initialize timer for this scenario if it doesn't exist
		if (!scenarioTimers.has(scenarioIndex)) {
			scenarioTimers.set(scenarioIndex, 0);
		}

		// Update timer every second
		timerInterval = setInterval(() => {
			if (currentTimerStart) {
				const elapsed = Math.floor((Date.now() - currentTimerStart) / 1000);
				const existingTime = scenarioTimers.get(scenarioIndex) || 0;
				scenarioTimers = new Map(scenarioTimers.set(scenarioIndex, existingTime + elapsed));
				currentTimerStart = Date.now(); // Reset start for next interval
			}
		}, 1000);
	}

	function stopTimer() {
		if (timerInterval) {
			clearInterval(timerInterval);
			timerInterval = null;
		}

		// Save final elapsed time before stopping
		if (currentTimerStart !== null) {
			const elapsed = Math.floor((Date.now() - currentTimerStart) / 1000);
			const existingTime = scenarioTimers.get(selectedScenarioIndex) || 0;
			scenarioTimers = new Map(scenarioTimers.set(selectedScenarioIndex, existingTime + elapsed));
			currentTimerStart = null;
		}
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	/**
	 * Check if a scenario should be abandoned and call /abandon endpoint if needed.
	 * A scenario is abandoned if it's been started but not completed within the timeout period.
	 */
	async function checkAndAbandonScenario(index: number) {
		const state = scenarioStates.get(index);
		if (!state?.assignment_id) return;

		// Check if scenario is completed
		const isCompleted = state.step2Completed && state.step3Completed;
		if (isCompleted) {
			// Scenario is completed, no need to abandon
			return;
		}

		// Check if scenario was started
		if (!state.assignmentStarted) {
			// Scenario was never started, no need to abandon
			return;
		}

		// Check timeout
		const startTime = scenarioStartTimes.get(index);
		if (!startTime) return;

		const elapsed = Date.now() - startTime;
		if (elapsed < ABANDONMENT_TIMEOUT_MS) {
			// Not yet timed out, reset timeout
			if (abandonmentTimeout) {
				clearTimeout(abandonmentTimeout);
			}
			abandonmentTimeout = setTimeout(() => {
				checkAndAbandonScenario(index);
			}, ABANDONMENT_TIMEOUT_MS - elapsed);
			return;
		}

		// Scenario has timed out - abandon it
		try {
			const [prompt] = scenarioList[index] || [];
			if (prompt === CUSTOM_SCENARIO_PROMPT) return; // Don't abandon custom scenarios

			const abandonResponse = await abandonScenario(localStorage.token, {
				assignment_id: state.assignment_id
			});

			console.log('✅ Abandoned scenario due to timeout:', state.assignment_id);

			// If reassigned, update the scenario list and state
			if (abandonResponse.reassigned && abandonResponse.new_assignment_id) {
				// Update scenario list with new prompt/response
				if (abandonResponse.new_prompt_text && abandonResponse.new_response_text) {
					scenarioList[index] = [
						abandonResponse.new_prompt_text,
						abandonResponse.new_response_text
					];
				}

				// Update state with new assignment
				state.assignment_id = abandonResponse.new_assignment_id;
				state.scenario_id = abandonResponse.new_scenario_id;
				state.assignmentStarted = false; // Reset so /start will be called again
				scenarioStates.set(index, state);

				console.log('✅ Scenario reassigned:', abandonResponse.new_assignment_id);
			}
		} catch (e) {
			console.error('Failed to abandon scenario (non-blocking):', e);
		}
	}

	function saveCurrentScenarioState() {
		// Guard: Don't save during scenario transitions to prevent saving old state to new scenario index
		if (isLoadingScenario) {
			console.log('⚠️ saveCurrentScenarioState skipped - isLoadingScenario is true');
			return;
		}

		// Get existing customPrompt if we're saving state for a custom scenario
		const existingState = scenarioStates.get(selectedScenarioIndex);
		const currentState: ScenarioState = {
			versions: [...versions],
			currentVersionIndex,
			confirmedVersionIndex,
			highlightedTexts1: [...highlightedTexts1],
			selectedModerations: new Set(selectedModerations),
			customInstructions: [...customInstructions],
			showOriginal1,
			showComparisonView,
			attentionCheckSelected,
			attentionCheckPassed,
			markedNotApplicable,
			customPrompt:
				isCustomScenario && customScenarioGenerated
					? customScenarioPrompt
					: existingState?.customPrompt,
			responseHighlightedHTML: responseHighlightedHTML,
			promptHighlightedHTML: promptHighlightedHTML,
			// Unified initial decision flow state (3-step flow)
			step1Completed,
			step2Completed,
			step3Completed,
			concernLevel,
			concernReason,
			satisfactionLevel,
			satisfactionReason,
			nextAction,
			// Assignment tracking (preserve existing values)
			assignment_id: existingState?.assignment_id,
			scenario_id: existingState?.scenario_id,
			assignmentStarted: existingState?.assignmentStarted
		};
		scenarioStates.set(selectedScenarioIndex, currentState);
		// Force reactive update by reassigning the Map
		// This ensures the sidebar updates when scenario completion state changes
		scenarioStates = new Map(scenarioStates);

		// Save to localStorage for persistence across navigation (child-specific)
		try {
			const serializedStates = new Map();
			scenarioStates.forEach((state, index) => {
				serializedStates.set(index, {
					...state,
					selectedModerations: Array.from(state.selectedModerations) // Convert Set to Array for JSON
				});
			});

			// Use child-specific localStorage keys
			const stateKey = selectedChildId
				? `moderationScenarioStates_${selectedChildId}`
				: 'moderationScenarioStates';
			const timerKey = selectedChildId
				? `moderationScenarioTimers_${selectedChildId}`
				: 'moderationScenarioTimers';
			const currentKey = selectedChildId
				? `moderationCurrentScenario_${selectedChildId}`
				: 'moderationCurrentScenario';

			localStorage.setItem(stateKey, JSON.stringify(Array.from(serializedStates.entries())));
			localStorage.setItem(timerKey, JSON.stringify(Array.from(scenarioTimers.entries())));
			localStorage.setItem(currentKey, selectedScenarioIndex.toString());
			console.log(`Saved moderation states to localStorage for child: ${selectedChildId}`);
		} catch (e) {
			console.error('Failed to save moderation states to localStorage:', e);
		}
	}

	async function loadScenario(index: number, forceReload: boolean = false) {
		// Skip if same scenario and not forcing reload
		if (index === selectedScenarioIndex && !forceReload) return;

		// Save current state before switching (unless forcing reload for new child)
		if (!forceReload) {
			saveCurrentScenarioState();
		}

		// Set loading flag to gate reactive updates during state restoration
		isLoadingScenario = true;

		selectedScenarioIndex = index;
		const [prompt, response] = scenarioList[index];

		console.log(
			'🔍 Loading scenario:',
			index,
			'Prompt:',
			prompt,
			'Is custom:',
			prompt === CUSTOM_SCENARIO_PROMPT
		);

		// Set original content FIRST, before clearing HTML, so reactive statements have correct fallback values
		// (Custom scenario handling will override these later if needed)
		childPrompt1 = prompt;
		originalResponse1 = response;

		// Reset content variables to defaults at the start to prevent persisting from previous scenario
		// BUT: Don't reset completion flags yet - wait until after backend check to preserve skip/accept states
		// This ensures clean content state before loading backend/localStorage data for THIS specific scenario
		highlightedTexts1 = [];
		console.log('🟢 Clearing HTML for scenario', index, '- previous values:', {
			responseHighlightedHTMLLength: responseHighlightedHTML?.length || 0,
			promptHighlightedHTMLLength: promptHighlightedHTML?.length || 0
		});
		responseHighlightedHTML = ''; // Clear highlighted HTML from previous scenario
		promptHighlightedHTML = ''; // Clear highlighted HTML from previous scenario
		concernLevel = null;
		concernReason = '';
		satisfactionLevel = null;
		satisfactionReason = '';
		nextAction = null;
		step1Completed = false;
		step2Completed = false;
		step3Completed = false;
		versions = [];
		currentVersionIndex = -1;
		confirmedVersionIndex = null;
		selectedModerations = new Set();
		customInstructions = [];
		showOriginal1 = false;
		showComparisonView = false;
		attentionCheckSelected = false;
		attentionCheckProcessing = false; // Reset processing flag when loading new scenario
		// Reset Step 3 UI state fields
		moderationPanelExpanded = false;
		expandedGroups.clear();
		showCustomInput = false;
		customInstructionInput = '';
		// Don't set initialDecisionStep here - use temporary variable and set once at end to prevent reactive updates
		// initialDecisionStep will be set once after all state restoration is complete
		// Reset completion flags - these will be restored from backend/localStorage if they exist
		markedNotApplicable = false;
		// Removed step4Completed - now 3-step flow
		// Initialize panel visibility to false - will be set correctly after state restoration
		moderationPanelVisible = false;
		// showInitialDecisionPane is now derived

		// Fetch session data from backend (primary source of truth) FIRST
		let backendSession = null;
		let versionSessions: any[] = [];
		try {
			if (selectedChildId && $user?.id) {
				const sessions = await getModerationSessions(localStorage.token, selectedChildId);
				// Find base session (version_number=0) and all version sessions
				backendSession = sessions.find(
					(s: any) =>
						s.scenario_index === index &&
						s.session_number === sessionNumber &&
						s.attempt_number === 1 &&
						s.version_number === 0
				);
				versionSessions = sessions
					.filter(
						(s: any) =>
							s.scenario_index === index &&
							s.session_number === sessionNumber &&
							s.attempt_number === 1 &&
							s.version_number > 0
					)
					.sort((a, b) => a.version_number - b.version_number);

				if (backendSession) {
					console.log('✅ Found backend session for scenario', index, backendSession);
				} else {
					console.log(
						'ℹ️ No backend session found for scenario',
						index,
						'- using localStorage fallback'
					);
				}
				if (versionSessions.length > 0) {
					console.log('✅ Found', versionSessions.length, 'version sessions for scenario', index);
				}
			}
		} catch (e) {
			console.error('Failed to fetch backend session (non-blocking):', e);
			// Continue with localStorage fallback
		}

		// Handle custom scenario specially
		if (prompt === CUSTOM_SCENARIO_PROMPT) {
			// Check if custom scenario was already generated (response is not placeholder)
			const savedState = scenarioStates.get(index);
			const isGenerated = response && response !== CUSTOM_SCENARIO_PLACEHOLDER;
			console.log(
				'📋 Custom scenario check - Is generated:',
				isGenerated,
				'Response preview:',
				response?.substring(0, 50),
				'Saved state:',
				savedState
			);
			if (isGenerated) {
				// Custom scenario was previously generated - restore its values
				// Use the saved customPrompt if available, otherwise use prompt
				customScenarioPrompt = savedState?.customPrompt || CUSTOM_SCENARIO_PROMPT;
				customScenarioResponse = response;
				customScenarioGenerated = true;
				console.log(
					'✅ Custom scenario already generated - prompt:',
					customScenarioPrompt.substring(0, 50)
				);

				// Set childPrompt1 to the actual custom prompt, not the marker
				childPrompt1 = customScenarioPrompt;
				originalResponse1 = response;

				// Continue to load the full saved state below
			} else {
				// Custom scenario has NOT been generated yet - show input form
				customScenarioPrompt = '';
				customScenarioResponse = '';
				customScenarioGenerated = false;

				// Reset state to ensure we show the input form
				versions = [];
				currentVersionIndex = -1;
				confirmedVersionIndex = null;
				highlightedTexts1 = [];
				selectedModerations = new Set();
				customInstructions = [];
				showOriginal1 = false;
				showComparisonView = false;
				moderationPanelVisible = false;
				moderationPanelExpanded = false;
				expandedGroups.clear();
				attentionCheckSelected = false;
				markedNotApplicable = false;

				childPrompt1 = prompt;
				originalResponse1 = response;

				console.log('🆕 Custom scenario NOT generated yet - showing input form');

				// Don't load saved state for ungenerated custom scenario
				return;
			}
		}

		const savedState = scenarioStates.get(index);

		// Call /start endpoint if this scenario has an assignment_id and hasn't been started yet
		// Skip for custom scenarios and attention checks (they don't have assignments)
		if (
			savedState?.assignment_id &&
			!savedState.assignmentStarted &&
			prompt !== CUSTOM_SCENARIO_PROMPT
		) {
			try {
				await startScenario(localStorage.token, {
					assignment_id: savedState.assignment_id
				});
				// Mark as started in state
				if (savedState) {
					savedState.assignmentStarted = true;
					scenarioStates.set(index, savedState);
				}
				// Track start time for abandonment detection
				scenarioStartTimes.set(index, Date.now());
				// Reset abandonment timeout
				if (abandonmentTimeout) {
					clearTimeout(abandonmentTimeout);
				}
				// Set new abandonment timeout
				abandonmentTimeout = setTimeout(() => {
					checkAndAbandonScenario(index);
				}, ABANDONMENT_TIMEOUT_MS);
				console.log('✅ Called /start endpoint for assignment:', savedState.assignment_id);
			} catch (e) {
				console.error('Failed to call /start endpoint (non-blocking):', e);
				// Continue loading even if start fails
			}
		}

		// Restore data from backend first (primary source), then fall back to localStorage
		if (backendSession) {
			// Step 1: Restore highlights from backend
			if (
				backendSession.highlighted_texts &&
				Array.isArray(backendSession.highlighted_texts) &&
				backendSession.highlighted_texts.length > 0
			) {
				// Handle both legacy string[] format and new dict[] format
				const firstItem = backendSession.highlighted_texts[0];
				if (typeof firstItem === 'string') {
					// Legacy format - convert to HighlightInfo
					highlightedTexts1 = (backendSession.highlighted_texts as unknown as string[]).map(
						(text) => ({
							text,
							startOffset: -1,
							endOffset: -1
						})
					);
				} else {
					// New format - already objects
					highlightedTexts1 = (backendSession.highlighted_texts as any[]).map((h) => ({
						text: h.text,
						startOffset: h.start_offset ?? -1,
						endOffset: h.end_offset ?? -1
					}));
				}
				step1Completed = true;
				console.log('✅ Restored highlights from backend:', highlightedTexts1.length);
			}

			// Step 2: Restore concern reason from backend (now in column, not metadata)
			if (backendSession.concern_reason) {
				concernReason = backendSession.concern_reason;
				step2Completed = true;
				console.log('✅ Restored Step 2 data from backend');
			}

			// Step 3: Restore pre-moderation judgment from backend (direct columns only)
			if (backendSession.concern_level !== null && backendSession.concern_level !== undefined) {
				concernLevel = backendSession.concern_level;
			}

			// Step 3 completion is now determined by satisfaction check (satisfaction_level, satisfaction_reason, next_action)
			// Note: would_show_child column was removed (migration 84b2215f7772) - it existed in DB but not in model
			// Satisfaction data will be restored after version reconstruction (see below)

			// Restore other fields from backend if available
			if (backendSession.initial_decision === 'not_applicable') {
				markedNotApplicable = true;
				step1Completed = true;
				step2Completed = true;
				step3Completed = true;
				// Removed accept_original handling - users can no longer accept original
				confirmedVersionIndex = null; // Not applicable means no version confirmed
				showOriginal1 = true;
			}

			// Reconstruct versions from backend version sessions (single pass with reduce)
			let confirmedSession: any = null;
			if (versionSessions && versionSessions.length > 0) {
				const {
					versions: restoredVersions,
					confirmedIndex,
					confirmedSession: foundConfirmedSession
				} = versionSessions.reduce(
					(acc: any, session: any) => {
						// Handle both legacy string[] format and new dict[] format for highlighted_texts
						let highlightedTexts: HighlightInfo[] = [];
						if (
							session.highlighted_texts &&
							Array.isArray(session.highlighted_texts) &&
							session.highlighted_texts.length > 0
						) {
							const firstItem = session.highlighted_texts[0];
							if (typeof firstItem === 'string') {
								// Legacy format - convert to HighlightInfo
								highlightedTexts = (session.highlighted_texts as unknown as string[]).map(
									(text) => ({
										text,
										startOffset: -1,
										endOffset: -1
									})
								);
							} else {
								// New format - already objects
								highlightedTexts = (session.highlighted_texts as any[]).map((h) => ({
									text: h.text,
									startOffset: h.start_offset ?? -1,
									endOffset: h.end_offset ?? -1
								}));
							}
						}
						const version = {
							response: session.refactored_response || '',
							strategies: session.strategies || [],
							customInstructions: (session.custom_instructions || []).map(
								(text: string, idx: number) => ({ id: `custom_${idx}`, text })
							),
							highlightedTexts,
							moderationResult: {} as ModerationResponse // ModerationResult may need to be reconstructed if stored
						};
						acc.versions.push(version);
						if (session.is_final_version === true) {
							acc.confirmedIndex = session.version_number - 1; // Convert to 0-based index
							acc.confirmedSession = session;
						}
						return acc;
					},
					{ versions: [], confirmedIndex: null, confirmedSession: null }
				);

				versions = restoredVersions;
				confirmedSession = foundConfirmedSession;

				if (confirmedIndex !== null) {
					confirmedVersionIndex = confirmedIndex;
					step3Completed = true;
					currentVersionIndex = confirmedIndex;
					showComparisonView = true;
					console.log('✅ Restored confirmed version from backend:', confirmedIndex);
				} else if (versions.length > 0) {
					// If versions exist but none confirmed, default to latest
					currentVersionIndex = versions.length - 1;
					showComparisonView = true;
				}
				console.log('✅ Restored', versions.length, 'versions from backend');
			}

			// Unified satisfaction data restoration: confirmed version first, then base session
			// Helper function to restore satisfaction data from a session (now in columns, not metadata)
			const restoreSatisfactionFromSession = (session: any) => {
				if (session) {
					if (session.satisfaction_level !== undefined && session.satisfaction_level !== null) {
						satisfactionLevel = session.satisfaction_level;
					}
					if (session.satisfaction_reason) {
						satisfactionReason = session.satisfaction_reason;
					}
					if (session.next_action) {
						nextAction = session.next_action;
					}
				}
			};

			// Restore satisfaction data from confirmed version if it exists, otherwise from base session
			if (confirmedSession) {
				restoreSatisfactionFromSession(confirmedSession);
				console.log('✅ Restored satisfaction data from confirmed version');
			} else if (backendSession) {
				restoreSatisfactionFromSession(backendSession);
				console.log('✅ Restored satisfaction data from base session');
			}
		}

		// Track what backend provided to avoid overwriting with localStorage
		const backendProvided = new Set<string>();
		if (backendSession) {
			if (backendSession.highlighted_texts && backendSession.highlighted_texts.length > 0) {
				backendProvided.add('highlightedTexts1');
			}
			if (backendSession.concern_reason) {
				backendProvided.add('concernReason');
			}
			if (backendSession.concern_level !== null && backendSession.concern_level !== undefined) {
				backendProvided.add('concernLevel');
			}
			if (
				backendSession.satisfaction_level !== null &&
				backendSession.satisfaction_level !== undefined
			) {
				backendProvided.add('satisfactionLevel');
			}
			if (backendSession.satisfaction_reason) {
				backendProvided.add('satisfactionReason');
			}
			if (backendSession.next_action) {
				backendProvided.add('nextAction');
			}
			if (backendSession.initial_decision === 'not_applicable') {
				backendProvided.add('markedNotApplicable');
			}
		}
		if (versions.length > 0) {
			backendProvided.add('versions');
		}
		if (confirmedVersionIndex !== null) {
			backendProvided.add('confirmedVersionIndex');
		}
		if (step1Completed || step2Completed || step3Completed) {
			backendProvided.add('step1Completed');
			backendProvided.add('step2Completed');
			backendProvided.add('step3Completed');
		}
		if (satisfactionLevel !== null || satisfactionReason || nextAction) {
			backendProvided.add('satisfactionLevel');
			backendProvided.add('satisfactionReason');
			backendProvided.add('nextAction');
		}

		// Helper function to restore from localStorage only if backend didn't provide it
		const restoreFromLocalStorageIfMissing = (
			savedState: ScenarioState | undefined,
			backendProvided: Set<string>
		) => {
			if (!savedState) return;

			// Restore HTML fields only if backend didn't provide them
			if (!backendProvided.has('responseHighlightedHTML') && savedState.responseHighlightedHTML) {
				console.log(
					'🟡 Restoring responseHighlightedHTML from savedState for scenario',
					index,
					'- length:',
					savedState.responseHighlightedHTML.length
				);
				responseHighlightedHTML = savedState.responseHighlightedHTML;
			} else {
				console.log(
					'🟡 NOT restoring responseHighlightedHTML - backendProvided:',
					backendProvided.has('responseHighlightedHTML'),
					'savedState has HTML:',
					!!savedState.responseHighlightedHTML
				);
			}
			if (!backendProvided.has('promptHighlightedHTML') && savedState.promptHighlightedHTML) {
				console.log(
					'🟡 Restoring promptHighlightedHTML from savedState for scenario',
					index,
					'- length:',
					savedState.promptHighlightedHTML.length
				);
				promptHighlightedHTML = savedState.promptHighlightedHTML;
			} else {
				console.log(
					'🟡 NOT restoring promptHighlightedHTML - backendProvided:',
					backendProvided.has('promptHighlightedHTML'),
					'savedState has HTML:',
					!!savedState.promptHighlightedHTML
				);
			}

			// Extract highlighted texts from HTML if HTML was restored
			if (
				(responseHighlightedHTML || promptHighlightedHTML) &&
				(!backendProvided.has('responseHighlightedHTML') ||
					!backendProvided.has('promptHighlightedHTML'))
			) {
				const responseTexts = extractTextFromHighlightedHTML(responseHighlightedHTML);
				const promptTexts = extractTextFromHighlightedHTML(promptHighlightedHTML);
				highlightedTexts1 = [...responseTexts, ...promptTexts].map((t) => ({ text: t }));
			} else if (
				!backendProvided.has('highlightedTexts1') &&
				savedState.highlightedTexts1?.length > 0
			) {
				// Fallback: restore from highlightedTexts1 if HTML not available
				highlightedTexts1 = [...savedState.highlightedTexts1];
			}

			if (!backendProvided.has('versions') && savedState.versions?.length > 0) {
				versions = [...savedState.versions];
				currentVersionIndex = savedState.currentVersionIndex;
			}

			if (
				!backendProvided.has('confirmedVersionIndex') &&
				savedState.confirmedVersionIndex !== null
			) {
				confirmedVersionIndex = savedState.confirmedVersionIndex;
			}

			if (!backendProvided.has('markedNotApplicable')) {
				markedNotApplicable = savedState.markedNotApplicable || false;
			}

			// Restore step completion flags only if backend didn't provide them
			// Simplified: if backend provided any step completion, don't restore from localStorage
			if (
				!backendProvided.has('step1Completed') &&
				!backendProvided.has('step2Completed') &&
				!backendProvided.has('step3Completed')
			) {
				// No backend data - restore all from localStorage
				step1Completed = savedState.step1Completed || false;
				step2Completed = savedState.step2Completed || false;
				step3Completed = savedState.step3Completed || false;
			}

			// Restore Step 2 data only if backend didn't provide it
			if (!backendProvided.has('concernLevel')) {
				concernLevel = savedState.concernLevel ?? null;
			}
			if (!backendProvided.has('concernReason')) {
				concernReason = savedState.concernReason || '';
			}

			// Restore Step 3 satisfaction data only if backend didn't provide it
			if (!backendProvided.has('satisfactionLevel')) {
				satisfactionLevel = savedState.satisfactionLevel ?? null;
			}
			if (!backendProvided.has('satisfactionReason')) {
				satisfactionReason = savedState.satisfactionReason || '';
			}
			if (!backendProvided.has('nextAction')) {
				nextAction = savedState.nextAction || null;
			}

			// Always restore UI state from localStorage (these don't conflict with backend)
			selectedModerations = new Set(savedState.selectedModerations);
			customInstructions = [...savedState.customInstructions];
			showOriginal1 = savedState.showOriginal1;
			showComparisonView = savedState.showComparisonView || false;
			attentionCheckSelected = savedState.attentionCheckSelected || false;
			attentionCheckPassed = savedState.attentionCheckPassed || false;
		};

		// Restore from localStorage using helper function
		if (savedState) {
			restoreFromLocalStorageIfMissing(savedState, backendProvided);
		}

		// If versions exist and not completed, ensure we're in Step 3 to match side-by-side display
		// BUT: Don't do this if markedNotApplicable (scenario is completed)
		// initialDecisionStep is now derived from completion flags, so we just need to mark steps complete
		if (versions.length > 0 && !step3Completed && !markedNotApplicable) {
			// Ensure all previous steps are marked complete to allow navigation back
			step1Completed = true;
			step2Completed = true;
			// Don't set step3Completed here - let user complete satisfaction check
			showComparisonView = true; // Show comparison view
			if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
				// Keep the saved currentVersionIndex
			} else {
				currentVersionIndex = versions.length - 1; // Default to latest version
			}
		}

		// If no localStorage state and no backend session, initialize to defaults
		if (!savedState && !backendSession) {
			// No data from either source - initialize to defaults
			highlightedTexts1 = [];
			step1Completed = false;
			step2Completed = false;
			step3Completed = false;
			concernLevel = null;
			versions = [];
			currentVersionIndex = -1;
			confirmedVersionIndex = null;
			selectedModerations = new Set();
			customInstructions = [];
			showOriginal1 = false;
			showComparisonView = false;
			moderationPanelExpanded = false;
			expandedGroups.clear();
			attentionCheckSelected = false;
			markedNotApplicable = false;
		}

		// Only override childPrompt1/originalResponse1 for custom scenarios (regular scenarios were set at start)
		// Custom scenarios need special handling because they use customScenarioPrompt instead of the marker
		if (prompt === CUSTOM_SCENARIO_PROMPT && customScenarioGenerated && customScenarioPrompt) {
			childPrompt1 = customScenarioPrompt;
			originalResponse1 = response;
		}
		// Otherwise, childPrompt1 and originalResponse1 were already set at the start of loadScenario
		selectionButtonsVisible1 = false;
		currentSelection1 = '';

		// Show original response when in Step 1 for highlighting
		if (initialDecisionStep === 1) {
			showOriginal1 = true;
		}

		// Wait for all state restoration to complete
		await tick();

		// Clear loading flag to allow reactive updates now that all state is restored
		isLoadingScenario = false;

		// Wait for reactive updates to complete after clearing the flag
		await tick();

		// FINAL: Set panel visibility ONCE after ALL state restoration is complete
		// This must be the absolute last thing to prevent any flashing
		// Calculate step directly from state variables, not from initialDecisionStep (which is reactive and may change during restoration)
		const isStep3 = step1Completed && step2Completed && !step3Completed;
		const isEndState = markedNotApplicable || confirmedVersionIndex !== null;

		if (isEndState) {
			// Scenario is in an end state - close panels
			moderationPanelVisible = false;
		} else {
			// Set panel visibility based on complete state: Step 3 + no confirmed version + not marked not applicable + step 2 completed + no versions
			const shouldShowPanel =
				isStep3 &&
				confirmedVersionIndex === null &&
				!markedNotApplicable &&
				step2Completed &&
				versions.length === 0;
			moderationPanelVisible = shouldShowPanel;
		}

		// Start timer for the new scenario
		startTimer(index);

		// Save the new scenario state immediately
		saveCurrentScenarioState();
	}

	// Local restart removed; use global sidebar reset
	function showResetConfirmation() {}

	function confirmReset() {}

	function cancelReset() {}

	function loadSavedStates() {
		try {
			// Use child-specific localStorage keys
			const stateKey = selectedChildId
				? `moderationScenarioStates_${selectedChildId}`
				: 'moderationScenarioStates';
			const timerKey = selectedChildId
				? `moderationScenarioTimers_${selectedChildId}`
				: 'moderationScenarioTimers';
			const currentKey = selectedChildId
				? `moderationCurrentScenario_${selectedChildId}`
				: 'moderationCurrentScenario';

			// Load scenario states
			const savedStates = localStorage.getItem(stateKey);
			if (savedStates) {
				const parsedStates = new Map(JSON.parse(savedStates));
				scenarioStates.clear();
				parsedStates.forEach((state: any, index: any) => {
					scenarioStates.set(index, {
						...state,
						selectedModerations: new Set(state.selectedModerations) // Convert Array back to Set
					});
				});
				// Reassign Map to trigger reactivity - Svelte needs Map reassignment to detect changes
				scenarioStates = new Map(scenarioStates);
				console.log(`Loaded saved scenario states from localStorage for child: ${selectedChildId}`);
			}

			// Load timers
			const savedTimers = localStorage.getItem(timerKey);
			if (savedTimers) {
				scenarioTimers = new Map(JSON.parse(savedTimers));
				console.log(`Loaded saved timers from localStorage for child: ${selectedChildId}`);
			}

			// Load current scenario
			const savedCurrentScenario = localStorage.getItem(currentKey);
			if (savedCurrentScenario) {
				const scenarioIndex = parseInt(savedCurrentScenario);
				if (scenarioIndex >= 0 && scenarioIndex < scenarioList.length) {
					selectedScenarioIndex = scenarioIndex;
					const [prompt, response] = scenarioList[scenarioIndex];

					// If this is a custom scenario, restore the custom prompt first
					if (
						prompt === CUSTOM_SCENARIO_PROMPT &&
						response &&
						response !== CUSTOM_SCENARIO_PLACEHOLDER
					) {
						const state = scenarioStates.get(scenarioIndex);
						if (state?.customPrompt) {
							customScenarioPrompt = state.customPrompt;
							customScenarioResponse = response;
							customScenarioGenerated = true;
							childPrompt1 = customScenarioPrompt; // Use the actual custom prompt
							originalResponse1 = response;
							console.log(
								'Restored custom scenario with prompt:',
								customScenarioPrompt.substring(0, 50)
							);
						} else {
							// Fallback if state not loaded yet
							childPrompt1 = prompt;
							originalResponse1 = response;
						}
					} else {
						childPrompt1 = prompt;
						originalResponse1 = response;
					}
					console.log('Restored current scenario:', scenarioIndex);
				}
			}
		} catch (e) {
			console.error('Failed to load saved states from localStorage:', e);
		}
	}

	function resetConversation() {
		// Reset current scenario state
		highlightedTexts1 = [];
		versions = [];
		currentVersionIndex = -1;
		confirmedVersionIndex = null;
		selectedModerations = new Set();
		customInstructions = [];
		showComparisonView = false;
		// showOriginal1 and moderationPanelVisible are now derived
		attentionCheckSelected = false;
		attentionCheckPassed = false;
		attentionCheckProcessing = false;
		markedNotApplicable = false;
		selectionButtonsVisible1 = false;
		// Reset unified initial decision flow state
		step1Completed = false;
		step2Completed = false;
		step3Completed = false;
		// Removed step4Completed - now 3-step flow
		concernLevel = null;
		// showInitialDecisionPane is now derived

		// Reset ALL scenario states
		scenarioStates.clear();

		// Reset ALL timers
		scenarioTimers.clear();
		stopTimer();

		// Clear child-specific localStorage
		if (selectedChildId) {
			const stateKey = `moderationScenarioStates_${selectedChildId}`;
			const timerKey = `moderationScenarioTimers_${selectedChildId}`;
			const currentKey = `moderationCurrentScenario_${selectedChildId}`;

			localStorage.removeItem(stateKey);
			localStorage.removeItem(timerKey);
			localStorage.removeItem(currentKey);
		} else {
			// Fallback to non-specific keys
			localStorage.removeItem('moderationScenarioStates');
			localStorage.removeItem('moderationScenarioTimers');
			localStorage.removeItem('moderationCurrentScenario');
		}

		// Reset to first scenario
		selectedScenarioIndex = 0;
		if (scenarioList.length > 0 && scenarioList[0]) {
			const [prompt, response] = scenarioList[0];
			childPrompt1 = prompt;
			originalResponse1 = response;
		}

		// Start fresh timer for first scenario
		startTimer(0);

		console.log('All scenarios reset - cleared states, timers, and returned to scenario 1');
	}

	// Version navigation functions
	function navigateToVersion(direction: 'prev' | 'next') {
		if (confirmedVersionIndex !== null) return; // Don't navigate if confirmed

		if (direction === 'prev' && currentVersionIndex > 0) {
			currentVersionIndex--;
		} else if (direction === 'next' && currentVersionIndex < versions.length - 1) {
			currentVersionIndex++;
		}

		// Don't auto-populate moderation panel - keep it clear to avoid confusion
		// Users should understand they're creating new versions from the original, not editing the viewed version
	}

	/**
	 * Confirm a version as the final version (original or moderated).
	 *
	 * Saves to backend with is_final_version: true on the specific version row.
	 *
	 * Row operation:
	 *   - If confirming original (confirmedVersionIndex === -1): UPDATE version_number: 0
	 *   - If confirming moderated version: UPDATE version_number: confirmedVersionIndex + 1
	 *
	 * Saves:
	 *   - is_final_version: true (marks this version as the selected final version)
	 *   - initial_decision: 'accept_original' or 'moderate' based on version type
	 *   - concern_level: From Step 2 if completed (using getCurrentStepData())
	 *   - strategies, custom_instructions, refactored_response: From version if moderated
	 *   - highlighted_texts: Current highlights
	 *
	 * Also clears is_final_version on other versions for this scenario/attempt.
	 */
	async function confirmCurrentVersion() {
		if (confirmedVersionIndex === null) {
			// Confirm current version
			confirmedVersionIndex = currentVersionIndex;
			step3Completed = true;
			moderationPanelVisible = false;
			moderationPanelExpanded = false;
			expandedGroups.clear();
			console.log('Confirm version - state:', { confirmedVersionIndex, markedNotApplicable });
			saveCurrentScenarioState(); // Save the decision

			// Save to backend with is_final_version: true
			try {
				const stepData = getCurrentStepData();
				const sessionId = `scenario_${selectedScenarioIndex}`;
				// Get the version number for the confirmed version (0 = original, 1+ = moderated versions)
				const versionNumber = confirmedVersionIndex === -1 ? 0 : confirmedVersionIndex + 1;
				await saveModerationSession(localStorage.token, {
					session_id: sessionId,
					user_id: $user?.id || 'unknown',
					child_id: selectedChildId || 'unknown',
					scenario_index: selectedScenarioIndex,
					attempt_number: 1,
					version_number: versionNumber,
					session_number: sessionNumber,
					scenario_prompt: childPrompt1,
					original_response: originalResponse1,
					initial_decision: confirmedVersionIndex === -1 ? 'accept_original' : 'moderate',
					concern_level: stepData.concern_level,
					strategies:
						confirmedVersionIndex >= 0 && versions[confirmedVersionIndex]
							? versions[confirmedVersionIndex].strategies
							: [],
					custom_instructions:
						confirmedVersionIndex >= 0 && versions[confirmedVersionIndex]
							? versions[confirmedVersionIndex].customInstructions.map((c) => c.text)
							: [],
					highlighted_texts: highlightedTexts1.map((h) => ({ text: h.text })),
					refactored_response:
						confirmedVersionIndex >= 0 && versions[confirmedVersionIndex]
							? versions[confirmedVersionIndex].response
							: undefined,
					is_final_version: true,
					decided_at: Date.now(),
					is_attention_check: isAttentionCheckScenario,
					attention_check_selected: attentionCheckSelected,
					attention_check_passed:
						isAttentionCheckScenario && attentionCheckSelected && selectedModerations.size > 0
				});
				console.log('Final version confirmed and saved to backend');
			} catch (e) {
				console.error('Failed to save final version to backend', e);
			}
		} else {
			// Unconfirm - navigate back to Step 4
			confirmedVersionIndex = null;
			step3Completed = false;
			if (step3Completed) {
				// Step 4 no longer exists - ensure all steps are complete
				step1Completed = true;
				step2Completed = true;
				step3Completed = true;
				moderationPanelVisible = true;
			}
			moderationPanelExpanded = false;
			expandedGroups.clear();
			console.log('Unconfirm version - state:', { confirmedVersionIndex, markedNotApplicable });
			saveCurrentScenarioState(); // Save the decision
		}
	}

	function getCurrentVersionResponse(): string {
		if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
			return versions[currentVersionIndex].response;
		}
		return originalResponse1;
	}

	function getCurrentVersionStrategies(): string[] {
		if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
			return versions[currentVersionIndex].strategies;
		}
		return [];
	}

	function getCurrentVersionCustomInstructions(): Array<{ id: string; text: string }> {
		if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
			return versions[currentVersionIndex].customInstructions;
		}
		return [];
	}

	function toggleModerationSelection(option: string) {
		// Special handling for Custom option - same as clicking group header
		if (option === 'Custom') {
			showCustomInput = !showCustomInput;
			return;
		}

		// Handle attention check selection: sets flags, saves to backend, navigates to next scenario
		if (option === 'ATTENTION_CHECK' || option === 'I read the instructions') {
			// If deselecting, just toggle
			if (attentionCheckSelected) {
				attentionCheckSelected = false;
				attentionCheckPassed = false;
				attentionCheckProcessing = false;
				return;
			}

			// If selecting and this is an attention check scenario, handle specially
			if (isAttentionCheckScenario) {
				attentionCheckSelected = true;
				attentionCheckPassed = true;
				attentionCheckProcessing = true; // Lock button immediately
				console.log(
					'[ATTENTION_CHECK] Scenario:',
					selectedScenarioIndex,
					'Selected:',
					attentionCheckSelected,
					'Passed:',
					attentionCheckPassed,
					'Timestamp:',
					new Date().toISOString()
				);

				// Immediately save attention check as passed and navigate to next
				(async () => {
					try {
						// Save attention check status to backend
						const sessionId = `scenario_${selectedScenarioIndex}`;
						await saveModerationSession(localStorage.token, {
							session_id: sessionId,
							user_id: $user?.id || 'unknown',
							child_id: selectedChildId || 'unknown',
							scenario_index: selectedScenarioIndex,
							attempt_number: 1,
							version_number: 0,
							session_number: sessionNumber,
							scenario_prompt: childPrompt1,
							original_response: originalResponse1,
							initial_decision: undefined,
							strategies: [],
							custom_instructions: [],
							highlighted_texts: highlightedTexts1.map((h) => ({ text: h.text })),
							refactored_response: undefined,
							is_final_version: false,
							is_attention_check: true,
							attention_check_selected: true,
							attention_check_passed: true
						});

						// Show success message
						toast.success('✓ Passed attention check!');

						// Mark scenario as completed with all necessary flags
						// Scenario completion is now tracked via confirmedVersionIndex
						step3Completed = true; // Complete the initial decision flow
						moderationPanelVisible = false; // Close moderation panel
						// showInitialDecisionPane is now derived // Hide initial decision pane

						// Save state to localStorage so it persists when navigating back
						saveCurrentScenarioState();
					} catch (e) {
						console.error('Failed to save attention check status:', e);
						toast.error('Failed to save attention check status');
						attentionCheckProcessing = false; // Unlock on error
					}
				})();

				return;
			} else {
				// Not an attention check scenario, just toggle
				attentionCheckSelected = !attentionCheckSelected;
				console.log(
					'[ATTENTION_CHECK] Scenario:',
					selectedScenarioIndex,
					'Selected:',
					attentionCheckSelected,
					'Timestamp:',
					new Date().toISOString()
				);
				return;
			}
		}

		// Toggle selection for standard options and saved customs
		if (selectedModerations.has(option)) {
			selectedModerations.delete(option);
		} else {
			// Check if limit of 3 is reached
			if (selectedModerations.size >= 3) {
				toast.error('Limit of 3 moderation strategies per scenario');
				return;
			}
			selectedModerations.add(option);
		}
		selectedModerations = selectedModerations; // Trigger reactivity
	}

	function toggleGroupExpansion(groupName: string) {
		// Special handling for Custom category - toggle input instead of group
		if (groupName === 'Custom') {
			showCustomInput = !showCustomInput;
			// Auto-expand the group when showing input
			if (showCustomInput) {
				expandedGroups.add('Custom');
			}
			expandedGroups = expandedGroups;
			return;
		}

		// Normal group expansion for other categories
		if (expandedGroups.has(groupName)) {
			expandedGroups.delete(groupName);
		} else {
			expandedGroups.add(groupName);
		}
		expandedGroups = expandedGroups; // Trigger reactivity
	}

	function addCustomInstruction() {
		const trimmed = customInstructionInput.trim();
		if (!trimmed) {
			toast.error('Please enter a custom instruction');
			return;
		}

		// Create unique ID for this custom instruction
		const id = `custom_${Date.now()}`;

		// Add to custom instructions array
		customInstructions = [...customInstructions, { id, text: trimmed }];

		// Add to selected moderations automatically
		selectedModerations.add(id);
		selectedModerations = selectedModerations;

		// Close input and reset
		showCustomInput = false;
		customInstructionInput = '';

		toast.success('Custom instruction added and selected');
	}

	function unmarkSatisfaction() {
		// Reset decision state
		confirmedVersionIndex = null;
		// Removed step4Completed - now 3-step flow
		// Navigate back to Step 4 if step 3 is completed
		if (step3Completed) {
			initialDecisionStep = 4;
			moderationPanelVisible = true;
		}
		moderationPanelExpanded = false;
		expandedGroups.clear();
		saveCurrentScenarioState();
		toast.info('Response unmarked. Please make a decision again.');
	}

	function removeCustomInstruction(id: string) {
		// Remove from custom instructions array
		customInstructions = customInstructions.filter((c) => c.id !== id);

		// Remove from selections if it was selected
		selectedModerations.delete(id);
		selectedModerations = selectedModerations;
	}

	function cancelCustomInput() {
		showCustomInput = false;
		customInstructionInput = '';
	}

	// Removed acceptOriginalResponse() - users can no longer accept original response without moderation

	// ============================================================================
	// MODERATION SESSION BACKEND SAVE FLOW - DOCUMENTATION
	// ============================================================================
	//
	// DATABASE CONVENTIONS:
	// ---------------------
	// The moderation_session table uses a hybrid storage approach:
	//
	// DIRECT COLUMNS (use for frequently queried, structured data):
	//   - concern_level (Integer): Pre-moderation judgment concern level (1-5)
	//   - initial_decision (Text): Final decision ('moderate' | 'not_applicable')
	//   - highlighted_texts (JSONField): Array of highlighted concern phrases
	//   - strategies (JSONField): Array of moderation strategy names
	//   - custom_instructions (JSONField): Array of custom instruction texts
	//   - refactored_response (Text): Final moderated response text
	//   - is_final_version (Boolean): Marks which version was selected as final
	//
	// SESSION_METADATA (JSONField, use for flexible, evolving data):
	//   - child_accomplish (string): Step 2 comprehension check - what child is trying to accomplish
	//   - assistant_doing (string): Step 2 comprehension check - what GenAI Chatbot is doing
	//   - decision (string): Final decision type (for metadata tracking)
	//   - decided_at (number): Timestamp when decision was made
	//   - version_index (number): Index of version in versions array (for version rows)
	//   - highlights_saved_at (number): Timestamp when highlights were saved
	//   - saved_at (number): Timestamp when step data was saved
	//
	// ROW OPERATIONS:
	// ---------------
	// All Steps 1-4 operate on version_number: 0 (UPDATE existing row or CREATE if first time)
	// Version creation (applySelectedModerations) creates NEW rows with version_number: 1, 2, 3...
	// Each moderated version is a separate row, allowing version history tracking
	//
	// VERSION NUMBER LOGIC:
	// ---------------------
	// - version_number: 0 = Original scenario state (Steps 1-4, accept original, skip)
	// - version_number: 1+ = Moderated versions (each new moderation creates a new row)
	// - When confirming a version, set is_final_version: true on that specific version row
	//
	// SAVE FLOW SUMMARY:
	// -----------------
	// Step 1 (completeStep1):
	//   - skipped=true: Saves initial_decision='not_applicable', concern_level=undefined
	//   - skipped=false: Saves highlighted_texts only
	//
	// Step 2 (completeStep2):
	//   - Saves child_accomplish and assistant_doing to session_metadata
	//   - Updates version_number: 0 row
	//
	// Step 3 (completeStep3):
	//   - Saves concern_level to DIRECT COLUMNS
	//   - Saves child_accomplish and assistant_doing to session_metadata (re-saves for consistency)
	//   - Updates version_number: 0 row
	//
	// Step 4 Final Decisions:
	//   - markNotApplicable(): Saves initial_decision='not_applicable' + all step data (if completed)
	//   - confirmCurrentVersion(): Saves is_final_version=true + all step data on specific version row
	//
	// Version Creation (applySelectedModerations):
	//   - Creates NEW row with version_number: currentVersionIndex + 1
	//   - Includes all step data (concern_level, child_accomplish, assistant_doing)
	//   - Saves strategies, custom_instructions, highlighted_texts, refactored_response
	//
	// ============================================================================

	// Unified Initial Decision Flow Functions

	/**
	 * Helper function to get current step data for saving to backend.
	 *
	 * Returns an object containing all step-related data that should be included
	 * in backend save operations. Fields from steps not yet reached are set to
	 * undefined (not null) to match TypeScript API expectations.
	 *
	 * @returns {Object} Step data object with:
	 *   - concern_level: number | undefined - Pre-moderation concern level (1-5) if Step 2 completed
	 *   - concern_reason: string | undefined - Explanation of concern if Step 2 completed
	 */
	function getCurrentStepData(): {
		concern_level: number | undefined;
		concern_reason: string | undefined;
	} {
		return {
			concern_level:
				step2Completed && concernLevel !== null && concernLevel !== undefined
					? concernLevel
					: undefined,
			concern_reason: step2Completed && concernReason?.trim() ? concernReason.trim() : undefined
		};
	}

	/**
	 * Step 1: Complete highlighting or skip scenario.
	 *
	 * Saves to backend with version_number: 0 (UPDATE existing row or CREATE if first time).
	 *
	 * **NEW REQUIREMENT**: User MUST highlight at least one concern to continue.
	 * Cannot proceed without selections - only skip scenario is allowed.
	 *
	 * **HIGHLIGHT SAVING BEHAVIOR:**
	 *
	 * This function saves highlights to the `moderation_session` table (NOT the `selection` table).
	 *
	 * **Two separate highlight storage systems:**
	 *
	 * 1. **`selection` table** (individual rows):
	 *    - Already saved immediately when user highlighted text (via `saveSelection()`)
	 *    - Each highlight is a separate row for analytics
	 *    - NOT affected by this function - remains in database even if skipped
	 *
	 * 2. **`moderation_session` table** (JSON array in `highlighted_texts` column):
	 *    - Saved here when user presses "Continue" (skipped=false)
	 *    - Set to empty array `[]` when user presses "Skip" (skipped=true)
	 *    - Used for session state restoration and moderation workflow
	 *
	 * **When skipped=true:**
	 *   - Saves initial_decision='not_applicable'
	 *   - Sets highlighted_texts: [] (empty array)
	 *   - Sets concern_level to undefined (steps not reached)
	 *   - Note: Highlights in `selection` table remain untouched
	 *
	 * **When skipped=false:**
	 *   - **VALIDATES**: Requires at least one highlight (highlightedTexts1.length > 0)
	 *   - Saves highlighted_texts: highlightedTexts1.map(h => ({ text: h.text })) (all highlights as JSON array)
	 *   - No step 2-3 data saved yet
	 *
	 * @param {boolean} skipped - If true, marks scenario as not applicable and skips all remaining steps
	 */
	async function completeStep1(skipped: boolean = false) {
		if (skipped) {
			markedNotApplicable = true;
			step1Completed = true;
			step2Completed = true; // Skip steps 2 and 3
			step3Completed = true;

			// Call /skip endpoint for new assignment tracking system
			const state = scenarioStates.get(selectedScenarioIndex);
			const [prompt] = scenarioList[selectedScenarioIndex] || [];
			if (state?.assignment_id && prompt !== CUSTOM_SCENARIO_PROMPT) {
				try {
					await skipScenario(localStorage.token, {
						assignment_id: state.assignment_id,
						skip_stage: 'step1',
						skip_reason: 'not_applicable',
						skip_reason_text: 'User marked scenario as not applicable'
					});
					console.log('✅ Called /skip endpoint for assignment:', state.assignment_id);
				} catch (e) {
					console.error('Failed to call /skip endpoint (non-blocking):', e);
					// Continue even if skip endpoint fails
				}
			}

			// Save skip decision immediately to backend
			// Note: Highlights in `selection` table remain untouched (already saved when user highlighted)
			// Only `moderation_session.highlighted_texts` is set to empty array
			try {
				const sessionId = `scenario_${selectedScenarioIndex}`;
				await saveModerationSession(localStorage.token, {
					session_id: sessionId,
					user_id: $user?.id || 'unknown',
					child_id: selectedChildId || 'unknown',
					scenario_index: selectedScenarioIndex,
					attempt_number: 1,
					version_number: 0,
					session_number: sessionNumber,
					scenario_prompt: childPrompt1,
					original_response: originalResponse1,
					initial_decision: 'not_applicable',
					concern_level: undefined, // Steps not reached
					strategies: [],
					custom_instructions: [],
					highlighted_texts: [], // Empty array - highlights remain in `selection` table
					refactored_response: undefined,
					is_final_version: false,
					decided_at: Date.now(),
					is_attention_check: isAttentionCheckScenario,
					attention_check_selected: false,
					attention_check_passed: false
				});
			} catch (e) {
				console.error('Failed to save skip decision', e);
			}

			// showInitialDecisionPane is now derived
		} else {
			// **NEW VALIDATION**: Require at least one highlight to continue
			if (highlightedTexts1.length === 0) {
				toast.error('Please highlight at least one concern to continue, or skip this scenario');
				return; // Cannot proceed without highlights
			}

			// User has highlighted at least one concern
			step1Completed = true;
			step1Completed = true; // Mark step 1 complete to move to step 2

			// Save highlights to `moderation_session` table (batch save as JSON array)
			// Note: Individual highlights were already saved to `selection` table via `saveSelection()`
			// This saves all highlights together for session state restoration
			try {
				const sessionId = `scenario_${selectedScenarioIndex}`;
				await saveModerationSession(localStorage.token, {
					session_id: sessionId,
					user_id: $user?.id || 'unknown',
					child_id: selectedChildId || 'unknown',
					scenario_index: selectedScenarioIndex,
					attempt_number: 1,
					version_number: 0,
					session_number: sessionNumber,
					scenario_prompt: childPrompt1,
					original_response: originalResponse1,
					initial_decision: undefined, // No decision yet, just saving highlights
					strategies: [],
					custom_instructions: [],
					highlighted_texts: highlightedTexts1.map((h) => ({ text: h.text })), // Save all highlights as JSON array to `moderation_session` table
					refactored_response: undefined,
					is_final_version: false,
					highlights_saved_at: Date.now(),
					is_attention_check: isAttentionCheckScenario,
					attention_check_selected: attentionCheckSelected,
					attention_check_passed: false
				});
				console.log('Highlights saved to moderation_session table successfully');
			} catch (e) {
				console.error('Failed to save highlights to moderation_session table (non-blocking):', e);
				// Don't throw - allow step to complete even if backend save fails
			}
		}
		saveCurrentScenarioState();
	}

	/**
	 * Step 2: Complete concern assessment (Assess) and mark scenario as complete.
	 *
	 * SIMPLIFIED FLOW: This is now the final step - marks scenario as complete.
	 * (Step 3 moderation has been commented out for the identification-only experiment)
	 *
	 * Saves to backend with version_number: 0 and is_final_version: true.
	 *
	 * Saves:
	 *   - concern_reason: User's explanation of concern level (to session_metadata.concern_reason)
	 *   - highlighted_texts: Preserves highlights from Step 1
	 *   - initial_decision: 'identification' (marks this as identification-only completion)
	 *   - is_final_version: true (marks scenario as complete)
	 *
	 * Marks scenario as complete and navigates to next scenario if available.
	 */
	async function completeStep2() {
		// Validate explanation field is filled
		if (!concernReason.trim()) {
			toast.error('Please explain why this content concerns you');
			return;
		}

		// Validate minimum length requirement
		if (concernReason.trim().length < 10) {
			toast.error('Please provide at least 10 characters in your explanation');
			return;
		}

		// Mark step 2 and step 3 as complete (simplified flow - no Step 3)
		step2Completed = true;
		step3Completed = true; // Mark step 3 complete since we're skipping moderation

		// Mark scenario as complete by setting confirmedVersionIndex
		// This triggers isScenarioCompleted() to return true
		confirmedVersionIndex = 0; // 0 indicates original/identification is confirmed

		// Save state to trigger sidebar reactive updates
		// This updates scenarioStates Map which triggers scenarioStatesUpdateTrigger
		// and scenarioCompletionStatuses reactive array to recompute
		saveCurrentScenarioState();

		// Call /complete endpoint for new assignment tracking system
		const state = scenarioStates.get(selectedScenarioIndex);
		if (state?.assignment_id && prompt !== CUSTOM_SCENARIO_PROMPT) {
			try {
				const completeResponse = await completeScenario(localStorage.token, {
					assignment_id: state.assignment_id
				});
				console.log(
					'✅ Called /complete endpoint for assignment:',
					state.assignment_id,
					'issue_any:',
					completeResponse.issue_any
				);
			} catch (e) {
				console.error('Failed to call /complete endpoint (non-blocking):', e);
				// Continue even if complete endpoint fails
			}
		}

		// Save identification completion to backend with is_final_version: true
		// Use try-catch to ensure errors don't prevent step completion
		try {
			const sessionId = `scenario_${selectedScenarioIndex}`;
			await saveModerationSession(localStorage.token, {
				session_id: sessionId,
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId || 'unknown',
				scenario_index: selectedScenarioIndex,
				attempt_number: 1,
				version_number: 0,
				session_number: sessionNumber,
				scenario_prompt: childPrompt1,
				original_response: originalResponse1,
				initial_decision: 'accept_original', // Simplified flow - identification only (uses accept_original as semantic match)
				concern_level: undefined, // No longer collected in Step 2
				concern_reason: concernReason.trim(),
				decided_at: Date.now(),
				strategies: [],
				custom_instructions: [],
				highlighted_texts: highlightedTexts1.map((h) => ({ text: h.text })),
				refactored_response: undefined,
				is_final_version: true, // Mark as final - scenario is complete
				is_attention_check: isAttentionCheckScenario,
				attention_check_selected: attentionCheckSelected,
				attention_check_passed: false
			});
			console.log('✅ Identification complete - scenario marked as final');
		} catch (e) {
			console.error('Failed to save identification completion (non-blocking):', e);
			// Don't throw - allow step to complete even if backend save fails
		}
	}

	// ============================================================================
	// STEP 3 FUNCTION - PRESERVED FOR DISABLED STEP 3 UI (identification-only experiment)
	// This function is only called by the Step 3 UI block which is disabled via {#if false && ...}
	// The function is kept uncommented to satisfy TypeScript type checking.
	// To fully disable: Comment out when Step 3 UI is removed entirely.
	// ============================================================================
	/**
	 * Step 3: Submit satisfaction check after version created.
	 * NOTE: This function is only used by the disabled Step 3 UI.
	 *
	 * Saves satisfaction level (1-5 Likert), reason, and next action to backend.
	 *
	 * @param {number} level - Satisfaction level (1-5 Likert scale)
	 * @param {string} reason - User's explanation
	 * @param {string} action - 'try_again' | 'move_on' (determined by satisfaction level: 1-3 = try_again, 4-5 = move_on)
	 */
	async function submitSatisfactionCheck(
		level: number,
		reason: string,
		action: 'try_again' | 'move_on'
	) {
		// Validate level is 1-5
		if (level < 1 || level > 5) {
			toast.error('Please select a satisfaction level between 1 and 5');
			return;
		}

		// Validate reason if level is 1-3 (dissatisfied)
		if (level <= 3 && !reason.trim()) {
			toast.error('Please explain why you are not satisfied');
			return;
		}

		// Set satisfaction state
		satisfactionLevel = level;
		satisfactionReason = reason.trim();
		nextAction = action;

		// Save to backend
		try {
			const stepData = getCurrentStepData();
			const sessionId = `scenario_${selectedScenarioIndex}`;
			const versionNumber = currentVersionIndex >= 0 ? currentVersionIndex + 1 : 1;

			await saveModerationSession(localStorage.token, {
				session_id: sessionId,
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId || 'unknown',
				scenario_index: selectedScenarioIndex,
				attempt_number: 1,
				version_number: versionNumber,
				session_number: sessionNumber,
				scenario_prompt: childPrompt1,
				original_response: originalResponse1,
				initial_decision: 'moderate',
				concern_level: stepData.concern_level,
				concern_reason: stepData.concern_reason || concernReason,
				satisfaction_level: level,
				satisfaction_reason: reason.trim(),
				next_action: action,
				decided_at: Date.now(),
				strategies:
					currentVersionIndex >= 0 && versions[currentVersionIndex]
						? versions[currentVersionIndex].strategies
						: [],
				custom_instructions:
					currentVersionIndex >= 0 && versions[currentVersionIndex]
						? versions[currentVersionIndex].customInstructions.map((c) => c.text)
						: [],
				highlighted_texts: highlightedTexts1.map((h) => ({ text: h.text })),
				refactored_response:
					currentVersionIndex >= 0 && versions[currentVersionIndex]
						? versions[currentVersionIndex].response
						: undefined,
				is_final_version: action === 'move_on', // Mark as final if moving on
				is_attention_check: isAttentionCheckScenario,
				attention_check_selected: attentionCheckSelected,
				attention_check_passed: false
			});

			console.log('✅ Satisfaction check saved to backend');

			// If moving on, confirm the version and mark scenario as complete
			if (action === 'move_on') {
				confirmedVersionIndex = currentVersionIndex;
				step3Completed = true;
				// UI visibility is now derived, no need to set directly
				saveCurrentScenarioState();
			}
		} catch (e) {
			console.error('Failed to save satisfaction check', e);
			toast.error('Failed to save your response. Please try again.');
		}

		saveCurrentScenarioState();
	}
	// END STEP 3 FUNCTION BLOCK

	// Removed old completeStep3() - Step 3 is now "Update" which uses submitSatisfactionCheck() after version creation

	// Navigate to a specific step (for back navigation)
	// SIMPLIFIED FLOW: Only Steps 1 and 2 are active (Step 3 is disabled for identification-only experiment)
	// Sets/unsets completion flags to control which step is shown (step is derived from flags)
	function navigateToStep(step: number) {
		// Type guard - only allow steps 1 or 2 (Step 3 is disabled)
		// Original: if (step !== 1 && step !== 2 && step !== 3) return;
		if (step !== 1 && step !== 2) return;

		// Set/unset completion flags to control which step is shown
		if (step === 1) {
			step1Completed = false; // Go back to step 1
			showOriginal1 = true; // Show original for highlighting
			moderationPanelVisible = false;
			showInitialDecisionPane = true; // Explicitly keep pane open
		} else if (step === 2) {
			// Go to step 2 - ensure step 1 is complete, unset step 2
			step1Completed = true;
			step2Completed = false;
			moderationPanelVisible = false;
			showInitialDecisionPane = true; // Explicitly keep pane open
		}
		// COMMENTED OUT - Step 3 navigation disabled for identification-only experiment
		// else if (step === 3) {
		// 	// Go to step 3 - ensure steps 1-2 are complete, unset step 3
		// 	step1Completed = true;
		// 	step2Completed = true;
		// 	step3Completed = false;
		// 	moderationPanelVisible = false;
		// 	showInitialDecisionPane = true; // Explicitly keep pane open
		// }
		saveCurrentScenarioState();
	}

	function returnToHighlighting() {
		// Navigate back to Step 1 to edit highlights
		moderationPanelVisible = false;
		showInitialDecisionPane = true;
		step1Completed = false; // Go back to step 1
		showOriginal1 = true;
		// Preserve versions - don't clear them
		saveCurrentScenarioState();
	}

	/**
	 * Mark scenario as not applicable (skip).
	 *
	 * Saves to backend with version_number: 0 (UPDATE existing row).
	 *
	 * Saves:
	 *   - initial_decision: 'not_applicable'
	 *   - concern_level: From Step 2 if completed before marking (using getCurrentStepData())
	 *   - highlighted_texts: Cleared (empty array)
	 *
	 * Marks scenario as completed and closes moderation panel.
	 */
	async function markNotApplicable() {
		// No blocking for attention check; allow normal flow
		markedNotApplicable = true;
		confirmedVersionIndex = -1; // Mark as decided
		moderationPanelVisible = false;
		highlightedTexts1 = []; // Clear highlights when skipping
		console.log('Mark not applicable - state:', { markedNotApplicable, confirmedVersionIndex });
		saveCurrentScenarioState(); // Save the decision
		toast.success('Scenario marked as not applicable');
		console.log('User marked scenario as not applicable:', selectedScenarioIndex);

		// Save complete session data
		try {
			const stepData = getCurrentStepData();
			const sessionId = `scenario_${selectedScenarioIndex}`;
			await saveModerationSession(localStorage.token, {
				session_id: sessionId,
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId || 'unknown',
				scenario_index: selectedScenarioIndex,
				attempt_number: 1,
				version_number: 0,
				session_number: sessionNumber,
				scenario_prompt: childPrompt1,
				original_response: originalResponse1,
				initial_decision: 'not_applicable',
				concern_level: stepData.concern_level,
				strategies: [],
				custom_instructions: [],
				highlighted_texts: [],
				refactored_response: undefined,
				is_final_version: false,
				decided_at: Date.now(),
				is_attention_check: isAttentionCheckScenario,
				attention_check_selected: attentionCheckSelected,
				attention_check_passed: false
			});
		} catch (e) {
			console.error('Failed to save moderation session', e);
		}
	}

	function unmarkNotApplicable() {
		markedNotApplicable = false;
		// Reset all step completion flags to reopen the modal
		step1Completed = false;
		step2Completed = false;
		step3Completed = false;
		// Removed step4Completed - now 3-step flow
		// Navigate back to Step 1 and reopen the modal
		step1Completed = false; // Reset to step 1
		showInitialDecisionPane = true;
		saveCurrentScenarioState();
		toast.info('Scenario unmarked - please make a decision');
		console.log('User unmarked scenario as not applicable:', selectedScenarioIndex);
	}

	/**
	 * Undo scenario completion (identification-only flow).
	 * Resets the scenario to allow editing the identification.
	 */
	function undoScenarioCompleted() {
		confirmedVersionIndex = null;
		step2Completed = false;
		step3Completed = false;
		// Navigate back to Step 2 to allow editing
		step1Completed = true; // Keep step 1 completed
		showInitialDecisionPane = true;
		saveCurrentScenarioState();
		toast.info('Scenario unmarked - you can edit your identification');
		console.log('User undid scenario completion:', selectedScenarioIndex);
	}

	function clearSelections() {
		selectedModerations.clear();
		customInstructions = []; // Clear custom instructions too
		attentionCheckSelected = false;
		selectedModerations = selectedModerations; // Trigger reactivity
	}

	/**
	 * Apply selected moderation strategies and create a new moderated version.
	 *
	 * Saves to backend by CREATING a NEW row with version_number: currentVersionIndex + 1.
	 * Each moderated version is a separate row, allowing version history tracking.
	 *
	 * Row operation: CREATE (new row for each version)
	 *
	 * Saves:
	 *   - version_number: currentVersionIndex + 1 (new version)
	 *   - initial_decision: 'moderate'
	 *   - concern_level: From Step 3 if completed (using getCurrentStepData())
	 *   - child_accomplish: From Step 2 if completed (to session_metadata)
	 *   - assistant_doing: From Step 2 if completed (to session_metadata)
	 *   - strategies: Array of selected moderation strategy names
	 *   - custom_instructions: Array of custom instruction texts
	 *   - highlighted_texts: Current highlights
	 *   - refactored_response: Generated moderated response text
	 *   - is_final_version: false (will be set to true when confirmed)
	 *
	 * Creates a new version in the versions array and updates UI to show comparison view.
	 */
	async function applySelectedModerations() {
		// Check if no strategies selected (attention check alone doesn't count for non-attention-check scenarios)
		if (selectedModerations.size === 0 && !attentionCheckSelected) {
			toast.error('Please select at least one moderation strategy');
			return;
		}

		// If only attention check is selected (and it's not an attention check scenario), require other strategies
		if (selectedModerations.size === 0 && attentionCheckSelected && !isAttentionCheckScenario) {
			toast.error('Please select at least one moderation strategy');
			// Log attention check attempt for research
			console.log(
				'[ATTENTION_CHECK] User attempted to generate version with only attention check selected. Scenario:',
				selectedScenarioIndex
			);
			return;
		}

		// Log if attention check is selected along with other strategies
		if (attentionCheckSelected) {
			console.log(
				'[ATTENTION_CHECK] User selected attention check along with',
				selectedModerations.size,
				'other strategies. Scenario:',
				selectedScenarioIndex
			);
		}

		console.log('Applying moderations:', Array.from(selectedModerations).join(', '));
		moderationLoading = true;

		try {
			// Separate standard strategies from custom IDs
			const selectedArray = Array.from(selectedModerations);
			const standardStrategies: string[] = [];
			const customTexts: string[] = [];

			selectedArray.forEach((selection) => {
				if (selection.startsWith('custom_')) {
					const custom = customInstructions.find((c) => c.id === selection);
					if (custom) {
						customTexts.push(custom.text);
					}
				} else {
					standardStrategies.push(selection);
				}
			});

			// Get child's age from the selected child profile
			const selectedChild = childProfiles.find((child) => child.id === selectedChildId);
			const childAge = selectedChild?.child_age || null;
			console.log('Applying moderation with child age:', childAge);

			// Call moderation API with request guard
			const requestId = ++currentRequestId;
			const scenarioAtRequest = selectedScenarioIndex;
			const result = await applyModeration(
				localStorage.token,
				standardStrategies,
				childPrompt1,
				customTexts,
				originalResponse1, // Pass original response for refactoring
				highlightedTexts1.map((h) => h.text), // Pass highlighted texts
				childAge // Pass child's age for age-appropriate moderation
			);

			// Drop responses that arrive after user switched scenarios
			if (result && requestId === currentRequestId && scenarioAtRequest === selectedScenarioIndex) {
				// Store custom instructions before clearing
				const usedCustomInstructions = customInstructions
					.filter((c) => selectedArray.includes(c.id))
					.map((c) => ({ ...c }));

				// Create new version
				const newVersion: ModerationVersion = {
					response: result.refactored_response,
					strategies: [...standardStrategies],
					customInstructions: usedCustomInstructions,
					highlightedTexts: [...highlightedTexts1],
					moderationResult: result
				};

				versions = [...versions, newVersion]; // Trigger reactivity
				currentVersionIndex = versions.length - 1;
				showOriginal1 = false; // Ensure we're viewing the new version
				showComparisonView = true; // Auto-show side-by-side comparison view
				moderationPanelVisible = false; // Hide moderation panel so review buttons show
				moderationPanelExpanded = false; // Collapse panel

				// Scroll to top to see the new moderated response
				if (mainContentContainer) {
					mainContentContainer.scrollTo({ top: 0, behavior: 'smooth' });
				}

				// Snapshot attention check flag BEFORE clearing selections
				const attentionSelectedSnapshot = attentionCheckSelected;

				const total = standardStrategies.length + customTexts.length;
				toast.success(
					`Created version ${versions.length} with ${total} moderation strateg${total === 1 ? 'y' : 'ies'}`
				);

				// Save complete session data with the new version (use snapshot)
				try {
					const stepData = getCurrentStepData();
					const sessionId = `scenario_${selectedScenarioIndex}`;
					await saveModerationSession(localStorage.token, {
						session_id: sessionId,
						user_id: $user?.id || 'unknown',
						child_id: selectedChildId || 'unknown',
						scenario_index: selectedScenarioIndex,
						attempt_number: 1,
						version_number: currentVersionIndex + 1,
						session_number: sessionNumber,
						scenario_prompt: childPrompt1,
						original_response: originalResponse1,
						initial_decision: 'moderate',
						concern_level: stepData.concern_level,
						strategies: [...standardStrategies],
						custom_instructions: usedCustomInstructions.map((c) => c.text), // Convert to string array
						highlighted_texts: highlightedTexts1.map((h) => ({ text: h.text })),
						refactored_response: result.refactored_response,
						is_final_version: false,
						decided_at: Date.now(),
						is_attention_check: isAttentionCheckScenario,
						attention_check_selected: attentionSelectedSnapshot,
						attention_check_passed:
							isAttentionCheckScenario &&
							attentionSelectedSnapshot &&
							(standardStrategies.length > 0 || customTexts.length > 0)
					});
				} catch (e) {
					console.error('Failed to save moderation session', e);
				}

				// Clear current selections for next iteration (after save)
				selectedModerations = new Set();
				customInstructions = [];
				attentionCheckSelected = false;
			} else {
				toast.error('Failed to apply moderation');
			}
		} catch (error: any) {
			console.error('Error applying moderation:', error);
			toast.error(`Error: ${error.message || 'Failed to apply moderation'}`);
		} finally {
			moderationLoading = false;
		}
	}

	function completeModeration() {
		// Save current scenario state
		saveCurrentScenarioState();

		// New rule: require a terminal decision for every scenario (including custom)
		let allCompleted = true;
		for (let i = 0; i < scenarioList.length; i++) {
			if (!isScenarioCompleted(i)) {
				allCompleted = false;
				break;
			}
		}
		if (!allCompleted) {
			toast.error('Please make a selection for every scenario before continuing');
			return;
		}

		// Show confirmation modal
		showConfirmationModal = true;
	}

	function proceedToNextStep() {
		// Update assignment step to 3 (exit survey)
		localStorage.setItem('assignmentStep', '3');
		localStorage.setItem('moderationScenariosAccessed', 'true');
		localStorage.setItem('unlock_exit', 'true');
		window.dispatchEvent(new Event('storage'));
		window.dispatchEvent(new Event('workflow-updated'));
		// Ask backend to mark latest per-scenario submission as final for this child/session
		try {
			finalizeModeration(localStorage.token, {
				child_id: selectedChildId,
				session_number: sessionNumber
			}).catch((e) => console.error('Finalize moderation failed:', e));
		} catch (e) {
			console.error('Finalize moderation error:', e);
		}
		goto('/exit-survey');
	}

	function continueModeration() {
		showConfirmationModal = false;
	}

	// Handler for profile updates - defined at component level for cleanup
	const handleProfileUpdate = async () => {
		console.log('🔄 Profile updated event received, reloading child profiles and scenarios...');
		await loadChildProfiles();

		// Reset all scenario states to start fresh
		resetAllScenarioStates();

		// Regenerate scenarios with updated characteristics
		await loadRandomScenarios();

		console.log('✅ Scenarios reloaded after profile update');
	};

	// =================================================================================================
	// COMPONENT INITIALIZATION ORDER DOCUMENTATION
	// =================================================================================================
	//
	// PURPOSE:
	// This `onMount` function handles asynchronous initialization that must happen after the component
	// has mounted and the DOM is ready. It coordinates the loading of child profiles, scenario generation,
	// state restoration, and timer/bootstrap logic.
	//
	// INITIALIZATION SEQUENCE:
	// ------------------------------------------------------------------------------------------------
	// 1. SIDEBAR SETUP (synchronous)
	//    - Close assignment steps sidebar
	//    - Initialize sidebar state based on screen size
	//    - Set up resize listener for responsive behavior
	//
	// 2. WARMUP CHECK (handled in reactive statement, NOT in onMount)
	//    - See WARMUP/LOAD INITIALIZATION FLOW DOCUMENTATION above
	//    - This is done synchronously via reactive statement to prevent UI flash
	//    - `onMount` only handles timer/bootstrap logic IF warmup is completed
	//
	// 3. SESSION NUMBER RESOLUTION (asynchronous)
	//    - If localStorage was cleared, query backend for max session number
	//    - Initialize new session number based on backend history
	//    - Ensures fresh session on cold start
	//
	// 4. ACTIVITY TRACKING (asynchronous)
	//    - Start tracking user activity time for current scenario
	//    - Only runs if child and session are established
	//
	// 5. NAVIGATION GUARD (synchronous check)
	//    - Verify user is at correct workflow step
	//    - Redirect to child profile page if not ready
	//
	// 6. CHILD PROFILE LOADING (asynchronous)
	//    - Load child profiles from backend (filtered by is_current: true)
	//    - Set selectedChildId based on current child or first available
	//    - Resolve session number after child profiles are loaded
	//
	// 7. SCENARIO GENERATION/FETCHING (asynchronous)
	//    - For Prolific users: Fetch available scenarios from backend
	//    - For regular users: Generate personality-based scenarios
	//    - Handle session change detection and state clearing
	//
	// 8. STATE RESTORATION (asynchronous)
	//    - Load saved states from backend (prioritized over localStorage)
	//    - Restore highlights, step completion, decisions, versions
	//    - Load first scenario to ensure UI is updated
	//
	// 9. TIMER/BOOTSTRAP (conditional, asynchronous)
	//    - Only if warmup is completed AND not showing warmup
	//    - Start timer for current scenario
	//    - Bootstrap scenario persistence in backend
	//
	// WHY CERTAIN OPERATIONS ARE SYNCHRONOUS VS ASYNCHRONOUS:
	// ------------------------------------------------------------------------------------------------
	// - SYNCHRONOUS (reactive statements, immediate checks):
	//   * Warmup visibility check - Must happen before template renders to prevent flash
	//   * Navigation guard - Must block before async operations start
	//   * Sidebar setup - UI state that should be set immediately
	//
	// - ASYNCHRONOUS (onMount, await):
	//   * Backend API calls - Network requests take time
	//   * State restoration - Depends on scenarios being loaded first
	//   * Timer/bootstrap - Only needed after everything else is ready
	//
	// THE ROLE OF REACTIVE STATEMENTS VS LIFECYCLE HOOKS:
	// ------------------------------------------------------------------------------------------------
	// - REACTIVE STATEMENTS ($:):
	//   * Execute when dependencies change
	//   * Run during render phase (synchronously)
	//   * Used for: Warmup visibility, state synchronization, computed values
	//   * Example: `$: if ($user?.id) { ... }` runs when `$user` changes
	//
	// - LIFECYCLE HOOKS (onMount, onDestroy):
	//   * Execute once at specific lifecycle points
	//   * Run after initial render (asynchronously)
	//   * Used for: API calls, event listeners, cleanup
	//   * Example: `onMount(async () => { ... })` runs after component mounts
	//
	// WARMUP VISIBILITY HANDLING:
	// ------------------------------------------------------------------------------------------------
	// Warmup visibility is handled in a reactive statement (NOT in onMount) because:
	// 1. It must be set before template renders to prevent flash
	// 2. It depends on `$user?.id` which may not be available immediately
	// 3. Reactive statement automatically re-runs when `$user` becomes available
	// 4. `onMount` only handles timer/bootstrap logic IF warmup is already completed
	//
	// =================================================================================================

	onMount(async () => {
		hasHydrated = true;
		// Close assignment steps sidebar by default (scenarios sidebar is controlled separately by sidebarOpen)
		showSidebar.set(false);

		// Check for admin access via user_id query parameter
		const adminUserId = $page.url.searchParams.get('user_id');
		let targetUserId = $user?.id;
		let isAdminView = false;

		if (adminUserId && $user?.role === 'admin') {
			// Admin is viewing another user's quiz
			isAdminView = true;
			targetUserId = adminUserId;
			console.log('Admin viewing quiz for user:', adminUserId);
		}

		try {
			// Initialize sidebar state based on screen size for mobile
			sidebarOpen = window.innerWidth >= 768;
			const onResize = () => {
				const shouldOpen = window.innerWidth >= 768;
				if (shouldOpen !== sidebarOpen) {
					sidebarOpen = shouldOpen;
				}
			};
			window.addEventListener('resize', onResize);
			onDestroy(() => window.removeEventListener('resize', onResize));
		} catch {}

		// Warmup completion check is now handled synchronously via reactive statement
		// to prevent flash where regular UI renders before tutorial check completes

		// Prepare available scenarios; fetch after child profile is known
		let availableScenarioIndices: number[] = [];

		// If localStorage was cleared, start a new session for this child based on backend history
		try {
			const childIdForSession = selectedChildId || childProfileSync.getCurrentChildId();
			if (childIdForSession) {
				const sessionKey = `moderationSessionNumber_${childIdForSession}`;
				const existing = localStorage.getItem(sessionKey);
				if (!existing) {
					const sessions = await getModerationSessions(localStorage.token, childIdForSession);
					const maxSession =
						Array.isArray(sessions) && sessions.length > 0
							? Math.max(...sessions.map((s: any) => Number(s.session_number || 0)))
							: 0;
					localStorage.setItem(sessionKey, String(maxSession + 1));
				}
			}
		} catch (e) {
			console.warn('Failed to ensure fresh session on cold start', e);
		}

		// Ensure activity tracking is running once we have child and (possibly) session established
		await startActivityTracking();

		// Custom scenario is added during scenario list building (buildScenarioList function)
		// No need to check for default scenarios anymore since we only use personality-based scenarios

		// Guard navigation if user tries to jump ahead
		const step = parseInt(localStorage.getItem('assignmentStep') || '0');
		if (step < 1) {
			goto('/kids/profile');
			return;
		}

		// Listen for profile updates to reload scenarios when characteristics change
		window.addEventListener('child-profiles-updated', handleProfileUpdate);

		// Load child profiles for personality-based scenario generation
		// (loadSavedStates will be called after scenarios are loaded in loadRandomScenarios)
		await loadChildProfiles();
		// Resolve session number after child profiles are loaded
		resolveSessionNumber();
		console.log('Resolved session number after loading child profiles:', sessionNumber);

		// Now that we know the selected child, fetch available scenarios for Prolific users
		try {
			const sessionInfo = await getCurrentSession(localStorage.token);
			if (sessionInfo.is_prolific_user && selectedChildId) {
				// Skip if we shouldn't repoll (locked and no change)
				let prospectiveSession = sessionNumber;
				try {
					const stored = localStorage.getItem(`moderationSessionNumber_${selectedChildId}`);
					if (stored && !Number.isNaN(Number(stored))) prospectiveSession = Number(stored);
				} catch {}
				if (!shouldRepollScenarios(selectedChildId, prospectiveSession)) {
					console.log('Repoll skipped: locked and no child/session change');
				} else {
					const fetchId = beginScenarioFetch();
					// Initialize tracked session IDs
					const currentSessionId = localStorage.getItem('prolificSessionId') || '';
					const urlSessionId = $page.url.searchParams.get('SESSION_ID') || '';
					trackedSessionId = currentSessionId;
					trackedUrlSessionId = urlSessionId;

					const lastLoadedSessionId = localStorage.getItem('lastLoadedModerationSessionId') || '';

					// If session changed since last load, wipe cached moderation state
					if (currentSessionId && currentSessionId !== lastLoadedSessionId) {
						resetAllScenarioStates();
						clearModerationLocalKeys();
						localStorage.setItem('lastLoadedModerationSessionId', currentSessionId);
					}

					const availableScenarios = await getAvailableScenarios(
						localStorage.token,
						selectedChildId
					);
					if (!isFetchCurrent(fetchId)) {
						console.log('Stale available scenarios response ignored');
						return;
					}
					availableScenarioIndices = availableScenarios.available_scenarios || [];
					// Prefer locally established session number (fresh session on cold start)
					try {
						const stored = localStorage.getItem(`moderationSessionNumber_${selectedChildId}`);
						if (stored && !Number.isNaN(Number(stored))) {
							sessionNumber = Number(stored);
						} else {
							sessionNumber = availableScenarios.session_number;
						}
					} catch {
						sessionNumber = availableScenarios.session_number;
					}
					console.log(
						'Prolific user - available scenarios (from backend):',
						availableScenarioIndices,
						'session:',
						sessionNumber
					);
					lastPolledChildId = selectedChildId;
					lastPolledSession = sessionNumber;
					endScenarioFetch(fetchId);
				}
			}
		} catch (error) {
			console.log('Not a Prolific user or error fetching scenarios:', error);
		}

		// Automatically generate personality-based scenarios if child profiles exist
		console.log('Child profiles loaded:', childProfiles.length);
		if (childProfiles.length > 0) {
			console.log('Generating personality-based scenarios...');
			console.log(
				'Before generation - scenarioList.length:',
				scenarioList.length,
				'selectedChildId:',
				selectedChildId,
				'usePersonalityScenarios:',
				usePersonalityScenarios,
				'scenariosLockedForSession:',
				scenariosLockedForSession
			);

			// On hard refresh, if scenarioList is empty, clear any stale locks
			if (scenarioList.length === 0 && scenariosLockedForSession) {
				console.warn(
					'Hard refresh detected: scenarioList is empty but lock is set. Clearing lock to allow regeneration...'
				);
				scenariosLockedForSession = false;
			}

			try {
				console.log('Calling loadRandomScenarios()...');
				await loadRandomScenarios();
				console.log('Random scenarios loaded. Current scenarioList length:', scenarioList.length);
				if (scenarioList.length === 0) {
					console.warn(
						'⚠️ WARNING: loadRandomScenarios() completed but scenarioList is still empty!'
					);
				}
			} catch (e) {
				console.error('❌ Error in loadRandomScenarios:', e);
			}

			// Safety check: Ensure scenarios were populated - always attempt regeneration if empty
			if (scenarioList.length === 0) {
				console.warn(
					'WARNING: scenarioList is empty after loadRandomScenarios(). Attempting to force generation...'
				);
				// Force regeneration by clearing locks
				scenariosLockedForSession = false;
				// Clear any scenario states that might be interfering
				const stateKey = selectedChildId
					? `moderationScenarioStates_${selectedChildId}`
					: 'moderationScenarioStates';
				console.log('Clearing scenario states key:', stateKey);
				localStorage.removeItem(stateKey);
				// Scenarios are now stored in backend, no localStorage cleanup needed
				// Try generating again
				try {
					await loadRandomScenarios();
					if (scenarioList.length === 0) {
						console.error(
							'ERROR: Failed to generate scenarios after retry. scenarioList is still empty.'
						);
						console.error('Debug info:', {
							selectedChildId,
							childProfilesLength: childProfiles.length,
							scenarioListLength: scenarioList.length
						});
					} else {
						console.log(
							'Successfully generated scenarios on retry. scenarioList length:',
							scenarioList.length
						);
					}
				} catch (e) {
					console.error('Error in retry loadRandomScenarios:', e);
				}
			}

			// Filter/top-up only if not locked by canonical package
			if (!scenariosLockedForSession) {
				// Target number of base scenarios (custom is added separately; attention check is embedded)
				const TARGET_SCENARIO_COUNT = 8;
				let finalIndices: number[] = [];
				if (availableScenarioIndices.length > 0) {
					finalIndices = [
						...new Set(availableScenarioIndices.filter((i) => Number.isInteger(i) && i >= 0))
					];
				}

				// Fetch completed scenario indices to avoid previously seen ones
				let completed: number[] = [];
				try {
					const fetchId2 = beginScenarioFetch();
					const resp = await fetch(`${WEBUI_API_BASE_URL}/workflow/completed-scenarios`, {
						method: 'GET',
						headers: {
							'Content-Type': 'application/json',
							...(localStorage.token ? { authorization: `Bearer ${localStorage.token}` } : {})
						}
					});
					if (resp.ok) {
						const data = await resp.json();
						if (isFetchCurrent(fetchId2)) {
							completed = Array.isArray(data?.completed_scenario_indices)
								? data.completed_scenario_indices
								: [];
						} else {
							console.log('Stale completed scenarios response ignored');
						}
					}
					if (isFetchCurrent(fetchId2)) {
						endScenarioFetch(fetchId2);
					}
				} catch (e) {
					// Non-fatal; fallback below
				}

				// Build unseen pool from current scenarioList (personality generated) removing seen and already picked
				const allIndices = Array.from({ length: scenarioList.length }, (_, i) => i).filter(
					(i) => i >= 0
				);
				const seenSet = new Set<number>(completed);
				const pickedSet = new Set<number>(finalIndices);
				const unseenPool = allIndices.filter((i) => !seenSet.has(i) && !pickedSet.has(i));

				// Top up to target count from unseenPool at random
				while (finalIndices.length < TARGET_SCENARIO_COUNT && unseenPool.length > 0) {
					const rand = Math.floor(Math.random() * unseenPool.length);
					const pick = unseenPool.splice(rand, 1)[0];
					finalIndices.push(pick);
				}

				// Map indices to scenarios
				if (finalIndices.length > 0) {
					const filteredScenarios = finalIndices
						.filter((index) => index < scenarioList.length)
						.map((index) => scenarioList[index])
						.filter(Boolean);

					// Ensure custom scenario is at the end if it was in original list
					const hasCustom = scenarioList.some(([q]) => q === CUSTOM_SCENARIO_PROMPT);
					if (hasCustom) {
						const customIdx = filteredScenarios.findIndex(([q]) => q === CUSTOM_SCENARIO_PROMPT);
						if (customIdx === -1) {
							// Custom not in filtered scenarios, add it
							filteredScenarios.push([CUSTOM_SCENARIO_PROMPT, CUSTOM_SCENARIO_PLACEHOLDER]);
						} else if (customIdx !== filteredScenarios.length - 1) {
							// Custom exists but not at end, move it
							const custom = filteredScenarios.splice(customIdx, 1)[0];
							filteredScenarios.push(custom);
						}
					}

					if (filteredScenarios.length > 0) {
						// Replace scenarios and reset in-memory UI state to avoid old responses
						if (!scenariosLockedForSession) {
							scenarioList = filteredScenarios;
						}
						resetAllScenarioStates();
						selectedScenarioIndex = 0;
						loadScenario(0, true);
						console.log(
							'Final scenarios for session (filled to target if needed):',
							scenarioList.length
						);
					}
				}
			}

			// If no scenarios were loaded from backend, show error
			if (!scenariosLockedForSession && scenarioList.length === 0) {
				console.error('ERROR: No scenarios available from backend API');
				toast.error(
					'Failed to load scenarios from backend. Please refresh the page or contact support if the issue persists.'
				);
			}
		} else {
			console.log('No child profiles found, using default scenarios');
		}

		// Load the current scenario state if it exists
		const savedState = scenarioStates.get(selectedScenarioIndex);
		if (savedState) {
			versions = [...savedState.versions];
			currentVersionIndex = savedState.currentVersionIndex;
			confirmedVersionIndex = savedState.confirmedVersionIndex;
			highlightedTexts1 = [...savedState.highlightedTexts1];
			selectedModerations = new Set(savedState.selectedModerations);
			customInstructions = [...savedState.customInstructions];
			showComparisonView = savedState.showComparisonView || false;
			attentionCheckSelected = savedState.attentionCheckSelected || false;
			attentionCheckPassed = savedState.attentionCheckPassed || false;
			markedNotApplicable = savedState.markedNotApplicable || false;

			// Restore unified initial decision flow state
			// Step is now derived from completion flags, restore those instead
			step1Completed = savedState.step1Completed || false;
			step2Completed = savedState.step2Completed || false;
			step3Completed = savedState.step3Completed || false;

			// Restore Step 2 data
			concernLevel = savedState.concernLevel ?? null;
			concernReason = savedState.concernReason || '';

			// Restore Step 3 data
			satisfactionLevel = savedState.satisfactionLevel ?? null;
			satisfactionReason = savedState.satisfactionReason || '';
			nextAction = savedState.nextAction || null;

			// If versions exist and not completed, ensure all steps are complete
			if (versions.length > 0 && !step3Completed) {
				step1Completed = true;
				step2Completed = true;
				// Keep step3Completed false so user can still interact with Step 3
				showComparisonView = true; // Show comparison view
				if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
					// Keep the saved currentVersionIndex
				} else {
					currentVersionIndex = versions.length - 1; // Default to latest version
				}
			}

			// UI visibility is now derived via reactive statements, no need to set here
		}
		// FIX: Removed extra closing brace that was causing syntax error "Expected ')' but found 'if'"
		// The onMount callback properly closes at line 3704 with });
		// This extra brace was prematurely closing the onMount callback, causing parser errors.

		// Warmup visibility is now handled synchronously via reactive statement
		// Only start timer if warmup is completed (bootstrap save removed to avoid NULL initial_decision)
		if (warmupCompleted && !showWarmup) {
			// Start timer for the current scenario only if not in warmup
			startTimer(selectedScenarioIndex);
			// Removed bootstrap save - records will be created when user makes actual decisions
			// (skip, confirm, etc.) to avoid creating NULL initial_decision records
		}

		// Mark initial mount as complete to enable session change detection
		isInitialMount = false;
	});

	onDestroy(() => {
		// Save current state before leaving
		saveCurrentScenarioState();
		// Clean up timer on component destroy
		stopTimer();
		// Cleanup abandonment timeout
		if (abandonmentTimeout) {
			clearTimeout(abandonmentTimeout);
			abandonmentTimeout = null;
		}
		// Remove event listener
		window.removeEventListener('child-profiles-updated', handleProfileUpdate);
	});

	// Reactive statements to save state when changes occur
	$: if (
		highlightedTexts1.length > 0 ||
		selectedModerations.size > 0 ||
		customInstructions.length > 0 ||
		markedNotApplicable ||
		step1Completed ||
		step2Completed ||
		step3Completed
	) {
		saveCurrentScenarioState();
	}

	// Warm-up tutorial functions
	async function completeWarmup() {
		try {
			const warmupKey = `moderationWarmupCompleted_${$user?.id}`;
			localStorage.setItem(warmupKey, 'true');
			warmupCompleted = true;
			showWarmup = false;
			warmupStep = 0;
			warmupConfirmed = false;
			toast.success('Tutorial complete! You are ready to moderate scenarios.');

			// Start the regular moderation flow
			startTimer(selectedScenarioIndex);
			// Removed bootstrap save - records will be created when user makes actual decisions
			// (skip, confirm, etc.) to avoid creating NULL initial_decision records
		} catch (e) {
			console.error('Error completing warmup', e);
		}
	}

	function skipWarmup() {
		completeWarmup();
	}

	function showTutorial() {
		showWarmup = true;
		warmupStep = 0;
		warmupSelectedStrategies = [];
		warmupModeratedResponse = '';
		warmupConfirmed = false;
		// Temporarily allow tutorial to show even if previously completed
		// We'll use a separate flag to track if user wants to see it again
	}

	async function generateWarmupResponse() {
		const warmupPrompt = 'Can you help me with my homework?';
		const warmupResponse =
			"Of course! I'd be happy to help you with your homework. What subject are you working on? If you tell me what you're studying, I can guide you through the problem or explain concepts to help you understand better.";

		try {
			moderationLoading = true;
			const result = await applyModeration(
				localStorage.token,
				warmupSelectedStrategies,
				warmupPrompt,
				[],
				warmupResponse,
				[],
				undefined
			);
			if (result) {
				warmupModeratedResponse = result.refactored_response || warmupResponse;
				warmupStep = 2; // Move to review step
			}
		} catch (error: any) {
			console.error('Error generating warmup response:', error);
			toast.error(`Error: ${error.message || 'Failed to generate response'}`);
		} finally {
			moderationLoading = false;
		}
	}

	function confirmWarmup() {
		if (!warmupModeratedResponse) {
			toast.error('Please generate a moderated response first');
			return;
		}
		warmupConfirmed = true;
		warmupStep = 3;
	}
</script>

<svelte:head>
	<title>Review Scenarios</title>
</svelte:head>

{#if showWarmup}
	<!-- Warm-up Tutorial -->
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] bg-gradient-to-br from-yellow-50 via-blue-50 to-purple-50 dark:from-yellow-900/20 dark:via-blue-900/20 dark:to-purple-900/20"
	>
		<div class="flex-1 flex flex-col items-center justify-center p-6">
			<div
				class="max-w-4xl w-full bg-white dark:bg-gray-800 rounded-xl shadow-2xl border-2 border-yellow-200 dark:border-yellow-800 p-8"
			>
				<!-- Header -->
				<div class="text-center mb-8">
					<div
						class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-yellow-400 to-blue-500 mb-4"
					>
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 10V3L4 14h7v7l9-11h-7z"
							/>
						</svg>
					</div>
					<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
						Welcome to Moderation Practice!
					</h1>
					<p class="text-lg text-gray-600 dark:text-gray-400">
						Learn how to moderate AI responses for children
					</p>
					<div class="flex justify-center items-center gap-2 mt-4">
						<span class="text-sm font-semibold text-gray-700 dark:text-gray-300"
							>Step {warmupStep + 1} of 4</span
						>
						<div class="flex gap-1">
							{#each [0, 1, 2, 3] as step}
								<div
									class="w-2 h-2 rounded-full {step === warmupStep
										? 'bg-blue-500'
										: step < warmupStep
											? 'bg-green-500'
											: 'bg-gray-300'}"
								></div>
							{/each}
						</div>
					</div>
				</div>

				{#if warmupStep === 0}
					<!-- Step 0: Introduction -->
					<div class="space-y-6">
						<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
							<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
								What is Moderation?
							</h2>
							<p class="text-gray-700 dark:text-gray-300 mb-4">
								As a parent, you'll review AI responses to your child's questions. Your job is to:
							</p>
							<ul class="space-y-2 text-gray-700 dark:text-gray-300">
								<li class="flex items-start">
									<span class="mr-2 text-green-500">✓</span>
									<span>Review each response for appropriateness</span>
								</li>
								<li class="flex items-start">
									<span class="mr-2 text-green-500">✓</span>
									<span>Select moderation strategies if needed</span>
								</li>
								<li class="flex items-start">
									<span class="mr-2 text-green-500">✓</span>
									<span>Generate and approve a moderated version</span>
								</li>
							</ul>
						</div>
						<button
							on:click={() => (warmupStep = 1)}
							class="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg"
						>
							Start Tutorial →
						</button>
					</div>
				{:else if warmupStep === 1}
					<!-- Step 1: Review and Select Strategies -->
					<div class="space-y-6">
						<div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
							<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
								Practice Scenario
							</h2>
							<div class="mb-4">
								<p class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2">
									Child's Question:
								</p>
								<p
									class="text-lg text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded p-4"
								>
									"Can you help me with my homework?"
								</p>
							</div>
							<div>
								<p class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2">
									AI Response:
								</p>
								<p
									class="text-base text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 rounded p-4"
								>
									Of course! I'd be happy to help you with your homework. What subject are you
									working on? If you tell me what you're studying, I can guide you through the
									problem or explain concepts to help you understand better.
								</p>
							</div>
						</div>

						<div
							class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-lg p-4 mb-6"
						>
							<p class="text-sm text-yellow-800 dark:text-yellow-200">
								💡 <strong>Tip:</strong> This response is already appropriate, but try selecting "Tailor
								to Age Group" to see how moderation works!
							</p>
						</div>

						<div>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
								Select a moderation strategy:
							</h3>
							<div class="grid grid-cols-2 gap-3">
								{#each ['Tailor to Age Group'] as strategy}
									<button
										on:click={() => {
											if (!warmupSelectedStrategies.includes(strategy)) {
												warmupSelectedStrategies = [...warmupSelectedStrategies, strategy];
											} else {
												warmupSelectedStrategies = warmupSelectedStrategies.filter(
													(s) => s !== strategy
												);
											}
										}}
										class="p-4 rounded-lg border-2 transition-all {warmupSelectedStrategies.includes(
											strategy
										)
											? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
											: 'border-gray-300 dark:border-gray-700 hover:border-blue-400'}"
									>
										<span class="text-sm font-medium text-gray-900 dark:text-white">{strategy}</span
										>
									</button>
								{/each}
							</div>
						</div>

						<div class="flex gap-3">
							<button
								on:click={() => (warmupStep = 0)}
								class="flex-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 font-semibold py-3 px-6 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
							>
								← Back
							</button>
							<button
								on:click={generateWarmupResponse}
								disabled={warmupSelectedStrategies.length === 0 || moderationLoading}
								class="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{moderationLoading ? 'Generating...' : 'Generate Response →'}
							</button>
						</div>
					</div>
				{:else if warmupStep === 2}
					<!-- Step 2: Review Generated Response -->
					<div class="space-y-6">
						<div
							class="bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 rounded-lg p-4"
						>
							<p class="text-sm font-semibold text-green-800 dark:text-green-200 mb-2">
								✓ Moderated Response Generated!
							</p>
							<p class="text-sm text-green-700 dark:text-green-300">
								Review the response below, then confirm to complete the tutorial.
							</p>
						</div>

						<div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-6">
							<p class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2">
								Moderated Response:
							</p>
							<p
								class="text-base text-gray-900 dark:text-white bg-white dark:bg-gray-800 rounded p-4"
							>
								{warmupModeratedResponse}
							</p>
						</div>

						<div class="flex gap-3">
							<button
								on:click={() => (warmupStep = 1)}
								class="flex-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 font-semibold py-3 px-6 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
							>
								← Back
							</button>
							<button
								on:click={confirmWarmup}
								class="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg"
							>
								Confirm Response ✓
							</button>
						</div>
					</div>
				{:else if warmupStep === 3}
					<!-- Step 3: Completion -->
					<div class="space-y-6 text-center">
						<div
							class="bg-gradient-to-br from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg p-8"
						>
							<div
								class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-500 mb-4"
							>
								<svg
									class="w-10 h-10 text-white"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									/>
								</svg>
							</div>
							<h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-3">
								Tutorial Complete!
							</h2>
							<p class="text-lg text-gray-700 dark:text-gray-300 mb-6">
								You're ready to start moderating real scenarios. Remember to review each response
								carefully and select appropriate strategies.
							</p>
							<button
								on:click={completeWarmup}
								class="bg-gradient-to-r from-green-600 to-blue-600 text-white font-semibold py-3 px-8 rounded-lg hover:from-green-700 hover:to-blue-700 transition-all shadow-lg text-lg"
							>
								Start Moderation →
							</button>
						</div>
					</div>
				{/if}

				<!-- Skip Tutorial Button -->
				{#if warmupStep < 3}
					<div class="mt-6 text-center">
						<button
							on:click={skipWarmup}
							class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 underline"
						>
							Skip Tutorial
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<!-- Regular Moderation UI -->
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav
			class="px-2.5 pt-1.5 pb-2 backdrop-blur-xl w-full drag-region bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800"
		>
			<div class="flex items-center">
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
					<button
						id="sidebar-toggle-button"
						class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<div class="m-auto self-center">
							<MenuLines />
						</div>
					</button>
				</div>

				<div class="flex w-full items-center justify-between">
					<div class="flex items-center">
						{#if !sidebarOpen}
							<button
								class="px-3 py-2 text-xs rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => {
									sidebarOpen = true;
								}}
								aria-label="Open scenarios">Scenarios</button
							>
						{:else}
							<div class="flex items-center text-xl font-semibold">Review Scenarios</div>
						{/if}
					</div>

					<!-- Controls -->
					<div class="flex items-center space-x-3 {!sidebarOpen ? 'max-md:hidden' : ''}">
						<!-- Help Button - HIDDEN -->
						<!-- Help button has been hidden for the time being -->
						<!--
				<button
					on:click={() => showHelpVideo = true}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
					aria-label="Show help video"
				>
					Help
				</button>
				-->
						<!-- Navigation Buttons -->
						<div class="flex items-center space-x-2">
							<!-- Previous Task Button -->
							<button
								on:click={() => goto('/kids/profile')}
								class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M15 19l-7-7 7-7"
									></path>
								</svg>
								<span>Previous Task</span>
							</button>

							<!-- Next Task Button -->
							{#if typeof window !== 'undefined' && parseInt(localStorage.getItem('assignmentStep') || '0') >= 3}
								<button
									on:click={() => goto('/exit-survey')}
									class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 bg-blue-500 hover:bg-blue-600 text-white"
								>
									<span>Next Task</span>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 5l7 7-7 7"
										></path>
									</svg>
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</nav>

		<div class="flex-1 flex bg-white dark:bg-gray-900 overflow-hidden">
			<!-- Left Sidebar: Scenario List -->
			<div
				class="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 flex flex-col bg-gray-50 dark:bg-gray-900 {sidebarOpen
					? 'md:flex'
					: 'hidden md:hidden'}"
			>
				<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 p-4">
					<div class="flex items-center justify-between">
						<h1 class="text-xl font-bold text-gray-900 dark:text-white">Scenarios</h1>
						<div class="flex items-center space-x-2">
							<!-- Tutorial Button - DISABLED -->
							<!-- Tutorial feature has been disabled -->
							<button
								class="text-xs px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800"
								on:click={() => {
									sidebarOpen = !sidebarOpen;
								}}
								aria-label="Toggle scenarios">{sidebarOpen ? 'Hide' : 'Show'}</button
							>
						</div>
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						{completionCount}
					</p>
				</div>

				<div class="flex-1 overflow-y-auto p-3 space-y-2">
					{#each scenarioList as [prompt, response], index}
						<button
							on:click={() => loadScenario(index)}
							class="w-full text-left p-3 rounded-lg border transition-all duration-200 {selectedScenarioIndex ===
							index
								? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500 dark:border-blue-600 shadow-sm'
								: scenarioCompletionStatuses[index]
									? 'bg-gray-100 dark:bg-gray-800/50 border-gray-300 dark:border-gray-700 opacity-60 hover:opacity-80'
									: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-sm'}"
						>
							<div class="flex items-start space-x-2">
								<div class="flex-shrink-0 relative">
									<div
										class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold {selectedScenarioIndex ===
										index
											? 'bg-blue-500 text-white'
											: prompt === CUSTOM_SCENARIO_PROMPT
												? 'bg-purple-500 text-white'
												: scenarioCompletionStatuses[index]
													? 'bg-gray-400 dark:bg-gray-600 text-gray-200 dark:text-gray-400'
													: 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}"
									>
										{#if prompt === CUSTOM_SCENARIO_PROMPT}
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 4v16m8-8H4"
												></path>
											</svg>
										{:else}
											{index + 1}
										{/if}
									</div>
								</div>

								<div class="flex-1 min-w-0">
									<p
										class="text-sm font-medium {scenarioCompletionStatuses[index]
											? 'text-gray-500 dark:text-gray-500'
											: prompt === CUSTOM_SCENARIO_PROMPT
												? 'text-purple-900 dark:text-purple-100'
												: 'text-gray-900 dark:text-white'} line-clamp-2 leading-tight"
									>
										{customScenarioGenerated &&
										prompt === CUSTOM_SCENARIO_PROMPT &&
										customScenarioPrompt
											? customScenarioPrompt
											: prompt}
									</p>
								</div>
							</div>

							<div class="mt-2 flex items-center justify-between">
								{#if selectedScenarioIndex === index}
									<div class="flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
										<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
											<path
												fill-rule="evenodd"
												d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
												clip-rule="evenodd"
											></path>
										</svg>
										<span>Currently viewing</span>
									</div>
								{:else if scenarioCompletionStatuses[index]}
									<!-- Use reactive array instead of isScenarioCompleted(index) function call
							     to ensure template updates when scenarioStates changes -->
									<div class="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-500">
										<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
											<path
												fill-rule="evenodd"
												d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
												clip-rule="evenodd"
											></path>
										</svg>
										<span>Completed</span>
									</div>
								{:else}
									<div></div>
								{/if}

								{#if scenarioTimers.has(index) && (scenarioTimers.get(index) || 0) > 0}
									<div class="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
										<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
											<path
												fill-rule="evenodd"
												d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
												clip-rule="evenodd"
											></path>
										</svg>
										<span>{formatTime(scenarioTimers.get(index) || 0)}</span>
									</div>
								{/if}
							</div>
						</button>
					{/each}
				</div>

				<!-- Removed bottom divider and reset area -->
			</div>

			<!-- Right Side: Chat Thread -->
			<div class="flex-1 flex flex-col">
				<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 p-4">
					<h1 class="text-xl font-bold text-gray-900 dark:text-white">Conversation Review</h1>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Please the conversation below, and answer the questions that follow.
					</p>
				</div>

				<div class="flex-1 overflow-y-auto p-6 space-y-4" bind:this={mainContentContainer}>
					<!-- Custom Scenario Input (only shown for custom scenario before generation) -->
					{#if isCustomScenario && !customScenarioGenerated}
						<div class="max-w-3xl mx-auto mt-2 space-y-6">
							<div
								class="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg p-8 border border-purple-200 dark:border-purple-800 shadow-lg"
							>
								<div class="flex items-start space-x-3 mb-6">
									<svg
										class="w-8 h-8 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-1"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
										></path>
									</svg>
									<div>
										<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
											Create Your Own Scenario
										</h3>
										<p class="text-sm text-gray-600 dark:text-gray-400">
											Enter a custom child prompt below and we'll generate an AI response for you to
											review and moderate.
										</p>
									</div>
								</div>

								<div class="space-y-4">
									<div>
										<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											Child's Question or Prompt
										</label>
										<textarea
											bind:value={customScenarioPrompt}
											placeholder={CUSTOM_SCENARIO_PLACEHOLDER}
											rows="6"
											minlength="10"
											class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none text-base"
										></textarea>
										<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
											💡 Tip: Write this from the perspective of a child asking a question or making
											a statement.
										</p>
									</div>

									<Tooltip
										content={(!customScenarioPrompt.trim() ||
											customScenarioPrompt.trim().length < 10) &&
										!customScenarioGenerating
											? 'Please enter at least 10 characters'
											: ''}
										placement="top"
										className="w-full"
									>
										<button
											on:click={generateCustomScenarioResponse}
											disabled={customScenarioGenerating ||
												!customScenarioPrompt.trim() ||
												customScenarioPrompt.trim().length < 10}
											class="w-full flex items-center justify-center space-x-2 px-6 py-4 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors duration-200 shadow-md hover:shadow-lg"
										>
											{#if customScenarioGenerating}
												<svg
													class="animate-spin h-5 w-5 text-white"
													fill="none"
													viewBox="0 0 24 24"
												>
													<circle
														class="opacity-25"
														cx="12"
														cy="12"
														r="10"
														stroke="currentColor"
														stroke-width="4"
													></circle>
													<path
														class="opacity-75"
														fill="currentColor"
														d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
													></path>
												</svg>
												<span>Generating Response...</span>
											{:else}
												<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M13 10V3L4 14h7v7l9-11h-7z"
													></path>
												</svg>
												<span>Generate AI Response</span>
											{/if}
										</button>
									</Tooltip>
								</div>
							</div>
						</div>
					{:else if !isCustomScenario || customScenarioGenerated}
						<!-- Child Prompt Bubble -->
						<div class="flex justify-end">
							<!-- 
						DRAG-TO-HIGHLIGHT UI: Child Prompt Bubble
						All three highlighting indicators must use identical conditions:
						1. cursor-text class: Visual cursor feedback
						2. title attribute: Hover tooltip
						3. Tooltip visibility: "← Drag to highlight" arrow indicator
						See DRAG-TO-HIGHLIGHT FEATURE DOCUMENTATION above for details.
					-->
							<div
								class="max-w-[80%] bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm relative select-text {isHighlightingEnabled
									? 'cursor-text hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all'
									: ''}"
								bind:this={promptContainer1}
								on:mouseup={handleTextSelection}
								title={isHighlightingEnabled ? 'Drag over text to highlight concerns' : ''}
							>
								{#if isHighlightingEnabled && highlightedTexts1.length === 0}
									<div
										class="absolute -top-6 right-0 text-xs text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 px-2 py-1 rounded shadow-sm border border-gray-200 dark:border-gray-700 pointer-events-none"
									>
										← Drag to highlight
									</div>
								{/if}
								<p class="text-sm whitespace-pre-wrap">{@html childPromptHTML}</p>
								<!-- Auto-highlight enabled: No button needed -->
							</div>
						</div>
					{/if}

					<!-- AI Response Bubble (hidden for custom scenario before generation) -->
					{#if !isCustomScenario || customScenarioGenerated}
						<!-- Side-by-Side Comparison View -->
						{#if showComparisonView && versions.length > 0 && currentVersionIndex >= 0 && currentVersionIndex < versions.length}
							<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
								<!-- Left Column: Original Response -->
								<div class="max-w-full">
									<div class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">
										Original Response
									</div>
									<div
										class="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm"
									>
										<div class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
											{@html getHighlightedHTML(originalResponse1, highlightedTexts1)}
										</div>
									</div>
								</div>

								<!-- Right Column: Moderated Response -->
								<div class="max-w-full">
									<div class="flex items-center justify-between mb-2">
										<div class="text-xs font-semibold text-gray-600 dark:text-gray-400">
											Moderated Version {currentVersionIndex + 1}
										</div>
										<!-- Version Navigation Controls -->
										{#if versions.length > 1}
											<div class="flex items-center space-x-1">
												<button
													on:click={() => navigateToVersion('prev')}
													disabled={currentVersionIndex <= 0 || confirmedVersionIndex !== null}
													class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
													title="Previous version"
												>
													<svg
														class="w-3 h-3"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M15 19l-7-7 7-7"
														></path>
													</svg>
												</button>

												<span class="text-xs font-medium text-gray-700 dark:text-gray-300">
													{confirmedVersionIndex !== null &&
													currentVersionIndex === confirmedVersionIndex
														? '✓ '
														: ''}
													{currentVersionIndex + 1}/{versions.length}
												</span>

												<button
													on:click={() => navigateToVersion('next')}
													disabled={currentVersionIndex >= versions.length - 1 ||
														confirmedVersionIndex !== null}
													class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
													title="Next version"
												>
													<svg
														class="w-3 h-3"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M9 5l7 7-7 7"
														></path>
													</svg>
												</button>
											</div>
										{/if}
									</div>
									<div
										class="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm"
									>
										<div class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
											{@html versions[currentVersionIndex].response}
										</div>

										<!-- Applied Strategies inside moderated version -->
										{#if versions[currentVersionIndex].strategies.length > 0 || versions[currentVersionIndex].customInstructions.length > 0}
											<div class="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
												<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
													Applied Strategies:
												</p>
												<div class="flex flex-wrap gap-1">
													{#each versions[currentVersionIndex].strategies as strategy}
														<span
															class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded"
														>
															{strategy}
														</span>
													{/each}
													{#each versions[currentVersionIndex].customInstructions as custom}
														<span
															class="inline-flex items-center px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200 rounded"
														>
															Custom: {custom.text}
														</span>
													{/each}
												</div>
											</div>
										{/if}
									</div>
								</div>
							</div>
						{:else}
							<!-- Single Response View -->
							<div class="flex justify-start">
								<!-- 
						DRAG-TO-HIGHLIGHT UI: AI Response Bubble
						All three highlighting indicators must use identical conditions:
						1. cursor-text class: Visual cursor feedback
						2. title attribute: Hover tooltip
						3. Tooltip visibility: "Drag to highlight →" arrow indicator
						See DRAG-TO-HIGHLIGHT FEATURE DOCUMENTATION above for details.
					-->
								<div
									bind:this={responseContainer1}
									on:mouseup={handleTextSelection}
									class="max-w-[80%] bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm relative select-text {isHighlightingEnabled
										? 'cursor-text hover:ring-2 hover:ring-gray-300 dark:hover:ring-gray-600 transition-all'
										: ''}"
									title={isHighlightingEnabled ? 'Drag over text to highlight concerns' : ''}
								>
									{#if isHighlightingEnabled && highlightedTexts1.length === 0}
										<div
											class="absolute -top-6 left-0 text-xs text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 px-2 py-1 rounded shadow-sm border border-gray-200 dark:border-gray-700 pointer-events-none"
										>
											Drag to highlight →
										</div>
									{/if}
									<div
										class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap response-text"
									>
										{@html response1HTML}
									</div>
									<!-- Auto-highlight enabled: No button needed -->

									<!-- Original Accepted Indicator -->
									{#if false}
										<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
											<div
												class="flex items-center justify-between px-3 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg"
											>
												<div class="flex items-center space-x-2">
													<svg
														class="w-4 h-4 text-green-600 dark:text-green-400"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
														></path>
													</svg>
													<span class="text-xs font-medium text-green-700 dark:text-green-300">
														Original response accepted as satisfactory
													</span>
												</div>
												<button
													on:click={unmarkSatisfaction}
													class="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
												>
													Undo
												</button>
											</div>
										</div>
									{/if}

									{#if highlightedTexts1.length > 0 && showOriginal1 && !markedNotApplicable}
										<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
											<div class="flex items-center justify-between mb-1">
												<p class="text-xs font-semibold text-gray-700 dark:text-gray-300">
													Highlighted Concerns ({highlightedTexts1.length}):
												</p>
												{#if moderationPanelVisible}
													<button
														on:click={returnToHighlighting}
														class="text-xs px-2 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
													>
														Change/Add Highlighted Text
													</button>
												{/if}
											</div>
											<div class="flex flex-wrap gap-1">
												{#each highlightedTexts1 as highlight}
													<button
														class="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-700 text-gray-800 dark:text-gray-100 rounded hover:bg-yellow-200 dark:hover:bg-yellow-600 transition-colors"
														on:click={() => removeHighlight(highlight)}
														title="Click to remove"
													>
														{highlight.text.length > 30
															? highlight.text.substring(0, 30) + '...'
															: highlight.text}
														<svg
															class="w-3 h-3 ml-1"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M6 18L18 6M6 6l12 12"
															></path>
														</svg>
													</button>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Applied Strategies Display (below response) -->
									{#if versions.length > 0 && !showOriginal1 && currentVersionIndex >= 0 && currentVersionIndex < versions.length}
										<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
											<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
												Applied Strategies:
											</p>
											<div class="flex flex-wrap gap-1">
												{#each versions[currentVersionIndex].strategies as strategy}
													<span
														class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded"
													>
														{strategy}
													</span>
												{/each}
												{#each versions[currentVersionIndex].customInstructions as custom}
													<span
														class="inline-flex items-center px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200 rounded"
													>
														Custom: {custom.text}
													</span>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							</div>
						{/if}
					{/if}

					<!-- Unified Initial Decision Pane -->
					<!-- SIMPLIFIED FLOW: Only Steps 1 and 2 are shown (Step 3 is disabled) -->
					{#if showInitialDecisionPane && !markedNotApplicable && initialDecisionStep >= 1 && initialDecisionStep <= 2 && (!isCustomScenario || customScenarioGenerated)}
						<div class="flex justify-center mt-6">
							<div class="w-full max-w-4xl px-4">
								<div
									class="p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg"
								>
									<!-- Step Indicators -->
									<!-- SIMPLIFIED FLOW: Only showing Steps 1 (Highlight) and 2 (Reflect) -->
									<!-- Step 3 (Moderate) has been removed for identification-only experiment -->
									<div class="flex items-center justify-between mb-6">
										{#each [1, 2] as step}
											{@const stepCompleted =
												(step === 1 && step1Completed) || (step === 2 && step2Completed)}
											{@const stepCurrent = step === initialDecisionStep}
											{@const stepLocked =
												(step > 1 && !step1Completed) || (step > 2 && !step2Completed)}
											<button
												on:click={() => navigateToStep(step)}
												disabled={stepLocked}
												class="flex items-center space-x-2 transition-all {stepCurrent
													? 'text-blue-600 dark:text-blue-400'
													: stepCompleted
														? 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
														: 'text-gray-300 dark:text-gray-600'} {stepLocked
													? 'cursor-not-allowed opacity-50'
													: 'cursor-pointer'}"
											>
												<div
													class="w-8 h-8 rounded-full border-2 flex items-center justify-center transition-all {stepCurrent
														? 'border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 scale-110'
														: stepCompleted
															? 'border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-700 hover:border-gray-500 dark:hover:border-gray-400'
															: 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'}"
												>
													{#if stepCompleted}
														<svg
															class="w-5 h-5 text-green-600 dark:text-green-400"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M5 13l4 4L19 7"
															></path>
														</svg>
													{:else}
														<span class="text-sm font-semibold">{step}</span>
													{/if}
												</div>
												<span class="text-sm font-medium hidden sm:inline">
													{step === 1 ? 'Highlight' : 'Reflect'}
												</span>
											</button>
											{#if step < 2}
												<div
													class="flex-1 h-0.5 mx-2 transition-colors {(step === 1 &&
														step1Completed) ||
													(step === 2 && step2Completed)
														? 'bg-gray-400 dark:bg-gray-500'
														: 'bg-gray-200 dark:bg-gray-700'}"
												></div>
											{/if}
										{/each}
									</div>

									<!-- Step 1: Highlighting or Skip -->
									{#if initialDecisionStep === 1}
										<div class="space-y-4">
											<div>
												<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">
													Step 1: Highlight the content that concerns you
												</h3>

												{#if highlightedTexts1.length > 0}
													<div
														class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800"
													>
														<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
															✓ {highlightedTexts1.length} section{highlightedTexts1.length === 1
																? ''
																: 's'} highlighted
														</p>
														<div class="flex flex-wrap gap-2">
															{#each highlightedTexts1 as highlight}
																<button
																	class="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-700 text-gray-800 dark:text-gray-100 rounded hover:bg-yellow-200 dark:hover:bg-yellow-600 transition-colors"
																	on:click={() => removeHighlight(highlight)}
																	title="Click to remove"
																>
																	{highlight.text.length > 40
																		? highlight.text.substring(0, 40) + '...'
																		: highlight.text}
																	<svg
																		class="w-3 h-3 ml-1"
																		fill="none"
																		stroke="currentColor"
																		viewBox="0 0 24 24"
																	>
																		<path
																			stroke-linecap="round"
																			stroke-linejoin="round"
																			stroke-width="2"
																			d="M6 18L18 6M6 6l12 12"
																		></path>
																	</svg>
																</button>
															{/each}
														</div>
														<p class="text-xs text-gray-600 dark:text-gray-400 mt-2">
															Drag over more text to add highlights, or click "Continue" when done.
														</p>
													</div>
												{:else}
													<div
														class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800"
													>
														<p class="text-xs text-yellow-800 dark:text-yellow-200">
															⚠️ Drag over text in the response above to highlight concerns. If this
															scenario is not relevant, click "Skip Scenario".
														</p>
													</div>
												{/if}
											</div>

											<!-- Action buttons - Continue disabled when no highlights, only Skip enabled -->
											<div
												class="flex space-x-3 pt-2 border-t border-gray-200 dark:border-gray-700"
											>
												<button
													on:click={() => completeStep1(false)}
													disabled={highlightedTexts1.length === 0}
													class="flex-1 px-6 py-3 {highlightedTexts1.length > 0
														? 'bg-green-500 hover:bg-green-600 text-white'
														: 'bg-gray-400 text-white cursor-not-allowed opacity-50'} font-medium rounded-lg transition-colors flex items-center justify-center space-x-2 disabled:cursor-not-allowed"
												>
													<span>Continue</span>
													{#if highlightedTexts1.length === 0}
														<span class="text-xs opacity-75">(highlight required)</span>
													{/if}
												</button>
												<button
													on:click={() => completeStep1(true)}
													class="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
												>
													Skip Scenario
												</button>
											</div>
										</div>
									{/if}

									<!-- Step 2: Assess -->
									{#if initialDecisionStep === 2}
										<div class="space-y-4">
											<div>
												<div class="flex items-center justify-between mb-2">
													<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
														Step 2: Explain why this content concerns you
													</h3>
													<button
														on:click={() => navigateToStep(1)}
														class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center justify-center space-x-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-gray-200"
													>
														<svg
															class="w-3 h-3 flex-shrink-0"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M10 19l-7-7m0 0l7-7m-7 7h18"
															></path>
														</svg>
														<span>Back</span>
													</button>
												</div>
											</div>

											<!-- Explanation field -->
											<div class="space-y-4">
												<div>
													<label
														class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
													>
														Explain why this content concerns you <span class="text-red-500">*</span
														>
													</label>
													<textarea
														bind:value={concernReason}
														placeholder="Explain why this content concerns you... (minimum 10 characters)"
														rows="5"
														minlength="10"
														class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 resize-none"
													></textarea>
												</div>
											</div>

											<div>
												<button
													on:click={completeStep2}
													disabled={!concernReason.trim() || concernReason.trim().length < 10}
													class="w-full px-6 py-3 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
												>
													Submit
												</button>
											</div>
										</div>
									{/if}

									<!-- ============================================================================
						     STEP 3 (MODERATION) - COMMENTED OUT FOR IDENTIFICATION-ONLY EXPERIMENT
						     This entire block is disabled but preserved for future restoration.
						     To restore: Change `{#if false && initialDecisionStep === 3}` back to `{#if initialDecisionStep === 3}`
						     ============================================================================ -->
									<!-- Step 3: Update -->
									{#if false && initialDecisionStep === 3}
										<div class="space-y-4">
											<div>
												<div class="flex items-center justify-between mb-2">
													<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
														Step 3: Moderate
													</h3>
													<button
														on:click={() => navigateToStep(2)}
														disabled={moderationLoading}
														class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center justify-center space-x-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-gray-200 disabled:opacity-50"
													>
														<svg
															class="w-3 h-3 flex-shrink-0"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M10 19l-7-7m0 0l7-7m-7 7h18"
															></path>
														</svg>
														<span>Back</span>
													</button>
												</div>
												{#if versions.length > 0 && showComparisonView}
													<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
														Review the moderated version above. You can confirm it or try different
														strategies.
													</p>
												{:else}
													<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
														How would you like to moderate the content?
													</p>
												{/if}
											</div>

											<!-- Step 3: Satisfaction Check UI (unified panel - always shown when versions exist) -->
											{#if versions.length > 0 && showComparisonView && !moderationPanelVisible}
												<div
													class="space-y-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
												>
													<h4 class="text-base font-semibold text-gray-900 dark:text-white mb-3">
														How satisfied are you with the updated response?
													</h4>

													<!-- Satisfaction Likert Scale (1-5) - Required -->
													<div class="space-y-2">
														<label
															class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
														>
															Satisfaction Level <span class="text-red-500">*</span>
														</label>
														{#each [1, 2, 3, 4, 5] as level}
															<label
																class="flex items-center p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors {satisfactionLevel ===
																level
																	? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500'
																	: ''}"
															>
																<input
																	type="radio"
																	name="satisfactionLevel"
																	value={level}
																	bind:group={satisfactionLevel}
																	class="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
																/>
																<span class="ml-3 text-sm text-gray-700 dark:text-gray-300">
																	{level === 1
																		? '1 - Very Dissatisfied'
																		: level === 2
																			? '2 - Dissatisfied'
																			: level === 3
																				? '3 - Neutral'
																				: level === 4
																					? '4 - Satisfied'
																					: '5 - Very Satisfied'}
																</span>
															</label>
														{/each}
													</div>

													<!-- Why field - Always shown, required (minimum 10 characters) -->
													<div>
														<label
															class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
														>
															Why? <span class="text-red-500">*</span>
														</label>
														<textarea
															bind:value={satisfactionReason}
															placeholder="Explain your satisfaction level... (minimum 10 characters)"
															rows="3"
															minlength="10"
															class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 resize-none"
														></textarea>
													</div>

													<!-- Navigation Buttons -->
													<div
														class="flex space-x-3 pt-2 border-t border-gray-200 dark:border-gray-700"
													>
														<!-- Moderate Again Button -->
														<button
															on:click={async () => {
																// Validate satisfaction level is set
																if (satisfactionLevel === null) {
																	toast.error('Please select a satisfaction level');
																	return;
																}

																// Validate reason is filled and meets minimum length
																if (!satisfactionReason.trim()) {
																	toast.error('Please explain your satisfaction level');
																	return;
																}

																if (satisfactionReason.trim().length < 10) {
																	toast.error(
																		'Please provide at least 10 characters in your explanation'
																	);
																	return;
																}

																try {
																	// Save satisfaction check to backend
																	await submitSatisfactionCheck(
																		satisfactionLevel,
																		satisfactionReason,
																		'try_again'
																	);

																	// Reset satisfaction state to allow creating new version
																	satisfactionLevel = null;
																	satisfactionReason = '';
																	nextAction = null;

																	// Clear selected moderations to start fresh
																	selectedModerations = new Set();
																	customInstructions = [];

																	// Show moderation panel for another iteration
																	moderationPanelVisible = true;
																	moderationPanelExpanded = true;
																	toast.info(
																		'Select moderation strategies to create another version'
																	);

																	// Scroll to moderation panel after it opens
																	setTimeout(() => {
																		if (moderationPanelElement) {
																			moderationPanelElement.scrollIntoView({
																				behavior: 'smooth',
																				block: 'start'
																			});
																		}
																	}, 100);
																} catch (error) {
																	console.error('Failed to save satisfaction check:', error);
																	toast.error('Failed to save your response. Please try again.');
																}
															}}
															disabled={satisfactionLevel === null ||
																!satisfactionReason.trim() ||
																satisfactionReason.trim().length < 10}
															class="flex-1 px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
														>
															Moderate Again
														</button>

														<!-- Continue to next scenario Button -->
														<button
															on:click={async () => {
																// Validate satisfaction level is set
																if (satisfactionLevel === null) {
																	toast.error('Please select a satisfaction level');
																	return;
																}

																// Validate reason is filled and meets minimum length
																if (!satisfactionReason.trim()) {
																	toast.error('Please explain your satisfaction level');
																	return;
																}

																if (satisfactionReason.trim().length < 10) {
																	toast.error(
																		'Please provide at least 10 characters in your explanation'
																	);
																	return;
																}

																try {
																	// Save satisfaction check to backend (this already handles navigation)
																	await submitSatisfactionCheck(
																		satisfactionLevel,
																		satisfactionReason,
																		'move_on'
																	);
																	// submitSatisfactionCheck already handles confirmCurrentVersion() and navigation (lines 2590-2603)
																} catch (error) {
																	console.error('Failed to save satisfaction check:', error);
																	toast.error('Failed to save your response. Please try again.');
																}
															}}
															disabled={satisfactionLevel === null ||
																!satisfactionReason.trim() ||
																satisfactionReason.trim().length < 10}
															class="flex-1 px-6 py-3 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
														>
															Continue to next scenario
														</button>
													</div>
												</div>
											{:else}
												<!-- Strategy instruction and Clear button -->
												<div class="flex items-center justify-between mb-3">
													<p class="text-sm text-gray-600 dark:text-gray-400">
														Choose up to <b>3 strategies</b> to improve the AI's response.
													</p>
													{#if selectedModerations.size > 0 || attentionCheckSelected}
														<button
															on:click={clearSelections}
															class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
														>
															Clear All
														</button>
													{/if}
												</div>

												<!-- Grouped Strategy Options (Legacy validated design) -->
												<div class="space-y-3 mb-4" bind:this={moderationPanelElement}>
													{#each Object.entries(moderationOptions) as [category, options]}
														<div
															class="border-2 {category === 'Refuse and Remove'
																? 'border-red-500 dark:border-red-600'
																: category === 'Investigate and Empathize'
																	? 'border-blue-500 dark:border-blue-600'
																	: category === 'Correct their Understanding'
																		? 'border-green-500 dark:border-green-600'
																		: category === 'Match their Age'
																			? 'border-yellow-500 dark:border-yellow-600'
																			: category === 'Defer to Support'
																				? 'border-purple-500 dark:border-purple-600'
																				: 'border-pink-500 dark:border-pink-600'} rounded-lg bg-gray-50 dark:bg-gray-800/50"
														>
															<!-- Group Header -->
															<button
																on:click={() => toggleGroupExpansion(category)}
																class="w-full p-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors rounded-lg"
															>
																<div class="flex items-center justify-between">
																	<div class="flex items-center">
																		<span
																			class="w-3 h-3 rounded-full mr-3 {category ===
																			'Refuse and Remove'
																				? 'bg-red-500'
																				: category === 'Investigate and Empathize'
																					? 'bg-blue-500'
																					: category === 'Correct their Understanding'
																						? 'bg-green-500'
																						: category === 'Match their Age'
																							? 'bg-yellow-500'
																							: category === 'Defer to Support'
																								? 'bg-purple-500'
																								: 'bg-pink-500'}"
																		></span>
																		<h4 class="text-sm font-bold text-gray-900 dark:text-white">
																			{category === 'Custom' && showCustomInput
																				? '✨ Custom (Open)'
																				: category}
																		</h4>
																	</div>
																	<div class="flex items-center space-x-2">
																		{#if (category === 'Attention Check' && attentionCheckSelected) || options.some( (option) => selectedModerations.has(option) ) || (category === 'Custom' && customInstructions.length > 0)}
																			<span
																				class="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-full"
																			>
																				{#if category === 'Custom'}
																					{customInstructions.filter((c) =>
																						selectedModerations.has(c.id)
																					).length} selected
																				{:else if category === 'Attention Check'}
																					{attentionCheckSelected ? 1 : 0} selected
																				{:else}
																					{options.filter((option) =>
																						selectedModerations.has(option)
																					).length} selected
																				{/if}
																			</span>
																		{/if}
																		{#if category !== 'Custom' || !showCustomInput}
																			<svg
																				class="w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform {expandedGroups.has(
																					category
																				) ||
																				(category === 'Custom' && showCustomInput)
																					? 'rotate-180'
																					: ''}"
																				fill="none"
																				stroke="currentColor"
																				viewBox="0 0 24 24"
																			>
																				<path
																					stroke-linecap="round"
																					stroke-linejoin="round"
																					stroke-width="2"
																					d="M19 9l-7 7-7-7"
																				></path>
																			</svg>
																		{:else}
																			<svg
																				class="w-5 h-5 text-purple-500 dark:text-purple-400 transition-transform rotate-180"
																				fill="none"
																				stroke="currentColor"
																				viewBox="0 0 24 24"
																			>
																				<path
																					stroke-linecap="round"
																					stroke-linejoin="round"
																					stroke-width="2"
																					d="M19 9l-7 7-7-7"
																				></path>
																			</svg>
																		{/if}
																	</div>
																</div>
															</button>

															<!-- Group Content (2-column grid with button toggles) -->
															{#if expandedGroups.has(category) && category !== 'Custom'}
																<div class="px-3 pb-3">
																	<div class="grid grid-cols-2 gap-2">
																		{#each options as option}
																			<Tooltip
																				content={moderationTooltips[option] || ''}
																				placement="top-end"
																				className="w-full"
																				tippyOptions={{ delay: [200, 0] }}
																			>
																				<button
																					on:click={() => toggleModerationSelection(option)}
																					disabled={moderationLoading}
																					aria-pressed={option === 'I read the instructions'
																						? attentionCheckSelected
																						: selectedModerations.has(option)}
																					class="p-2 text-xs font-medium text-center rounded-lg transition-all min-h-[40px] flex items-center justify-center {(
																						option === 'I read the instructions'
																							? attentionCheckSelected
																							: selectedModerations.has(option)
																					)
																						? 'bg-blue-500 text-white hover:bg-blue-600 ring-2 ring-blue-400 shadow-lg'
																						: 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600'} disabled:opacity-50"
																				>
																					{option}
																				</button>
																			</Tooltip>
																		{/each}
																	</div>
																</div>
															{/if}

															<!-- Custom Input Field -->
															{#if category === 'Custom' && showCustomInput}
																<div class="px-3 pb-3 pt-2">
																	<div class="space-y-2">
																		<label
																			class="block text-xs font-medium text-purple-900 dark:text-purple-200"
																		>
																			Enter custom moderation instruction:
																		</label>
																		<textarea
																			bind:value={customInstructionInput}
																			rows="2"
																			placeholder="E.g., Emphasize problem-solving skills..."
																			class="w-full px-3 py-2 text-sm border border-purple-300 dark:border-purple-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
																			on:keydown={(e) => {
																				if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
																					addCustomInstruction();
																				} else if (e.key === 'Escape') {
																					cancelCustomInput();
																				}
																			}}
																		></textarea>
																		<div class="flex justify-end space-x-2">
																			<button
																				on:click={cancelCustomInput}
																				class="px-3 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
																			>
																				Cancel
																			</button>
																			<button
																				on:click={addCustomInstruction}
																				class="px-3 py-1 text-xs font-medium bg-purple-500 hover:bg-purple-600 text-white rounded transition-colors"
																			>
																				Add
																			</button>
																		</div>
																	</div>
																</div>
															{/if}
														</div>
													{/each}
												</div>

												<!-- Custom Instructions Display -->
												{#if customInstructions.length > 0}
													<div
														class="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg mb-3"
													>
														<h4
															class="text-xs font-semibold text-purple-900 dark:text-purple-200 mb-2"
														>
															Custom Instructions ({customInstructions.length}):
														</h4>
														<div class="space-y-2">
															{#each customInstructions as custom}
																<div
																	class="flex items-start justify-between bg-white dark:bg-purple-900/30 p-2 rounded border-2 {selectedModerations.has(
																		custom.id
																	)
																		? 'border-purple-500'
																		: 'border-transparent'}"
																>
																	<button
																		on:click={() => toggleModerationSelection(custom.id)}
																		class="flex-1 text-left mr-2"
																	>
																		<div class="flex items-center space-x-1 mb-1">
																			<div
																				class="w-3 h-3 rounded border-2 {selectedModerations.has(
																					custom.id
																				)
																					? 'bg-purple-500 border-purple-500'
																					: 'border-gray-300 dark:border-gray-600'} flex items-center justify-center"
																			>
																				{#if selectedModerations.has(custom.id)}
																					<svg
																						class="w-2 h-2 text-white"
																						fill="none"
																						stroke="currentColor"
																						viewBox="0 0 24 24"
																					>
																						<path
																							stroke-linecap="round"
																							stroke-linejoin="round"
																							stroke-width="3"
																							d="M5 13l4 4L19 7"
																						></path>
																					</svg>
																				{/if}
																			</div>
																			<p
																				class="text-xs text-purple-800 dark:text-purple-200 font-medium"
																			>
																				#{customInstructions.indexOf(custom) + 1}
																			</p>
																		</div>
																		<p
																			class="text-xs text-gray-700 dark:text-gray-300 line-clamp-2"
																		>
																			{custom.text}
																		</p>
																	</button>
																	<button
																		on:click={() => removeCustomInstruction(custom.id)}
																		class="text-red-500 hover:text-red-700 dark:text-red-400 flex-shrink-0"
																		title="Remove"
																	>
																		<svg
																			class="w-3 h-3"
																			fill="none"
																			stroke="currentColor"
																			viewBox="0 0 24 24"
																		>
																			<path
																				stroke-linecap="round"
																				stroke-linejoin="round"
																				stroke-width="2"
																				d="M6 18L18 6M6 6l12 12"
																			></path>
																		</svg>
																	</button>
																</div>
															{/each}
														</div>
													</div>
												{/if}

												<!-- Action Buttons -->
												<div class="flex space-x-3">
													<button
														on:click={applySelectedModerations}
														disabled={moderationLoading ||
															(selectedModerations.size === 0 && !attentionCheckSelected) ||
															attentionCheckProcessing}
														class="flex-1 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2"
													>
														{#if moderationLoading}
															<div
																class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
															></div>
															<span>Creating Version...</span>
														{:else}
															<span>Generate New Version</span>
														{/if}
													</button>
												</div>
											{/if}
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/if}

					<!-- Completion Indicator for identification-only flow (shows after Submit) -->
					{#if confirmedVersionIndex === 0 && versions.length === 0}
						<div class="mt-3">
							<div
								class="flex items-center justify-between px-3 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800"
							>
								<div class="flex items-center space-x-2">
									<svg
										class="w-4 h-4 text-green-600 dark:text-green-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
										></path>
									</svg>
									<span class="text-xs font-medium text-green-700 dark:text-green-300">
										Scenario Completed
									</span>
								</div>
								<button
									on:click={undoScenarioCompleted}
									class="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
								>
									Undo
								</button>
							</div>
						</div>
					{/if}

					<!-- Not Applicable Indicator (moved from response bubble) -->
					{#if markedNotApplicable}
						<div class="mt-3">
							<div
								class="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg"
							>
								<div class="flex items-center space-x-2">
									<svg
										class="w-4 h-4 text-gray-600 dark:text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
										></path>
									</svg>
									<span class="text-xs font-medium text-gray-700 dark:text-gray-300">
										Marked as not applicable
									</span>
								</div>
								<button
									on:click={unmarkNotApplicable}
									class="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
								>
									Undo
								</button>
							</div>
						</div>
					{/if}

					<!-- Confirmation Indicator moved below the response area -->
					{#if versions.length > 0 && !showOriginal1 && confirmedVersionIndex !== null}
						{#if confirmedVersionIndex === currentVersionIndex}
							<div class="mt-3">
								<div
									class="flex items-center justify-between px-3 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800"
								>
									<div class="flex items-center space-x-2">
										<svg
											class="w-4 h-4 text-green-600 dark:text-green-400"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
											></path>
										</svg>
										<span class="text-xs font-medium text-green-700 dark:text-green-300">
											Scenario Moderated
										</span>
									</div>
									<button
										on:click={() => {
											confirmCurrentVersion();
											// Confirmation will be saved in the session data
										}}
										class="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
									>
										Edit Moderation
									</button>
								</div>
							</div>
						{:else}
							<div class="mt-3">
								<div
									class="flex items-center justify-between px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg"
								>
									<span class="text-xs font-medium text-gray-600 dark:text-gray-400">
										Another version is confirmed
									</span>
									<button
										on:click={() => {
											confirmCurrentVersion(); // Unconfirm to go back
										}}
										class="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
									>
										Back
									</button>
								</div>
							</div>
						{/if}
					{/if}

					<!-- Moderation Panel (Legacy - only shown when not in Step 4) -->
					{#if moderationPanelVisible && initialDecisionStep !== 3}
						<div
							class="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
							bind:this={moderationPanelElement}
						>
							<div class="flex items-center justify-between mb-1">
								<h3 class="text-sm font-semibold text-gray-900 dark:text-white">
									Select Moderation Strategies
								</h3>
								<button
									on:click={() => navigateToStep(3)}
									disabled={moderationLoading}
									class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center justify-center space-x-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-gray-200 disabled:opacity-50"
								>
									<svg
										class="w-3 h-3 flex-shrink-0"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M10 19l-7-7m0 0l7-7m-7 7h18"
										></path>
									</svg>
									<span>Back</span>
								</button>
							</div>

							<p class="text-base text-gray-600 dark:text-gray-400 mb-3">
								Choose up to <b>3 strategies</b> to improve the AI's response. Click on a group to see
								its strategies, or hover over each option for details.
							</p>

							<!-- Strategy Count -->
							<div class="flex items-center justify-end mb-3">
								{#if selectedModerations.size > 0 || attentionCheckSelected}
									<button
										on:click={clearSelections}
										class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
									>
										Clear All
									</button>
								{/if}
							</div>

							<!-- Grouped Strategy Options -->
							<div class="space-y-4 mb-4">
								{#each Object.entries(moderationOptions) as [category, options]}
									<div
										class="border-2 {category === 'Refuse and Remove'
											? 'border-red-500 dark:border-red-600'
											: category === 'Investigate and Empathize'
												? 'border-blue-500 dark:border-blue-600'
												: category === 'Correct their Understanding'
													? 'border-green-500 dark:border-green-600'
													: category === 'Match their Age'
														? 'border-yellow-500 dark:border-yellow-600'
														: category === 'Defer to Support'
															? 'border-purple-500 dark:border-purple-600'
															: 'border-pink-500 dark:border-pink-600'} rounded-lg bg-gray-50 dark:bg-gray-800/50"
									>
										<!-- Group Header (Always Visible) -->
										<button
											on:click={() => toggleGroupExpansion(category)}
											class="w-full p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors rounded-lg"
										>
											<div class="flex items-center justify-between">
												<div class="flex items-center">
													<span
														class="w-3 h-3 rounded-full mr-3 {category === 'Refuse and Remove'
															? 'bg-red-500'
															: category === 'Investigate and Empathize'
																? 'bg-blue-500'
																: category === 'Correct their Understanding'
																	? 'bg-green-500'
																	: category === 'Match their Age'
																		? 'bg-yellow-500'
																		: category === 'Defer to Support'
																			? 'bg-purple-500'
																			: 'bg-pink-500'}"
													></span>
													<h4 class="text-base font-bold text-gray-900 dark:text-white">
														{category === 'Custom' && showCustomInput
															? '✨ Custom (Open)'
															: category}
													</h4>
												</div>
												<div class="flex items-center space-x-2">
													{#if (category === 'Attention Check' && attentionCheckSelected) || options.some( (option) => selectedModerations.has(option) ) || (category === 'Custom' && customInstructions.length > 0)}
														<span
															class="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-full"
														>
															{#if category === 'Custom'}
																{customInstructions.filter((c) => selectedModerations.has(c.id))
																	.length} selected
															{:else if category === 'Attention Check'}
																{attentionCheckSelected ? 1 : 0} selected
															{:else}
																{options.filter((option) => selectedModerations.has(option)).length} selected
															{/if}
														</span>
													{/if}
													{#if category !== 'Custom' || !showCustomInput}
														<svg
															class="w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform {expandedGroups.has(
																category
															) ||
															(category === 'Custom' && showCustomInput)
																? 'rotate-180'
																: ''}"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M19 9l-7 7-7-7"
															></path>
														</svg>
													{:else}
														<svg
															class="w-5 h-5 text-purple-500 dark:text-purple-400 transition-transform rotate-180"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M19 9l-7 7-7-7"
															></path>
														</svg>
													{/if}
												</div>
											</div>
										</button>

										<!-- Group Content (Expandable) - Skip for Custom category -->
										{#if expandedGroups.has(category) && category !== 'Custom'}
											<div class="px-4 pb-4">
												<div class="grid grid-cols-2 gap-3">
													{#each options as option}
														<Tooltip
															content={moderationTooltips[option] || ''}
															placement="top-end"
															className="w-full"
															tippyOptions={{ delay: [200, 0] }}
														>
															<button
																on:click={() => toggleModerationSelection(option)}
																disabled={moderationLoading}
																aria-pressed={option === 'I read the instructions'
																	? attentionCheckSelected
																	: selectedModerations.has(option)}
																class="p-3 text-sm font-medium text-center rounded-lg transition-all min-h-[50px] flex items-center justify-center {(
																	option === 'I read the instructions'
																		? attentionCheckSelected
																		: selectedModerations.has(option)
																)
																	? 'bg-blue-500 text-white hover:bg-blue-600 ring-2 ring-blue-400 shadow-lg'
																	: 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600'} disabled:opacity-50"
															>
																{option}
															</button>
														</Tooltip>
													{/each}
												</div>
											</div>
										{/if}

										<!-- Custom Input Field - Shows directly when Custom category is clicked -->
										{#if category === 'Custom' && showCustomInput}
											<div class="px-4 pb-4 pt-2">
												<div class="space-y-3">
													<label
														class="block text-sm font-medium text-purple-900 dark:text-purple-200"
													>
														Enter custom moderation instruction:
													</label>
													<textarea
														bind:value={customInstructionInput}
														rows="3"
														placeholder="E.g., Emphasize problem-solving skills, Include mindfulness techniques, Focus on building independence..."
														class="w-full px-3 py-2 border border-purple-300 dark:border-purple-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
														on:keydown={(e) => {
															if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
																addCustomInstruction();
															} else if (e.key === 'Escape') {
																cancelCustomInput();
															}
														}}
													></textarea>
													<div class="flex justify-end">
														<div class="flex space-x-2">
															<button
																on:click={cancelCustomInput}
																class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
															>
																Cancel
															</button>
															<button
																on:click={addCustomInstruction}
																class="px-3 py-1.5 text-sm font-medium bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
															>
																Add
															</button>
														</div>
													</div>
												</div>
											</div>
										{/if}
									</div>
								{/each}
							</div>

							<!-- Custom Instructions -->
							{#if customInstructions.length > 0}
								<div
									class="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg mb-3"
								>
									<h4 class="text-xs font-semibold text-purple-900 dark:text-purple-200 mb-2">
										Custom Instructions ({customInstructions.length}):
									</h4>
									<div class="space-y-2">
										{#each customInstructions as custom}
											<div
												class="flex items-start justify-between bg-white dark:bg-purple-900/30 p-2 rounded border-2 {selectedModerations.has(
													custom.id
												)
													? 'border-purple-500'
													: 'border-transparent'}"
											>
												<button
													on:click={() => toggleModerationSelection(custom.id)}
													class="flex-1 text-left mr-2"
												>
													<div class="flex items-center space-x-1 mb-1">
														<div
															class="w-3 h-3 rounded border-2 {selectedModerations.has(custom.id)
																? 'bg-purple-500 border-purple-500'
																: 'border-gray-300 dark:border-gray-600'} flex items-center justify-center"
														>
															{#if selectedModerations.has(custom.id)}
																<svg
																	class="w-2 h-2 text-white"
																	fill="none"
																	stroke="currentColor"
																	viewBox="0 0 24 24"
																>
																	<path
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="3"
																		d="M5 13l4 4L19 7"
																	></path>
																</svg>
															{/if}
														</div>
														<p class="text-xs text-purple-800 dark:text-purple-200 font-medium">
															#{customInstructions.indexOf(custom) + 1}
														</p>
													</div>
													<p class="text-xs text-gray-700 dark:text-gray-300 line-clamp-2">
														{custom.text}
													</p>
												</button>
												<button
													on:click={() => removeCustomInstruction(custom.id)}
													class="text-red-500 hover:text-red-700 dark:text-red-400 flex-shrink-0"
													title="Remove"
												>
													<svg
														class="w-3 h-3"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M6 18L18 6M6 6l12 12"
														></path>
													</svg>
												</button>
											</div>
										{/each}
									</div>
								</div>
							{/if}

							<!-- Apply Button -->
							<button
								on:click={applySelectedModerations}
								disabled={moderationLoading ||
									(selectedModerations.size === 0 && !attentionCheckSelected) ||
									(selectedModerations.size === 0 && attentionCheckSelected) ||
									attentionCheckProcessing}
								class="w-full px-4 py-2.5 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2"
							>
								{#if moderationLoading}
									<div
										class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
									></div>
									<span>Creating Version...</span>
								{:else}
									<span>Generate New Version</span>
								{/if}
							</button>
						</div>
					{/if}

					<!-- Footer with Navigation -->
					<div
						class="flex-shrink-0 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
					>
						<div class="flex items-center justify-between">
							<!-- Previous Scenario Button -->
							{#if selectedScenarioIndex > 0}
								<button
									on:click={() => loadScenario(selectedScenarioIndex - 1)}
									class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex items-center space-x-2"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 19l-7-7 7-7"
										></path>
									</svg>
									<span>Previous</span>
								</button>
							{:else}
								<div></div>
							{/if}

							<!-- Next Scenario or Done Button -->
							{#if selectedScenarioIndex < scenarioList.length - 1}
								<button
									on:click={() => loadScenario(selectedScenarioIndex + 1)}
									class="px-4 py-2 text-sm font-medium rounded-lg transition-all flex items-center space-x-2 {currentScenarioCompleted
										? 'bg-green-500 text-white hover:bg-green-600 shadow-lg hover:shadow-xl'
										: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								>
									<span>Next</span>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 5l7 7-7 7"
										></path>
									</svg>
								</button>
							{:else if currentScenarioCompleted}
								<button
									on:click={completeModeration}
									class="px-6 py-2 text-sm font-medium rounded-lg transition-all shadow-lg bg-purple-500 text-white hover:bg-purple-600 flex items-center space-x-2"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M5 13l4 4L19 7"
										></path>
									</svg>
									<span>Done</span>
								</button>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Custom Instruction Modal - REMOVED: Now using inline input -->

		<!-- Confirmation Modal -->
		{#if showConfirmationModal}
			<div
				class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
				on:click={() => (showConfirmationModal = false)}
				role="dialog"
				aria-modal="true"
				aria-labelledby="confirmation-modal-title"
			>
				<div
					class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl"
					on:click|stopPropagation
				>
					<div class="text-center mb-6">
						<div
							class="w-16 h-16 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4"
						>
							<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 13l4 4L19 7"
								></path>
							</svg>
						</div>
						<h3
							id="confirmation-modal-title"
							class="text-2xl font-bold text-gray-900 dark:text-white mb-2"
						>
							Ready to Continue?
						</h3>
						<p class="text-gray-600 dark:text-gray-400">
							Would you like to proceed to the exit survey?
						</p>
					</div>

					<div class="flex flex-col space-y-3">
						<button
							on:click={proceedToNextStep}
							class="bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						>
							Yes, Continue to Exit Survey
						</button>
						<button
							on:click={continueModeration}
							class="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						>
							No, Continue Working on Scenarios
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Reset Confirmation Modal -->
		{#if showResetConfirmationModal}
			<div
				class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
				on:click={cancelReset}
				role="dialog"
				aria-modal="true"
				aria-labelledby="reset-confirmation-modal-title"
			>
				<div
					class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl"
					on:click|stopPropagation
				>
					<div class="text-center mb-6">
						<div
							class="w-16 h-16 bg-gradient-to-r from-red-500 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-4"
						>
							<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
								></path>
							</svg>
						</div>
						<h3
							id="reset-confirmation-modal-title"
							class="text-2xl font-bold text-gray-900 dark:text-white mb-2"
						>
							Restart All Scenarios?
						</h3>
						<p class="text-gray-600 dark:text-gray-400">
							This will reset all your progress, including completed scenarios, timers, and
							moderation work. This action cannot be undone.
						</p>
					</div>

					<div class="flex flex-col space-y-3">
						<button
							on:click={confirmReset}
							class="bg-gradient-to-r from-red-500 to-orange-600 hover:from-red-600 hover:to-orange-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						>
							Yes, Restart All Scenarios
						</button>
						<button
							on:click={cancelReset}
							class="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						>
							No, Keep My Progress
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<!-- Assignment Time Tracker (separate from moderation tracking) -->
<AssignmentTimeTracker userId={get(user)?.id || ''} {sessionNumber} enabled={true} />

<!-- Help Video Modal -->
<VideoModal
	isOpen={showHelpVideo}
	videoSrc="/video/Moderation-Scenario-Demo.mp4"
	title="Moderation Scenario Tutorial"
/>

<style>
	.response-text :global(.selection-highlight) {
		background-color: #fef3c7;
		padding: 0 2px;
		border-radius: 2px;
	}

	:global(.dark) .response-text :global(.selection-highlight) {
		background-color: #ca8a04;
		color: #fef3c7;
	}
</style>
