<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';

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

	// Multi-child support
	interface ChildProfileItem {
		id: string;
		name: string;
		childAge: string;
		childGender: string;
		childCharacteristics: string;
		parentingStyle: string;
	}

	let childProfiles: ChildProfileItem[] = [];
	let selectedChildIndex: number = 0;
	let showProfileModal: boolean = false;
	let editInModal: boolean = false;

	function getChildGridTemplate(): string {
		const cols = Math.max(1, Math.min((childProfiles?.length || 1), 5));
		return `repeat(${cols}, minmax(120px, 1fr))`;
	}

	function ensureAtLeastOneChild() {
		// No-op: allow empty list of children per user request
	}

	function hydrateFormFromSelectedChild() {
		ensureAtLeastOneChild();
		const sel = childProfiles[selectedChildIndex];
		childName = sel?.name || '';
		childAge = sel?.childAge || '';
		childGender = sel?.childGender || '';
		childCharacteristics = sel?.childCharacteristics || '';
		parentingStyle = sel?.parentingStyle || '';
	}

	function applyFormToSelectedChild() {
		ensureAtLeastOneChild();
		const sel = childProfiles[selectedChildIndex];
		if (!sel) return;
		sel.name = childName;
		sel.childAge = childAge;
		sel.childGender = childGender;
		sel.childCharacteristics = childCharacteristics;
		sel.parentingStyle = parentingStyle;
	}

	function deleteChild(index: number) {
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
		
		// Save updated profiles
		localStorage.setItem('childProfiles', JSON.stringify(childProfiles));
	}

	function addNewChild() {
		childProfiles = [
			...childProfiles,
			{
				id: crypto.randomUUID(),
				name: '',
				childAge: '',
				childGender: '',
				childCharacteristics: '',
				parentingStyle: ''
			}
		];
		selectedChildIndex = childProfiles.length - 1;
		hydrateFormFromSelectedChild();
	}

	function loadChildProfile() {
		try {
			const savedProfiles = localStorage.getItem('childProfiles');
			if (savedProfiles) {
				childProfiles = JSON.parse(savedProfiles);
			} else {
				// Migrate old single profile if it exists
				const oldName = localStorage.getItem('childName');
				const oldAge = localStorage.getItem('childAge');
				const oldGender = localStorage.getItem('childGender');
				const oldCharacteristics = localStorage.getItem('childCharacteristics');
				const oldParentingStyle = localStorage.getItem('parentingStyle');
				
				if (oldName || oldAge || oldGender || oldCharacteristics || oldParentingStyle) {
					childProfiles = [{
						id: crypto.randomUUID(),
						name: oldName || '',
						childAge: oldAge || '',
						childGender: oldGender || '',
						childCharacteristics: oldCharacteristics || '',
						parentingStyle: oldParentingStyle || ''
					}];
					
					// Clear old storage
					localStorage.removeItem('childName');
					localStorage.removeItem('childAge');
					localStorage.removeItem('childGender');
					localStorage.removeItem('childCharacteristics');
					localStorage.removeItem('parentingStyle');
					
					// Save new format
					localStorage.setItem('childProfiles', JSON.stringify(childProfiles));
				}
			}
		} catch (error) {
			console.error('Error loading child profiles:', error);
		}
		
		if (childProfiles.length > 0) {
			hydrateFormFromSelectedChild();
		}
	}

	function saveChildProfile() {
		// If no profiles exist, create a new one
		if (childProfiles.length === 0) {
			childProfiles = [{
				id: crypto.randomUUID(),
				name: childName,
				childAge: childAge,
				childGender: childGender,
				childCharacteristics: childCharacteristics,
				parentingStyle: parentingStyle
			}];
			selectedChildIndex = 0;
		} else {
			applyFormToSelectedChild();
		}
		
		localStorage.setItem('childProfiles', JSON.stringify(childProfiles));
		
		// Go back to main kids page
		goto('/');
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
		loadChildProfile();
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
		{#if childProfiles.length > 0}
			<div class="mb-8">
				<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Select Your Profile</h2>
					<div class="grid gap-3" style={`grid-template-columns: ${getChildGridTemplate()}`}>
						{#each childProfiles as c, i}
							<div class="relative group">
								<button 
									type="button"
									class={`w-full px-6 py-4 rounded-full transition-all duration-200 ${i===selectedChildIndex ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg ring-2 ring-blue-400/50 transform scale-105' : 'bg-gradient-to-r from-gray-700 to-gray-600 text-white ring-1 ring-gray-500/30 hover:from-gray-600 hover:to-gray-500 hover:ring-gray-400/50 hover:scale-102'}`}
									on:click={() => { selectedChildIndex = i; hydrateFormFromSelectedChild(); }}>
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
							on:click={addNewChild}>
							<span class="font-medium">+ Add Profile</span>
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Profile Form -->
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
								<option value="3 years old">3 years old</option>
								<option value="4 years old">4 years old</option>
								<option value="5 years old">5 years old</option>
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
	</div>
	</div>
</div>
