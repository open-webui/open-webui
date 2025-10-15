<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import { user } from '$lib/stores';

	let childProfiles: ChildProfile[] = [];
	let currentChild: ChildProfile | null = null;
	let selectedChildIndex: number = 0;
	let loading = true;
	let error = '';

	const loadChildProfiles = async () => {
		try {
			loading = true;
			childProfiles = await childProfileSync.getChildProfiles();
			
			if (childProfiles.length === 0) {
				// No profiles exist, redirect to create one
				goto('/kids/profile');
				return;
			}

			// Get current child
			const currentChildId = childProfileSync.getCurrentChildId();
			if (currentChildId) {
				const index = childProfiles.findIndex(child => child.id === currentChildId);
				if (index !== -1) {
					selectedChildIndex = index;
					currentChild = childProfiles[index];
				} else {
					selectedChildIndex = 0;
					currentChild = childProfiles[0];
				}
			} else {
				selectedChildIndex = 0;
				currentChild = childProfiles[0];
			}
		} catch (err) {
			console.error('Failed to load child profiles:', err);
			error = 'Failed to load child profile';
		} finally {
			loading = false;
		}
	};

	const selectChild = (index: number) => {
		selectedChildIndex = index;
		currentChild = childProfiles[index];
		childProfileSync.setCurrentChildId(currentChild.id);
	};

	const goToEdit = () => {
		goto('/kids/profile');
	};

	const goBack = () => {
		goto('/');
	};

	onMount(() => {
		loadChildProfiles();
	});
</script>

<svelte:head>
	<title>Child Profile Preview</title>
</svelte:head>

<div class="w-full h-full flex flex-col bg-gray-50 dark:bg-gray-900">
	<div class="flex-1 overflow-y-auto">
		<div class="max-w-4xl mx-auto px-4 py-8">
		<!-- Header -->
		<div class="mb-8">
			<button
				on:click={goBack}
				class="flex items-center text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 mb-4 transition-colors"
			>
				<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
				</svg>
				Back to Chat
			</button>
			
			<div class="flex items-center justify-between">
				<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
					Child Profile Preview
				</h1>
				
				<button
					on:click={goToEdit}
					class="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 font-medium"
				>
					Edit Profile
				</button>
			</div>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
			</div>
		{:else if error}
			<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
				<div class="flex items-center">
					<svg class="w-5 h-5 text-red-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
					</svg>
					<p class="text-red-800 dark:text-red-200">{error}</p>
				</div>
			</div>
		{:else if childProfiles.length === 0}
			<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
				<div class="text-center">
					<svg class="w-16 h-16 text-blue-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
					</svg>
					<h3 class="text-lg font-medium text-blue-900 dark:text-blue-100 mb-2">
						No Child Profile Found
					</h3>
					<p class="text-blue-700 dark:text-blue-300 mb-4">
						You haven't created a child profile yet. Let's set one up!
					</p>
					<button
						on:click={goToEdit}
						class="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 font-medium"
					>
						Create Child Profile
					</button>
				</div>
			</div>
		{:else}
			<!-- Multiple Children Selection -->
			{#if childProfiles.length > 1}
				<div class="mb-8">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
						Select Child Profile
					</h2>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
						{#each childProfiles as child, index}
							<button
								on:click={() => selectChild(index)}
								class="p-4 rounded-lg border-2 transition-all duration-200 text-left {selectedChildIndex === index ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}"
							>
								<div class="flex items-center space-x-3">
									<div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
										<span class="text-white font-semibold text-lg">
											{(child.name || 'Kid').charAt(0).toUpperCase()}
										</span>
									</div>
									<div class="flex-1">
										<h3 class="font-medium text-gray-900 dark:text-white">
											{child.name || `Kid ${index + 1}`}
										</h3>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{child.child_age || 'Age not set'} • {child.child_gender || 'Gender not set'}
										</p>
									</div>
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Current Child Profile Display -->
			{#if currentChild}
				<div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
					<div class="flex items-center space-x-6 mb-8">
						<div class="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
							<span class="text-white font-bold text-2xl">
								{(currentChild.name || 'Kid').charAt(0).toUpperCase()}
							</span>
						</div>
						<div>
							<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
								{currentChild.name || 'Unnamed Child'}
							</h2>
							<div class="flex items-center space-x-4">
								{#if currentChild.child_age}
									<span class="bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-sm font-medium">
										{currentChild.child_age}
									</span>
								{/if}
								{#if currentChild.child_gender}
									<span class="bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200 px-3 py-1 rounded-full text-sm font-medium">
										{currentChild.child_gender}
									</span>
								{/if}
							</div>
						</div>
					</div>

					<!-- Profile Details -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
						<!-- Basic Information -->
						<div>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
								Basic Information
							</h3>
							<div class="space-y-3">
								<div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
									<span class="text-gray-600 dark:text-gray-400 font-medium">Name:</span>
									<span class="text-gray-900 dark:text-white">{currentChild.name || 'Not set'}</span>
								</div>
								<div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
									<span class="text-gray-600 dark:text-gray-400 font-medium">Age:</span>
									<span class="text-gray-900 dark:text-white">{currentChild.child_age || 'Not set'}</span>
								</div>
								<div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
									<span class="text-gray-600 dark:text-gray-400 font-medium">Gender:</span>
									<span class="text-gray-900 dark:text-white">{currentChild.child_gender || 'Not set'}</span>
								</div>
								<div class="flex justify-between py-2">
									<span class="text-gray-600 dark:text-gray-400 font-medium">Created:</span>
									<span class="text-gray-900 dark:text-white">
										{currentChild.created_at ? (() => {
											try {
												const date = new Date(currentChild.created_at);
												return isNaN(date.getTime()) ? 'Unknown' : date.toLocaleDateString();
											} catch {
												return 'Unknown';
											}
										})() : 'Unknown'}
									</span>
								</div>
							</div>
						</div>

						<!-- Characteristics -->
						<div>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
								Learning Characteristics
							</h3>
							{#if currentChild.child_characteristics}
								<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
									<p class="text-gray-700 dark:text-gray-300 leading-relaxed">
										{currentChild.child_characteristics}
									</p>
								</div>
							{:else}
								<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
									<p class="text-gray-500 dark:text-gray-400 italic">
										No learning characteristics have been set yet.
									</p>
								</div>
							{/if}
						</div>
					</div>

					<!-- Personalization Note -->
					<div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
						<div class="text-sm text-gray-500 dark:text-gray-400 mb-6">
							This profile helps personalize the AI learning experience for {currentChild.name || 'your child'}.
						</div>
						
						<!-- Next Step Button -->
						<div class="flex justify-end">
							<button
								on:click={() => {
									// Update assignment step and proceed to next step
									localStorage.setItem('assignmentStep', '2');
									// Navigate to chat page and trigger parent mode
									window.location.href = '/';
									// Set a flag to trigger parent mode after page load
									localStorage.setItem('triggerParentMode', 'true');
								}}
								class="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
							>
								Choose and Next Step →
							</button>
						</div>
					</div>
				</div>
			{/if}
		{/if}
		</div>
	</div>
</div>
