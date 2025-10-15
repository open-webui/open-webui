<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';

	onMount(() => {
		// Ensure user has completed all steps
		const currentStep = parseInt(localStorage.getItem('assignmentStep') || '1');
		if (currentStep < 4) {
			// Redirect to appropriate step if not completed
			switch (currentStep) {
				case 1:
					goto('/kids/profile');
					break;
				case 2:
					goto('/moderation-scenario');
					break;
				case 3:
					goto('/exit-survey');
					break;
			}
		}
	});

	function startNewWorkflow() {
		// Reset to step 1 to start workflow again
		localStorage.setItem('assignmentStep', '1');
		localStorage.removeItem('assignmentCompleted');
		goto('/');
	}

	function goToHome() {
		goto('/');
	}
</script>

<svelte:head>
	<title>Assignment Complete</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] bg-gradient-to-br from-green-50 to-emerald-100 dark:from-gray-900 dark:to-gray-800 transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<div class="flex-1 flex items-center justify-center p-8">
		<div class="max-w-2xl w-full">
			<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-12 text-center border border-gray-200 dark:border-gray-700">
				<!-- Success Icon -->
				<div class="mb-8">
					<div class="w-24 h-24 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce">
						<svg class="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
						</svg>
					</div>

					<h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">
						🎉 Congratulations!
					</h1>
					<p class="text-xl text-gray-600 dark:text-gray-300 mb-2">
						You've completed the research assignment
					</p>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Thank you for your participation and valuable feedback
					</p>
				</div>

				<!-- Summary Stats -->
				<div class="grid grid-cols-3 gap-4 mb-8 py-6 border-y border-gray-200 dark:border-gray-700">
					<div class="text-center">
						<div class="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-1">✓</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">Child Profile</div>
					</div>
					<div class="text-center">
						<div class="text-3xl font-bold text-purple-600 dark:text-purple-400 mb-1">✓</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">Moderation Scenarios</div>
					</div>
					<div class="text-center">
						<div class="text-3xl font-bold text-green-600 dark:text-green-400 mb-1">✓</div>
						<div class="text-xs text-gray-600 dark:text-gray-400">Exit Survey</div>
					</div>
				</div>

				<!-- Action Buttons -->
				<div class="flex flex-col space-y-3">
					<button
						on:click={goToHome}
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-4 rounded-lg font-semibold text-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
					>
						Return to Home
					</button>
					<button
						on:click={startNewWorkflow}
						class="px-8 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border-2 border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium"
					>
						Start New Assignment
					</button>
				</div>

				<!-- Additional Information -->
				<div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Your responses have been recorded. You can close this window or start a new assignment.
					</p>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	@keyframes bounce {
		0%, 100% {
			transform: translateY(0);
		}
		50% {
			transform: translateY(-10px);
		}
	}

	.animate-bounce {
		animation: bounce 2s infinite;
	}
</style>

