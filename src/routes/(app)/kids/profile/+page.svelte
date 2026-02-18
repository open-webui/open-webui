<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar, user } from '$lib/stores';
	import { get } from 'svelte/store';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import { getWorkflowState } from '$lib/apis/workflow';
	import { getChildProfiles } from '$lib/apis/child-profiles';
	import { assignScenariosForChild } from '$lib/services/scenarioAssignment';
	import AssignmentTimeTracker from '$lib/components/assignment/AssignmentTimeTracker.svelte';
	import VideoModal from '$lib/components/common/VideoModal.svelte';
	import ChildProfileForm from '$lib/components/profile/ChildProfileForm.svelte';

	const i18n = getContext('i18n');

	let showConfirmationModal: boolean = false;
	let childSelectedForQuestions: number = -1;
	let showScrollIndicator: boolean = false;
	let hasScrolled: boolean = false;
	let mainPageContainer: HTMLElement;

	// Assignment time tracking
	$: sessionNumber = $user?.session_number || 1;

	// Video modal state
	let showHelpVideo: boolean = false;

	// Function to determine session number for new child profile
	async function determineSessionNumberForUser(userId: string, token: string): Promise<number> {
		try {
			const profiles = await getChildProfiles(token);
			if (Array.isArray(profiles) && profiles.length > 0) {
				const maxSession = Math.max(...profiles.map((p: ChildProfile) => p.session_number || 1));
				const nextSession = maxSession + 1;
				console.log(`Determined session number: ${nextSession} (max existing: ${maxSession})`);
				return nextSession;
			} else {
				console.log('No existing profiles, using session number: 1');
				return 1;
			}
		} catch (error) {
			console.error('Error determining session number, defaulting to 1:', error);
			return 1;
		}
	}

	async function handleProfileCreated(profile: ChildProfile) {
		// Trigger scenario assignment for quiz workflow
		const userId = ($user as any)?.id;
		const token = localStorage.getItem('token') || '';

		if (userId && token) {
			const sessionNumber = await determineSessionNumberForUser(userId, token);
			assignScenariosForChild(profile.id, userId, sessionNumber, token, 6)
				.then((result) => {
					console.log(`✅ Assigned ${result.assignmentCount} scenarios for child ${profile.id}`);
					if (result.assignmentCount < 6) {
						console.warn(`⚠️ Only ${result.assignmentCount}/6 scenarios assigned`);
					}
				})
				.catch((error) => {
					console.error('❌ Failed to assign scenarios:', error);
				});
		}

		// Set child as selected for questions
		const profiles = await childProfileSync.getChildProfiles();
		const index = profiles.findIndex((p) => p.id === profile.id);
		if (index !== -1) {
			childSelectedForQuestions = index;
			await childProfileSync.setCurrentChildId(profile.id);

			// Backend has child profile; sidebar will refetch workflow state
			window.dispatchEvent(new Event('workflow-updated'));

			// Show confirmation modal
			showConfirmationModal = true;
		}
	}

	async function handleProfileSaved(profile: ChildProfile) {
		// Set child as selected for questions if not already
		const profiles = await childProfileSync.getChildProfiles();
		const index = profiles.findIndex((p) => p.id === profile.id);
		if (index !== -1) {
			childSelectedForQuestions = index;
			await childProfileSync.setCurrentChildId(profile.id);

			// Backend has child profile; sidebar will refetch workflow state
			window.dispatchEvent(new Event('workflow-updated'));

			// Show confirmation modal
			showConfirmationModal = true;
		}
	}

	async function handleChildSelected(profile: ChildProfile, index: number) {
		childSelectedForQuestions = index;
		await childProfileSync.setCurrentChildId(profile.id);

		// Backend has child profile; sidebar will refetch workflow state
		window.dispatchEvent(new Event('workflow-updated'));

		// Show confirmation modal (as in original workflow)
		showConfirmationModal = true;
	}

	async function proceedToNextStep() {
		window.dispatchEvent(new Event('workflow-updated'));
		goto('/moderation-scenario');
	}

	function continueEditing() {
		showConfirmationModal = false;
	}

	onMount(async () => {
		// Redirect if instructions not completed (check backend)
		try {
			const token = (typeof window !== 'undefined' && localStorage.token) || '';
			if (token) {
				const state = await getWorkflowState(token);
				if (!state?.progress_by_section?.instructions_completed) {
					goto('/assignment-instructions');
					return;
				}
			}
		} catch {
			// On error, allow access (fallback)
		}

		// Wait for user store to be loaded
		const waitForUser = () => {
			return new Promise<void>((resolve) => {
				const currentUser = get(user);
				if (currentUser && currentUser.id) {
					resolve();
					return;
				}
				const unsubscribe = user.subscribe((userData) => {
					if (userData && userData.id) {
						unsubscribe();
						resolve();
					}
				});
			});
		};

		await waitForUser();

		// Load profiles and set selected child for questions
		const profiles = await childProfileSync.getChildProfiles();
		const currentChildId = childProfileSync.getCurrentChildId();
		if (currentChildId && profiles.length > 0) {
			const index = profiles.findIndex((p) => p.id === currentChildId);
			if (index !== -1) {
				childSelectedForQuestions = index;
			}
		}

		// Set up scroll indicator
		const timer = setTimeout(() => {
			if (!hasScrolled) {
				showScrollIndicator = true;
			}
		}, 8000);

		const handleScroll = () => {
			hasScrolled = true;
			showScrollIndicator = false;
		};

		// Wait for component to mount and find the scroll container
		setTimeout(() => {
			const scrollContainer = document.querySelector('.overflow-y-auto');
			if (scrollContainer) {
				scrollContainer.addEventListener('scroll', handleScroll);
			}
			window.addEventListener('scroll', handleScroll);
		}, 100);

		return () => {
			clearTimeout(timer);
			const scrollContainer = document.querySelector('.overflow-y-auto');
			if (scrollContainer) {
				scrollContainer.removeEventListener('scroll', handleScroll);
			}
			window.removeEventListener('scroll', handleScroll);
		};
	});
</script>

<svelte:head>
	<title>Child Profile - Kids Mode</title>
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
					<div class="flex items-center text-xl font-semibold">Child Profile</div>
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
					on:click={() => goto('/assignment-instructions')}
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
					on:click={() => goto('/moderation-scenario')}
					disabled={childSelectedForQuestions === -1}
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 {childSelectedForQuestions !==
					-1
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

	<!-- Child Profile Form Component (MVP fields only - no research fields, no personality traits) -->
	<ChildProfileForm
		showResearchFields={false}
		requireResearchFields={false}
		showPersonalityTraits={false}
		onProfileCreated={handleProfileCreated}
		onProfileSaved={handleProfileSaved}
		onChildSelected={handleChildSelected}
	/>

	<!-- Confirmation Modal for Workflow Progression -->
	{#if showConfirmationModal}
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div
			class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
			on:click={() => (showConfirmationModal = false)}
		>
			<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
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
					<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Task 1 Complete</h3>
					<p class="text-gray-600 dark:text-gray-400">
						Would you like to proceed to the next step?
					</p>
				</div>

				<div class="flex flex-col space-y-3">
					<button
						on:click={proceedToNextStep}
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
					>
						Yes, Proceed to the Next Step
					</button>
					<button
						on:click={continueEditing}
						class="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
					>
						No, Continue Editing Profile
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Scroll Indicator -->
	{#if showScrollIndicator}
		<div
			class="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 flex flex-col items-center animate-bounce"
		>
			<span class="text-sm text-gray-400 dark:text-gray-500 mb-1">Scroll down</span>
			<svg
				class="w-6 h-6 text-gray-400 dark:text-gray-500"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 14l-7 7m0 0l-7-7m7 7V3"
				></path>
			</svg>
		</div>
	{/if}

	<!-- Assignment Time Tracker -->
	<AssignmentTimeTracker userId={get(user)?.id || ''} {sessionNumber} enabled={true} />

	<!-- Help Video Modal -->
	<VideoModal
		isOpen={showHelpVideo}
		videoSrc="/video/Child-Profile-Demo.mp4"
		title="Child Profile Tutorial"
	/>
</div>
