<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	// Assignment workflow state
	let assignmentStep: number = 1;

	// Survey responses
	let surveyResponses = {
		parentGender: '',
		parentAge: '',
		areaOfResidency: '',
		parentEducation: '',
		parentEthnicity: []
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
		
		// Show completion message and redirect
		alert('Thank you for completing the survey! Your demographic information has been recorded.');
		goto('/');
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
							Please provide some demographic information to help us understand our participants
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
					<!-- Question 1: Parent Gender -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							1. What is your gender?
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentGender} value="male" class="mr-3">
								<span class="text-gray-900 dark:text-white">Male</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentGender} value="female" class="mr-3">
								<span class="text-gray-900 dark:text-white">Female</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentGender} value="non-binary" class="mr-3">
								<span class="text-gray-900 dark:text-white">Non-binary</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentGender} value="other" class="mr-3">
								<span class="text-gray-900 dark:text-white">Other</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentGender} value="prefer-not-to-say" class="mr-3">
								<span class="text-gray-900 dark:text-white">Prefer not to say</span>
							</label>
						</div>
					</div>

					<!-- Question 2: Parent Age -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							2. What is your age range?
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="18-24" class="mr-3">
								<span class="text-gray-900 dark:text-white">18-24 years</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="25-34" class="mr-3">
								<span class="text-gray-900 dark:text-white">25-34 years</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="35-44" class="mr-3">
								<span class="text-gray-900 dark:text-white">35-44 years</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="45-54" class="mr-3">
								<span class="text-gray-900 dark:text-white">45-54 years</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="55-64" class="mr-3">
								<span class="text-gray-900 dark:text-white">55-64 years</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="65+" class="mr-3">
								<span class="text-gray-900 dark:text-white">65+ years</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentAge} value="prefer-not-to-say" class="mr-3">
								<span class="text-gray-900 dark:text-white">Prefer not to say</span>
							</label>
						</div>
					</div>

					<!-- Question 3: Area of Residency -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							3. What type of area do you live in?
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.areaOfResidency} value="urban" class="mr-3">
								<span class="text-gray-900 dark:text-white">Urban (city)</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.areaOfResidency} value="suburban" class="mr-3">
								<span class="text-gray-900 dark:text-white">Suburban</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.areaOfResidency} value="rural" class="mr-3">
								<span class="text-gray-900 dark:text-white">Rural (countryside)</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.areaOfResidency} value="prefer-not-to-say" class="mr-3">
								<span class="text-gray-900 dark:text-white">Prefer not to say</span>
							</label>
						</div>
					</div>

					<!-- Question 4: Parent Education -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							4. What is your highest level of education?
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="high-school" class="mr-3">
								<span class="text-gray-900 dark:text-white">High school diploma or equivalent</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="some-college" class="mr-3">
								<span class="text-gray-900 dark:text-white">Some college, no degree</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="associates" class="mr-3">
								<span class="text-gray-900 dark:text-white">Associate degree</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="bachelors" class="mr-3">
								<span class="text-gray-900 dark:text-white">Bachelor's degree</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="masters" class="mr-3">
								<span class="text-gray-900 dark:text-white">Master's degree</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="doctoral" class="mr-3">
								<span class="text-gray-900 dark:text-white">Doctoral degree</span>
							</label>
							<label class="flex items-center">
								<input type="radio" bind:group={surveyResponses.parentEducation} value="prefer-not-to-say" class="mr-3">
								<span class="text-gray-900 dark:text-white">Prefer not to say</span>
							</label>
						</div>
					</div>

					<!-- Question 5: Parent Ethnicity -->
					<div>
						<label class="block text-lg font-medium text-gray-900 dark:text-white mb-3">
							5. What is your ethnicity? (Select all that apply)
						</label>
						<div class="space-y-2">
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="white" class="mr-3">
								<span class="text-gray-900 dark:text-white">White</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="black-african-american" class="mr-3">
								<span class="text-gray-900 dark:text-white">Black or African American</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="hispanic-latino" class="mr-3">
								<span class="text-gray-900 dark:text-white">Hispanic or Latino</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="asian" class="mr-3">
								<span class="text-gray-900 dark:text-white">Asian</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="native-american" class="mr-3">
								<span class="text-gray-900 dark:text-white">Native American or Alaska Native</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="pacific-islander" class="mr-3">
								<span class="text-gray-900 dark:text-white">Native Hawaiian or Pacific Islander</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="middle-eastern" class="mr-3">
								<span class="text-gray-900 dark:text-white">Middle Eastern or North African</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="mixed-race" class="mr-3">
								<span class="text-gray-900 dark:text-white">Mixed race</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="other" class="mr-3">
								<span class="text-gray-900 dark:text-white">Other</span>
							</label>
							<label class="flex items-center">
								<input type="checkbox" bind:group={surveyResponses.parentEthnicity} value="prefer-not-to-say" class="mr-3">
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
		</div>
	</div>
</div>
