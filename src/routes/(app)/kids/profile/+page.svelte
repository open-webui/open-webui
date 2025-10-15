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
	let showAddProfileModal: boolean = false;
	let showForm: boolean = false; // Control form visibility
	let showConfirmationModal: boolean = false; // Confirmation modal for workflow progression

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
			
			toast.success('Child profile deleted successfully!');
		} catch (error) {
			console.error('Failed to delete child profile:', error);
			toast.error('Failed to delete child profile');
		}
	}

	function openAddProfileModal() {
		// Reset form fields
		childName = '';
		childAge = '';
		childGender = '';
		childCharacteristics = '';
		parentingStyle = '';
		showAddProfileModal = true;
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
			showAddProfileModal = false;
			toast.success('Child profile created successfully!');
			
			// Show confirmation modal after creating new profile
			showConfirmationModal = true;
		} catch (error) {
			console.error('Failed to create child profile:', error);
			toast.error('Failed to create child profile');
		}
	}

	function cancelAddProfile() {
		showAddProfileModal = false;
		// Reset form fields
		childName = '';
		childAge = '';
		childGender = '';
		childCharacteristics = '';
		parentingStyle = '';
	}

	function selectChild(index: number) {
		selectedChildIndex = index;
		hydrateFormFromSelectedChild();
		showForm = true;
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
			
			// Don't automatically show form - user must click on a child
			showForm = false;
			selectedChildIndex = -1;
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

			// If no profiles exist, create a new one
			if (childProfiles.length === 0) {
				const newChild = await childProfileSync.createChildProfile({
					name: childName,
					child_age: childAge,
					child_gender: childGender,
					child_characteristics: childCharacteristics,
					parenting_style: parentingStyle
				});
				childProfiles = [newChild];
				selectedChildIndex = 0;
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
			
			toast.success('Child profile saved successfully!');
			
			// Show confirmation modal for workflow progression
			showConfirmationModal = true;
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

	onMount(async () => {
		await loadChildProfile();
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
	</nav>

	<div class="flex-1 max-h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
		<div class="max-w-4xl mx-auto px-4 py-8">
		<!-- Header -->
		<div class="mb-8">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-gray-600 dark:text-gray-400">
						Set up your profile to personalize your AI learning experience.
					</p>
				</div>
				<button
					on:click={() => goto('/')}
					class="flex items-center space-x-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
					</svg>
					<span>Back to Chat</span>
				</button>
			</div>
		</div>

		<!-- Child Selection -->
		{#if childProfiles && childProfiles.length > 0}
			<div class="mb-8">
				<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Select Your Profile</h2>
					<div class="grid gap-3" style={`grid-template-columns: ${getChildGridTemplate()}`}>
						{#each childProfiles as c, i}
							<div class="relative group">
								<button 
									type="button"
									class={`w-full px-6 py-4 rounded-full transition-all duration-200 ${i===selectedChildIndex ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg ring-2 ring-blue-400/50 transform scale-105' : 'bg-gradient-to-r from-gray-700 to-gray-600 text-white ring-1 ring-gray-500/30 hover:from-gray-600 hover:to-gray-500 hover:ring-gray-400/50 hover:scale-102'}`}
									on:click={() => selectChild(i)}>
									<span class="font-medium">{c.name || `Kid ${i + 1}`}</span>
								</button>
								<button 
									type="button"
									class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center"
									on:click|stopPropagation={() => deleteChild(i)}
									title="Delete child">
									×
								</button>
							</div>
						{/each}
						<button 
							type="button" 
							class="px-6 py-4 rounded-full bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg ring-1 ring-emerald-400/30 hover:from-emerald-400 hover:to-teal-500 hover:ring-emerald-300/50 hover:scale-105 transition-all duration-200" 
							on:click={openAddProfileModal}>
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
						on:click={openAddProfileModal}>
						+ Add Your First Child Profile
					</button>
				</div>
			</div>
		{/if}

		<!-- Profile Form - Only show when a child is selected -->
		{#if showForm && selectedChildIndex >= 0}
		<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8">
			<form on:submit|preventDefault={saveChildProfile} class="space-y-6">
				<!-- Child Information Section -->
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
					<!-- Left Column: Child Data -->
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
								<option value="6 years old">6 years old</option>
								<option value="7 years old">7 years old</option>
								<option value="8 years old">8 years old</option>
								<option value="9 years old">9 years old</option>
								<option value="10 years old">10 years old</option>
								<option value="11 years old">11 years old</option>
								<option value="12 years old">12 years old</option>
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
					</div>

					<!-- Right Column: Parent Information -->
					<div class="space-y-6">
						<h3 class="text-xl font-semibold text-gray-900 dark:text-white">Parent Information</h3>
						
						<div>
							<label for="parentingStyle" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Parenting Style
							</label>
							<textarea
								id="parentingStyle"
								bind:value={parentingStyle}
								rows="4"
								placeholder="Describe your parenting approach and values"
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
							></textarea>
						</div>
					</div>
				</div>

				<!-- Save Button -->
				<div class="flex justify-end pt-6">
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

		<!-- Add Profile Modal -->
		{#if showAddProfileModal}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={cancelAddProfile}>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-2xl w-full mx-4 shadow-2xl relative" on:click|stopPropagation>
				<div class="flex items-center justify-between mb-6">
					<h3 class="text-xl font-semibold text-gray-900 dark:text-white">
						Add New Child Profile
					</h3>
					<button
						type="button"
						on:click={cancelAddProfile}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
						aria-label="Close dialog"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
				
				<form on:submit|preventDefault={saveNewProfile} class="space-y-6">
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
						<!-- Child Information -->
						<div class="space-y-4">
							<h4 class="text-lg font-medium text-gray-900 dark:text-white">Child Information</h4>
							
							<div>
								<label for="modalChildName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Name *
								</label>
								<input
									type="text"
									id="modalChildName"
									bind:value={childName}
									placeholder="Enter child's name"
									required
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								/>
							</div>

							<div>
								<label for="modalChildAge" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Age *
								</label>
								<select
									id="modalChildAge"
									bind:value={childAge}
									required
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								>
									<option value="">Select age</option>
									<option value="6 years old">6 years old</option>
									<option value="7 years old">7 years old</option>
									<option value="8 years old">8 years old</option>
									<option value="9 years old">9 years old</option>
									<option value="10 years old">10 years old</option>
									<option value="11 years old">11 years old</option>
									<option value="12 years old">12 years old</option>
									<option value="13 years old">13 years old</option>
									<option value="14 years old">14 years old</option>
									<option value="15 years old">15 years old</option>
									<option value="16 years old">16 years old</option>
									<option value="17 years old">17 years old</option>
								</select>
							</div>

							<div>
								<label for="modalChildGender" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Gender *
								</label>
								<select
									id="modalChildGender"
									bind:value={childGender}
									required
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								>
									<option value="">Select gender</option>
									<option value="Male">Male</option>
									<option value="Female">Female</option>
									<option value="Other">Other</option>
									<option value="Prefer not to say">Prefer not to say</option>
								</select>
							</div>
						</div>

						<!-- Parent Information -->
						<div class="space-y-4">
							<h4 class="text-lg font-medium text-gray-900 dark:text-white">Parent Information</h4>
							
							<div>
								<label for="modalChildCharacteristics" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Characteristics & Interests
								</label>
								<textarea
									id="modalChildCharacteristics"
									bind:value={childCharacteristics}
									rows="4"
									placeholder="Describe your child's personality, interests, learning style, etc."
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
								></textarea>
							</div>

							<div>
								<label for="modalParentingStyle" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Parenting Style
								</label>
								<textarea
									id="modalParentingStyle"
									bind:value={parentingStyle}
									rows="4"
									placeholder="Describe your parenting approach and values"
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
								></textarea>
							</div>
						</div>
					</div>

					<div class="flex justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
						<button
							type="button"
							on:click={cancelAddProfile}
							class="px-6 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
						>
							Cancel
						</button>
						<button
							type="submit"
							class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-6 py-2 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						>
							Create Profile
						</button>
					</div>
				</form>
			</div>
		</div>
		{/if}

		<!-- Confirmation Modal for Workflow Progression -->
		{#if showConfirmationModal}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showConfirmationModal = false}>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl" on:click|stopPropagation>
				<div class="text-center mb-6">
					<div class="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
						</svg>
					</div>
					<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
						Profile Saved!
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
						Yes, Continue to Moderation Scenarios
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
</div>
