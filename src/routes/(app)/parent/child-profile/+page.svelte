<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar, user } from '$lib/stores';
	import { get } from 'svelte/store';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import ChildProfileForm from '$lib/components/profile/ChildProfileForm.svelte';

	let profileSaved: boolean = false;

	async function handleProfileSaved(profile: ChildProfile) {
		profileSaved = true;
		// Redirect to parent dashboard after a short delay
		setTimeout(() => {
			goto('/parent');
		}, 1500);
	}

	async function handleProfileCreated(profile: ChildProfile) {
		profileSaved = true;
		// Redirect to parent dashboard after a short delay
		setTimeout(() => {
			goto('/parent');
		}, 1500);
	}

	async function handleChildSelected(profile: ChildProfile, index: number) {
		// Parent view only needs to update backend selection
		await childProfileSync.setCurrentChildId(profile.id);
	}

	function handleContinue() {
		goto('/parent');
	}
</script>

<svelte:head>
	<title>Child Profile - Parent Onboarding</title>
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
					<div class="flex items-center text-xl font-semibold">Child Profile Setup</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<button
					on:click={() => goto('/parent')}
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
					<span>Back</span>
				</button>
				{#if profileSaved}
					<button
						on:click={handleContinue}
						class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 bg-blue-500 hover:bg-blue-600 text-white"
					>
						<span>Continue</span>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"
							></path>
						</svg>
					</button>
				{/if}
			</div>
		</div>
	</nav>

	<!-- Child Profile Form Component (without research fields or personality traits) -->
	<ChildProfileForm
		showResearchFields={false}
		requireResearchFields={false}
		showPersonalityTraits={false}
		onProfileCreated={handleProfileCreated}
		onProfileSaved={handleProfileSaved}
		onChildSelected={handleChildSelected}
	/>
</div>
