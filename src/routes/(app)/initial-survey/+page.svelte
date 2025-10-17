<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { toast } from 'svelte-sonner';

	// Survey responses
	let surveyResponses = {
		experienceWithAI: '',
		parentingApproach: '',
		contentModerationExperience: '',
		expectations: '',
		concerns: '',
		techComfort: ''
	};

	onMount(() => {
		// Check if user has already completed the initial survey
		const initialSurveyCompleted = localStorage.getItem('initialSurveyCompleted');
		if (initialSurveyCompleted === 'true') {
			goto('/assignment-instructions');
			return;
		}
	});

	async function submitSurvey() {
		try {
			// Save to backend
			const response = await fetch('/api/v1/initial-surveys', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(surveyResponses)
			});

			if (!response.ok) {
				throw new Error('Failed to save survey responses');
			}

			// Mark as completed
			localStorage.setItem('initialSurveyCompleted', 'true');
			toast.success('Survey submitted successfully!');
			
			// Navigate to assignment instructions
			goto('/assignment-instructions');
		} catch (error) {
			console.error('Error submitting survey:', error);
			toast.error('Failed to submit survey. Please try again.');
		}
	}

	function goBack() {
		goto('/assignment-instructions');
	}
</script>

<svelte:head>
	<title>Initial Survey</title>
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
						Initial Survey
					</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<button
					disabled
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 text-gray-400 dark:text-gray-500 cursor-not-allowed"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
					</svg>
					<span>Previous Task</span>
				</button>
				<button
					on:click={() => goto('/assignment-instructions')}
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 bg-blue-500 hover:bg-blue-600 text-white"
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
				<div class="flex items-center justify-between">
					<div>
						<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
							Pre-Assignment Survey
						</h1>
						<p class="text-gray-600 dark:text-gray-300 mt-2">
							Please help us understand your background and expectations before starting the assignment.
						</p>
					</div>
					<button
						on:click={goBack}
						class="flex items-center space-x-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
						</svg>
						<span>Back to Instructions</span>
					</button>
				</div>
			</div>

			<!-- Survey Form -->
			<div class="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
				<form on:submit|preventDefault={submitSurvey} class="space-y-8">
					<!-- Question 1 -->
					<div>
							<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								1. What is your experience with AI systems and chatbots? <span class="text-red-500">*</span>
							</label>
						<textarea
							bind:value={surveyResponses.experienceWithAI}
							rows="4"
							placeholder="Please describe your experience with AI tools, chatbots, or similar technologies..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 2 -->
					<div>
							<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								2. How would you describe your general parenting approach? <span class="text-red-500">*</span>
							</label>
						<textarea
							bind:value={surveyResponses.parentingApproach}
							rows="4"
							placeholder="Please describe your parenting style, values, and approach to guiding your child..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 3 -->
					<div>
							<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								3. Have you had experience moderating content for your child before? <span class="text-red-500">*</span>
							</label>
						<textarea
							bind:value={surveyResponses.contentModerationExperience}
							rows="4"
							placeholder="Please describe any experience you have with monitoring, filtering, or guiding your child's access to digital content..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 4 -->
					<div>
							<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								4. What are your expectations for this assignment? <span class="text-red-500">*</span>
							</label>
						<textarea
							bind:value={surveyResponses.expectations}
							rows="4"
							placeholder="What do you hope to learn or achieve through this assignment?"
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 5 -->
					<div>
							<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								5. Do you have any concerns about AI systems interacting with children? <span class="text-red-500">*</span>
							</label>
						<textarea
							bind:value={surveyResponses.concerns}
							rows="4"
							placeholder="Please share any concerns, worries, or considerations you have about AI systems and children..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 6 -->
					<div>
							<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
								6. How comfortable are you with technology in general? <span class="text-red-500">*</span>
							</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.techComfort} value="very-comfortable" class="mr-3">
								<span class="text-gray-900 dark:text-white">Very Comfortable</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.techComfort} value="somewhat-comfortable" class="mr-3">
								<span class="text-gray-900 dark:text-white">Somewhat Comfortable</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.techComfort} value="neutral" class="mr-3">
								<span class="text-gray-900 dark:text-white">Neutral</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.techComfort} value="somewhat-uncomfortable" class="mr-3">
								<span class="text-gray-900 dark:text-white">Somewhat Uncomfortable</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.techComfort} value="very-uncomfortable" class="mr-3">
								<span class="text-gray-900 dark:text-white">Very Uncomfortable</span>
							</label>
						</div>
					</div>

					<!-- Submit Button -->
					<div class="flex justify-end pt-6">
						<button
							type="submit"
							class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						>
							Submit Survey & Continue
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</div>
