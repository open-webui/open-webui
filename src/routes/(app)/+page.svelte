<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import Chat from '$lib/components/chat/Chat.svelte';

	let assignmentStep = 1;

	onMount(() => {
		// Check current assignment step from localStorage
		const storedStep = localStorage.getItem('assignmentStep');
		if (storedStep) {
			assignmentStep = parseInt(storedStep);
		} else {
			// Initialize to step 1 for new users
			localStorage.setItem('assignmentStep', '1');
			assignmentStep = 1;
		}

		// Check if assignment is completed
		const assignmentCompleted = localStorage.getItem('assignmentCompleted');
		if (assignmentCompleted === 'true') {
			// Show chat interface for completed users
			return;
		}

		// Redirect to assignment instructions for new users
		goto('/assignment-instructions');
	});

	function continueToWorkflow() {
		// Navigate based on current assignment step
		switch (assignmentStep) {
			case 1:
				goto('/kids/profile');
				break;
			case 2:
				goto('/moderation-scenario');
				break;
			case 3:
				goto('/exit-survey');
				break;
			case 4:
			default:
				goto('/completion');
				break;
		}
	}
</script>

{#if localStorage.getItem('assignmentCompleted') === 'true'}
	<Chat />
{:else}
	<div
		class="flex flex-col w-full h-screen max-h-[100dvh] bg-gray-50 dark:bg-gray-900 transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<div class="flex-1 flex items-center justify-center">
			<div class="max-w-3xl mx-auto px-8 py-12 text-center">
				<!-- Placeholder content -->
				<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-12 border border-gray-200 dark:border-gray-700">
					<div class="mb-8">
						<h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">
							&#123;insert intro page&#125;
						</h1>
						<p class="text-lg text-gray-600 dark:text-gray-400">
							Welcome to the research assignment workflow
						</p>
					</div>

					<button
						on:click={continueToWorkflow}
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-12 py-4 rounded-lg font-semibold text-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
					>
						Continue
					</button>

					<div class="mt-6 text-sm text-gray-500 dark:text-gray-400">
						Step {assignmentStep} of 3
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
