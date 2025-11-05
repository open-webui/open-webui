<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar, user } from '$lib/stores';
	import { get } from 'svelte/store';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { toast } from 'svelte-sonner';
	import AssignmentTimeTracker from '$lib/components/assignment/AssignmentTimeTracker.svelte';
	import { getCurrentAttempt } from '$lib/apis/workflow';
	import { childProfileSync } from '$lib/services/childProfileSync';

	// Assignment workflow state
	let assignmentStep: number = 1;

    // Survey responses
	let surveyResponses = {
		parentGender: '',
		parentAge: '',
		areaOfResidency: '',
		parentEducation: '',
    parentEthnicity: [],
    genaiFamiliarity: '',
    genaiUsageFrequency: '',
    parentingStyle: ''
	};

    // API
    import { createExitQuiz, listExitQuiz } from '$lib/apis/exit-quiz';
    import { getChildProfiles as apiGetChildProfiles } from '$lib/apis/child-profiles';

	// Save/Edit pattern state
	let isSaved: boolean = false;
	let showConfirmationModal: boolean = false;

	// Assignment time tracking
	let attemptNumber: number = 1;
	let currentChildId: string | null = null;

// Debounce helper
function debounce(fn: (...args: any[]) => void, delay = 400) {
    let t: any;
    return (...args: any[]) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), delay);
    };
}

function draftKey(userId: string, childId: string) {
    const u = userId || 'anon';
    const c = childId || 'pending';
    return `exitSurveyDraft:${u}:${c}`;
}
function completedKey(userId: string, childId: string) {
    const u = userId || 'anon';
    const c = childId || 'pending';
    return `exitSurveyCompleted:${u}:${c}`;
}

async function resolveChildId(token: string): Promise<string> {
    const selectedIdxStr = localStorage.getItem('selectedChildForQuestions');
    let child_id = '';

    const currentChild = childProfileSync.getCurrentChild();
    if (currentChild?.id) {
        child_id = currentChild.id;
    } else {
        const profiles = await childProfileSync.getChildProfiles();
        if (profiles && Array.isArray(profiles) && profiles.length > 0) {
            const raw = selectedIdxStr !== null ? parseInt(selectedIdxStr, 10) : 0;
            const safeIdx = Number.isFinite(raw) && raw >= 0 && raw < profiles.length ? raw : 0;
            const sel = profiles[safeIdx];
            child_id = sel?.id || '';
        } else {
            try {
                const apiProfiles = await apiGetChildProfiles(token);
                if (apiProfiles && Array.isArray(apiProfiles) && apiProfiles.length > 0) {
                    const raw = selectedIdxStr !== null ? parseInt(selectedIdxStr, 10) : 0;
                    const safeIdx = Number.isFinite(raw) && raw >= 0 && raw < apiProfiles.length ? raw : 0;
                    child_id = apiProfiles[safeIdx]?.id || '';
                }
            } catch {}
        }
    }
    return child_id;
}

onMount(async () => {
    assignmentStep = parseInt(localStorage.getItem('assignmentStep') || '3');

	// Get current attempt number and child ID
	try {
		const token = localStorage.token || '';
		if (token) {
			const attemptData = await getCurrentAttempt(token);
			attemptNumber = attemptData.current_attempt || 1;
		}
		const currentChild = childProfileSync.getCurrentChild();
		currentChildId = currentChild?.id || null;
	} catch (e) {
		console.warn('Failed to get attempt number or child ID', e);
	}

    const token = localStorage.token || '';
    const userId = get(user)?.id || 'anon';
    const childId = await resolveChildId(token);

    // Rehydrate from backend if any saved rows exist (works even if local completion flag was cleared)
    if (childId) {
        try {
            const rows = await listExitQuiz(token, childId);
            if (rows && Array.isArray(rows) && rows.length > 0) {
                const latest = [...rows].sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0))[0];
                const ans: any = latest?.answers || {};
                surveyResponses = {
                    parentGender: ans.parentGender || '',
                    parentAge: ans.parentAge || '',
                    areaOfResidency: ans.areaOfResidency || '',
                    parentEducation: ans.parentEducation || '',
                    parentEthnicity: Array.isArray(ans.parentEthnicity) ? ans.parentEthnicity : [],
                    genaiFamiliarity: ans.genaiFamiliarity || '',
                    genaiUsageFrequency: ans.genaiUsageFrequency || '',
                    parentingStyle: ans.parentingStyle || ''
                };
                isSaved = true;
                // Ensure sidebar unlock for completion if a saved survey exists
                try {
                    localStorage.setItem('assignmentStep', '4');
                    localStorage.setItem('assignmentCompleted', 'true');
                    localStorage.setItem('unlock_completion', 'true');
                    window.dispatchEvent(new Event('storage'));
                    window.dispatchEvent(new Event('workflow-updated'));
                } catch {}
                // Also restore local completion flag for smoother UX next time
                try { localStorage.setItem(completedKey(userId, childId), 'true'); } catch {}
                return; // prefer saved view
            }
        } catch {}
    }

    // Load draft if present
    try {
        const raw = localStorage.getItem(draftKey(userId, childId));
        if (raw) {
            const draft = JSON.parse(raw);
            if (draft && typeof draft === 'object') {
                surveyResponses = {
                    parentGender: draft.parentGender || '',
                    parentAge: draft.parentAge || '',
                    areaOfResidency: draft.areaOfResidency || '',
                    parentEducation: draft.parentEducation || '',
                    parentEthnicity: Array.isArray(draft.parentEthnicity) ? draft.parentEthnicity : [],
                    genaiFamiliarity: draft.genaiFamiliarity || '',
                    genaiUsageFrequency: draft.genaiUsageFrequency || '',
                    parentingStyle: draft.parentingStyle || ''
                };
            }
        }
    } catch {}
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
            if (!surveyResponses.parentingStyle) {
                toast.error('Please select your parenting style');
                return;
            }

            // Resolve child_id: prefer selection saved by earlier steps, else pick first
            const token = localStorage.token || '';
            const selectedIdxStr = localStorage.getItem('selectedChildForQuestions');
            let child_id = '';

            // Prefer persisted current child via user settings
            const currentChild = childProfileSync.getCurrentChild();
            if (currentChild?.id) {
                child_id = currentChild.id;
            } else {
                // Fallback: use cached or backend-synced profiles and the saved index
                const profiles = await childProfileSync.getChildProfiles();
                if (profiles && Array.isArray(profiles) && profiles.length > 0) {
                    const raw = selectedIdxStr !== null ? parseInt(selectedIdxStr, 10) : 0;
                    const safeIdx = Number.isFinite(raw) && raw >= 0 && raw < profiles.length ? raw : 0;
                    const sel = profiles[safeIdx];
                    child_id = sel?.id || '';
                }
            }
            if (!child_id) {
                // Final fallback: directly query backend using token
                try {
                    const apiProfiles = await apiGetChildProfiles(token);
                    if (apiProfiles && Array.isArray(apiProfiles) && apiProfiles.length > 0) {
                        const raw = selectedIdxStr !== null ? parseInt(selectedIdxStr, 10) : 0;
                        const safeIdx = Number.isFinite(raw) && raw >= 0 && raw < apiProfiles.length ? raw : 0;
                        child_id = apiProfiles[safeIdx]?.id || '';
                    }
                } catch (e) {
                    // ignore and fall through to error
                }
            }

            if (!child_id) {
                toast.error('No child profile found. Please create/select a child on the Child Profile page.');
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
                parentingStyle: surveyResponses.parentingStyle
            };

            // Persist to backend (exit quiz)
            await createExitQuiz(token, { child_id, answers, meta: { page: 'exit-survey' } });
			
            // Mark assignment as completed before showing confirmation
			localStorage.setItem('assignmentStep', '4');
			localStorage.setItem('assignmentCompleted', 'true');
			localStorage.setItem('unlock_completion', 'true');
			window.dispatchEvent(new Event('storage'));
			window.dispatchEvent(new Event('workflow-updated'));
			// Mark as saved and open confirmation modal
			isSaved = true;
			showConfirmationModal = true;

            // Clear draft and set per-user per-child completion flag
            const userId = get(user)?.id || 'anon';
            try { localStorage.removeItem(draftKey(userId, child_id)); } catch {}
            localStorage.setItem(completedKey(userId, child_id), 'true');
		} catch (error) {
			console.error('Error saving survey:', error);
			toast.error('Failed to save survey. Please try again.');
		}
	}

// Autosave draft on changes (debounced)
const saveDraft = debounce(async () => {
    const token = localStorage.token || '';
    const userId = get(user)?.id || 'anon';
    const cid = await resolveChildId(token);
    const key = draftKey(userId, cid);
    try {
        localStorage.setItem(key, JSON.stringify(surveyResponses));
    } catch {}
}, 500);

$: saveDraft();

	function startEditing() {
		isSaved = false;
	}

	function proceedToNextStep() {
		// Update assignment step to 4 (completion)
		localStorage.setItem('assignmentStep', '4');
		localStorage.setItem('assignmentCompleted', 'true');
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
	<nav class="px-2.5 pt-1 backdrop-blur-xl w-full drag-region">
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
					<div class="flex items-center text-xl font-semibold">
                        Exit Survey
					</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<button
					on:click={goBack}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex items-center space-x-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
					</svg>
					<span>Previous Task</span>
				</button>
				<button
					on:click={handleNextTask}
					disabled={!isSaved}
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 {
						isSaved
							? 'bg-blue-500 hover:bg-blue-600 text-white'
							: 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
					}"
				>
					<span>Next Task</span>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
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
					<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
                        Exit Survey
					</h1>
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
                        <h3 class="text-xl font-semibold text-gray-900 dark:text-white">Exit Survey Responses</h3>
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
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Parenting Style</div>
						<p class="text-gray-900 dark:text-white">
							{surveyResponses.parentingStyle 
								? (surveyResponses.parentingStyle === 'A' ? 'I set clear rules and follow through, but I explain my reasons, listen to my child\'s point of view, and encourage independence.' :
								   surveyResponses.parentingStyle === 'B' ? 'I set strict rules and expect obedience; I rarely negotiate and use firm consequences when rules aren\'t followed.' :
								   surveyResponses.parentingStyle === 'C' ? 'I\'m warm and supportive with few rules or demands; my child mostly sets their own routines and limits.' :
								   surveyResponses.parentingStyle === 'D' ? 'I give my child a lot of freedom and usually take a hands-off approach unless safety or basic needs require me to step in.' :
								   surveyResponses.parentingStyle === 'E' ? 'None of these fits me / It depends on the situation.' :
								   surveyResponses.parentingStyle)
								: 'Not specified'}
						</p>
					</div>
                    <div>
                        <div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">GenAI Familiarity</div>
                        <p class="text-gray-900 dark:text-white">{surveyResponses.genaiFamiliarity || 'Not specified'}</p>
                    </div>
                    <div>
                        <div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">GenAI Usage Frequency</div>
                        <p class="text-gray-900 dark:text-white">{surveyResponses.genaiUsageFrequency || 'Not specified'}</p>
                    </div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Gender</div>
						<p class="text-gray-900 dark:text-white">{surveyResponses.parentGender || 'Not specified'}</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Age Range</div>
						<p class="text-gray-900 dark:text-white">{surveyResponses.parentAge || 'Not specified'}</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Area of Residency</div>
						<p class="text-gray-900 dark:text-white">{surveyResponses.areaOfResidency || 'Not specified'}</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Education Level</div>
						<p class="text-gray-900 dark:text-white">{surveyResponses.parentEducation || 'Not specified'}</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Ethnicity</div>
						<p class="text-gray-900 dark:text-white">{surveyResponses.parentEthnicity.length > 0 ? surveyResponses.parentEthnicity.join(', ') : 'Not specified'}</p>
					</div>
					</div>
				</div>
			{:else}
				<!-- Editable form -->
				<div class="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
					<form on:submit|preventDefault={submitSurvey} class="space-y-8">
						<!-- Question 1: Parenting Style -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								1. Which description best matches your typical approach to day-to-day parenting? (Choose the closest fit.) <span class="text-red-500">*</span>
							</div>
							<div class="space-y-3">
								<label class="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors {
									surveyResponses.parentingStyle === 'A' 
										? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
										: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
								}">
									<input type="radio" bind:group={surveyResponses.parentingStyle} value="A" class="mt-1 mr-3" />
									<div>
										<div class="font-semibold text-gray-900 dark:text-white">I set clear rules and follow through, but I explain my reasons, listen to my child's point of view, and encourage independence.</div>
									</div>
								</label>
								<label class="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors {
									surveyResponses.parentingStyle === 'B' 
										? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
										: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
								}">
									<input type="radio" bind:group={surveyResponses.parentingStyle} value="B" class="mt-1 mr-3" />
									<div>
										<div class="font-semibold text-gray-900 dark:text-white">I set strict rules and expect obedience; I rarely negotiate and use firm consequences when rules aren't followed.</div>
									</div>
								</label>
								<label class="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors {
									surveyResponses.parentingStyle === 'C' 
										? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
										: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
								}">
									<input type="radio" bind:group={surveyResponses.parentingStyle} value="C" class="mt-1 mr-3" />
									<div>
										<div class="font-semibold text-gray-900 dark:text-white">I'm warm and supportive with few rules or demands; my child mostly sets their own routines and limits.</div>
									</div>
								</label>
								<label class="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors {
									surveyResponses.parentingStyle === 'D' 
										? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
										: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
								}">
									<input type="radio" bind:group={surveyResponses.parentingStyle} value="D" class="mt-1 mr-3" />
									<div>
										<div class="font-semibold text-gray-900 dark:text-white">I give my child a lot of freedom and usually take a hands-off approach unless safety or basic needs require me to step in.</div>
									</div>
								</label>
								<label class="flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors {
									surveyResponses.parentingStyle === 'E' 
										? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
										: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
								}">
									<input type="radio" bind:group={surveyResponses.parentingStyle} value="E" class="mt-1 mr-3" />
									<div>
										<div class="font-semibold text-gray-900 dark:text-white">None of these fits me / It depends on the situation.</div>
									</div>
								</label>
							</div>
						</div>

						<!-- GenAI familiarity -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								2. How familiar are you with ChatGPT or other Large Language Models (LLMs)? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiFamiliarity} value="regular_user" class="mr-3" />I regularly use ChatGPT or other LLMs for work or personal use</label>
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiFamiliarity} value="tried_few_times" class="mr-3" />I have tried them a few times but don’t use them often</label>
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiFamiliarity} value="heard_never_used" class="mr-3" />I have heard of them but never used them</label>
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiFamiliarity} value="dont_know" class="mr-3" />I don’t know what they are</label>
						<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiFamiliarity} value="prefer-not-to-answer" class="mr-3" />Prefer not to answer</label>
							</div>
						</div>

						<!-- Personal GenAI use frequency -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								3. How often do you personally use ChatGPT or similar AI tools? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiUsageFrequency} value="daily" class="mr-3" />Daily or almost daily</label>
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiUsageFrequency} value="weekly" class="mr-3" />Weekly</label>
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiUsageFrequency} value="monthly_or_less" class="mr-3" />Monthly or less</label>
								<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiUsageFrequency} value="do_not_use" class="mr-3" />I do not use these tools</label>
						<label class="flex items-center"><input type="radio" bind:group={surveyResponses.genaiUsageFrequency} value="prefer-not-to-answer" class="mr-3" />Prefer not to answer</label>
							</div>
						</div>
						<!-- Question 4: Parent Gender -->
						<div>
                    <div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
                                4. What is your gender? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentGender} value="male" class="mr-3" id="gender-male">
									<span class="text-gray-900 dark:text-white">Male</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentGender} value="female" class="mr-3" id="gender-female">
									<span class="text-gray-900 dark:text-white">Female</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentGender} value="non-binary" class="mr-3" id="gender-non-binary">
									<span class="text-gray-900 dark:text-white">Non-binary</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentGender} value="other" class="mr-3" id="gender-other">
									<span class="text-gray-900 dark:text-white">Other</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentGender} value="prefer-not-to-say" class="mr-3" id="gender-prefer-not-to-say">
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

						<!-- Question 5: Parent Age -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
                                5. What is your age range? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="18-24" class="mr-3" id="age-18-24">
									<span class="text-gray-900 dark:text-white">18-24 years</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="25-34" class="mr-3" id="age-25-34">
									<span class="text-gray-900 dark:text-white">25-34 years</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="35-44" class="mr-3" id="age-35-44">
									<span class="text-gray-900 dark:text-white">35-44 years</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="45-54" class="mr-3" id="age-45-54">
									<span class="text-gray-900 dark:text-white">45-54 years</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="55-64" class="mr-3" id="age-55-64">
									<span class="text-gray-900 dark:text-white">55-64 years</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="65+" class="mr-3" id="age-65-plus">
									<span class="text-gray-900 dark:text-white">65+ years</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentAge} value="prefer-not-to-say" class="mr-3" id="age-prefer-not-to-say">
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

                        <!-- Question 6: Area of Residency -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
                                6. What type of area do you live in? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.areaOfResidency} value="urban" class="mr-3" id="area-urban">
									<span class="text-gray-900 dark:text-white">Urban (city)</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.areaOfResidency} value="suburban" class="mr-3" id="area-suburban">
									<span class="text-gray-900 dark:text-white">Suburban</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.areaOfResidency} value="rural" class="mr-3" id="area-rural">
									<span class="text-gray-900 dark:text-white">Rural (countryside)</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.areaOfResidency} value="prefer-not-to-say" class="mr-3" id="area-prefer-not-to-say">
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

                        <!-- Question 7: Parent Education -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
                                7. What is your highest level of education? <span class="text-red-500">*</span>
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="high-school" class="mr-3" id="education-high-school">
									<span class="text-gray-900 dark:text-white">High school diploma or equivalent</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="some-college" class="mr-3" id="education-some-college">
									<span class="text-gray-900 dark:text-white">Some college, no degree</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="associates" class="mr-3" id="education-associates">
									<span class="text-gray-900 dark:text-white">Associate degree</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="bachelors" class="mr-3" id="education-bachelors">
									<span class="text-gray-900 dark:text-white">Bachelor's degree</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="masters" class="mr-3" id="education-masters">
									<span class="text-gray-900 dark:text-white">Master's degree</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="doctoral" class="mr-3" id="education-doctoral">
									<span class="text-gray-900 dark:text-white">Doctoral degree</span>
								</label>
								<label class="flex items-center">
									<input type="radio" bind:group={surveyResponses.parentEducation} value="prefer-not-to-say" class="mr-3" id="education-prefer-not-to-say">
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
						</div>

                        <!-- Question 8: Parent Ethnicity -->
						<div>
							<div class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
                                8. What is your ethnicity? (Select all that apply)
							</div>
							<div class="space-y-2">
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="white" class="mr-3" id="ethnicity-white">
									<span class="text-gray-900 dark:text-white">White</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="black-african-american" class="mr-3" id="ethnicity-black-african-american">
									<span class="text-gray-900 dark:text-white">Black or African American</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="hispanic-latino" class="mr-3" id="ethnicity-hispanic-latino">
									<span class="text-gray-900 dark:text-white">Hispanic or Latino</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="asian" class="mr-3" id="ethnicity-asian">
									<span class="text-gray-900 dark:text-white">Asian</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="native-american" class="mr-3" id="ethnicity-native-american">
									<span class="text-gray-900 dark:text-white">Native American or Alaska Native</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="pacific-islander" class="mr-3" id="ethnicity-pacific-islander">
									<span class="text-gray-900 dark:text-white">Native Hawaiian or Pacific Islander</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="middle-eastern" class="mr-3" id="ethnicity-middle-eastern">
									<span class="text-gray-900 dark:text-white">Middle Eastern or North African</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="mixed-race" class="mr-3" id="ethnicity-mixed-race">
									<span class="text-gray-900 dark:text-white">Mixed race</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="other" class="mr-3" id="ethnicity-other">
									<span class="text-gray-900 dark:text-white">Other</span>
								</label>
								<label class="flex items-center">
									<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="prefer-not-to-say" class="mr-3" id="ethnicity-prefer-not-to-say">
									<span class="text-gray-900 dark:text-white">Prefer not to say</span>
								</label>
							</div>
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
		on:click={() => showConfirmationModal = false}
		on:keydown={(e) => e.key === 'Escape' && (showConfirmationModal = false)}
		role="dialog" 
		aria-modal="true" 
		aria-labelledby="confirmation-modal-title"
	>
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" on:click|stopPropagation>
			<div class="text-center mb-6">
				<div class="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
					<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
					</svg>
				</div>
				<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
					Task 3 Complete
				</h3>
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
	<AssignmentTimeTracker 
		userId={get(user)?.id || ''} 
		childId={currentChildId}
		attemptNumber={attemptNumber}
		enabled={true}
	/>
</div>