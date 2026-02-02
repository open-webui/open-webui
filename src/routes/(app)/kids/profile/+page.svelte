<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { showSidebar, user } from '$lib/stores';
	import { get } from 'svelte/store';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import { getChildProfiles } from '$lib/apis/child-profiles';
	import { assignScenariosForChild } from '$lib/services/scenarioAssignment';
	import AssignmentTimeTracker from '$lib/components/assignment/AssignmentTimeTracker.svelte';
	import VideoModal from '$lib/components/common/VideoModal.svelte';
	import { getUserType } from '$lib/utils';
	import ChildProfileForm from '$lib/components/profile/ChildProfileForm.svelte';

	const i18n = getContext('i18n');

	let showConfirmationModal: boolean = false;
	let childSelectedForQuestions: number = -1;
	let showScrollIndicator: boolean = false;
	let hasScrolled: boolean = false;
	let mainPageContainer: HTMLElement;

	// Assignment time tracking
	$: sessionNumber = $user?.session_number || 1;

	// Video modal state
	let showHelpVideo: boolean = false;

	// Function to determine session number for new child profile
	async function determineSessionNumberForUser(userId: string, token: string): Promise<number> {
		try {
			const profiles = await getChildProfiles(token);
			if (Array.isArray(profiles) && profiles.length > 0) {
				const maxSession = Math.max(...profiles.map((p: ChildProfile) => p.session_number || 1));
				const nextSession = maxSession + 1;
				console.log(`Determined session number: ${nextSession} (max existing: ${maxSession})`);
				return nextSession;
			} else {
				console.log('No existing profiles, using session number: 1');
				return 1;
			}
		} catch (error) {
			console.error('Error determining session number, defaulting to 1:', error);
			return 1;
		}
	}

	async function handleProfileCreated(profile: ChildProfile) {
		// Trigger scenario assignment for quiz workflow
		const userId = ($user as any)?.id;
		const token = localStorage.getItem('token') || '';

		if (userId && token) {
			const sessionNumber = await determineSessionNumberForUser(userId, token);
			assignScenariosForChild(profile.id, userId, sessionNumber, token, 6)
				.then((result) => {
					console.log(`✅ Assigned ${result.assignmentCount} scenarios for child ${profile.id}`);
					if (result.assignmentCount < 6) {
						console.warn(`⚠️ Only ${result.assignmentCount}/6 scenarios assigned`);
					}
				})
				.catch((error) => {
					console.error('❌ Failed to assign scenarios:', error);
				});
		}

		// Set child as selected for questions
		const profiles = await childProfileSync.getChildProfiles();
		const index = profiles.findIndex((p) => p.id === profile.id);
		if (index !== -1) {
			childSelectedForQuestions = index;
			await childProfileSync.setCurrentChildId(profile.id);

			// Unlock Step 2
			localStorage.setItem('assignmentStep', '2');
			localStorage.setItem('moderationScenariosAccessed', 'true');
			localStorage.setItem('unlock_moderation', 'true');
			window.dispatchEvent(new Event('storage'));
			window.dispatchEvent(new Event('workflow-updated'));

			// Show confirmation modal
			showConfirmationModal = true;
		}
	}

	function getChildGridTemplate(): string {
		const cols = Math.max(1, Math.min((childProfiles?.length || 0) + 1, 5));
		return `repeat(${cols}, minmax(120px, 1fr))`;
	}

	// Reactive statement to track selected characteristics
	$: console.log('Selected characteristics:', selectedSubCharacteristics);
	$: console.log('Expanded traits:', Array.from(expandedTraits));

	// Personality trait helper functions
	function toggleTrait(traitId: string) {
		if (expandedTraits.has(traitId)) {
			expandedTraits.delete(traitId);
		} else {
			expandedTraits.add(traitId);
		}
		expandedTraits = expandedTraits; // Trigger reactivity
	}

	function getSelectedSubCharacteristics(): SubCharacteristic[] {
		const selected: SubCharacteristic[] = [];

		// Go through all traits and find selected characteristics
		for (const trait of personalityTraits) {
			const matchingChars = trait.subCharacteristics.filter((sub) =>
				selectedSubCharacteristics.includes(sub.id)
			);
			selected.push(...matchingChars);
		}

		return selected;
	}

	function getSelectedSubCharacteristicNames(): string[] {
		return getSelectedSubCharacteristics().map((sub) => sub.name);
	}

	function getPersonalityDescription(): string {
		const subChars = getSelectedSubCharacteristics();

		if (subChars.length === 0) return '';

		// Group characteristics by trait
		const traitGroups = new Map<string, string[]>();

		for (const subChar of subChars) {
			// Find which trait this belongs to
			const trait = personalityTraits.find((t) =>
				t.subCharacteristics.some((sc) => sc.id === subChar.id)
			);

			if (trait) {
				if (!traitGroups.has(trait.name)) {
					traitGroups.set(trait.name, []);
				}
				traitGroups.get(trait.name)!.push(subChar.name);
			}
		}

		// Format as "Trait: char1, char2\nTrait2: char3, char4"
		const descriptions: string[] = [];
		for (const [traitName, chars] of traitGroups.entries()) {
			descriptions.push(`${traitName}: ${chars.join(', ')}`);
		}

		return descriptions.join('\n');
	}

	function ensureAtLeastOneChild() {
		// No-op: allow empty list of children per user request
	}

	function hydrateFormFromSelectedChild() {
		ensureAtLeastOneChild();
		const sel = childProfiles[selectedChildIndex];

		// Debug: Log the selected child data to verify survey fields are present
		console.log('Hydrating form from child profile:', {
			id: sel?.id,
			name: sel?.name,
			is_only_child: (sel as any)?.is_only_child,
			child_has_ai_use: (sel as any)?.child_has_ai_use,
			parent_llm_monitoring_level: (sel as any)?.parent_llm_monitoring_level,
			child_ai_use_contexts: (sel as any)?.child_ai_use_contexts
		});

		childName = sel?.name || '';
		childAge = sel?.child_age || '';

		// Handle gender - check if it's stored as "Other: [text]" format (legacy) or separate field
		const genderValue = sel?.child_gender || '';
		if (genderValue.startsWith('Other: ')) {
			// Legacy format - parse it
			childGender = 'Other';
			childGenderOther = genderValue.substring('Other: '.length);
		} else if (genderValue === 'Other') {
			// New format - use separate field
			childGender = 'Other';
			childGenderOther = (sel as any)?.child_gender_other || '';
		} else {
			childGender = genderValue;
			childGenderOther = (sel as any)?.child_gender_other || '';
		}

		// Research fields (optional if older profiles lack them)
		// Handle is_only_child - convert boolean to string for radio buttons
		if (typeof (sel as any)?.is_only_child === 'boolean') {
			isOnlyChild = (sel as any).is_only_child ? 'yes' : 'no';
		} else {
			isOnlyChild = '';
		}

		// Handle child_has_ai_use
		childHasAIUse = (sel as any)?.child_has_ai_use || '';

		// Handle child_ai_use_contexts - ensure it's an array
		const contexts = (sel as any)?.child_ai_use_contexts;
		if (Array.isArray(contexts)) {
			childAIUseContexts = contexts;
		} else if (contexts) {
			// If it's a string or other type, try to parse it
			childAIUseContexts = [];
		} else {
			childAIUseContexts = [];
		}

		// Handle monitoring level
		const monitoringValue = (sel as any)?.parent_llm_monitoring_level;
		if (monitoringValue) {
			parentLLMMonitoringLevel = monitoringValue;
		} else {
			parentLLMMonitoringLevel = '';
		}

		// Load "Other" text fields
		childAIUseContextsOther = (sel as any)?.child_ai_use_contexts_other || '';
		parentLLMMonitoringOther = (sel as any)?.parent_llm_monitoring_other || '';

		// Parse personality traits from stored characteristics
		if (sel?.child_characteristics) {
			const characteristics = sel.child_characteristics;

			// Check if this contains our format: "Trait: char1, char2\n\nAdditional characteristics:\ntext"
			if (characteristics.includes('Additional characteristics:')) {
				// Extract the additional characteristics part (after "Additional characteristics:")
				const additionalStart = characteristics.indexOf('Additional characteristics:');
				if (additionalStart !== -1) {
					childCharacteristics = characteristics
						.substring(additionalStart + 'Additional characteristics:'.length)
						.trim();

					// Extract personality traits part (before "Additional characteristics:")
					const personalityPart = characteristics.substring(0, additionalStart).trim();

					// Parse trait lines: "Trait: char1, char2\nTrait2: char3, char4"
					if (personalityPart) {
						const traitLines = personalityPart.split('\n');
						const restoredIds: string[] = [];

						for (const line of traitLines) {
							// Format: "Trait: char1, char2"
							const match = line.match(/^([^:]+):\s*(.+)$/);
							if (match) {
								const traitName = match[1].trim();
								const charNames = match[2]
									.split(',')
									.map((c) => c.trim())
									.filter((c) => c);

								// Find the trait by name
								const trait = personalityTraits.find((t) => t.name === traitName);
								if (trait) {
									// Match characteristic names to IDs
									for (const charName of charNames) {
										const subChar = trait.subCharacteristics.find((sc) => sc.name === charName);
										if (subChar) {
											restoredIds.push(subChar.id);
										}
									}
								}
							}
						}

						// Restore selected characteristics
						selectedSubCharacteristics = restoredIds;

						// Expand traits that have selected characteristics
						for (const trait of personalityTraits) {
							if (trait.subCharacteristics.some((sc) => restoredIds.includes(sc.id))) {
								expandedTraits.add(trait.id);
							}
						}
					} else {
						selectedSubCharacteristics = [];
						expandedTraits = new Set();
					}
				} else {
					// No "Additional characteristics:" found, treat whole thing as additional
					childCharacteristics = characteristics;
					selectedSubCharacteristics = [];
					expandedTraits = new Set();
				}
			} else {
				// If it doesn't contain our format, treat the whole thing as additional characteristics
				childCharacteristics = characteristics;
				selectedSubCharacteristics = [];
				expandedTraits = new Set();
			}
		} else {
			// No characteristics field, reset everything
			childCharacteristics = '';
			selectedSubCharacteristics = [];
			expandedTraits = new Set();
		}
	}

	function applyFormToSelectedChild() {
		ensureAtLeastOneChild();
		const sel = childProfiles[selectedChildIndex];
		if (!sel) return;
		sel.name = childName;
		sel.child_age = childAge;
		sel.child_gender = childGender;
		// Combine personality traits with characteristics
		const personalityDesc = getPersonalityDescription();
		const combinedCharacteristics = personalityDesc
			? childCharacteristics.trim()
				? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
				: personalityDesc
			: childCharacteristics;

		sel.child_characteristics = combinedCharacteristics;
		// Attach research fields to selected child for local view
		(sel as any).is_only_child = isOnlyChild === 'yes';
		(sel as any).child_has_ai_use = childHasAIUse || null;
		(sel as any).child_ai_use_contexts = childAIUseContexts || [];
		(sel as any).parent_llm_monitoring_level = parentLLMMonitoringLevel || null;

		// Attach "Other" text fields
		(sel as any).child_gender_other = childGenderOther || null;
		(sel as any).child_ai_use_contexts_other = childAIUseContextsOther || null;
		(sel as any).parent_llm_monitoring_other = parentLLMMonitoringOther || null;
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

		// Reset personality traits
		selectedSubCharacteristics = [];
		expandedTraits = new Set();
		// Reset research fields
		isOnlyChild = '';
		childHasAIUse = '';
		childAIUseContexts = [];
		parentLLMMonitoringLevel = '';
		childGenderOther = '';
		childAIUseContextsOther = '';
		parentLLMMonitoringOther = '';
		showForm = true;
		isEditing = true; // Set editing mode
		// Set selected index to -1 to indicate we're creating a new profile
		selectedChildIndex = -1;
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

			// Reset personality traits
			selectedSubCharacteristics = [];
			expandedTraits = new Set();
		}
	}

	async function selectChild(index: number) {
		selectedChildIndex = index;
		hydrateFormFromSelectedChild();
		showForm = false;
		isEditing = false;

		// Update the current child ID in the service
		const childId = childProfiles[index]?.id;
		if (childId) {
			await childProfileSync.setCurrentChildId(childId);
			console.log('Selected child profile:', childId);

			// Set this child as selected for questions (same as selectChildForQuestions)
			childSelectedForQuestions = index;

			// Unlock Step 2 (but don't show modal yet - that happens after save)
			localStorage.setItem('assignmentStep', '2');
			localStorage.setItem('moderationScenariosAccessed', 'true');
			localStorage.setItem('unlock_moderation', 'true');
			window.dispatchEvent(new Event('storage'));
			window.dispatchEvent(new Event('workflow-updated'));
			// Don't show modal here - it will be shown after save
		}
	}

	// Ensure childProfiles is always an array
	function ensureChildProfilesArray() {
		if (!childProfiles || !Array.isArray(childProfiles)) {
			console.warn('Child profiles returned invalid value, defaulting to empty array');
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
			// Enforce child quiz required fields
			if (!isOnlyChild) {
				toast.error('Please indicate if this child is an only child');
				return;
			}
			if (!childHasAIUse) {
				toast.error('Please answer whether this child has used ChatGPT or similar AI tools');
				return;
			}
			if (childHasAIUse === 'yes' && childAIUseContexts.length === 0) {
				toast.error('Please select at least one context of AI use');
				return;
			}
			if (
				childHasAIUse === 'yes' &&
				childAIUseContexts.includes('other') &&
				!childAIUseContextsOther.trim()
			) {
				toast.error('Please specify the context of AI use');
				return;
			}
			if (!parentLLMMonitoringLevel) {
				toast.error("Please indicate how you've monitored or adjusted this child's AI use");
				return;
			}
			if (parentLLMMonitoringLevel === 'other' && !parentLLMMonitoringOther.trim()) {
				toast.error("Please specify how you have monitored or adjusted your child's AI use");
				return;
			}

			// Track if we're editing an existing profile
			const isEditingExisting = childProfiles.length > 0 && selectedChildIndex >= 0;

			// If no profiles exist or we're creating a new profile, create a new one
			if (childProfiles.length === 0 || selectedChildIndex === -1) {
				// Combine personality traits with characteristics
				const personalityDesc = getPersonalityDescription();
				const combinedCharacteristics = personalityDesc
					? childCharacteristics.trim()
						? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
						: personalityDesc
					: childCharacteristics;

				// Determine session number before creating child profile
				const userId = get(user)?.id;
				const token = localStorage.getItem('token') || '';
				let sessionNumber = 1;

				if (userId && token) {
					sessionNumber = await determineSessionNumberForUser(userId, token);
				}

				const newChild = await childProfileSync.createChildProfile({
					name: childName,
					child_age: childAge,
					child_gender: childGender === 'Other' ? 'Other' : childGender,
					child_characteristics: combinedCharacteristics,
					is_only_child: isOnlyChild === 'yes',
					child_has_ai_use: childHasAIUse as any,
					child_ai_use_contexts: childAIUseContexts,
					parent_llm_monitoring_level: parentLLMMonitoringLevel as any,
					child_gender_other: childGenderOther || undefined,
					child_ai_use_contexts_other: childAIUseContextsOther || undefined,
					parent_llm_monitoring_other: parentLLMMonitoringOther || undefined,
					session_number: sessionNumber
				} as any);
				if (childProfiles.length === 0) {
					childProfiles = [newChild];
					selectedChildIndex = 0;
				} else {
					childProfiles = [...childProfiles, newChild];
					selectedChildIndex = childProfiles.length - 1;
				}

				// Set the new profile as the current selected profile
				await childProfileSync.setCurrentChildId(newChild.id);

				// Trigger async scenario assignment (don't await - runs in background)
				if (userId && token) {
					assignScenariosForChild(newChild.id, userId, sessionNumber, token, 6)
						.then((result) => {
							console.log(
								`✅ Assigned ${result.assignmentCount} scenarios for child ${newChild.id}`
							);
							if (result.assignmentCount < 6) {
								console.warn(`⚠️ Only ${result.assignmentCount}/6 scenarios assigned`);
							}
						})
						.catch((error) => {
							console.error('❌ Failed to assign scenarios:', error);
						});
				}

				// Automatically select the newly created child for questions
				childSelectedForQuestions = selectedChildIndex;

				// Unlock Step 2
				localStorage.setItem('assignmentStep', '2');
				localStorage.setItem('moderationScenariosAccessed', 'true');
				localStorage.setItem('unlock_moderation', 'true');
				window.dispatchEvent(new Event('storage'));
				window.dispatchEvent(new Event('workflow-updated'));
			} else {
				// Apply current form to selected child
				applyFormToSelectedChild();

				const selectedChild = childProfiles[selectedChildIndex];
				if (selectedChild) {
					// Combine personality traits with characteristics
					const personalityDesc = getPersonalityDescription();
					const combinedCharacteristics = personalityDesc
						? childCharacteristics.trim()
							? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
							: personalityDesc
						: childCharacteristics;

					// Clear moderation state for this child (scenarios are now stored in backend)
					localStorage.removeItem(`moderationScenarioStates_${selectedChild.id}`);
					localStorage.removeItem(`moderationScenarioTimers_${selectedChild.id}`);
					localStorage.removeItem(`moderationCurrentScenario_${selectedChild.id}`);

					// Update the child profile via API
					await childProfileSync.updateChildProfile(selectedChild.id, {
						name: childName,
						child_age: childAge,
						child_gender: childGender,
						child_characteristics: combinedCharacteristics,
						is_only_child: isOnlyChild === 'yes',
						child_has_ai_use: childHasAIUse as any,
						child_ai_use_contexts: childAIUseContexts,
						parent_llm_monitoring_level: parentLLMMonitoringLevel as any,
						child_gender_other: childGenderOther || undefined,
						child_ai_use_contexts_other: childAIUseContextsOther || undefined,
						parent_llm_monitoring_other: parentLLMMonitoringOther || undefined
					} as any);

					// Update childSelectedForQuestions to show the green checkmark on the saved profile
					childSelectedForQuestions = selectedChildIndex;

					// Keep backend in sync by setting the current child ID
					await childProfileSync.setCurrentChildId(selectedChild.id);
				}
			}

			// Dispatch event to notify sidebar of child profile changes
			window.dispatchEvent(new CustomEvent('child-profiles-updated'));

			// Show appropriate success message
			if (isEditingExisting) {
				toast.success('Profile updated! New moderation scenarios have been generated.');
			} else {
				toast.success('Child profile saved successfully!');
			}

			// Scroll to top to see the saved profile
			if (mainPageContainer) {
				mainPageContainer.scrollTo({ top: 0, behavior: 'smooth' });
			}

			// Exit edit mode after saving and mark as completed
			isEditing = false;
			showForm = false;
			isProfileCompleted = true;

			// If a child is selected for questions, show confirmation modal
			if (childSelectedForQuestions >= 0 && childSelectedForQuestions < childProfiles.length) {
				showConfirmationModal = true;
			}
		} catch (error) {
			console.error('Failed to save child profile:', error);
			toast.error('Failed to save child profile. Please try again.');
		}
	}

	async function handleProfileSaved(profile: ChildProfile) {
		// Set child as selected for questions if not already
		const profiles = await childProfileSync.getChildProfiles();
		const index = profiles.findIndex((p) => p.id === profile.id);
		if (index !== -1) {
			childSelectedForQuestions = index;
			await childProfileSync.setCurrentChildId(profile.id);

			// Unlock Step 2
			localStorage.setItem('assignmentStep', '2');
			localStorage.setItem('moderationScenariosAccessed', 'true');
			localStorage.setItem('unlock_moderation', 'true');
			window.dispatchEvent(new Event('storage'));
			window.dispatchEvent(new Event('workflow-updated'));

			// Show confirmation modal
			showConfirmationModal = true;
		}
	}

	async function handleChildSelected(profile: ChildProfile, index: number) {
		childSelectedForQuestions = index;
		await childProfileSync.setCurrentChildId(profile.id);

		// Unlock Step 2
		localStorage.setItem('assignmentStep', '2');
		localStorage.setItem('moderationScenariosAccessed', 'true');
		localStorage.setItem('unlock_moderation', 'true');
		window.dispatchEvent(new Event('storage'));
		window.dispatchEvent(new Event('workflow-updated'));

		// Show confirmation modal (as in original workflow)
		showConfirmationModal = true;
	}

	async function proceedToNextStep() {
		const userType = await getUserType($user, [], {
			mayFetchWhitelist: $user?.role === 'admin'
		});

		if (userType === 'interviewee') {
			localStorage.setItem('assignmentStep', '2');
			goto('/moderation-scenario');
		} else if (userType === 'parent') {
			goto('/parent');
		} else {
			goto('/');
		}
	}

	function continueEditing() {
		showConfirmationModal = false;
	}

	onMount(async () => {
		// Redirect if instructions not confirmed
		if (localStorage.getItem('instructionsCompleted') !== 'true') {
			goto('/assignment-instructions');
			return;
		}

		// Wait for user store to be loaded
		const waitForUser = () => {
			return new Promise<void>((resolve) => {
				const currentUser = get(user);
				if (currentUser && currentUser.id) {
					resolve();
					return;
				}
				const unsubscribe = user.subscribe((userData) => {
					if (userData && userData.id) {
						unsubscribe();
						resolve();
					}
				});
			});
		};

		await waitForUser();

		// Load profiles and set selected child for questions
		const profiles = await childProfileSync.getChildProfiles();
		const currentChildId = childProfileSync.getCurrentChildId();
		if (currentChildId && profiles.length > 0) {
			const index = profiles.findIndex((p) => p.id === currentChildId);
			if (index !== -1) {
				childSelectedForQuestions = index;
			}
		}

		// Set up scroll indicator
		const timer = setTimeout(() => {
			if (!hasScrolled) {
				showScrollIndicator = true;
			}
		}, 8000);

		const handleScroll = () => {
			hasScrolled = true;
			showScrollIndicator = false;
		};

		const scrollContainer = document.querySelector('.overflow-y-auto');
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
					<div class="flex items-center text-xl font-semibold">Child Profile</div>
				</div>
			</div>

			<!-- Navigation Buttons -->
			<div class="flex items-center space-x-2">
				<!-- Help Button -->
				<button
					on:click={() => (showHelpVideo = true)}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
					aria-label="Show help video"
				>
					Help
				</button>
				<button
					on:click={() => goto('/assignment-instructions')}
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
					<span>Previous Task</span>
				</button>
				<button
					on:click={() => {
						localStorage.setItem('assignmentStep', '2');
						goto('/moderation-scenario');
					}}
					disabled={childSelectedForQuestions === -1}
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center space-x-2 {childSelectedForQuestions !==
					-1
						? 'bg-blue-500 hover:bg-blue-600 text-white'
						: 'text-gray-400 dark:text-gray-500 cursor-not-allowed'}"
				>
					<span>Next Task</span>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"
						></path>
					</svg>
				</button>
			</div>
		</div>
	</nav>

	<!-- Child Profile Form Component -->
	<ChildProfileForm
		showResearchFields={true}
		requireResearchFields={true}
		onProfileCreated={handleProfileCreated}
		onProfileSaved={handleProfileSaved}
		onChildSelected={handleChildSelected}
	/>

	<!-- Confirmation Modal for Workflow Progression -->
	{#if showConfirmationModal}
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div
			class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
			on:click={() => (showConfirmationModal = false)}
		>
			<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
			<div
				class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl"
				on:click|stopPropagation
			>
				<div class="text-center mb-6">
					<div
						class="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4"
					>
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M5 13l4 4L19 7"
							></path>
						</svg>
					</div>
					<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Task 1 Complete</h3>
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

	<!-- Scroll Indicator -->
	{#if showScrollIndicator}
		<div
			class="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-40 flex flex-col items-center animate-bounce"
		>
			<span class="text-sm text-gray-400 dark:text-gray-500 mb-1">Scroll down</span>
			<svg
				class="w-6 h-6 text-gray-400 dark:text-gray-500"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 14l-7 7m0 0l-7-7m7 7V3"
				></path>
			</svg>
		</div>
	{/if}

	<!-- Assignment Time Tracker -->
	<AssignmentTimeTracker userId={get(user)?.id || ''} {sessionNumber} enabled={true} />

	<!-- Help Video Modal -->
	<VideoModal
		isOpen={showHelpVideo}
		videoSrc="/video/Child-Profile-Demo.mp4"
		title="Child Profile Tutorial"
	/>
</div>
