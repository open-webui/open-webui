<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto, afterNavigate } from '$app/navigation';
	import { showSidebar, user, mobile } from '$lib/stores';
	import { get } from 'svelte/store';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { toast } from 'svelte-sonner';
	import AssignmentTimeTracker from '$lib/components/assignment/AssignmentTimeTracker.svelte';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import VideoModal from '$lib/components/common/VideoModal.svelte';
	import ChildPersonalitySection from '$lib/components/profile/ChildPersonalitySection.svelte';
	import { personalityTraits } from '$lib/data/personalityTraits';

	// Survey responses
	let surveyResponses: any = {
		parentGender: '',
		parentAge: '',
		areaOfResidency: '',
		parentEducation: '',
		parentEthnicity: [],
		genaiFamiliarity: '',
		genaiUsageFrequency: '',
		parentInternetUseFrequency: '', // 1 (never) to 8 (several times per day)
		parentingStyle: [], // Changed to array for multi-select
		// Child profile research fields
		isOnlyChild: '',
		childHasAIUse: '',
		childAIUseContexts: [],
		parentLLMMonitoringLevel: '',
		childGenderOther: '',
		childAIUseContextsOther: '',
		parentLLMMonitoringOther: '',
		childInternetUseFrequency: '', // 1 (never) to 8 (several times per day)
		// Child personality (Big 5) and additional info
		childPersonalitySubCharacteristics: [] as string[],
		childAdditionalInfo: ''
	};

	// API
	import { createExitQuiz, listExitQuiz } from '$lib/apis/exit-quiz';
	import { getChildProfiles as apiGetChildProfiles } from '$lib/apis/child-profiles';
	import {
		getCurrentAttempt,
		getWorkflowDraft,
		saveWorkflowDraft,
		deleteWorkflowDraft
	} from '$lib/apis/workflow';

	// Save/Edit pattern state
	let isSaved: boolean = false;
	let showConfirmationModal: boolean = false;

	// Attempt and child context (populated in onMount from backend)
	let attemptNumber: number = 1;
	let currentChildId: string | null = null;
	let currentChildProfile: any = null;

	// Assignment time tracking
	$: sessionNumber = $user?.session_number || 1;

	// Video modal state
	let showHelpVideo: boolean = false;

	// Debounce helper
	function debounce(fn: (...args: any[]) => void, delay = 400) {
		let t: any;
		return (...args: any[]) => {
			clearTimeout(t);
			t = setTimeout(() => fn(...args), delay);
		};
	}

	// 8-point scale: How often do you use the Internet? (1 = never to 8 = several times per day)
	const INTERNET_USE_SCALE: { value: string; label: string }[] = [
		{ value: '1', label: 'Never' },
		{ value: '2', label: 'Less than once a month' },
		{ value: '3', label: 'About once a month' },
		{ value: '4', label: 'About once a week' },
		{ value: '5', label: 'Several times a week' },
		{ value: '6', label: 'About once a day' },
		{ value: '7', label: 'Once a day' },
		{ value: '8', label: 'Several times per day' }
	];

	function getInternetUseLabel(value: string): string {
		return INTERNET_USE_SCALE.find((s) => s.value === value)?.label || value || 'Not specified';
	}

	/** Format selected personality sub-characteristic IDs into readable string (TraitName: char1, char2; ...). */
	function formatPersonalityDescription(selectedIds: string[]): string {
		if (!selectedIds || selectedIds.length === 0) return '';
		const traitGroups = new Map<string, string[]>();
		for (const id of selectedIds) {
			for (const trait of personalityTraits) {
				const sub = trait.subCharacteristics.find((sc) => sc.id === id);
				if (sub) {
					if (!traitGroups.has(trait.name)) traitGroups.set(trait.name, []);
					traitGroups.get(trait.name)!.push(sub.name);
					break;
				}
			}
		}
		return [...traitGroups.entries()]
			.map(([name, chars]) => `${name}: ${chars.join(', ')}`)
			.join('; ');
	}

	async function resolveChildId(token: string): Promise<string> {
		let child_id = '';

		// Primary source: backend-persisted current child ID
		const currentChildId = childProfileSync.getCurrentChildId();
		if (currentChildId) {
			child_id = currentChildId;
		} else {
			// Fallback: use cached child profile
			const currentChild = childProfileSync.getCurrentChild();
			if (currentChild?.id) {
				child_id = currentChild.id;
			} else {
				// Fallback: use first available profile
				const profiles = await childProfileSync.getChildProfiles();
				if (profiles && Array.isArray(profiles) && profiles.length > 0) {
					child_id = profiles[0]?.id || '';
				} else {
					try {
						const apiProfiles = await apiGetChildProfiles(token);
						if (apiProfiles && Array.isArray(apiProfiles) && apiProfiles.length > 0) {
							child_id = apiProfiles[0]?.id || '';
						}
					} catch {}
				}
			}
		}
		return child_id;
	}

	/** Apply loaded answers into surveyResponses in place so bind:group and other bindings update. */
	function applyAnswersToForm(ans: Record<string, unknown>) {
		surveyResponses.parentGender = (ans.parentGender as string) || '';
		surveyResponses.parentAge = (ans.parentAge as string) || '';
		surveyResponses.areaOfResidency = (ans.areaOfResidency as string) || '';
		surveyResponses.parentEducation = (ans.parentEducation as string) || '';
		surveyResponses.parentEthnicity = Array.isArray(ans.parentEthnicity)
			? [...ans.parentEthnicity]
			: [];
		surveyResponses.genaiFamiliarity = (ans.genaiFamiliarity as string) || '';
		surveyResponses.genaiUsageFrequency = (ans.genaiUsageFrequency as string) || '';
		surveyResponses.parentInternetUseFrequency = (ans.parentInternetUseFrequency as string) || '';
		surveyResponses.parentingStyle = Array.isArray(ans.parentingStyle)
			? [...ans.parentingStyle]
			: ans.parentingStyle
				? [ans.parentingStyle]
				: [];
		// Child profile research fields
		surveyResponses.isOnlyChild = (ans.isOnlyChild as string) || '';
		surveyResponses.childHasAIUse = (ans.childHasAIUse as string) || '';
		surveyResponses.childAIUseContexts = Array.isArray(ans.childAIUseContexts)
			? [...ans.childAIUseContexts]
			: [];
		surveyResponses.parentLLMMonitoringLevel = (ans.parentLLMMonitoringLevel as string) || '';
		surveyResponses.childGenderOther = (ans.childGenderOther as string) || '';
		surveyResponses.childAIUseContextsOther = (ans.childAIUseContextsOther as string) || '';
		surveyResponses.parentLLMMonitoringOther = (ans.parentLLMMonitoringOther as string) || '';
		surveyResponses.childInternetUseFrequency = (ans.childInternetUseFrequency as string) || '';
		surveyResponses.childPersonalitySubCharacteristics = Array.isArray(
			ans.childPersonalitySubCharacteristics
		)
			? [...(ans.childPersonalitySubCharacteristics as string[])]
			: [];
		surveyResponses.childAdditionalInfo = (ans.childAdditionalInfo as string) || '';
	}

	/** Load saved responses from backend (exit quiz rows or draft) so the form repopulates when revisiting the page after completion. */
	async function loadSavedResponses() {
		const token = localStorage.token || '';
		const childId = await resolveChildId(token);

		// Get current attempt number and child ID
		try {
			if (token) {
				const attemptData = await getCurrentAttempt(token);
				attemptNumber = attemptData.current_attempt || 1;
			}
			const currentChild = childProfileSync.getCurrentChild();
			currentChildId = currentChild?.id || null;
			currentChildProfile = currentChild;
		} catch (e) {
			console.warn('Failed to get attempt number or child ID', e);
		}

		// Rehydrate from backend: only use responses for the current attempt (after reset, this returns [] so form stays empty)
		if (token) {
			try {
				const rows = await listExitQuiz(token, childId || undefined, true);
				if (rows && Array.isArray(rows) && rows.length > 0) {
					const latest = [...rows].sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0))[0];
					const ans: Record<string, unknown> = (latest?.answers as Record<string, unknown>) || {};
					applyAnswersToForm(ans);
					isSaved = true;
					await tick(); // flush so bind:group and DOM see the updated values
					window.dispatchEvent(new Event('workflow-updated'));
					return;
				}
			} catch (e) {
				console.warn('Failed to load exit quiz responses for repopulation', e);
			}
		}

		// Load draft from backend when no submitted response exists
		if (childId && token) {
			try {
				const draftRes = await getWorkflowDraft(token, childId, 'exit_survey');
				if (draftRes?.data && typeof draftRes.data === 'object') {
					const d = draftRes.data as Record<string, unknown>;
					applyAnswersToForm(d);
					await tick();
				}
			} catch {}
		}
	}

	onMount(async () => {
		// Ensure sidebar is visible on survey pages (unless on mobile)
		if (!$mobile) {
			showSidebar.set(true);
		}
		await loadSavedResponses();
	});

	// Repopulate when navigating back to exit survey (e.g. from completion) so the form shows saved data for the session
	afterNavigate(async ({ to }) => {
		if (to?.pathname && to.pathname.startsWith('/exit-survey')) {
			await loadSavedResponses();
		}
	});

	async function submitSurvey() {
		try {
			// Validate required fields
			if (!surveyResponses.parentGender) {
				toast.error('Please select your gender');
				return;
			}
			if (!surveyResponses.parentAge) {
				toast.error('Please select your age range');
				return;
			}
			if (!surveyResponses.areaOfResidency) {
				toast.error('Please select your area of residency');
				return;
			}
			if (!surveyResponses.parentEducation) {
				toast.error('Please select your education level');
				return;
			}
			if (!surveyResponses.genaiFamiliarity) {
				toast.error('Please select your familiarity with LLMs');
				return;
			}
			if (!surveyResponses.genaiUsageFrequency) {
				toast.error('Please select your personal AI use frequency');
				return;
			}
			if (!surveyResponses.parentingStyle || surveyResponses.parentingStyle.length === 0) {
				toast.error('Please select at least one parenting style');
				return;
			}
			if (!surveyResponses.parentInternetUseFrequency) {
				toast.error('Please select how often you use the Internet');
				return;
			}
			if (!surveyResponses.parentEthnicity || surveyResponses.parentEthnicity.length === 0) {
				toast.error('Please select at least one ethnicity');
				return;
			}
			if (!surveyResponses.childInternetUseFrequency) {
				toast.error('Please select how often this child uses the Internet');
				return;
			}
			const hasPersonality =
				(surveyResponses.childPersonalitySubCharacteristics &&
					surveyResponses.childPersonalitySubCharacteristics.length > 0) ||
				(surveyResponses.childAdditionalInfo && surveyResponses.childAdditionalInfo.trim() !== '');
			if (!hasPersonality) {
				toast.error(
					'Please select at least one personality characteristic or add additional information about your child'
				);
				return;
			}

			// Resolve child_id using the consolidated resolveChildId function
			const token = localStorage.token || '';
			let child_id = await resolveChildId(token);

			if (!child_id) {
				toast.error(
					'No child profile found. Please create/select a child on the Child Profile page.'
				);
				return;
			}

			// Map survey responses into answers payload
			const answers = {
				parentGender: surveyResponses.parentGender,
				parentAge: surveyResponses.parentAge,
				areaOfResidency: surveyResponses.areaOfResidency,
				parentEducation: surveyResponses.parentEducation,
				parentEthnicity: surveyResponses.parentEthnicity,
				genaiFamiliarity: surveyResponses.genaiFamiliarity,
				genaiUsageFrequency: surveyResponses.genaiUsageFrequency,
				parentInternetUseFrequency: surveyResponses.parentInternetUseFrequency,
				parentingStyle: surveyResponses.parentingStyle, // Now an array
				// Child profile research fields
				isOnlyChild: surveyResponses.isOnlyChild,
				childHasAIUse: surveyResponses.childHasAIUse,
				childAIUseContexts: surveyResponses.childAIUseContexts,
				parentLLMMonitoringLevel: surveyResponses.parentLLMMonitoringLevel,
				childGenderOther: surveyResponses.childGenderOther,
				childAIUseContextsOther: surveyResponses.childAIUseContextsOther,
				parentLLMMonitoringOther: surveyResponses.parentLLMMonitoringOther,
				childInternetUseFrequency: surveyResponses.childInternetUseFrequency,
				childPersonalitySubCharacteristics: surveyResponses.childPersonalitySubCharacteristics,
				childAdditionalInfo: surveyResponses.childAdditionalInfo
			};

			// Persist to backend (exit quiz)
			await createExitQuiz(token, { child_id, answers, meta: { page: 'exit-survey' } });

			window.dispatchEvent(new Event('workflow-updated'));
			isSaved = true;
			showConfirmationModal = true;

			// Clear draft in backend
			try {
				await deleteWorkflowDraft(token, child_id, 'exit_survey');
			} catch {}
		} catch (error) {
			console.error('Error saving survey:', error);
			toast.error('Failed to save survey. Please try again.');
		}
	}

	// Autosave draft on changes (debounced) - saves to backend
	const saveDraft = debounce(async () => {
		const token = localStorage.token || '';
		const cid = await resolveChildId(token);
		if (cid && token) {
			try {
				await saveWorkflowDraft(
					token,
					cid,
					'exit_survey',
					surveyResponses as Record<string, unknown>
				);
			} catch {}
		}
	}, 500);

	$: saveDraft();

	function startEditing() {
		isSaved = false;
	}

	function proceedToNextStep() {
		window.dispatchEvent(new Event('workflow-updated'));
		goto('/completion');
	}

	function continueEditing() {
		showConfirmationModal = false;
	}

	function handleNextTask() {
		if (isSaved) {
			showConfirmationModal = true;
		} else {
			toast.error('Please save the survey before proceeding to the next task');
		}
	}

	function goBack() {
		goto('/moderation-scenario');
	}
</script>

<svelte:head>
	<title>Exit Survey</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav
		class="px-2.5 pt-1.5 pb-2 backdrop-blur-xl w-full drag-region bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800"
	>
		<div class="flex items-center justify-between">
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

				<div class="flex w-full">
					<div class="flex items-center text-xl font-semibold">Exit Survey</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<!-- Help Button -->
				<button
					on:click={() => (showHelpVideo = true)}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
					aria-label="Show help video"
				>
					Help
				</button>
				<button
					on:click={goBack}
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
					<span>Previous Task</span>
				</button>
				<button
					on:click={handleNextTask}
					disabled={!isSaved}
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 {isSaved
						? 'bg-blue-500 hover:bg-blue-600 text-white'
						: 'text-gray-400 dark:text-gray-500 cursor-not-allowed'}"
				>
					<span>Next Task</span>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"
						></path>
					</svg>
				</button>
			</div>
		</div>
	</nav>

	<div class="flex-1 max-h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
		<div class="max-w-4xl mx-auto px-4 py-8">
			<!-- Header -->
			<div class="mb-8">
				<div>
					<h1 class="text-3xl font-bold text-gray-900 dark:text-white">Exit Survey</h1>
					<p class="text-gray-600 dark:text-gray-300 mt-2">
						Please complete the exit survey to help us understand our participants
					</p>
				</div>
			</div>

			<!-- Survey Display/Form -->
			{#if isSaved}
				<!-- Read-only view after saving -->
				<div class="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
					<div class="flex justify-between items-start mb-6">
						<h3 class="text-xl font-semibold text-gray-900 dark:text-white">
							Exit Survey Responses
						</h3>
						<button
							type="button"
							on:click={startEditing}
							class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition"
						>
							Edit
						</button>
					</div>
					<div class="space-y-4">
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Parenting Style
							</div>
							<p class="text-gray-900 dark:text-white">
								{(() => {
									const arr = Array.isArray(surveyResponses.parentingStyle)
										? surveyResponses.parentingStyle
										: surveyResponses.parentingStyle
											? [surveyResponses.parentingStyle]
											: [];
									if (arr.length === 0) return 'Not specified';
									const styleLabels: Record<string, string> = {
										A: "I set clear rules and follow through, but I explain my reasons, listen to my child's point of view, and encourage independence.",
										B: "I set strict rules and expect obedience; I rarely negotiate and use firm consequences when rules aren't followed.",
										C: "I'm warm and supportive with few rules or demands; my child mostly sets their own routines and limits.",
										D: 'I give my child a lot of freedom and usually take a hands-off approach unless safety or basic needs require me to step in.',
										E: 'None of these fits me / It depends on the situation.',
										'prefer-not-to-answer': 'Prefer not to answer'
									};
									return arr.map((style: string) => styleLabels[style] || style).join('; ');
								})()}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								GenAI Familiarity
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.genaiFamiliarity || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								GenAI Usage Frequency
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.genaiUsageFrequency || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								How often do you use the Internet? (parent)
							</div>
							<p class="text-gray-900 dark:text-white">
								{getInternetUseLabel(surveyResponses.parentInternetUseFrequency)}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Gender
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.parentGender || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Age Range
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.parentAge || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Area of Residency
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.areaOfResidency || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Education Level
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.parentEducation || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Ethnicity
							</div>
							<p class="text-gray-900 dark:text-white">
								{Array.isArray(surveyResponses.parentEthnicity) &&
								surveyResponses.parentEthnicity.length > 0
									? surveyResponses.parentEthnicity.join(', ')
									: 'Not specified'}
							</p>
						</div>
						<!-- Child Profile Research Fields -->
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								How often does this child use the Internet?
							</div>
							<p class="text-gray-900 dark:text-white">
								{getInternetUseLabel(surveyResponses.childInternetUseFrequency)}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Is this child an only child?
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.isOnlyChild === 'yes'
									? 'Yes'
									: surveyResponses.isOnlyChild === 'no'
										? 'No'
										: surveyResponses.isOnlyChild === 'prefer_not_to_say'
											? 'Prefer not to say'
											: 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Has this child used ChatGPT or similar AI tools?
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.childHasAIUse === 'yes'
									? 'Yes'
									: surveyResponses.childHasAIUse === 'no'
										? 'No'
										: surveyResponses.childHasAIUse === 'unsure'
											? 'Not sure'
											: surveyResponses.childHasAIUse === 'prefer_not_to_say'
												? 'Prefer not to say'
												: 'Not specified'}
							</p>
						</div>
						{#if surveyResponses.childHasAIUse === 'yes'}
							<div>
								<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
									In what contexts has this child used these tools?
								</div>
								<p class="text-gray-900 dark:text-white">
									{(() => {
										const arr = Array.isArray(surveyResponses.childAIUseContexts)
											? surveyResponses.childAIUseContexts
											: [];
										if (arr.length === 0) return 'Not specified';
										const labels: Record<string, string> = {
											school_homework: 'For school or homework',
											general_knowledge: 'For general knowledge or casual questions',
											games_chatting: 'For playing games or chatting with the AI',
											personal_advice: 'For advice on personal or social issues',
											other: surveyResponses.childAIUseContextsOther || 'Other'
										};
										return arr.map((v: string) => labels[v] || v).join('; ');
									})()}
								</p>
							</div>
						{/if}
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Have you monitored or adjusted your child's use of LLMs like ChatGPT?
							</div>
							<p class="text-gray-900 dark:text-white">
								{surveyResponses.parentLLMMonitoringLevel === 'active_rules'
									? 'Yes — I actively monitor and set rules/limits'
									: surveyResponses.parentLLMMonitoringLevel === 'occasional_guidance'
										? 'Yes — occasional reminders or guidance'
										: surveyResponses.parentLLMMonitoringLevel === 'plan_to'
											? 'Not yet, but I plan to'
											: surveyResponses.parentLLMMonitoringLevel === 'no_monitoring'
												? 'No — I have not monitored or adjusted'
												: surveyResponses.parentLLMMonitoringLevel === 'other'
													? surveyResponses.parentLLMMonitoringOther || 'Other'
													: 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Child personality (selected traits)
							</div>
							<p class="text-gray-900 dark:text-white">
								{formatPersonalityDescription(surveyResponses.childPersonalitySubCharacteristics) ||
									'None selected'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Additional information about child
							</div>
							<p class="text-gray-900 dark:text-white whitespace-pre-wrap">
								{surveyResponses.childAdditionalInfo || 'None provided'}
							</p>
						</div>
					</div>
				</div>
			{:else}
				<!-- Editable form -->
				<div class="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
					<form on:submit|preventDefault={submitSurvey} class="space-y-8">
						<!-- Question 1: Parenting Style (multi-select) -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								1. Which of these descriptions match your typical approach to day-to-day parenting?
								(Select all that apply.) <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentingStyle}
										value="A"
										class="mr-3"
										id="parenting-style-a"
									/>
									<span class="text-gray-900 dark:text-white"
										>I set clear rules and follow through, but I explain my reasons, listen to my
										child's point of view, and encourage independence.</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentingStyle}
										value="B"
										class="mr-3"
										id="parenting-style-b"
									/>
									<span class="text-gray-900 dark:text-white"
										>I set strict rules and expect obedience; I rarely negotiate and use firm
										consequences when rules aren't followed.</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentingStyle}
										value="C"
										class="mr-3"
										id="parenting-style-c"
									/>
									<span class="text-gray-900 dark:text-white"
										>I'm warm and supportive with few rules or demands; my child mostly sets their
										own routines and limits.</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentingStyle}
										value="D"
										class="mr-3"
										id="parenting-style-d"
									/>
									<span class="text-gray-900 dark:text-white"
										>I give my child a lot of freedom and usually take a hands-off approach unless
										safety or basic needs require me to step in.</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentingStyle}
										value="E"
										class="mr-3"
										id="parenting-style-e"
									/>
									<span class="text-gray-900 dark:text-white"
										>None of these fits me / It depends on the situation.</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentingStyle}
										value="prefer-not-to-answer"
										class="mr-3"
										id="parenting-style-prefer-not-to-answer"
									/>
									<span class="text-gray-900 dark:text-white">Prefer not to answer</span>
								</label>
							</div>
						</div>

						<!-- 2. How often do you use the Internet? (parent) - 8-point scale -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								2. How often do you use the Internet? <span class="text-red-500">*</span>
							</div>
							<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
								Scale: 1 (never) to 8 (several times per day).
							</p>
							<div class="space-y-2">
								{#each INTERNET_USE_SCALE as option}
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentInternetUseFrequency}
											value={option.value}
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">{option.value}. {option.label}</span
										>
									</label>
								{/each}
							</div>
						</div>

						<!-- 3. GenAI familiarity -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								3. How familiar are you with ChatGPT or other Large Language Models (LLMs)? <span
									class="text-red-500">*</span
								>
							</div>
							<div class="space-y-2">
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiFamiliarity}
										value="regular_user"
										class="mr-3"
									/>I regularly use ChatGPT or other LLMs for work or personal use</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiFamiliarity}
										value="tried_few_times"
										class="mr-3"
									/>I have tried them a few times but don’t use them often</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiFamiliarity}
										value="heard_never_used"
										class="mr-3"
									/>I have heard of them but never used them</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiFamiliarity}
										value="dont_know"
										class="mr-3"
									/>I don’t know what they are</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiFamiliarity}
										value="prefer-not-to-answer"
										class="mr-3"
									/>Prefer not to answer</label
								>
							</div>
						</div>

						<!-- 4. Personal GenAI use frequency -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								4. How often do you personally use ChatGPT or similar AI tools? <span
									class="text-red-500">*</span
								>
							</div>
							<div class="space-y-2">
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiUsageFrequency}
										value="daily"
										class="mr-3"
									/>Daily or almost daily</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiUsageFrequency}
										value="weekly"
										class="mr-3"
									/>Weekly</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiUsageFrequency}
										value="monthly_or_less"
										class="mr-3"
									/>Monthly or less</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiUsageFrequency}
										value="do_not_use"
										class="mr-3"
									/>I do not use these tools</label
								>
								<label class="flex items-center"
									><input
										type="radio"
										bind:group={surveyResponses.genaiUsageFrequency}
										value="prefer-not-to-answer"
										class="mr-3"
									/>Prefer not to answer</label
								>
							</div>
						</div>

						<!-- 5. Parent Gender -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								5. What is your gender? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentGender}
										value="male"
										class="mr-3"
										id="gender-male"
									/>
									<span class="text-gray-900 dark:text-white">Male</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentGender}
										value="female"
										class="mr-3"
										id="gender-female"
									/>
									<span class="text-gray-900 dark:text-white">Female</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentGender}
										value="non-binary"
										class="mr-3"
										id="gender-non-binary"
									/>
									<span class="text-gray-900 dark:text-white">Non-binary</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentGender}
										value="other"
										class="mr-3"
										id="gender-other"
									/>
									<span class="text-gray-900 dark:text-white">Other</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentGender}
										value="prefer-not-to-say"
										class="mr-3"
										id="gender-prefer-not-to-say"
									/>
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

						<!-- 6. Parent Age -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								6. What is your age range? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="18-24"
										class="mr-3"
										id="age-18-24"
									/>
									<span class="text-gray-900 dark:text-white">18-24 years</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="25-34"
										class="mr-3"
										id="age-25-34"
									/>
									<span class="text-gray-900 dark:text-white">25-34 years</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="35-44"
										class="mr-3"
										id="age-35-44"
									/>
									<span class="text-gray-900 dark:text-white">35-44 years</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="45-54"
										class="mr-3"
										id="age-45-54"
									/>
									<span class="text-gray-900 dark:text-white">45-54 years</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="55-64"
										class="mr-3"
										id="age-55-64"
									/>
									<span class="text-gray-900 dark:text-white">55-64 years</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="65+"
										class="mr-3"
										id="age-65-plus"
									/>
									<span class="text-gray-900 dark:text-white">65+ years</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentAge}
										value="prefer-not-to-say"
										class="mr-3"
										id="age-prefer-not-to-say"
									/>
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

						<!-- 7. Area of Residency -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								7. What type of area do you live in? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.areaOfResidency}
										value="urban"
										class="mr-3"
										id="area-urban"
									/>
									<span class="text-gray-900 dark:text-white">Urban (city)</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.areaOfResidency}
										value="suburban"
										class="mr-3"
										id="area-suburban"
									/>
									<span class="text-gray-900 dark:text-white">Suburban</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.areaOfResidency}
										value="rural"
										class="mr-3"
										id="area-rural"
									/>
									<span class="text-gray-900 dark:text-white">Rural (countryside)</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.areaOfResidency}
										value="prefer-not-to-say"
										class="mr-3"
										id="area-prefer-not-to-say"
									/>
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

						<!-- 8. Parent Education -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								8. What is your highest level of education? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="high-school"
										class="mr-3"
										id="education-high-school"
									/>
									<span class="text-gray-900 dark:text-white"
										>High school diploma or equivalent</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="some-college"
										class="mr-3"
										id="education-some-college"
									/>
									<span class="text-gray-900 dark:text-white">Some college, no degree</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="associates"
										class="mr-3"
										id="education-associates"
									/>
									<span class="text-gray-900 dark:text-white">Associate degree</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="bachelors"
										class="mr-3"
										id="education-bachelors"
									/>
									<span class="text-gray-900 dark:text-white">Bachelor's degree</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="masters"
										class="mr-3"
										id="education-masters"
									/>
									<span class="text-gray-900 dark:text-white">Master's degree</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="doctoral"
										class="mr-3"
										id="education-doctoral"
									/>
									<span class="text-gray-900 dark:text-white">Doctoral degree</span>
								</label>
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={surveyResponses.parentEducation}
										value="prefer-not-to-say"
										class="mr-3"
										id="education-prefer-not-to-say"
									/>
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

						<!-- 9. Parent Ethnicity -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								9. What is your ethnicity? (Select all that apply) <span class="text-red-500"
									>*</span
								>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="white"
										class="mr-3"
										id="ethnicity-white"
									/>
									<span class="text-gray-900 dark:text-white">White</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="black-african-american"
										class="mr-3"
										id="ethnicity-black-african-american"
									/>
									<span class="text-gray-900 dark:text-white">Black or African American</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="hispanic-latino"
										class="mr-3"
										id="ethnicity-hispanic-latino"
									/>
									<span class="text-gray-900 dark:text-white">Hispanic or Latino</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="asian"
										class="mr-3"
										id="ethnicity-asian"
									/>
									<span class="text-gray-900 dark:text-white">Asian</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="native-american"
										class="mr-3"
										id="ethnicity-native-american"
									/>
									<span class="text-gray-900 dark:text-white">Native American or Alaska Native</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="pacific-islander"
										class="mr-3"
										id="ethnicity-pacific-islander"
									/>
									<span class="text-gray-900 dark:text-white"
										>Native Hawaiian or Pacific Islander</span
									>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="middle-eastern"
										class="mr-3"
										id="ethnicity-middle-eastern"
									/>
									<span class="text-gray-900 dark:text-white">Middle Eastern or North African</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="mixed-race"
										class="mr-3"
										id="ethnicity-mixed-race"
									/>
									<span class="text-gray-900 dark:text-white">Mixed race</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="other"
										class="mr-3"
										id="ethnicity-other"
									/>
									<span class="text-gray-900 dark:text-white">Other</span>
								</label>
								<label class="flex items-center">
									<input
										type="checkbox"
										bind:group={surveyResponses.parentEthnicity}
										value="prefer-not-to-say"
										class="mr-3"
										id="ethnicity-prefer-not-to-say"
									/>
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

						<!-- Child Profile Research Fields (moved from child profile form) -->
						<div class="pt-6 border-t border-gray-300 dark:border-gray-700">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
								Child Profile Information
							</h3>

							<!-- Display current child info to jog memory -->
							{#if currentChildProfile}
								<div
									class="mb-6 px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
								>
									<p class="text-sm text-gray-700 dark:text-gray-300">
										<strong>Answering about:</strong>
										{#if currentChildProfile.name}
											{currentChildProfile.name}
											{#if currentChildProfile.age || currentChildProfile.gender}
												<span class="text-gray-600 dark:text-gray-400">
													({[
														currentChildProfile.age ? `Age ${currentChildProfile.age}` : '',
														currentChildProfile.gender
													]
														.filter(Boolean)
														.join(', ')})
												</span>
											{/if}
										{:else}
											{[
												currentChildProfile.age ? `Age ${currentChildProfile.age}` : '',
												currentChildProfile.gender
											]
												.filter(Boolean)
												.join(', ') || 'Child profile'}
										{/if}
									</p>
								</div>
							{/if}

							<!-- Is Only Child -->
							<div class="mb-6">
								<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Is this child an only child? <span class="text-red-500">*</span>
								</div>
								<div class="space-y-2">
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.isOnlyChild}
											value="yes"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Yes</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.isOnlyChild}
											value="no"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">No</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.isOnlyChild}
											value="prefer_not_to_say"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Prefer not to say</span>
									</label>
								</div>
							</div>

							<!-- How often does this child use the Internet? - 8-point scale -->
							<div class="mb-6">
								<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									How often does this child use the Internet? <span class="text-red-500">*</span>
								</div>
								<p class="text-xs text-gray-600 dark:text-gray-400 mb-2">
									Scale: 1 (never) to 8 (several times per day).
								</p>
								<div class="space-y-2">
									{#each INTERNET_USE_SCALE as option}
										<label class="flex items-center">
											<input
												type="radio"
												bind:group={surveyResponses.childInternetUseFrequency}
												value={option.value}
												class="mr-3"
											/>
											<span class="text-gray-900 dark:text-white"
												>{option.value}. {option.label}</span
											>
										</label>
									{/each}
								</div>
							</div>

							<!-- Child Has AI Use -->
							<div class="mb-6">
								<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Has this child used ChatGPT or similar AI tools? <span class="text-red-500"
										>*</span
									>
								</div>
								<div class="space-y-2">
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.childHasAIUse}
											value="yes"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Yes</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.childHasAIUse}
											value="no"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">No</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.childHasAIUse}
											value="unsure"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Not sure</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.childHasAIUse}
											value="prefer_not_to_say"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Prefer not to say</span>
									</label>
								</div>
							</div>

							<!-- Child AI Use Contexts (if yes) -->
							{#if surveyResponses.childHasAIUse === 'yes'}
								<div class="mb-6">
									<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										In what contexts has this child used these tools? <span class="text-red-500"
											>*</span
										>
									</div>
									<div class="space-y-2">
										<label class="flex items-center">
											<input
												type="checkbox"
												bind:group={surveyResponses.childAIUseContexts}
												value="school_homework"
												class="mr-3"
											/>
											<span class="text-gray-900 dark:text-white">For school or homework</span>
										</label>
										<label class="flex items-center">
											<input
												type="checkbox"
												bind:group={surveyResponses.childAIUseContexts}
												value="general_knowledge"
												class="mr-3"
											/>
											<span class="text-gray-900 dark:text-white"
												>For general knowledge or casual questions</span
											>
										</label>
										<label class="flex items-center">
											<input
												type="checkbox"
												bind:group={surveyResponses.childAIUseContexts}
												value="games_chatting"
												class="mr-3"
											/>
											<span class="text-gray-900 dark:text-white"
												>For playing games or chatting with the AI</span
											>
										</label>
										<label class="flex items-center">
											<input
												type="checkbox"
												bind:group={surveyResponses.childAIUseContexts}
												value="personal_advice"
												class="mr-3"
											/>
											<span class="text-gray-900 dark:text-white"
												>For advice on personal or social issues</span
											>
										</label>
										<label class="flex items-center">
											<input
												type="checkbox"
												bind:group={surveyResponses.childAIUseContexts}
												value="other"
												class="mr-3"
											/>
											<span class="text-gray-900 dark:text-white">Other</span>
										</label>
										{#if surveyResponses.childAIUseContexts.includes('other')}
											<input
												type="text"
												bind:value={surveyResponses.childAIUseContextsOther}
												placeholder="Please specify the context"
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white mt-2"
											/>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Parent LLM Monitoring Level -->
							<div class="mb-6">
								<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Have you monitored or adjusted your child's use of Large Language Models like
									ChatGPT? <span class="text-red-500">*</span>
								</div>
								<div class="space-y-2">
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentLLMMonitoringLevel}
											value="active_rules"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white"
											>Yes — I actively monitor and set rules/limits</span
										>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentLLMMonitoringLevel}
											value="occasional_guidance"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white"
											>Yes — occasional reminders or guidance</span
										>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentLLMMonitoringLevel}
											value="plan_to"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Not yet, but I plan to</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentLLMMonitoringLevel}
											value="no_monitoring"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white"
											>No — I have not monitored or adjusted</span
										>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentLLMMonitoringLevel}
											value="other"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Other</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={surveyResponses.parentLLMMonitoringLevel}
											value="prefer_not_to_say"
											class="mr-3"
										/>
										<span class="text-gray-900 dark:text-white">Prefer not to say</span>
									</label>
									{#if surveyResponses.parentLLMMonitoringLevel === 'other'}
										<input
											type="text"
											bind:value={surveyResponses.parentLLMMonitoringOther}
											placeholder="Please specify how you have monitored or adjusted your child's AI use"
											class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white mt-2"
										/>
									{/if}
								</div>
							</div>
						</div>

						<!-- Child personality (Big Five) and additional info -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-2">
								Child personality (Big Five) <span class="text-red-500">*</span>
							</div>
							<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
								Select at least one personality characteristic that describes your child, or add
								additional details below.
							</p>
							<ChildPersonalitySection
								bind:selectedSubCharacteristics={surveyResponses.childPersonalitySubCharacteristics}
								bind:additionalInfo={surveyResponses.childAdditionalInfo}
								required={true}
							/>
						</div>

						<!-- Submit Button -->
						<div class="flex justify-end pt-6">
							<button
								type="submit"
								class="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
							>
								Submit Survey
							</button>
						</div>
					</form>
				</div>
			{/if}
		</div>
	</div>

	<!-- Confirmation Modal for Workflow Progression -->
	{#if showConfirmationModal}
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
		<div
			class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
			on:click={() => (showConfirmationModal = false)}
			on:keydown={(e) => e.key === 'Escape' && (showConfirmationModal = false)}
			role="dialog"
			aria-modal="true"
			aria-labelledby="confirmation-modal-title"
		>
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl"
				on:click|stopPropagation
			>
				<div class="text-center mb-6">
					<div
						class="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4"
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
					<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Task 3 Complete</h3>
					<p class="text-gray-600 dark:text-gray-400">
						Would you like to proceed to the completion page?
					</p>
				</div>

				<div class="flex flex-col space-y-3">
					<button
						on:click={proceedToNextStep}
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
					>
						Yes, Proceed to Completion
					</button>
					<button
						on:click={continueEditing}
						class="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
					>
						No, Continue Editing
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Assignment Time Tracker -->
	<AssignmentTimeTracker userId={get(user)?.id || ''} {sessionNumber} enabled={true} />

	<!-- Help Video Modal -->
	<VideoModal
		isOpen={showHelpVideo}
		videoSrc="/video/Exit-Survey-Demo.mp4"
		title="Exit Survey Tutorial"
	/>
</div>
