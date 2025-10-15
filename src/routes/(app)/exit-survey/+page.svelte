<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	// Assignment workflow state
	let assignmentStep: number = 1;

	// Survey responses
	let surveyResponses = {
		experience: '',
		challenges: '',
		moderationEffectiveness: '',
		recommendations: '',
		overallSatisfaction: ''
	};

	onMount(() => {
		// Check if user is on the correct step
		const currentStep = parseInt(localStorage.getItem('assignmentStep') || '1');
		if (currentStep < 3) {
			goto('/kids/profile');
			return;
		}
		assignmentStep = currentStep;
	});

	function submitSurvey() {
		// Here you would typically send the survey data to your backend
		console.log('Survey responses:', surveyResponses);
		
		// Mark assignment as completed
		localStorage.setItem('assignmentCompleted', 'true');
		localStorage.setItem('assignmentStep', '4');
		
		// Redirect to completion page
		goto('/completion');
	}

	function goBack() {
		goto('/moderation-scenario');
	}
</script>

<div class="w-full h-full flex flex-col bg-gray-50 dark:bg-gray-900">
	<div class="flex-1 overflow-y-auto">
		<div class="max-w-4xl mx-auto px-4 py-8">
			<!-- Header -->
			<div class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<div>
						<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
							Exit Survey
						</h1>
						<p class="text-gray-600 dark:text-gray-300 mt-2">
							Please provide feedback on your moderation experience
						</p>
					</div>
					<button
						on:click={goBack}
						class="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
					>
						← Back
					</button>
				</div>
			</div>

			<!-- Survey Form -->
			<div class="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
				<form on:submit|preventDefault={submitSurvey} class="space-y-8">
					<!-- Question 1 -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							1. How would you describe your overall experience with the AI moderation assignment?
						</label>
						<textarea
							bind:value={surveyResponses.experience}
							rows="4"
							placeholder="Please describe your experience..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 2 -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							2. What challenges did you face while moderating the AI responses?
						</label>
						<textarea
							bind:value={surveyResponses.challenges}
							rows="4"
							placeholder="Please describe any challenges you encountered..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 3 -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							3. How effective do you think the moderation strategies were in improving the AI responses?
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.moderationEffectiveness} value="very-effective" class="mr-3">
								<span class="text-gray-900 dark:text-white">Very Effective</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.moderationEffectiveness} value="somewhat-effective" class="mr-3">
								<span class="text-gray-900 dark:text-white">Somewhat Effective</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.moderationEffectiveness} value="neutral" class="mr-3">
								<span class="text-gray-900 dark:text-white">Neutral</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.moderationEffectiveness} value="somewhat-ineffective" class="mr-3">
								<span class="text-gray-900 dark:text-white">Somewhat Ineffective</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.moderationEffectiveness} value="very-ineffective" class="mr-3">
								<span class="text-gray-900 dark:text-white">Very Ineffective</span>
							</label>
						</div>
					</div>

					<!-- Question 4 -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							4. What recommendations would you make to improve the AI moderation system?
						</label>
						<textarea
							bind:value={surveyResponses.recommendations}
							rows="4"
							placeholder="Please provide your recommendations..."
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							required
						></textarea>
					</div>

					<!-- Question 5 -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							5. Overall, how satisfied are you with this assignment experience?
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.overallSatisfaction} value="very-satisfied" class="mr-3">
								<span class="text-gray-900 dark:text-white">Very Satisfied</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.overallSatisfaction} value="satisfied" class="mr-3">
								<span class="text-gray-900 dark:text-white">Satisfied</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.overallSatisfaction} value="neutral" class="mr-3">
								<span class="text-gray-900 dark:text-white">Neutral</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.overallSatisfaction} value="dissatisfied" class="mr-3">
								<span class="text-gray-900 dark:text-white">Dissatisfied</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.overallSatisfaction} value="very-dissatisfied" class="mr-3">
								<span class="text-gray-900 dark:text-white">Very Dissatisfied</span>
							</label>
						</div>
					</div>

					<!-- Submit Button -->
					<div class="flex justify-end pt-6">
						<button
							type="submit"
							class="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						>
							Complete Assignment
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</div>
