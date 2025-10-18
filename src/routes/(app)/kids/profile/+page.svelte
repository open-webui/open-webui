<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	// Child profile data
	let childName: string = '';
	let childAge: string = '';
	let childGender: string = '';
	let childCharacteristics: string = '';
	let parentGender: string = '';
	let parentAge: string = '';
	let parentPreference: string = '';
	let parentingStyle: string = '';

	// Multi-child support - using backend ChildProfile type
	let childProfiles: ChildProfile[] = [];
	let selectedChildIndex: number = -1; // Start with no selection
	let showProfileModal: boolean = false;
	let editInModal: boolean = false;
	let showForm: boolean = false; // Control form visibility
	let showConfirmationModal: boolean = false; // Confirmation modal for workflow progression
	let isEditing: boolean = false; // Track edit mode
	let isProfileCompleted: boolean = false; // Track if profile is completed
	let childSelectedForQuestions: number = -1; // Track which child is selected for questions (-1 = none selected)
	// State for scroll indicator
	let showScrollIndicator: boolean = false;
	let hasScrolled: boolean = false;

	function getChildGridTemplate(): string {
		const cols = Math.max(1, Math.min((childProfiles?.length || 0) + 1, 5));
		return `repeat(${cols}, minmax(120px, 1fr))`;
	}

	function ensureAtLeastOneChild() {
		// No-op: allow empty list of children per user request
	}

	function hydrateFormFromSelectedChild() {
		ensureAtLeastOneChild();
		const sel = childProfiles[selectedChildIndex];
		childName = sel?.name || '';
		childAge = sel?.child_age || '';
		childGender = sel?.child_gender || '';
		childCharacteristics = sel?.child_characteristics || '';
		parentingStyle = sel?.parenting_style || '';
	}

	function applyFormToSelectedChild() {
		ensureAtLeastOneChild();
		const sel = childProfiles[selectedChildIndex];
		if (!sel) return;
		sel.name = childName;
		sel.child_age = childAge;
		sel.child_gender = childGender;
		sel.child_characteristics = childCharacteristics;
		sel.parenting_style = parentingStyle;
	}

	async function deleteChild(index: number) {
		const childToDelete = childProfiles[index];
		if (!childToDelete) return;

		try {
			await childProfileSync.deleteChildProfile(childToDelete.id);
			childProfiles = childProfiles.filter((_, i) => i !== index);
			
			// Adjust selectedChildIndex if needed
			if (childProfiles.length === 0) {
				selectedChildIndex = 0;
				childName = '';
				childAge = '';
				childGender = '';
				childCharacteristics = '';
				parentingStyle = '';
			} else {
				if (selectedChildIndex >= childProfiles.length) {
					selectedChildIndex = childProfiles.length - 1;
				}
				hydrateFormFromSelectedChild();
			}
			
			// Dispatch event to notify sidebar of child profile changes
			window.dispatchEvent(new CustomEvent('child-profiles-updated'));
			
			toast.success('Child profile deleted successfully!');
		} catch (error) {
			console.error('Failed to delete child profile:', error);
			toast.error('Failed to delete child profile');
		}
	}

	function addNewProfile() {
		// Don't reset if already adding a new profile
		if (selectedChildIndex === -1 && showForm && isEditing) {
			return;
		}
		
		// Reset form fields
		childName = '';
		childAge = '';
		childGender = '';
		childCharacteristics = '';
		parentingStyle = '';
		showForm = true;
		isEditing = true; // Set editing mode
		// Set selected index to -1 to indicate we're creating a new profile
		selectedChildIndex = -1;
	}

	async function saveNewProfile() {
		try {
			// Validate required fields
			if (!childName.trim()) {
				toast.error('Please enter a name for the child');
				return;
			}
			if (!childAge) {
				toast.error('Please select an age');
				return;
			}
			if (!childGender) {
				toast.error('Please select a gender');
				return;
			}

			const newChild = await childProfileSync.createChildProfile({
				name: childName,
				child_age: childAge,
				child_gender: childGender,
				child_characteristics: childCharacteristics,
				parenting_style: parentingStyle
			});
			
			childProfiles = [...childProfiles, newChild];
			selectedChildIndex = childProfiles.length - 1;
			showForm = true;
			
			// Dispatch event to notify sidebar of child profile changes
			window.dispatchEvent(new CustomEvent('child-profiles-updated'));
			
			toast.success('Child profile created successfully!');
		} catch (error) {
			console.error('Failed to create child profile:', error);
			toast.error('Failed to create child profile');
		}
	}

	function cancelAddProfile() {
		if (childProfiles.length > 0) {
			// If profiles exist, return to view mode
			showForm = false;
			isEditing = false;
			hydrateFormFromSelectedChild();
		} else {
			// If no profiles, just hide form
			showForm = false;
			isEditing = false;
			childName = '';
			childAge = '';
			childGender = '';
			childCharacteristics = '';
			parentingStyle = '';
		}
	}

	function selectChild(index: number) {
		selectedChildIndex = index;
		hydrateFormFromSelectedChild();
		showForm = false;
		isEditing = false;
	}

	async function loadChildProfile() {
		try {
			// Load child profiles from API via childProfileSync
			childProfiles = await childProfileSync.getChildProfiles();
			
			// Ensure childProfiles is always an array
			if (!childProfiles || !Array.isArray(childProfiles)) {
				console.warn('Child profiles returned invalid value, defaulting to empty array');
				childProfiles = [];
			}
			
			// Autoselect first profile if profiles exist
			if (childProfiles.length > 0) {
				selectedChildIndex = 0;
				hydrateFormFromSelectedChild();
				showForm = false; // Don't show form initially, wait for Edit click
				isProfileCompleted = true; // Profile exists
				childSelectedForQuestions = -1; // Reset selection state
			} else {
				selectedChildIndex = -1;
				showForm = false;
				isProfileCompleted = false;
				childSelectedForQuestions = -1;
			}
		} catch (error) {
			console.error('Failed to load child profiles:', error);
			// Fallback to empty array
			childProfiles = [];
		}
	}

	async function saveChildProfile() {
		try {
			// Validate required fields
			if (!childName.trim()) {
				toast.error('Please enter a name for the child');
				return;
			}
			if (!childAge) {
				toast.error('Please select an age');
				return;
			}
			if (!childGender) {
				toast.error('Please select a gender');
				return;
			}

			// If no profiles exist or we're creating a new profile, create a new one
			if (childProfiles.length === 0 || selectedChildIndex === -1) {
				const newChild = await childProfileSync.createChildProfile({
					name: childName,
					child_age: childAge,
					child_gender: childGender,
					child_characteristics: childCharacteristics,
					parenting_style: parentingStyle
				});
				if (childProfiles.length === 0) {
					childProfiles = [newChild];
					selectedChildIndex = 0;
				} else {
					childProfiles = [...childProfiles, newChild];
					selectedChildIndex = childProfiles.length - 1;
				}
			} else {
				// Apply current form to selected child
				applyFormToSelectedChild();
				
				const selectedChild = childProfiles[selectedChildIndex];
				if (selectedChild) {
					// Update the child profile via API
					await childProfileSync.updateChildProfile(selectedChild.id, {
						name: childName,
						child_age: childAge,
						child_gender: childGender,
						child_characteristics: childCharacteristics,
						parenting_style: parentingStyle
					});
				}
			}
			
			// Dispatch event to notify sidebar of child profile changes
			window.dispatchEvent(new CustomEvent('child-profiles-updated'));
			
			toast.success('Child profile saved successfully!');
			
			// Exit edit mode after saving and mark as completed
			isEditing = false;
			showForm = false;
			isProfileCompleted = true;
		} catch (error) {
			console.error('Failed to save child profile:', error);
			toast.error('Failed to save child profile');
		}
	}

	function proceedToNextStep() {
		// Update assignment step to 2 (moderation scenarios)
		localStorage.setItem('assignmentStep', '2');
		goto('/moderation-scenario');
	}

	function continueEditing() {
		showConfirmationModal = false;
	}

	function startEditing() {
		isEditing = true;
		showForm = true;
	}

	function selectChildForQuestions(index: number) {
		childSelectedForQuestions = index;
		const childId = childProfiles[index]?.id;
		if (childId) {
			localStorage.setItem('selectedChildForQuestions', childId.toString());
		}
	// Unlock Step 2 immediately before showing the modal
	localStorage.setItem('assignmentStep', '2');
	localStorage.setItem('moderationScenariosAccessed', 'true');
	localStorage.setItem('unlock_moderation', 'true');
	window.dispatchEvent(new Event('storage'));
	window.dispatchEvent(new Event('workflow-updated'));
		toast.success(`${childProfiles[index]?.name} selected for questions`);
		showConfirmationModal = true;
	}

	function formatDisplayValue(value: string, type: string): string {
		if (!value) return 'Not specified';
		
		switch (type) {
			case 'age':
				return value;
			case 'gender':
				return value;
			default:
				return value;
		}
	}

	onMount(() => {
		(async () => {
		// Redirect if instructions not confirmed
		if (localStorage.getItem('instructionsCompleted') !== 'true') {
			goto('/assignment-instructions');
			return;
		}
			await loadChildProfile();
			
			// Check if child has been selected for questions
			const savedChildId = localStorage.getItem('selectedChildForQuestions');
			if (savedChildId) {
				const index = childProfiles.findIndex(c => c.id?.toString() === savedChildId);
				if (index !== -1) {
					childSelectedForQuestions = index;
				}
			}
		})();
		
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
</script>

<svelte:head>
	<title>Child Profile - Kids Mode</title>
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
						Child Profile
					</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<button
					on:click={() => goto('/assignment-instructions')}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors flex items-center space-x-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
					</svg>
					<span>Previous Task</span>
				</button>
				<button
					on:click={() => {
						localStorage.setItem('assignmentStep', '2');
						goto('/moderation-scenario');
					}}
					disabled={childSelectedForQuestions === -1}
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 {
						childSelectedForQuestions !== -1
							? 'bg-blue-500 hover:bg-blue-600 text-white'
							: 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
					}"
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
		<div class="mb-8"></div>

		<!-- Child Selection -->
		{#if childProfiles && childProfiles.length > 0}
			<div class="mb-8">
				<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Select Your Profile</h2>
					<div class="grid gap-3" style={`grid-template-columns: ${getChildGridTemplate()}`}>
						{#each childProfiles as c, i}
							<div class="relative group flex flex-col">
								<button 
									type="button"
									class={`w-full px-6 py-4 rounded-full transition-all duration-200 ${i===selectedChildIndex ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg ring-2 ring-blue-400/50 transform scale-105' : 'bg-gradient-to-r from-gray-700 to-gray-600 text-white ring-1 ring-gray-500/30 hover:from-gray-600 hover:to-gray-500 hover:ring-gray-400/50 hover:scale-102'}`}
									on:click={() => selectChild(i)}>
									<span class="font-medium">{c.name || `Kid ${i + 1}`}</span>
									{#if childSelectedForQuestions === i}
										<div class="absolute -top-1 -left-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center z-10">
											<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
											</svg>
										</div>
									{/if}
								</button>
								
								<!-- Add "Select for questions" button below each profile -->
								{#if childSelectedForQuestions !== i}
									<button
										type="button"
										on:click={() => selectChildForQuestions(i)}
										class="mt-2 w-full px-4 py-2 text-sm bg-green-500 hover:bg-green-600 text-white rounded-lg transition-all"
									>
										Select for questions
									</button>
								{:else}
									<div class="mt-2 w-full px-4 py-2 text-sm bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 rounded-lg text-center font-medium">
										Selected ✓
									</div>
								{/if}
								
								<!-- Delete button -->
								<button 
									type="button"
									class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center z-20"
									on:click|stopPropagation={() => deleteChild(i)}
									title="Delete child">
									×
								</button>
							</div>
						{/each}
						<button 
							type="button" 
							class="px-6 py-4 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 shadow-lg ring-1 ring-gray-300/30 dark:ring-gray-600/30 hover:bg-gray-300 dark:hover:bg-gray-600 hover:ring-gray-400/50 dark:hover:ring-gray-500/50 hover:scale-105 transition-all duration-200" 
							on:click={addNewProfile}>
							<span class="font-medium">+ Add Profile</span>
						</button>
					</div>
				</div>
			</div>
		{:else}
			<!-- Empty State - No child profiles -->
			<div class="mb-8">
				<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8 text-center">
					<div class="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
						</svg>
					</div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Child Profiles Yet</h2>
					<p class="text-gray-600 dark:text-gray-300 mb-6">
						Create your first child profile to get started with personalized AI learning.
					</p>
					<button 
						type="button" 
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						on:click={addNewProfile}>
						+ Add Your First Child Profile
					</button>
				</div>
			</div>
		{/if}

		<!-- Profile Display (Read-only when not editing) -->
		{#if childProfiles.length > 0 && selectedChildIndex >= 0 && !showForm}
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8">
			<div class="flex justify-between items-start mb-6">
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white">Profile Information</h3>
				<button
					type="button"
					on:click={startEditing}
					class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition"
				>
					Edit
				</button>
			</div>
			<div class="space-y-4">
				<div>
					<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Name</div>
					<p class="text-gray-900 dark:text-white">{childProfiles[selectedChildIndex]?.name || 'Not specified'}</p>
				</div>
				<div>
					<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Age</div>
					<p class="text-gray-900 dark:text-white">{childProfiles[selectedChildIndex]?.child_age || 'Not specified'}</p>
				</div>
				<div>
					<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Gender</div>
					<p class="text-gray-900 dark:text-white">{childProfiles[selectedChildIndex]?.child_gender || 'Not specified'}</p>
				</div>
				<div>
					<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Characteristics & Interests</div>
					<p class="text-gray-900 dark:text-white whitespace-pre-wrap">{childProfiles[selectedChildIndex]?.child_characteristics || 'Not specified'}</p>
				</div>
				<div>
					<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Parenting Style</div>
					<p class="text-gray-900 dark:text-white whitespace-pre-wrap">{childProfiles[selectedChildIndex]?.parenting_style || 'Not specified'}</p>
				</div>
			</div>
			
		</div>
		{/if}

		<!-- Profile Form - Show when form should be displayed -->
		{#if showForm && isEditing}
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8">
			<form on:submit|preventDefault={saveChildProfile} class="space-y-6">
				<!-- Form Fields -->
				<div class="space-y-6">
					<h3 class="text-xl font-semibold text-gray-900 dark:text-white">Child Information</h3>
					
					<div>
						<label for="childName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Name
						</label>
						<input
							type="text"
							id="childName"
							bind:value={childName}
							placeholder="Enter child's name"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
						/>
					</div>

					<div>
						<label for="childAge" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Age
						</label>
						<select
							id="childAge"
							bind:value={childAge}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
						>
							<option value="">Select age</option>
							<option value="13 years old">13 years old</option>
							<option value="14 years old">14 years old</option>
							<option value="15 years old">15 years old</option>
							<option value="16 years old">16 years old</option>
							<option value="17 years old">17 years old</option>
							<option value="18 years old">18 years old</option>
						</select>
					</div>

					<div>
						<label for="childGender" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Gender
						</label>
						<select
							id="childGender"
							bind:value={childGender}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
						>
							<option value="">Select gender</option>
							<option value="Male">Male</option>
							<option value="Female">Female</option>
							<option value="Non-binary">Non-binary</option>
							<option value="Prefer not to say">Prefer not to say</option>
						</select>
					</div>

					<div>
						<label for="childCharacteristics" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Characteristics & Interests
						</label>
						<textarea
							id="childCharacteristics"
							bind:value={childCharacteristics}
							rows="4"
							placeholder="Describe your child's personality, interests, learning style, etc."
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
						></textarea>
					</div>

					<div>
						<label for="parentingStyle" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Parenting Style
						</label>
						<textarea
							id="parentingStyle"
							bind:value={parentingStyle}
							rows="4"
							placeholder="Describe your parenting approach and values for this child"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
						></textarea>
					</div>
				</div>

				<!-- Save Button -->
				<div class="flex justify-end space-x-3 pt-6">
					{#if childProfiles.length > 0}
						<button
							type="button"
							on:click={cancelAddProfile}
							class="bg-gray-500 hover:bg-gray-600 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200"
						>
							Cancel
						</button>
					{/if}
					<button
						type="submit"
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
					>
						Save Profile
					</button>
				</div>
				</form>
		</div>
		{/if}


		<!-- Confirmation Modal for Workflow Progression -->
		{#if showConfirmationModal}
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showConfirmationModal = false}>
			<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" on:click|stopPropagation>
				<div class="text-center mb-6">
					<div class="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
						</svg>
					</div>
					<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
						Task 1 Complete
					</h3>
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
</div>
