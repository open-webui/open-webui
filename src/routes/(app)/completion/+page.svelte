<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';

	onMount(() => {
	// Ensure sidebar reflects completion when landing here (idempotent)
	localStorage.setItem('assignmentStep', '4');
	localStorage.setItem('assignmentCompleted', 'true');
	
	// Redirect to Prolific completion page
	// Open in new tab so user can see completion message and close this tab
	window.open('https://app.prolific.com/submissions/complete?cc=C4CEBIWM', '_blank');
	});
</script>

<svelte:head>
	<title>Completion</title>
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
						Completion
					</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<button
					on:click={() => goto('/exit-survey')}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex items-center space-x-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
					</svg>
					<span>Previous Task</span>
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
						Thank You for Completing the Study!
					</h1>
					<p class="text-gray-600 dark:text-gray-300 mt-2">
						You're all done! A new tab should have opened to complete your Prolific submission. If it didn't open automatically, please click the button below.
					</p>
				</div>
			</div>

			<!-- Manual Prolific Redirect Button -->
			<div class="mt-6">
				<a
					href="https://app.prolific.com/submissions/complete?cc=C4CEBIWM"
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors shadow-md"
				>
					<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
					</svg>
					Complete Prolific Submission
				</a>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
					Click here if the Prolific page didn't open automatically
				</p>
			</div>

		</div>
	</div>
</div>