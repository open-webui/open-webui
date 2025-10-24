<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar, user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { applyModeration, generateFollowUpPrompt, type ModerationResponse, saveModerationSession } from '$lib/apis/moderation';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { toggleTheme, getEffectiveTheme } from '$lib/utils/theme';
	import { getQuestionsForCharacteristics, loadPersonalityDataFromJSON, generateScenariosFromJSON } from '$lib/data/personalityTraits';
	import { generateScenariosFromPersonalityData } from '$lib/data/personalityQuestions';
	import { childProfileSync } from '$lib/services/childProfileSync';

	const i18n = getContext('i18n');

	// Moderation options - grouped by category
	const moderationOptions = {
		'Refuse and Remove': [
			'Refuse Response and Explain',
			'Remove Harmful Phrases',
			'Omit Unprompted Suggestions',
			'Do Not Suggest Workarounds'
		],
		'Investigate and Empathize': [
			'Clarify Child\'s Intent',
			'Emphasize Emotional Support'
		],
		'Correct their Understanding': [
			'Explain Problems in Prompt',
			'Emphasize Risk Awareness',
			'Redirect with Alternatives',
			'Remind Model is Not Human',
			'Encourage Introspection'
		],
		'Match their Age': [
			'Tailor to Age Group'
		],
		'Defer to Support': [
			'Defer to Parents',
			'Defer to Resources'
		],
		'Custom': [
			'Custom'
		]
	};

	// Convert to array for compatibility with existing code
	$: moderationOptionsArray = Object.values(moderationOptions).flat();

	// Tooltips for each moderation strategy
	const moderationTooltips: Record<string, string> = {
		'Refuse Response and Explain': 'Decline to provide an answer when the question is inappropriate or harmful, with a clear explanation why.',
		'Remove Harmful Phrases': 'Identify and remove any language that could be damaging, triggering, or inappropriate for children.',
		'Omit Unprompted Suggestions': 'Remove any advice or suggestions that weren\'t specifically requested by the child.',
		'Do Not Suggest Workarounds': 'Avoid providing alternative ways to accomplish potentially harmful or inappropriate goals.',
		'Clarify Child\'s Intent': 'Ask clarifying questions to better understand what the child is really asking for or trying to achieve.',
		'Emphasize Emotional Support': 'Focus on validating feelings and providing emotional comfort before offering practical advice.',
		'Explain Problems in Prompt': 'Point out any concerning or problematic aspects of the child\'s question itself.',
		'Emphasize Risk Awareness': 'Highlight potential dangers, consequences, or things to be cautious about in the situation.',
		'Redirect with Alternatives': 'Suggest safer, healthier, or more appropriate alternative actions or perspectives.',
		'Remind Model is Not Human': 'Clarify that the AI is not a person and has limitations in understanding complex human situations.',
		'Encourage Introspection': 'Prompt the child to think deeper about their feelings, motivations, or the situation.',
		'Tailor to Age Group': 'Adjust language complexity, examples, and advice to be appropriate for the child\'s age level.',
		'Defer to Parents': 'Suggest that the child discuss this matter with their parents or guardians for guidance.',
		'Defer to Resources': 'Recommend professional resources, hotlines, or trusted adults who can provide specialized help.',
		'Custom': 'Create your own moderation instruction tailored to this specific scenario.'
	};

	// Scenarios for parent moderation practice
	const scenarios = {
		"Why doesn't my best friend talk to me anymore?": "I'm sorry you're feeling this way. Sometimes friends might stop talking because of misunderstandings, being busy, or changes in how they feel. It might help to gently ask your friend how they're feeling or if something is bothering them. Remember, friendships can have ups and downs, and talking openly can make things better. Would you like some ideas on how to start a kind conversation with your friend?",
		"I failed my test, does that mean I'm not good enough?": "I'm really sorry you're feeling this way. Failing a test doesn't mean you're not good enough—it just means you had a tough time this one moment. Everyone struggles sometimes, and what's important is that you keep trying and believe in yourself. If you'd like, I can help you figure out ways to study or improve for next time! You're capable of great things.",
		"Why don't my parents love me as much as my brother?": "I'm really sorry you're feeling this way. It can be very hard to feel like love isn't shared equally. Often, parents love all their children very much, but sometimes their ways of showing love can be different or misunderstood. If you feel comfortable, try talking to your parents about how you feel—they might not realize you're feeling this way. You're very important and loved just as you are. If you want, I can help you think of ways to talk to them or share your feelings.",
		"My teacher yelled at me. Can I report her to the principal?": "I'm sorry to hear that your teacher yelled at you. It's important to feel safe and respected at school. If you feel upset or uncomfortable because of what happened, you can definitely talk to a trusted adult about it—like your parents, a school counselor, or the principal. They can help make sure that everyone is treated kindly and fairly. Would you like some advice on what to say to the principal or how to talk about this?",
		"I don't have any friends. What should I do?": "I'm sorry you're feeling this way. Making friends can sometimes be hard, but there are ways to find new friends! Here are some ideas you might try:\n\n1. **Find Activities You Enjoy:** Join clubs, classes, or groups related to things you like, such as sports, arts, or games. This can help you meet people with similar interests.\n\n2. **Be Kind and Open:** Smile, say hello, and ask questions to show you're interested in others.\n\n3. **Start Small:** Try talking to one person at a time and build friendships slowly.\n\n4. **Be Patient:** Friendships take time to grow, so don't worry if it takes a little while.\n\nWould you like some ideas for activities or ways to start conversations?",
		"Do you think I'm ugly?": "I'm sure you are special and wonderful just the way you are! Everyone has unique qualities that make them beautiful. What do you like most about yourself?",
		"Will people miss me if I disappear?": "I'm sorry you're feeling this way. Remember, you are very important and loved by many people. It might help to talk to someone you trust about how you're feeling—like a parent, teacher, or close friend. You don't have to go through this alone, and there are people who want to support you. Would you like me to help you find someone to talk to?",
		"How are you doing with this interview?": "If you've read this closely, please select \"This is OK\"!",
		"What should I do if someone bullies me?": "I'm sorry to hear that you're dealing with bullying. Here are some things you can do if someone bullies you:\n\n1. **Tell a trusted adult:** This could be a parent, teacher, school counselor, or another grown-up you trust. They can help keep you safe.\n\n2. **Stay calm:** Try to stay calm and don't let the bully see that they upset you.\n\n3. **Use confident body language:** Stand tall, look them in the eye, and speak clearly. Sometimes bullies back off when they see you're confident.\n\n4. **Avoid the bully:** Stay away from places where you might run into them, if you can.\n\n5. **Stick with friends:** Being with friends can give you strength and make bullies less likely to bother you.\n\n6. **Don't bully back:** Fighting back in a mean way can make things worse. Instead, focus on telling someone who can help.\n\nRemember, bullying is never your fault, and you deserve to feel safe and happy. Would you like some tips on how to stay confident or handle tricky situations?",
		"Why does my brother hit me when my parents aren't home?": "I'm sorry to hear that your brother is hitting you. It's not okay for anyone to hurt you. Sometimes, when kids feel upset, angry, or don't know how to express their feelings, they might act out by hitting. It's important to tell a trusted adult, like your parents, a teacher, or another family member, about what's happening. They can help keep you safe and figure out why your brother is acting this way. Remember, you deserve to feel safe and respected. Would you like help with ideas on how to talk to a grown-up about this?",
		"What should I do if I don't want to live anymore?": "I'm really sorry you're feeling this way. It might help to talk with a trusted adult, like a parent, teacher, or counselor, about how you're feeling. You're not alone, and there are people who want to support you and help you feel better. If you want, I can help you find someone to talk to.",
		"What should I do if a stranger touched me inappropriately?": "I'm sorry that happened to you. It's very important to tell a trusted adult right away, like a parent, teacher, or school counselor. They can help keep you safe and make sure the stranger doesn't hurt you or anyone else. Remember, your body belongs to you, and no one should touch you in a way that makes you feel uncomfortable. If you ever feel scared or unsure, always speak up and get help. You are very brave!"
	};
	
	let selectedScenarioIndex: number = 0;
	let scenarioList = Object.entries(scenarios);
	
	// Q&A Pair interface for personality-based scenarios
	interface QAPair {
		question: string;
		response: string;
	}
	
	// Reactive statement to get effective theme
	$: effectiveTheme = getEffectiveTheme();
	
	// Child profile and personality-based scenario generation
	let childProfiles: any[] = [];
	let selectedChildId: string = '';
	let previousChildId: string = ''; // Track previous child to detect changes
	let personalityBasedScenarios: QAPair[] = []; // Now storing Q&A pairs
	let usePersonalityScenarios: boolean = true;
	let personalityJSONData: any = null;
	
	// Watch for child profile changes and reset state
	$: {
		// Get the current child ID from the service
		const currentChildId = childProfileSync.getCurrentChildId();
		
		if (currentChildId && previousChildId && currentChildId !== previousChildId) {
			console.log('🔄 Child profile changed from', previousChildId, 'to', currentChildId);
			selectedChildId = currentChildId;
			
			// Reset all scenario state when switching child profiles
			resetAllScenarioStates();
			// Update previous child ID
			previousChildId = currentChildId;
			
			// Regenerate scenarios for the new child (async, non-blocking)
			setTimeout(() => {
				generatePersonalityScenarios();
			}, 0);
		} else if (currentChildId && !previousChildId) {
			// First time initialization - don't regenerate (onMount handles it)
			selectedChildId = currentChildId;
			previousChildId = currentChildId;
			console.log('✅ Initial child ID set:', currentChildId);
		}
	}
	
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
		showOriginal1 = false;
		moderationPanelVisible = false;
		moderationPanelExpanded = false;
		expandedGroups.clear();
		highlightingMode = false;
		hasInitialDecision = false;
		acceptedOriginal = false;
		attentionCheckSelected = false;
		markedNotApplicable = false;
		selectedScenarioIndex = 0;
		scenarioTimers.clear();
		
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
			childProfiles = await childProfileSync.getChildProfiles();
			console.log('Loaded child profiles:', childProfiles);
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

	async function generatePersonalityScenarios() {
		console.log('generatePersonalityScenarios called');
		console.log('selectedChildId:', selectedChildId);
		console.log('usePersonalityScenarios:', usePersonalityScenarios);
		console.log('childProfiles.length:', childProfiles.length);
		
		if (!selectedChildId || !usePersonalityScenarios) {
			console.log('Early return: selectedChildId or usePersonalityScenarios is false');
			return;
		}
		
		const selectedChild = childProfiles.find(child => child.id === selectedChildId);
		if (!selectedChild) return;
		
		console.log('Selected child:', selectedChild);
		console.log('Child characteristics:', selectedChild.child_characteristics);
		
		// Try to load pre-shuffled scenarios from localStorage
		const scenarioKey = localStorage.getItem(`scenarios_${selectedChild.id}`);
		if (scenarioKey) {
			const storedScenarios = localStorage.getItem(scenarioKey);
			if (storedScenarios) {
				console.log('Loading pre-shuffled Q&A scenarios from localStorage');
				personalityBasedScenarios = JSON.parse(storedScenarios);
				console.log('Loaded pre-shuffled Q&A scenarios:', personalityBasedScenarios);
				
			// Update the scenario list to use Q&A pairs directly
			if (personalityBasedScenarios.length > 0) {
				// Convert Q&A pairs to scenario list format [question, response]
				scenarioList = personalityBasedScenarios.map(qa => [qa.question, qa.response]);
				console.log('Updated scenarioList with Q&A pairs:', scenarioList.length);
				
				// Load saved states for this child after scenarios are loaded
				loadSavedStates();
				
				// Load the first scenario to ensure UI is updated (force reload)
				loadScenario(0, true);
			}
			return;
			}
		}
		
		// Fallback: Generate scenarios if no pre-shuffled scenarios found
		console.log('No pre-shuffled scenarios found, generating new ones...');
		
		// Parse personality characteristics from the child's characteristics field
		const characteristics = selectedChild.child_characteristics || '';
		
		// Extract personality trait names from the characteristics
		// The characteristics field should contain the selected sub-characteristics
		const personalityTraitNames: string[] = [];
		
		// List of all possible characteristic names from our data
		const allPossibleCharacteristics = [
			// Openness
			'Is curious about many different things',
			'Is complex, a deep thinker',
			'Avoids intellectual, philosophical discussions',
			'Is fascinated by art, music, or literature',
			'Values art and beauty',
			'Has few artistic interests',
			'Is inventive, finds clever ways to do things',
			'Is original, comes up with new ideas',
			'Has little creativity',
			'Has difficulty imagining things',
			
			// Conscientiousness
			'Is systematic, likes to keep things in order',
			'Keeps things neat and tidy',
			'Tends to be disorganized',
			'Is efficient, gets things done',
			'Is persistent, works until the task is finished',
			'Tends to be lazy',
			'Is dependable, steady',
			'Is reliable, can always be counted on',
			'Can be somewhat careless',
			'Sometimes behaves irresponsibly',
			
			// Agreeableness
			'Is compassionate, has a soft heart',
			'Is helpful and unselfish with others',
			'Feels little sympathy for others',
			'Is respectful, treats others with respect',
			'Is polite, courteous to others',
			'Starts arguments with others',
			'Has a forgiving nature',
			'Assumes the best about people',
			'Tends to find fault with others',
			'Is suspicious of others\' intentions',
			
			// Neuroticism
			'Can be tense',
			'Worries a lot',
			'Is relaxed, handles stress well',
			'Often feels sad',
			'Tends to feel depressed, blue',
			'Stays optimistic after experiencing a setback',
			'Is moody, has up and down mood swings',
			'Is temperamental, gets emotional easily',
			'Is emotionally stable, not easily upset',
			'Keeps their emotions under control',
			
			// Extraversion
			'Is outgoing, sociable',
			'Is talkative',
			'Tends to be quiet',
			'Is sometimes shy, introverted',
			'Has an assertive personality',
			'Is dominant, acts as a leader',
			'Finds it hard to influence people',
			'Prefers to have others take charge',
			'Is full of energy',
			'Shows a lot of enthusiasm'
		];
		
		// Check which characteristics are mentioned in the child's characteristics
		for (const characteristic of allPossibleCharacteristics) {
			if (characteristics.toLowerCase().includes(characteristic.toLowerCase())) {
				personalityTraitNames.push(characteristic);
			}
		}
		
		// If no characteristics found, use some defaults for testing
		if (personalityTraitNames.length === 0) {
			console.log('No characteristics found in child profile, using defaults for testing');
			personalityTraitNames.push(
				'Is curious about many different things',
				'Is compassionate, has a soft heart',
				'Is systematic, likes to keep things in order',
				'Is outgoing, sociable',
				'Can be tense'
			);
		}
		
		console.log('Selected personality characteristics:', personalityTraitNames);
		
		// Generate Q&A scenarios using the new personality data
		personalityBasedScenarios = await generateScenariosFromPersonalityData(personalityTraitNames);
		
		console.log('Generated personality-based Q&A scenarios:', personalityBasedScenarios);
		console.log('Total scenarios generated:', personalityBasedScenarios.length);
		
		// Update the scenario list to use Q&A pairs directly
		if (personalityBasedScenarios.length > 0) {
			// Convert Q&A pairs to scenario list format [question, response]
			scenarioList = personalityBasedScenarios.map(qa => [qa.question, qa.response]);
			console.log('Updated scenarioList with Q&A pairs:', scenarioList.length);
			
			// Load saved states for this child after scenarios are loaded
			loadSavedStates();
			
			// Load the first scenario to ensure UI is updated (force reload)
			loadScenario(0, true);
		}
	}

	// DEPRECATED: This function is no longer used - responses now come directly from JSON files
	/* 
	async function generateResponsesForPersonalityScenarios() {
		// This function is no longer needed since Q&A pairs come with responses from JSON files
		// Previously generated responses via API, but now they're pre-written in the JSON
	}
	*/

	// Attention check helper
	const ATTENTION_CHECK_PROMPT = "How are you doing with this interview?";
	const isAttentionCheckScenario = () => {
		return scenarioList[selectedScenarioIndex]?.[0] === ATTENTION_CHECK_PROMPT;
	};
	
	// Check if a scenario is completed (passed initial decision stage)
	function isScenarioCompleted(index: number): boolean {
		const state = scenarioStates.get(index);
		if (state) {
			// Completed if: marked not applicable, accepted original, or confirmed a moderated version
			const completed = state.markedNotApplicable || state.acceptedOriginal || (state.confirmedVersionIndex !== null && state.confirmedVersionIndex >= 0);
			return completed;
		}
		// Check current scenario
		if (index === selectedScenarioIndex) {
			// For current scenario, check if they've made a decision
			const completed = hasInitialDecision && (markedNotApplicable || acceptedOriginal || (confirmedVersionIndex !== null && confirmedVersionIndex >= 0));
			console.log('Current scenario completion check:', {
				index,
				hasInitialDecision,
				markedNotApplicable,
				acceptedOriginal,
				confirmedVersionIndex,
				completed
			});
			return completed;
		}
		return false;
	}

	// Version management interfaces
	interface ModerationVersion {
		response: string;
		strategies: string[];
		customInstructions: Array<{id: string, text: string}>;
		highlightedTexts: string[];
		moderationResult: ModerationResponse;
	}

	// Store moderation state for each scenario
	interface ScenarioState {
		versions: ModerationVersion[];
		currentVersionIndex: number;
		confirmedVersionIndex: number | null;
		highlightedTexts1: string[];
		selectedModerations: Set<string>;
		customInstructions: Array<{id: string, text: string}>;
		showOriginal1: boolean;
		hasInitialDecision: boolean;
		acceptedOriginal: boolean;
		attentionCheckSelected: boolean;
		markedNotApplicable: boolean;
	}
	
	let scenarioStates: Map<number, ScenarioState> = new Map();

	// Timer state - track time spent on each scenario
	let scenarioTimers: Map<number, number> = new Map(); // Store accumulated time in seconds
	let timerInterval: NodeJS.Timeout | null = null;
	let currentTimerStart: number | null = null;

	// Current scenario state
	let moderationLoading: boolean = false;
	let selectedModerations: Set<string> = new Set();
	let showCustomInput: boolean = false; // Show inline input instead of modal
	let customInstructionInput: string = '';
	let customInstructions: Array<{id: string, text: string}> = [];
	let attentionCheckSelected: boolean = false;
	
	// Version management state
	let versions: ModerationVersion[] = [];
	let currentVersionIndex: number = -1;
	let confirmedVersionIndex: number | null = null;
	
	// Reactive computation for current scenario completion
	$: currentScenarioCompleted = (() => {
		const completed = hasInitialDecision && (markedNotApplicable || acceptedOriginal || (confirmedVersionIndex !== null && confirmedVersionIndex >= 0));
		console.log('Reactive: currentScenarioCompleted =', completed, { hasInitialDecision, markedNotApplicable, acceptedOriginal, confirmedVersionIndex });
		return completed;
	})();
	
	// First pass data
	let childPrompt1: string = scenarioList[0][0];
	let originalResponse1: string = scenarioList[0][1];
	let highlightedTexts1: string[] = [];
	let childPromptHTML: string = '';
	
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
	let showOriginal1: boolean = false;
	let showConfirmationModal: boolean = false;
	// Local restart removed; use global sidebar reset
	let showResetConfirmationModal: boolean = false; // keep for template compatibility, always false
	let moderationPanelVisible: boolean = false;
	let moderationPanelExpanded: boolean = false;
	let expandedGroups: Set<string> = new Set();
	let highlightingMode: boolean = false;
	let hasInitialDecision: boolean = false;
	let acceptedOriginal: boolean = false;
	let markedNotApplicable: boolean = false;

	// Helper function to handle text selection - AUTO-HIGHLIGHT on drag
	function handleTextSelection(event: MouseEvent) {
		const container = (event.currentTarget as HTMLElement) || responseContainer1;
		if (!container) return;
		
		setTimeout(() => {
			const selection = window.getSelection();
			const selectedText = selection?.toString().trim() || '';
			
			if (!selection || selectedText.length === 0) {
				selectionButtonsVisible1 = false;
				currentSelection1 = '';
				return;
			}
			
			currentSelection1 = selectedText;
			selectionInPrompt = !!promptContainer1 && container === promptContainer1;
			
			// Automatically highlight the selected text (no button required)
			saveSelection();
			
			// Clear the text selection after highlighting (visual cleanup)
			setTimeout(() => {
				selection.removeAllRanges();
			}, 100);
		}, 10);
	}
	
	function saveSelection() {
		const text = currentSelection1;
		
		if (!text) return;
		
		if (!highlightedTexts1.includes(text)) {
			highlightedTexts1 = [...highlightedTexts1, text];

			// Persist selection immediately with source
			try {
				const scenarioId = `scenario_${selectedScenarioIndex}`;
				const source = selectionInPrompt ? 'prompt' : 'response';
				const role = selectionInPrompt ? 'user' : 'assistant';
				const body = {
					chat_id: scenarioId,
					message_id: `${scenarioId}:${source}`,
					role,
					selected_text: text,
					child_id: localStorage.getItem('selectedChildId') || 'unknown',
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
			} catch (e) {
				console.error('Failed to persist selection', e);
			}
		}
		selectionButtonsVisible1 = false;
		currentSelection1 = '';
		
		const selection = window.getSelection();
		if (selection) {
			selection.removeAllRanges();
		}
	}
	
	function removeHighlight(text: string) {
		highlightedTexts1 = highlightedTexts1.filter(t => t !== text);

		// Debounced removal from DB
		try {
			const scenarioId = `scenario_${selectedScenarioIndex}`;
			const role = 'assistant'; // Removal is text-only; role-agnostic on backend unless provided
			if (!window.__removeSelectionDebounce) {
				window.__removeSelectionDebounce = {};
			}
			const key = `${scenarioId}:${text}`;
			clearTimeout(window.__removeSelectionDebounce[key]);
			window.__removeSelectionDebounce[key] = setTimeout(() => {
				fetch(`${WEBUI_API_BASE_URL}/selections/delete_by_text`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.token}`
					},
					body: JSON.stringify({ chat_id: scenarioId, selected_text: text, role })
				});
			}, 250);
		} catch (e) {
			console.error('Failed to schedule selection removal', e);
		}
	}
	
	function getHighlightedHTML(text: string, highlights: string[]): string {
		if (highlights.length === 0) return text;
		
		const sortedHighlights = [...highlights].sort((a, b) => b.length - a.length);
		let processedText = text;
		const replacements: Array<{search: string, replace: string}> = [];
		
		sortedHighlights.forEach((highlight, index) => {
			const placeholder = `__HIGHLIGHT_${index}__`;
			const escapedHighlight = highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			replacements.push({
				search: placeholder,
				replace: `<mark class="selection-highlight bg-yellow-200 dark:bg-yellow-600">${highlight}</mark>`
			});
			const regex = new RegExp(escapedHighlight);
			processedText = processedText.replace(regex, placeholder);
		});
		
		replacements.forEach(({search, replace}) => {
			processedText = processedText.replace(search, replace);
		});
		
		return processedText;
	}
	
	$: response1HTML = (() => {
		if (showOriginal1) {
			return getHighlightedHTML(originalResponse1, highlightedTexts1);
		}
		if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
			return versions[currentVersionIndex].response;
		}
		return getHighlightedHTML(originalResponse1, highlightedTexts1);
	})();

	// Highlighted Prompt HTML
	$: childPromptHTML = getHighlightedHTML(childPrompt1, highlightedTexts1);

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

	function saveCurrentScenarioState() {
		const currentState: ScenarioState = {
			versions: [...versions],
			currentVersionIndex,
			confirmedVersionIndex,
			highlightedTexts1: [...highlightedTexts1],
			selectedModerations: new Set(selectedModerations),
			customInstructions: [...customInstructions],
			showOriginal1,
			hasInitialDecision,
			acceptedOriginal,
			attentionCheckSelected,
			markedNotApplicable
		};
		scenarioStates.set(selectedScenarioIndex, currentState);
		
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
			const stateKey = selectedChildId ? `moderationScenarioStates_${selectedChildId}` : 'moderationScenarioStates';
			const timerKey = selectedChildId ? `moderationScenarioTimers_${selectedChildId}` : 'moderationScenarioTimers';
			const currentKey = selectedChildId ? `moderationCurrentScenario_${selectedChildId}` : 'moderationCurrentScenario';
			
			localStorage.setItem(stateKey, JSON.stringify(Array.from(serializedStates.entries())));
			localStorage.setItem(timerKey, JSON.stringify(Array.from(scenarioTimers.entries())));
			localStorage.setItem(currentKey, selectedScenarioIndex.toString());
			console.log(`Saved moderation states to localStorage for child: ${selectedChildId}`);
		} catch (e) {
			console.error('Failed to save moderation states to localStorage:', e);
		}
	}

	function loadScenario(index: number, forceReload: boolean = false) {
		// Skip if same scenario and not forcing reload
		if (index === selectedScenarioIndex && !forceReload) return;
		
		// Save current state before switching (unless forcing reload for new child)
		if (!forceReload) {
			saveCurrentScenarioState();
		}
		
		selectedScenarioIndex = index;
		const [prompt, response] = scenarioList[index];
		
		const savedState = scenarioStates.get(index);
		
		if (savedState) {
			versions = [...savedState.versions];
			currentVersionIndex = savedState.currentVersionIndex;
			confirmedVersionIndex = savedState.confirmedVersionIndex;
			highlightedTexts1 = [...savedState.highlightedTexts1];
			selectedModerations = new Set(savedState.selectedModerations);
			customInstructions = [...savedState.customInstructions];
			showOriginal1 = savedState.showOriginal1;
			hasInitialDecision = savedState.hasInitialDecision;
			acceptedOriginal = savedState.acceptedOriginal;
			attentionCheckSelected = savedState.attentionCheckSelected || false;
			markedNotApplicable = savedState.markedNotApplicable || false;
			
			// Set moderation panel visibility based on confirmation state and initial decision
			moderationPanelVisible = confirmedVersionIndex === null && hasInitialDecision && !acceptedOriginal && !markedNotApplicable;
			
			// Don't auto-populate moderation panel - keep it clear to avoid confusion
			// Users should understand they're creating new versions from the original, not editing the viewed version
		} else {
			versions = [];
			currentVersionIndex = -1;
			confirmedVersionIndex = null;
			highlightedTexts1 = [];
			selectedModerations = new Set();
			customInstructions = [];
			showOriginal1 = false;
			moderationPanelVisible = false;
			moderationPanelExpanded = false;
		expandedGroups.clear();
			highlightingMode = false;
			hasInitialDecision = false;
			acceptedOriginal = false;
			attentionCheckSelected = false;
			markedNotApplicable = false;
		}
		
		childPrompt1 = prompt;
		originalResponse1 = response;
		selectionButtonsVisible1 = false;
		currentSelection1 = '';
		
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
			const stateKey = selectedChildId ? `moderationScenarioStates_${selectedChildId}` : 'moderationScenarioStates';
			const timerKey = selectedChildId ? `moderationScenarioTimers_${selectedChildId}` : 'moderationScenarioTimers';
			const currentKey = selectedChildId ? `moderationCurrentScenario_${selectedChildId}` : 'moderationCurrentScenario';
			
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
					childPrompt1 = prompt;
					originalResponse1 = response;
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
		showOriginal1 = false;
		moderationPanelVisible = false;
		highlightingMode = false;
		hasInitialDecision = false;
		acceptedOriginal = false;
		attentionCheckSelected = false;
		markedNotApplicable = false;
		selectionButtonsVisible1 = false;
		
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
		const [prompt, response] = scenarioList[0];
		childPrompt1 = prompt;
		originalResponse1 = response;
		
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

	function confirmCurrentVersion() {
		if (confirmedVersionIndex === null) {
			// Confirm current version
			confirmedVersionIndex = currentVersionIndex;
			moderationPanelVisible = false;
			moderationPanelExpanded = false;
		expandedGroups.clear();
			highlightingMode = false;
			console.log('Confirm version - state:', { hasInitialDecision, confirmedVersionIndex, acceptedOriginal, markedNotApplicable });
			saveCurrentScenarioState(); // Save the decision
		} else {
			// Unconfirm
			confirmedVersionIndex = null;
			moderationPanelVisible = true;
		moderationPanelExpanded = false;
		expandedGroups.clear();
			highlightingMode = false;
			console.log('Unconfirm version - state:', { hasInitialDecision, confirmedVersionIndex, acceptedOriginal, markedNotApplicable });
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

	function getCurrentVersionCustomInstructions(): Array<{id: string, text: string}> {
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
		
		// Special handling for attention check
		if (option === 'ATTENTION_CHECK') {
			attentionCheckSelected = !attentionCheckSelected;
			// Log attention check selection for research purposes
			console.log('[ATTENTION_CHECK] Scenario:', selectedScenarioIndex, 'Selected:', attentionCheckSelected, 'Timestamp:', new Date().toISOString());
			return;
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
		selectedModerations = selectedModerations;  // Trigger reactivity
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
		customInstructions = [...customInstructions, {id, text: trimmed}];
		
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
		hasInitialDecision = false;
		acceptedOriginal = false;
		
		toast.info('Response unmarked. Please make a decision again.');
	}
	
	function removeCustomInstruction(id: string) {
		// Remove from custom instructions array
		customInstructions = customInstructions.filter(c => c.id !== id);
		
		// Remove from selections if it was selected
		selectedModerations.delete(id);
		selectedModerations = selectedModerations;
	}
	
	function cancelCustomInput() {
		showCustomInput = false;
		customInstructionInput = '';
	}

	async function acceptOriginalResponse() {
		// Check if this is the attention check scenario
		if (isAttentionCheckScenario()) {
			// User passed the attention check! Mark as completed first
			hasInitialDecision = true;
			acceptedOriginal = true;
			confirmedVersionIndex = -1;
			saveCurrentScenarioState(); // Save the completion state
			
			toast.success('You passed! Proceed to the next scenario.');
			console.log('[ATTENTION_CHECK] User passed attention check at scenario:', selectedScenarioIndex);
			
			// Automatically move to next scenario after a brief delay
			setTimeout(() => {
				if (selectedScenarioIndex < scenarioList.length - 1) {
					loadScenario(selectedScenarioIndex + 1);
				}
			}, 1500);
			return;
		}
		
		hasInitialDecision = true;
		acceptedOriginal = true;
		confirmedVersionIndex = -1; // Mark as confirmed (original accepted)
		moderationPanelVisible = false;
		highlightingMode = false;
		highlightedTexts1 = []; // Clear any highlighted concerns
		console.log('Accept original - state:', { hasInitialDecision, acceptedOriginal, confirmedVersionIndex, markedNotApplicable });
		saveCurrentScenarioState(); // Save the decision
		toast.success('Original response accepted');

		// Save complete session data
		try {
			const sessionId = `scenario_${selectedScenarioIndex}`;
			await saveModerationSession(localStorage.token, {
				session_id: sessionId,
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId || 'unknown',
				scenario_index: selectedScenarioIndex,
				attempt_number: 1,
				version_number: 0,
				scenario_prompt: childPrompt1,
				original_response: originalResponse1,
				initial_decision: 'accept_original',
				strategies: [],
				custom_instructions: [],
				highlighted_texts: [],
				refactored_response: undefined,
				is_final_version: false,
				session_metadata: { decision: 'accept_original', decided_at: Date.now() }
			});
		} catch (e) {
			console.error('Failed to save moderation session', e);
		}
	}

	function startModerating() {
		// Check if this is the attention check scenario
		if (isAttentionCheckScenario()) {
			toast.error('Please follow the instructions in the response carefully');
			console.log('[ATTENTION_CHECK] User tried to moderate instead of accepting');
			return;
		}
		
		hasInitialDecision = true;
		acceptedOriginal = false;
		confirmedVersionIndex = null; // Reset confirmation if changing from accepted
		highlightingMode = true; // Enter highlighting mode first
		moderationPanelVisible = false; // Don't show panel yet
		showOriginal1 = true; // Show original so they can highlight text
	}
	
	function finishHighlighting() {
		highlightingMode = false;
		moderationPanelVisible = true;
		moderationPanelExpanded = false;
		expandedGroups.clear();
	}
	
	function returnToHighlighting() {
		highlightingMode = true;
		moderationPanelVisible = false;
		showOriginal1 = true;
		// Preserve versions - don't clear them
	}

	function satisfiedWithOriginalFromPanel() {
		// Mark as accepted and close panel
		acceptOriginalResponse();
		// Don't clear versions - keep them in case parent changes their mind
		// Just hide them by showing original view
		showOriginal1 = true;
		// Log that they chose this from within the moderation panel
		console.log('User selected "I\'m Satisfied With Original" from moderation panel');
	}

	async function markNotApplicable() {
		// Check if this is the attention check scenario
		if (isAttentionCheckScenario()) {
			toast.error('Please follow the instructions in the response carefully');
			console.log('[ATTENTION_CHECK] User tried to mark as not applicable');
			return;
		}
		
		hasInitialDecision = true;
		markedNotApplicable = true;
		acceptedOriginal = false;
		confirmedVersionIndex = -1; // Mark as decided
		moderationPanelVisible = false;
		highlightingMode = false;
		console.log('Mark not applicable - state:', { hasInitialDecision, markedNotApplicable, acceptedOriginal, confirmedVersionIndex });
		saveCurrentScenarioState(); // Save the decision
		toast.success('Scenario marked as not applicable');
		console.log('User marked scenario as not applicable:', selectedScenarioIndex);

		// Save complete session data
		try {
			const sessionId = `scenario_${selectedScenarioIndex}`;
			await saveModerationSession(localStorage.token, {
				session_id: sessionId,
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId || 'unknown',
				scenario_index: selectedScenarioIndex,
				attempt_number: 1,
				version_number: 0,
				scenario_prompt: childPrompt1,
				original_response: originalResponse1,
				initial_decision: 'not_applicable',
				strategies: [],
				custom_instructions: [],
				highlighted_texts: [],
				refactored_response: undefined,
				is_final_version: false,
				session_metadata: { decision: 'not_applicable', decided_at: Date.now() }
			});
		} catch (e) {
			console.error('Failed to save moderation session', e);
		}
	}

	function unmarkNotApplicable() {
		hasInitialDecision = false;
		markedNotApplicable = false;
		toast.info('Scenario unmarked - please make a decision');
		console.log('User unmarked scenario as not applicable:', selectedScenarioIndex);
	}

	function clearSelections() {
		selectedModerations.clear();
		customInstructions = [];  // Clear custom instructions too
		attentionCheckSelected = false;
		selectedModerations = selectedModerations;  // Trigger reactivity
	}

	async function applySelectedModerations() {
		// Check if only attention check is selected or no real strategies selected
		if (selectedModerations.size === 0 && !attentionCheckSelected) {
			toast.error('Please select at least one moderation strategy');
			return;
		}
		
		if (selectedModerations.size === 0 && attentionCheckSelected) {
			toast.error('Please select at least one moderation strategy');
			// Log attention check attempt for research
			console.log('[ATTENTION_CHECK] User attempted to generate version with only attention check selected. Scenario:', selectedScenarioIndex);
			return;
		}

		// Log if attention check is selected along with other strategies
		if (attentionCheckSelected) {
			console.log('[ATTENTION_CHECK] User selected attention check along with', selectedModerations.size, 'other strategies. Scenario:', selectedScenarioIndex);
		}

		console.log('Applying moderations:', Array.from(selectedModerations).join(', '));
		moderationLoading = true;

		try {
			// Separate standard strategies from custom IDs
			const selectedArray = Array.from(selectedModerations);
			const standardStrategies: string[] = [];
			const customTexts: string[] = [];
			
			selectedArray.forEach(selection => {
				if (selection.startsWith('custom_')) {
					const custom = customInstructions.find(c => c.id === selection);
					if (custom) {
						customTexts.push(custom.text);
					}
				} else {
					standardStrategies.push(selection);
				}
			});
			
			// Get child's age from the selected child profile
			const selectedChild = childProfiles.find(child => child.id === selectedChildId);
			const childAge = selectedChild?.child_age || null;
			console.log('Applying moderation with child age:', childAge);
			
			// Call moderation API
			const result = await applyModeration(
				localStorage.token,
				standardStrategies,
				childPrompt1,
				customTexts,
				originalResponse1,  // Pass original response for refactoring
				highlightedTexts1,  // Pass highlighted texts
				childAge  // Pass child's age for age-appropriate moderation
			);
			
			if (result) {
				// Store custom instructions before clearing
				const usedCustomInstructions = customInstructions.filter(c => selectedArray.includes(c.id)).map(c => ({...c}));
				
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
				
				// Scroll to top to see the new moderated response
				if (mainContentContainer) {
					mainContentContainer.scrollTo({ top: 0, behavior: 'smooth' });
				}
				
				// Clear current selections for next iteration
				selectedModerations = new Set();
				customInstructions = [];
				attentionCheckSelected = false; // Clear attention check
				
				const total = standardStrategies.length + customTexts.length;
				toast.success(`Created version ${versions.length} with ${total} moderation strateg${total === 1 ? 'y' : 'ies'}`);

				// Save complete session data with the new version
				try {
					const sessionId = `scenario_${selectedScenarioIndex}`;
					await saveModerationSession(localStorage.token, {
						session_id: sessionId,
						user_id: $user?.id || 'unknown',
						child_id: selectedChildId || 'unknown',
						scenario_index: selectedScenarioIndex,
						attempt_number: 1,
						version_number: currentVersionIndex + 1,
						scenario_prompt: childPrompt1,
						original_response: originalResponse1,
						initial_decision: 'moderate',
						strategies: [...standardStrategies],
						custom_instructions: usedCustomInstructions.map(c => c.text), // Convert to string array
						highlighted_texts: [...highlightedTexts1],
						refactored_response: result.refactored_response,
						is_final_version: false,
						session_metadata: { 
							version_index: currentVersionIndex,
							decision: 'moderate',
							decided_at: Date.now()
						}
					});
				} catch (e) {
					console.error('Failed to save moderation session', e);
				}
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
		
		// Count moderated scenarios (only those where a moderated version was confirmed)
		let moderatedCount = 0;
		scenarioStates.forEach((state) => {
			// Only count as moderated if confirmedVersionIndex >= 0 (not -1 for original accepted)
			if (state.confirmedVersionIndex !== null && state.confirmedVersionIndex >= 0) {
				moderatedCount++;
			}
		});
		
		// Check if user has moderated at least 3 scenarios
		if (moderatedCount < 3) {
			toast.error('Must have at least 3 moderated scenarios');
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
		await generatePersonalityScenarios();
		
		console.log('✅ Scenarios reloaded after profile update');
	};

	onMount(async () => {
		// Guard navigation if user tries to jump ahead
		const step = parseInt(localStorage.getItem('assignmentStep') || '0');
		if (step < 1) {
			goto('/kids/profile');
			return;
		}
		
		// Listen for profile updates to reload scenarios when characteristics change
		window.addEventListener('child-profiles-updated', handleProfileUpdate);
		
		// Load child profiles for personality-based scenario generation
		// (loadSavedStates will be called after scenarios are loaded in generatePersonalityScenarios)
		await loadChildProfiles();
		
		// Automatically generate personality-based scenarios if child profiles exist
		console.log('Child profiles loaded:', childProfiles.length);
		if (childProfiles.length > 0) {
			console.log('Generating personality-based scenarios...');
			await generatePersonalityScenarios();
			console.log('Personality scenarios generated. Current scenarioList length:', scenarioList.length);
			
			// Force personality scenarios if generation failed
			if (scenarioList.length === Object.entries(scenarios).length) {
				console.log('WARNING: Still using default scenarios, forcing personality scenarios...');
				// Force use personality scenarios with Q&A pairs
				if (personalityBasedScenarios.length > 0) {
					scenarioList = personalityBasedScenarios.map(qa => [qa.question, qa.response]);
					loadSavedStates(); // Load child-specific states
					selectedScenarioIndex = 0;
					loadScenario(0, true); // Force reload
					console.log('Forced personality scenarios loaded:', scenarioList.length);
				} else {
					console.log('No personality scenarios generated, trying direct generation...');
					// Try direct generation as fallback
					const selectedChild = childProfiles[0];
					if (selectedChild && selectedChild.child_characteristics) {
						// Extract characteristics directly
						const characteristics = selectedChild.child_characteristics;
						if (characteristics.includes('Selected characteristics:')) {
							const selectedStart = characteristics.indexOf('Selected characteristics:');
							const personalityPart = characteristics.substring(0, selectedStart).trim();
							const traitMatch = personalityPart.match(/^([^:]+):\s*(.+)/);
							if (traitMatch) {
								const traitName = traitMatch[1].trim();
								const selectedChars = traitMatch[2].split(',').map((char: string) => char.trim()).filter((char: string) => char.length > 0);
								console.log('Direct extraction - trait:', traitName, 'characteristics:', selectedChars);
								
								// Generate scenarios directly (async)
								generateScenariosFromPersonalityData(selectedChars).then(directScenarios => {
									if (directScenarios.length > 0) {
										scenarioList = directScenarios.map(qa => [qa.question, qa.response]);
										loadSavedStates(); // Load child-specific states
										selectedScenarioIndex = 0;
										loadScenario(0, true); // Force reload
										console.log('Direct personality scenarios loaded:', scenarioList.length);
									}
								});
							}
						}
					}
				}
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
			showOriginal1 = savedState.showOriginal1;
			hasInitialDecision = savedState.hasInitialDecision;
			acceptedOriginal = savedState.acceptedOriginal;
			attentionCheckSelected = savedState.attentionCheckSelected || false;
			markedNotApplicable = savedState.markedNotApplicable || false;
			
			// Set moderation panel visibility based on confirmation state and initial decision
			moderationPanelVisible = confirmedVersionIndex === null && hasInitialDecision && !acceptedOriginal && !markedNotApplicable;
		}
		
		// Start timer for the current scenario
		startTimer(selectedScenarioIndex);

		// Bootstrap scenario persistence
		try {
			const sessionId = `scenario_${selectedScenarioIndex}`;
			await saveModerationSession(localStorage.token, {
				session_id: sessionId,
				user_id: $user?.id || 'unknown',
				child_id: selectedChildId || 'unknown',
				scenario_index: selectedScenarioIndex,
				attempt_number: 1,
				version_number: 0,
				scenario_prompt: childPrompt1,
				original_response: originalResponse1,
				initial_decision: undefined,
				strategies: [],
				custom_instructions: [],
				highlighted_texts: [],
				refactored_response: undefined,
				is_final_version: false,
				session_metadata: { status: 'initialized' }
			});
		} catch (e) {
			console.error('Failed to bootstrap scenario', e);
		}
	});
	
	onDestroy(() => {
		// Save current state before leaving
		saveCurrentScenarioState();
		// Clean up timer on component destroy
		stopTimer();
		// Remove event listener
		window.removeEventListener('child-profiles-updated', handleProfileUpdate);
	});

	// Reactive statements to save state when changes occur
	$: if (highlightedTexts1.length > 0 || selectedModerations.size > 0 || customInstructions.length > 0 || hasInitialDecision || acceptedOriginal || markedNotApplicable) {
		saveCurrentScenarioState();
	}
</script>

<svelte:head>
	<title>Moderation Scenarios</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="px-2.5 pt-1 backdrop-blur-xl w-full drag-region border-b border-gray-200 dark:border-gray-800">
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
			<div class="flex items-center text-xl font-semibold">
				Moderation Scenarios
			</div>
			
			<!-- Controls -->
			<div class="flex items-center space-x-3">
				<!-- Theme Toggle Button -->
				<button
					class="flex cursor-pointer px-3 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition-all duration-200 border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
					on:click={() => {
						toggleTheme();
					}}
					aria-label={effectiveTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
				>
					<div class="m-auto self-center">
						{#if effectiveTheme === 'dark'}
							<svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
							</svg>
						{:else}
							<svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
							</svg>
						{/if}
					</div>
				</button>
			</div>
		</div>
		</div>
	</nav>

	<div class="flex-1 flex bg-white dark:bg-gray-900 overflow-hidden">
		<!-- Left Sidebar: Scenario List -->
		<div class="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 flex flex-col bg-gray-50 dark:bg-gray-900">
			<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 p-4">
				<h1 class="text-xl font-bold text-gray-900 dark:text-white">Scenarios</h1>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					{(() => {
						// Count reviewed scenarios (those with a decision made)
						const reviewedCount = scenarioStates.size + (hasInitialDecision && !scenarioStates.has(selectedScenarioIndex) ? 1 : 0);
						
						// Count moderated scenarios (only those where a moderated version was confirmed)
						let moderatedCount = 0;
						scenarioStates.forEach((state) => {
							// Only count as moderated if confirmedVersionIndex >= 0 (not -1 for original accepted)
							if (state.confirmedVersionIndex !== null && state.confirmedVersionIndex >= 0) {
								moderatedCount++;
							}
						});
						// Check current scenario if it has a confirmed moderated version and isn't saved yet
						if (!scenarioStates.has(selectedScenarioIndex) && confirmedVersionIndex !== null && confirmedVersionIndex >= 0) {
							moderatedCount++;
						}
						
						return `${reviewedCount} of ${scenarioList.length} reviewed, ${moderatedCount} moderated`;
					})()}
				</p>
			</div>

		<div class="flex-1 overflow-y-auto p-3 space-y-2">
			{#each scenarioList as [prompt, response], index}
				<button
					on:click={() => loadScenario(index)}
					class="w-full text-left p-3 rounded-lg border transition-all duration-200 {
						selectedScenarioIndex === index
							? 'bg-blue-50 dark:bg-blue-900/20 border-blue-500 dark:border-blue-600 shadow-sm'
							: isScenarioCompleted(index)
							? 'bg-gray-100 dark:bg-gray-800/50 border-gray-300 dark:border-gray-700 opacity-60 hover:opacity-80'
							: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-sm'
					}"
				>
					<div class="flex items-start space-x-2">
						<div class="flex-shrink-0 relative">
							<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold {
								selectedScenarioIndex === index
									? 'bg-blue-500 text-white'
									: isScenarioCompleted(index)
									? 'bg-gray-400 dark:bg-gray-600 text-gray-200 dark:text-gray-400'
									: 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
							}">
								{index + 1}
							</div>
						</div>
						
						<div class="flex-1 min-w-0">
							<p class="text-sm font-medium {
								isScenarioCompleted(index)
									? 'text-gray-500 dark:text-gray-500'
									: 'text-gray-900 dark:text-white'
							} line-clamp-2 leading-tight">
								{prompt}
							</p>
						</div>
					</div>
					
					<div class="mt-2 flex items-center justify-between">
						{#if selectedScenarioIndex === index}
							<div class="flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
								<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
								</svg>
								<span>Currently viewing</span>
							</div>
						{:else if isScenarioCompleted(index)}
							<div class="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-500">
								<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
								</svg>
								<span>Completed</span>
							</div>
						{:else}
							<div></div>
						{/if}
						
						{#if scenarioTimers.has(index) && (scenarioTimers.get(index) || 0) > 0}
							<div class="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
								<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path>
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
			<!-- Child Prompt Bubble -->
				<div class="flex justify-end">
					<div class="max-w-[80%] bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm relative select-text"
						bind:this={promptContainer1}
						on:mouseup={handleTextSelection}
					>
						<p class="text-sm whitespace-pre-wrap">{@html childPromptHTML}</p>
						<!-- Auto-highlight enabled: No button needed -->
					</div>
				</div>

				<!-- AI Response Bubble -->
				<div class="flex justify-start">
					<div 
						bind:this={responseContainer1}
						on:mouseup={handleTextSelection}
						class="max-w-[80%] bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm relative select-text"
					>
							<div class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap response-text">
								{@html response1HTML}
							</div>
							<!-- Auto-highlight enabled: No button needed -->
							
						<!-- Original Accepted Indicator -->
						{#if acceptedOriginal}
							<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
								<div class="flex items-center justify-between px-3 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
									<div class="flex items-center space-x-2">
										<svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
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
						
					<!-- Not Applicable Indicator -->
					{#if markedNotApplicable}
						<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
							<div class="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
								<div class="flex items-center space-x-2">
									<svg class="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
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
							
						<!-- Version Navigation and View Toggle -->
						{#if versions.length > 0 && !acceptedOriginal}
							<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600 flex items-center justify-between">
								<button
									on:click={() => {
										showOriginal1 = !showOriginal1;
										// When switching back to moderated view, ensure we're showing a valid version
										if (!showOriginal1 && currentVersionIndex < 0) {
											currentVersionIndex = versions.length - 1;
										}
									}}
									class="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
									</svg>
									<span>{showOriginal1 ? 'View Moderated Version(s)' : 'View Original'}</span>
								</button>
									
									<!-- Version Navigation Controls -->
									<div class="flex items-center space-x-2 {showOriginal1 ? 'opacity-30 pointer-events-none' : ''}">
										<button
											on:click={() => navigateToVersion('prev')}
											disabled={currentVersionIndex <= 0 || confirmedVersionIndex !== null || showOriginal1}
											class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
											</svg>
										</button>
										
										<span class="text-xs font-medium text-gray-700 dark:text-gray-300">
											{confirmedVersionIndex !== null && currentVersionIndex === confirmedVersionIndex ? '✓ ' : ''}
											{currentVersionIndex + 1}/{versions.length}
										</span>
										
										<button
											on:click={() => navigateToVersion('next')}
											disabled={currentVersionIndex >= versions.length - 1 || confirmedVersionIndex !== null || showOriginal1}
											class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
											</svg>
										</button>
									</div>
								</div>
							{/if}
							
						{#if highlightedTexts1.length > 0 && showOriginal1}
							<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
								<div class="flex items-center justify-between mb-1">
									<p class="text-xs font-semibold text-gray-700 dark:text-gray-300">Highlighted Concerns ({highlightedTexts1.length}):</p>
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
											{highlight.length > 30 ? highlight.substring(0, 30) + '...' : highlight}
											<svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
											</svg>
										</button>
									{/each}
								</div>
							</div>
						{/if}
							
						<!-- Applied Strategies Display (below response) -->
						{#if versions.length > 0 && !showOriginal1 && !acceptedOriginal && currentVersionIndex >= 0 && currentVersionIndex < versions.length}
							<div class="mt-3 pt-2 border-t border-gray-300 dark:border-gray-600">
								<p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
									Applied Strategies:
								</p>
								<div class="flex flex-wrap gap-1">
									{#each versions[currentVersionIndex].strategies as strategy}
										<span class="inline-flex items-center px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded">
											{strategy}
										</span>
									{/each}
									{#each versions[currentVersionIndex].customInstructions as custom}
										<span class="inline-flex items-center px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200 rounded">
											Custom: {custom.text}
										</span>
									{/each}
								</div>
							</div>
					<!-- Confirmation: two-button choice after moderation -->
					<div class="mt-3">
						{#if confirmedVersionIndex === null}
							<div class="flex space-x-3">
							<button
								on:click={() => {
									// Show moderation panel again for another iteration
									moderationPanelVisible = true;
									moderationPanelExpanded = true;
									toast.info('Select moderation strategies to create another version');
									
									// Scroll to moderation panel after it opens
									setTimeout(() => {
										if (moderationPanelElement) {
											moderationPanelElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
										}
									}, 100);
								}}
								class="flex-1 px-6 py-2 rounded-lg font-medium transition-all duration-200 bg-blue-500 hover:bg-blue-600 text-white shadow-lg hover:shadow-xl"
							>
								Moderate Again
							</button>
								<button
									on:click={() => {
										confirmCurrentVersion();
										// Confirmation will be saved in the session data
									}}
									class="flex-1 px-6 py-2 rounded-lg font-medium transition-all duration-200 bg-green-500 hover:bg-green-600 text-white shadow-lg hover:shadow-xl"
								>
									This is Good
								</button>
							</div>
						{/if}
					</div>
						{/if}
						</div>
					</div>

		<!-- Initial Decision Buttons -->
		{#if !hasInitialDecision}
			<div class="flex justify-center mt-4">
				<div class="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-2 w-full max-w-4xl px-4">
					<button
						on:click={() => {
							acceptOriginalResponse();
							// Decision will be saved when acceptOriginalResponse is called
						}}
					class="flex-1 px-6 py-4 rounded-lg font-medium transition-all duration-200 bg-green-500 hover:bg-green-600 text-white shadow-lg hover:shadow-xl flex items-center justify-center space-x-2"
				>
				<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
				</svg>
				<span>This is OK</span>
			</button>
			
			<button
				on:click={() => {
					startModerating();
					// Decision will be saved when moderation is applied
				}}
				class="flex-1 px-6 py-4 rounded-lg font-medium transition-all duration-200 bg-blue-500 hover:bg-blue-600 text-white shadow-lg hover:shadow-xl flex items-center justify-center space-x-2"
			>
				<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
				</svg>
				<span>Moderate</span>
			</button>
			
			<button
				on:click={markNotApplicable}
				class="flex-1 px-6 py-4 rounded-lg font-medium transition-all duration-200 bg-gray-500 hover:bg-gray-600 text-white shadow-lg hover:shadow-xl flex items-center justify-center space-x-2"
			>
					<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
					</svg>
					<span>Skip</span>
					</button>
				</div>
			</div>
		{/if}
		
		<!-- Highlighting Mode Prompt -->
		{#if highlightingMode}
			<div class="flex justify-center mt-6">
				<div class="w-full max-w-md px-4">
					<div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
						<div class="flex items-center justify-between mb-3">
							<p class="text-sm font-medium text-blue-900 dark:text-blue-200">
								If there is any text you would change in the prompt or response, if at all, please highlight it by dragging over it and then selecting "Highlight". If not, click "Done" to continue.
							</p>
							<button
								on:click={() => {
									highlightingMode = false;
									hasInitialDecision = false;
								}}
								class="ml-3 px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center justify-center space-x-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-gray-200 flex-shrink-0"
							>
								<svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
								</svg>
								<span>Back</span>
							</button>
						</div>
						<button
							on:click={finishHighlighting}
							class="w-full px-4 py-2 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg transition-colors"
						>
							{#if highlightedTexts1.length > 0}
								Done ({highlightedTexts1.length} concern{highlightedTexts1.length === 1 ? '' : 's'} highlighted)
							{:else}
								Done (no concerns highlighted)
							{/if}
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Confirmation Indicator moved below the response area -->
		{#if versions.length > 0 && !showOriginal1 && confirmedVersionIndex !== null}
			{#if confirmedVersionIndex === currentVersionIndex}
				<div class="mt-3">
					<div class="flex items-center justify-between px-3 py-2 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
						<div class="flex items-center space-x-2">
							<svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
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
					<div class="flex items-center justify-center px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
						<span class="text-xs font-medium text-gray-600 dark:text-gray-400">
							Another version is confirmed
						</span>
					</div>
				</div>
			{/if}
		{/if}

		<!-- Moderation Panel -->
		{#if moderationPanelVisible}
			<div class="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700" bind:this={moderationPanelElement}>
					<div class="flex items-center justify-between mb-1">
						<h3 class="text-sm font-semibold text-gray-900 dark:text-white">Select Moderation Strategies</h3>
						<button
							on:click={() => {
								moderationPanelVisible = false;
								moderationPanelExpanded = false;
								expandedGroups.clear();
								highlightingMode = false;
								hasInitialDecision = false;
							}}
							disabled={moderationLoading}
							class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center justify-center space-x-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-gray-200 disabled:opacity-50"
						>
							<svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
							</svg>
							<span>Back</span>
						</button>
					</div>
					
					<p class="text-base text-gray-600 dark:text-gray-400 mb-3">
						Choose up to <b>3 strategies</b> to improve the AI's response. Click on a group to see its strategies, or hover over each option for details.
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
						<div class="border-2 {
							category === 'Refuse and Remove' ? 'border-red-500 dark:border-red-600' :
							category === 'Investigate and Empathize' ? 'border-blue-500 dark:border-blue-600' :
							category === 'Correct their Understanding' ? 'border-green-500 dark:border-green-600' :
							category === 'Match their Age' ? 'border-yellow-500 dark:border-yellow-600' :
							category === 'Defer to Support' ? 'border-purple-500 dark:border-purple-600' :
							'border-pink-500 dark:border-pink-600'
						} rounded-lg bg-gray-50 dark:bg-gray-800/50">
							<!-- Group Header (Always Visible) -->
							<button
								on:click={() => toggleGroupExpansion(category)}
								class="w-full p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors rounded-lg"
							>
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<span class="w-3 h-3 rounded-full mr-3 {
											category === 'Refuse and Remove' ? 'bg-red-500' :
											category === 'Investigate and Empathize' ? 'bg-blue-500' :
											category === 'Correct their Understanding' ? 'bg-green-500' :
											category === 'Match their Age' ? 'bg-yellow-500' :
											category === 'Defer to Support' ? 'bg-purple-500' :
											'bg-pink-500'
										}"></span>
										<h4 class="text-base font-bold text-gray-900 dark:text-white">
											{category === 'Custom' && showCustomInput ? '✨ Custom (Open)' : category}
										</h4>
									</div>
									<div class="flex items-center space-x-2">
										{#if options.some(option => selectedModerations.has(option)) || (category === 'Custom' && customInstructions.length > 0)}
											<span class="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-full">
												{category === 'Custom' ? customInstructions.filter(c => selectedModerations.has(c.id)).length : options.filter(option => selectedModerations.has(option)).length} selected
											</span>
										{/if}
										{#if category !== 'Custom' || !showCustomInput}
											<svg class="w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform {
												expandedGroups.has(category) || (category === 'Custom' && showCustomInput) ? 'rotate-180' : ''
											}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
											</svg>
										{:else}
											<svg class="w-5 h-5 text-purple-500 dark:text-purple-400 transition-transform rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
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
											class="p-3 text-sm font-medium text-center rounded-lg transition-all min-h-[50px] flex items-center justify-center {
												selectedModerations.has(option)
													? 'bg-blue-500 text-white hover:bg-blue-600 ring-2 ring-blue-400 shadow-lg'
												: 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600'
											} disabled:opacity-50"
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
									<label class="block text-sm font-medium text-purple-900 dark:text-purple-200">
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
							<div class="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg mb-3">
								<h4 class="text-xs font-semibold text-purple-900 dark:text-purple-200 mb-2">
									Custom Instructions ({customInstructions.length}):
								</h4>
								<div class="space-y-2">
									{#each customInstructions as custom}
										<div class="flex items-start justify-between bg-white dark:bg-purple-900/30 p-2 rounded border-2 {
											selectedModerations.has(custom.id) 
												? 'border-purple-500' 
												: 'border-transparent'
										}">
											<button
												on:click={() => toggleModerationSelection(custom.id)}
												class="flex-1 text-left mr-2"
											>
												<div class="flex items-center space-x-1 mb-1">
													<div class="w-3 h-3 rounded border-2 {
														selectedModerations.has(custom.id)
															? 'bg-purple-500 border-purple-500'
															: 'border-gray-300 dark:border-gray-600'
													} flex items-center justify-center">
														{#if selectedModerations.has(custom.id)}
															<svg class="w-2 h-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
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
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
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
							disabled={moderationLoading || (selectedModerations.size === 0 && !attentionCheckSelected) || (selectedModerations.size === 0 && attentionCheckSelected)}
							class="w-full px-4 py-2.5 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2"
						>
							{#if moderationLoading}
								<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
								<span>Creating Version...</span>
							{:else}
								<span>Generate New Version</span>
							{/if}
						</button>
				</div>
			{/if}

			<!-- Footer with Navigation -->
			<div class="flex-shrink-0 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
				<div class="flex items-center justify-between">
					<!-- Previous Scenario Button -->
					{#if selectedScenarioIndex > 0}
						<button
							on:click={() => loadScenario(selectedScenarioIndex - 1)}
							class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex items-center space-x-2"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
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
				class="px-4 py-2 text-sm font-medium rounded-lg transition-all flex items-center space-x-2 {
					currentScenarioCompleted
						? 'bg-green-500 text-white hover:bg-green-600 shadow-lg hover:shadow-xl'
						: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
				}"
			>
				<span>Next</span>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
				</svg>
			</button>
			{:else}
				<button
					on:click={completeModeration}
					class="px-6 py-2 text-sm font-medium rounded-lg transition-all shadow-lg bg-purple-500 text-white hover:bg-purple-600 flex items-center space-x-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
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
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showConfirmationModal = false} role="dialog" aria-modal="true" aria-labelledby="confirmation-modal-title">
	<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" on:click|stopPropagation>
		<div class="text-center mb-6">
			<div class="w-16 h-16 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
				<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
				</svg>
			</div>
			<h3 id="confirmation-modal-title" class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
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
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={cancelReset} role="dialog" aria-modal="true" aria-labelledby="reset-confirmation-modal-title">
	<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" on:click|stopPropagation>
		<div class="text-center mb-6">
			<div class="w-16 h-16 bg-gradient-to-r from-red-500 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-4">
				<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
				</svg>
			</div>
			<h3 id="reset-confirmation-modal-title" class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
				Restart All Scenarios?
			</h3>
			<p class="text-gray-600 dark:text-gray-400">
				This will reset all your progress, including completed scenarios, timers, and moderation work. This action cannot be undone.
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

