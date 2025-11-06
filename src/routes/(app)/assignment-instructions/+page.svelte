<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar, user } from '$lib/stores';
	import { get } from 'svelte/store';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import AssignmentTimeTracker from '$lib/components/assignment/AssignmentTimeTracker.svelte';

	// State to track if Start button was clicked
	let startButtonClicked: boolean = false;
	// State to track if instructions have been read
	let instructionsCompleted: boolean = false;
	// State for scroll indicator
	let showScrollIndicator: boolean = false;
	let hasScrolled: boolean = false;
	// State for ready modal
	let showReadyModal: boolean = false;

	// Assignment time tracking
	let trackingEnabled: boolean = false;
	$: sessionNumber = $user?.session_number || 1;

	onMount(async () => {
		// Check if instructions have been read
		const instructionsRead = localStorage.getItem('instructionsCompleted');
		if (instructionsRead === 'true') {
			instructionsCompleted = true;
		}

		// Enable tracking if instructions are already completed (consent given)
		if (instructionsCompleted) {
			trackingEnabled = true;
		}

		// Default open sidebar on wide screens (md and up)
		try {
			if (typeof window !== 'undefined' && window.innerWidth >= 768) {
				showSidebar.set(true);
			}
		} catch (e) {}
		
		// Set up scroll indicator
		const timer = setTimeout(() => {
			if (!hasScrolled) {
				showScrollIndicator = true;
			}
		}, 8000); // Show after 8 seconds

		const handleScroll = () => {
			hasScrolled = true;
			showScrollIndicator = false;
		};

		// Find the scrollable container
		const scrollContainer = document.querySelector('.overflow-y-auto');
		
		// Attach to both window and container
		if (scrollContainer) {
			scrollContainer.addEventListener('scroll', handleScroll);
		}
		window.addEventListener('scroll', handleScroll);
		
		return () => {
			clearTimeout(timer);
			if (scrollContainer) {
				scrollContainer.removeEventListener('scroll', handleScroll);
			}
			window.removeEventListener('scroll', handleScroll);
		};
	});


	function startAssignment() {
		// Set initial assignment step
		localStorage.setItem('assignmentStep', '1');
		startButtonClicked = true;
		goto('/kids/profile');
	}
	
	function markInstructionsComplete() {
	// Unlock Step 1 immediately before showing the modal
	localStorage.setItem('instructionsCompleted', 'true');
	localStorage.setItem('assignmentStep', '1');
	localStorage.setItem('unlock_kids', 'true');
	window.dispatchEvent(new Event('storage'));
	window.dispatchEvent(new Event('workflow-updated'));
	showReadyModal = true;
	// Start time tracking after consent
	trackingEnabled = true;
	}
	
	function proceedToTasks() {
		instructionsCompleted = true;
		localStorage.setItem('instructionsCompleted', 'true');
		localStorage.setItem('assignmentStep', '1');
		showReadyModal = false;
		goto('/kids/profile');
	}
	
	function cancelReady() {
		showReadyModal = false;
	}

</script>

<svelte:head>
	<title>Assignment Instructions</title>
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
						Instructions
					</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			{#if instructionsCompleted}
				<div class="flex items-center space-x-2">
					<button
						on:click={() => goto('/kids/profile')}
						class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 bg-blue-500 hover:bg-blue-600 text-white"
					>
						<span>Next Task</span>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
						</svg>
					</button>
				</div>
			{/if}
		</div>
	</nav>

	<div class="flex-1 max-h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
		<div class="max-w-4xl mx-auto px-4 py-8">
			<!-- Header -->
			<div class="text-center mb-12">
				<p class="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
					In this survey, you'll complete three tasks to help us understand what moderation strategies would be most effective for children's conversations with AI.
				</p>
			</div>


			<!-- Task Steps -->
			<div class="space-y-6 mb-8">
				<!-- Task 1 -->
				<div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
					<div class="flex items-start space-x-4">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
								1
							</div>
						</div>
						<div class="flex-1">
							<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
								Child Profile Setup
							</h3>
							<p class="text-gray-600 dark:text-gray-300">
								Create a profile for your child including age, gender, interests, and characteristics.
							</p>
						</div>
					</div>
				</div>

				<!-- Task 2 -->
				<div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
					<div class="flex items-start space-x-4">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-purple-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
								2
							</div>
						</div>
						<div class="flex-1">
							<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
								Moderation Scenarios
							</h3>
							<p class="text-gray-600 dark:text-gray-300">
								Review and moderate AI responses to ensure they are appropriate for your child.
							</p>
						</div>
					</div>
				</div>

				<!-- Task 3 -->
				<div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
					<div class="flex items-start space-x-4">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-green-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
								3
							</div>
						</div>
						<div class="flex-1">
							<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
								Exit Survey
							</h3>
							<p class="text-gray-600 dark:text-gray-300">
								Complete a brief survey about your experience and provide some additional information.
							</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Demo Video -->
			<div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 mb-8">
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
					Demo Video
				</h3>
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					Watch this demonstration video to see how the workflow operates before you begin:
				</p>
				<div class="w-full max-w-4xl mx-auto">
					<!-- svelte-ignore a11y-media-has-caption -->
					<video
						controls
						class="w-full rounded-lg shadow-md"
						poster=""
						preload="metadata"
					>
						<source src="/video/Demo-Video.mp4" type="video/mp4" />
						Your browser does not support the video tag.
					</video>
				</div>
			</div>

			<!-- Important Notes -->
			<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6 mb-8">
				<h3 class="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-3">
					Note: Attention Check Questions
				</h3>
				<ul class="space-y-2 text-yellow-700 dark:text-yellow-300">
					<li class="flex items-start">
						<span class="mr-2">•</span>
						<span>We have implemented multiple types of attention check questions. </span>
					</li>
					<li class="flex items-start">
						<span class="mr-2">•</span>
						<span>Please read all content and complete this task to the best of your ability.</span>
					</li>
				</ul>
			</div>


			<!-- Done Button -->
			<div class="text-center mt-8">
				{#if !instructionsCompleted}
					<button
						on:click={markInstructionsComplete}
						class="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
					>
						I've Read the Instructions
					</button>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
						Click when you're ready to proceed
					</p>
				{:else}
					<div class="text-green-600 dark:text-green-400 flex items-center justify-center space-x-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
						</svg>
						<span class="font-medium">Instructions Read</span>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Scroll Indicator -->
	{#if showScrollIndicator}
		<div class="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 flex flex-col items-center animate-bounce">
			<span class="text-sm text-gray-400 dark:text-gray-500 mb-1">Scroll down</span>
			<svg class="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
			</svg>
		</div>
	{/if}

	<!-- Ready Modal -->
	{#if showReadyModal}
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={cancelReady}>
			<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" on:click|stopPropagation>
				<div class="text-center mb-6">
					<div class="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
						</svg>
					</div>
					<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
						Ready to Begin?
					</h3>
					<p class="text-gray-600 dark:text-gray-400">
						Have you read all the instructions?
					</p>
				</div>

				<div class="flex flex-col space-y-3">
					<button
						on:click={proceedToTasks}
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
					>
						Yes, I'm Ready
					</button>
					<button
						on:click={cancelReady}
						class="px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
					>
						No, Let me re-read
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Assignment Time Tracker -->
{#if trackingEnabled}
	<AssignmentTimeTracker 
		userId={get(user)?.id || ''} 
		sessionNumber={sessionNumber}
		enabled={trackingEnabled}
	/>
{/if}

</div>

