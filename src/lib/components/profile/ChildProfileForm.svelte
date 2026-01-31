<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { get } from 'svelte/store';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';
	import { getChildProfiles } from '$lib/apis/child-profiles';
	import { toast } from 'svelte-sonner';
	import {
		personalityTraits,
		type PersonalityTrait,
		type SubCharacteristic
	} from '$lib/data/personalityTraits';

	const i18n = getContext('i18n');

	// Props
	export let showResearchFields: boolean = false;
	export let requireResearchFields: boolean = false;
	export let allowEmptyProfiles: boolean = true;
	export let initialSelectedIndex: number = -1;

	// Callbacks
	export let onProfileSaved: ((profile: ChildProfile) => void | Promise<void>) | undefined =
		undefined;
	export let onProfileCreated: ((profile: ChildProfile) => void | Promise<void>) | undefined =
		undefined;
	export let onProfileUpdated: ((profile: ChildProfile) => void | Promise<void>) | undefined =
		undefined;
	export let onProfileDeleted: ((profileId: string) => void | Promise<void>) | undefined =
		undefined;
	export let onChildSelected:
		| ((profile: ChildProfile, index: number) => void | Promise<void>)
		| undefined = undefined;

	// Child profile data
	let childName: string = '';
	let childAge: string = '';
	let childGender: string = '';
	let childCharacteristics: string = '';

	// Child quiz research fields (conditional)
	let isOnlyChild: string = '';
	let childHasAIUse: string = '';
	let childAIUseContexts: string[] = [];
	let parentLLMMonitoringLevel: string = '';

	// "Other" text fields for additional information
	let childGenderOther: string = '';
	let childAIUseContextsOther: string = '';
	let parentLLMMonitoringOther: string = '';

	// Personality traits system
	let expandedTraits: Set<string> = new Set();
	let selectedSubCharacteristics: string[] = [];

	// Multi-child support
	let childProfiles: ChildProfile[] = [];
	let selectedChildIndex: number = initialSelectedIndex;
	let showForm: boolean = false;
	let isEditing: boolean = false;
	let isProfileCompleted: boolean = false;

	// Main page container for scrolling
	let mainPageContainer: HTMLElement;

	function getChildGridTemplate(): string {
		const cols = Math.max(1, Math.min((childProfiles?.length || 0) + 1, 5));
		return `repeat(${cols}, minmax(120px, 1fr))`;
	}

	// Personality trait helper functions
	function toggleTrait(traitId: string) {
		if (expandedTraits.has(traitId)) {
			expandedTraits.delete(traitId);
		} else {
			expandedTraits.add(traitId);
		}
		expandedTraits = expandedTraits;
	}

	function getSelectedSubCharacteristics(): SubCharacteristic[] {
		const selected: SubCharacteristic[] = [];
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

		const traitGroups = new Map<string, string[]>();
		for (const subChar of subChars) {
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

		childName = sel?.name || '';
		childAge = sel?.child_age || '';

		const genderValue = sel?.child_gender || '';
		if (genderValue.startsWith('Other: ')) {
			childGender = 'Other';
			childGenderOther = genderValue.substring('Other: '.length);
		} else if (genderValue === 'Other') {
			childGender = 'Other';
			childGenderOther = (sel as any)?.child_gender_other || '';
		} else {
			childGender = genderValue;
			childGenderOther = (sel as any)?.child_gender_other || '';
		}

		// Research fields (only if showResearchFields is true)
		if (showResearchFields) {
			if (typeof (sel as any)?.is_only_child === 'boolean') {
				isOnlyChild = (sel as any).is_only_child ? 'yes' : 'no';
			} else {
				isOnlyChild = '';
			}
			childHasAIUse = (sel as any)?.child_has_ai_use || '';
			const contexts = (sel as any)?.child_ai_use_contexts;
			if (Array.isArray(contexts)) {
				childAIUseContexts = contexts;
			} else {
				childAIUseContexts = [];
			}
			const monitoringValue = (sel as any)?.parent_llm_monitoring_level;
			parentLLMMonitoringLevel = monitoringValue || '';
			childAIUseContextsOther = (sel as any)?.child_ai_use_contexts_other || '';
			parentLLMMonitoringOther = (sel as any)?.parent_llm_monitoring_other || '';
		}

		// Parse personality traits from stored characteristics
		if (sel?.child_characteristics) {
			const characteristics = sel.child_characteristics;
			if (characteristics.includes('Additional characteristics:')) {
				const additionalStart = characteristics.indexOf('Additional characteristics:');
				if (additionalStart !== -1) {
					childCharacteristics = characteristics
						.substring(additionalStart + 'Additional characteristics:'.length)
						.trim();
					const personalityPart = characteristics.substring(0, additionalStart).trim();
					if (personalityPart) {
						const traitLines = personalityPart.split('\n');
						const restoredIds: string[] = [];
						for (const line of traitLines) {
							const match = line.match(/^([^:]+):\s*(.+)$/);
							if (match) {
								const traitName = match[1].trim();
								const charNames = match[2]
									.split(',')
									.map((c) => c.trim())
									.filter((c) => c);
								const trait = personalityTraits.find((t) => t.name === traitName);
								if (trait) {
									for (const charName of charNames) {
										const subChar = trait.subCharacteristics.find((sc) => sc.name === charName);
										if (subChar) {
											restoredIds.push(subChar.id);
										}
									}
								}
							}
						}
						selectedSubCharacteristics = restoredIds;
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
					childCharacteristics = characteristics;
					selectedSubCharacteristics = [];
					expandedTraits = new Set();
				}
			} else {
				childCharacteristics = characteristics;
				selectedSubCharacteristics = [];
				expandedTraits = new Set();
			}
		} else {
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
		const personalityDesc = getPersonalityDescription();
		const combinedCharacteristics = personalityDesc
			? childCharacteristics.trim()
				? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
				: personalityDesc
			: childCharacteristics;
		sel.child_characteristics = combinedCharacteristics;

		if (showResearchFields) {
			(sel as any).is_only_child = isOnlyChild === 'yes';
			(sel as any).child_has_ai_use = childHasAIUse || null;
			(sel as any).child_ai_use_contexts = childAIUseContexts || [];
			(sel as any).parent_llm_monitoring_level = parentLLMMonitoringLevel || null;
			(sel as any).child_gender_other = childGenderOther || null;
			(sel as any).child_ai_use_contexts_other = childAIUseContextsOther || null;
			(sel as any).parent_llm_monitoring_other = parentLLMMonitoringOther || null;
		}
	}

	async function deleteChild(index: number) {
		const childToDelete = childProfiles[index];
		if (!childToDelete) return;

		try {
			await childProfileSync.deleteChildProfile(childToDelete.id);
			childProfiles = childProfiles.filter((_, i) => i !== index);

			if (childProfiles.length === 0) {
				selectedChildIndex = -1;
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

			window.dispatchEvent(new CustomEvent('child-profiles-updated'));

			if (onProfileDeleted) {
				await onProfileDeleted(childToDelete.id);
			}

			toast.success('Child profile deleted successfully!');
		} catch (error) {
			console.error('Failed to delete child profile:', error);
			toast.error('Failed to delete child profile');
		}
	}

	function addNewProfile() {
		if (selectedChildIndex === -1 && showForm && isEditing) {
			return;
		}

		childName = '';
		childAge = '';
		childGender = '';
		childCharacteristics = '';
		selectedSubCharacteristics = [];
		expandedTraits = new Set();

		if (showResearchFields) {
			isOnlyChild = '';
			childHasAIUse = '';
			childAIUseContexts = [];
			parentLLMMonitoringLevel = '';
			childGenderOther = '';
			childAIUseContextsOther = '';
			parentLLMMonitoringOther = '';
		}

		showForm = true;
		isEditing = true;
		selectedChildIndex = -1;
	}

	function validateForm(): string | null {
		if (!childName.trim()) {
			return 'Please enter a name for the child';
		}
		if (!childAge) {
			return 'Please select an age';
		}
		if (!childGender) {
			return 'Please select a gender';
		}
		if (!childCharacteristics.trim()) {
			return 'Please enter additional characteristics & interests';
		}

		if (showResearchFields && requireResearchFields) {
			if (!isOnlyChild) {
				return 'Please indicate if this child is an only child';
			}
			if (!childHasAIUse) {
				return 'Please answer whether this child has used ChatGPT or similar AI tools';
			}
			if (childHasAIUse === 'yes' && childAIUseContexts.length === 0) {
				return 'Please select at least one context of AI use';
			}
			if (
				childHasAIUse === 'yes' &&
				childAIUseContexts.includes('other') &&
				!childAIUseContextsOther.trim()
			) {
				return 'Please specify the context of AI use';
			}
			if (!parentLLMMonitoringLevel) {
				return "Please indicate how you've monitored or adjusted this child's AI use";
			}
			if (parentLLMMonitoringLevel === 'other' && !parentLLMMonitoringOther.trim()) {
				return "Please specify how you have monitored or adjusted your child's AI use";
			}
		}

		return null;
	}

	async function saveNewProfile() {
		const validationError = validateForm();
		if (validationError) {
			toast.error(validationError);
			return;
		}

		try {
			const personalityDesc = getPersonalityDescription();
			const combinedCharacteristics = personalityDesc
				? childCharacteristics.trim()
					? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
					: personalityDesc
				: childCharacteristics;

			const profileData: any = {
				name: childName,
				child_age: childAge,
				child_gender: childGender === 'Other' ? 'Other' : childGender,
				child_characteristics: combinedCharacteristics
			};

			if (showResearchFields) {
				profileData.is_only_child = isOnlyChild === 'yes';
				profileData.child_has_ai_use = childHasAIUse;
				profileData.child_ai_use_contexts = childAIUseContexts;
				profileData.parent_llm_monitoring_level = parentLLMMonitoringLevel;
				if (childGenderOther) profileData.child_gender_other = childGenderOther;
				if (childAIUseContextsOther)
					profileData.child_ai_use_contexts_other = childAIUseContextsOther;
				if (parentLLMMonitoringOther)
					profileData.parent_llm_monitoring_other = parentLLMMonitoringOther;
			}

			const newChild = await childProfileSync.createChildProfile(profileData);
			childProfiles = [...childProfiles, newChild];
			selectedChildIndex = childProfiles.length - 1;
			showForm = true;

			await childProfileSync.setCurrentChildId(newChild.id);
			window.dispatchEvent(new CustomEvent('child-profiles-updated'));

			if (onProfileCreated) {
				await onProfileCreated(newChild);
			}

			toast.success('Child profile created successfully!');
		} catch (error) {
			console.error('Failed to create child profile:', error);
			let errorMessage = 'Failed to create child profile';
			if (error instanceof Error) {
				errorMessage = error.message;
			} else if (error && typeof error === 'object' && 'detail' in error) {
				const detail = (error as any).detail;
				errorMessage = typeof detail === 'string' ? detail : errorMessage;
			}
			toast.error(errorMessage);
		}
	}

	function cancelAddProfile() {
		if (childProfiles.length > 0) {
			showForm = false;
			isEditing = false;
			hydrateFormFromSelectedChild();
		} else {
			showForm = false;
			isEditing = false;
			childName = '';
			childAge = '';
			childGender = '';
			childCharacteristics = '';
			selectedSubCharacteristics = [];
			expandedTraits = new Set();
		}
	}

	async function selectChild(index: number) {
		selectedChildIndex = index;
		hydrateFormFromSelectedChild();
		showForm = false;
		isEditing = false;

		const childId = childProfiles[index]?.id;
		if (childId) {
			await childProfileSync.setCurrentChildId(childId);
			if (onChildSelected && childProfiles[index]) {
				await onChildSelected(childProfiles[index], index);
			}
		}
	}

	async function loadChildProfile() {
		try {
			childProfiles = await childProfileSync.getChildProfiles();
			if (!childProfiles || !Array.isArray(childProfiles)) {
				childProfiles = [];
			}

			if (childProfiles.length > 0) {
				const currentChildId = childProfileSync.getCurrentChildId();
				if (currentChildId) {
					const index = childProfiles.findIndex((c) => c.id === currentChildId);
					if (index !== -1) {
						selectedChildIndex = index;
					} else {
						selectedChildIndex = 0;
					}
				} else {
					selectedChildIndex = 0;
				}
				hydrateFormFromSelectedChild();
				showForm = false;
				isProfileCompleted = true;
			} else {
				selectedChildIndex = -1;
				showForm = false;
				isProfileCompleted = false;
			}
		} catch (error) {
			console.error('Failed to load child profiles:', error);
			childProfiles = [];
		}
	}

	async function saveChildProfile() {
		const validationError = validateForm();
		if (validationError) {
			toast.error(validationError);
			return;
		}

		try {
			const isEditingExisting = childProfiles.length > 0 && selectedChildIndex >= 0;

			if (childProfiles.length === 0 || selectedChildIndex === -1) {
				const personalityDesc = getPersonalityDescription();
				const combinedCharacteristics = personalityDesc
					? childCharacteristics.trim()
						? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
						: personalityDesc
					: childCharacteristics;

				const profileData: any = {
					name: childName,
					child_age: childAge,
					child_gender: childGender === 'Other' ? 'Other' : childGender,
					child_characteristics: combinedCharacteristics
				};

				if (showResearchFields) {
					profileData.is_only_child = isOnlyChild === 'yes';
					profileData.child_has_ai_use = childHasAIUse;
					profileData.child_ai_use_contexts = childAIUseContexts;
					profileData.parent_llm_monitoring_level = parentLLMMonitoringLevel;
					if (childGenderOther) profileData.child_gender_other = childGenderOther;
					if (childAIUseContextsOther)
						profileData.child_ai_use_contexts_other = childAIUseContextsOther;
					if (parentLLMMonitoringOther)
						profileData.parent_llm_monitoring_other = parentLLMMonitoringOther;
				}

				const newChild = await childProfileSync.createChildProfile(profileData);
				if (childProfiles.length === 0) {
					childProfiles = [newChild];
					selectedChildIndex = 0;
				} else {
					childProfiles = [...childProfiles, newChild];
					selectedChildIndex = childProfiles.length - 1;
				}

				await childProfileSync.setCurrentChildId(newChild.id);
				window.dispatchEvent(new CustomEvent('child-profiles-updated'));

				if (onProfileCreated) {
					await onProfileCreated(newChild);
				}
			} else {
				applyFormToSelectedChild();
				const selectedChild = childProfiles[selectedChildIndex];
				if (selectedChild) {
					const personalityDesc = getPersonalityDescription();
					const combinedCharacteristics = personalityDesc
						? childCharacteristics.trim()
							? `${personalityDesc}\n\nAdditional characteristics:\n${childCharacteristics}`
							: personalityDesc
						: childCharacteristics;

					const updateData: any = {
						name: childName,
						child_age: childAge,
						child_gender: childGender,
						child_characteristics: combinedCharacteristics
					};

					if (showResearchFields) {
						updateData.is_only_child = isOnlyChild === 'yes';
						updateData.child_has_ai_use = childHasAIUse;
						updateData.child_ai_use_contexts = childAIUseContexts;
						updateData.parent_llm_monitoring_level = parentLLMMonitoringLevel;
						if (childGenderOther) updateData.child_gender_other = childGenderOther;
						if (childAIUseContextsOther)
							updateData.child_ai_use_contexts_other = childAIUseContextsOther;
						if (parentLLMMonitoringOther)
							updateData.parent_llm_monitoring_other = parentLLMMonitoringOther;
					}

					const updatedChild = await childProfileSync.updateChildProfile(
						selectedChild.id,
						updateData
					);
					childProfiles[selectedChildIndex] = updatedChild;
					await childProfileSync.setCurrentChildId(selectedChild.id);

					if (onProfileUpdated) {
						await onProfileUpdated(updatedChild);
					}
				}
			}

			window.dispatchEvent(new CustomEvent('child-profiles-updated'));

			if (onProfileSaved) {
				const profile = childProfiles[selectedChildIndex];
				if (profile) {
					await onProfileSaved(profile);
				}
			}

			if (isEditingExisting) {
				toast.success('Profile updated!');
			} else {
				toast.success('Child profile saved successfully!');
			}

			if (mainPageContainer) {
				mainPageContainer.scrollTo({ top: 0, behavior: 'smooth' });
			}

			isEditing = false;
			showForm = false;
			isProfileCompleted = true;
		} catch (error) {
			console.error('Failed to save child profile:', error);
			let errorMessage = 'Failed to save child profile';
			if (error instanceof Error) {
				errorMessage = error.message;
			} else if (error && typeof error === 'object' && 'detail' in error) {
				const detail = (error as any).detail;
				errorMessage = typeof detail === 'string' ? detail : errorMessage;
			}
			toast.error(errorMessage);
		}
	}

	function startEditing() {
		if (selectedChildIndex >= 0 && selectedChildIndex < childProfiles.length) {
			hydrateFormFromSelectedChild();
			isEditing = true;
			showForm = true;
		} else {
			console.warn('Cannot start editing: no valid child selected');
		}
	}

	function joinContextsForDisplay(): string {
		const contexts: string[] =
			childProfiles &&
			selectedChildIndex >= 0 &&
			childProfiles[selectedChildIndex]?.child_ai_use_contexts
				? (childProfiles[selectedChildIndex].child_ai_use_contexts as unknown as string[])
				: [];
		return contexts.length > 0 ? contexts.join(', ') : 'Not specified';
	}

	onMount(async () => {
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
		await loadChildProfile();
	});
</script>

<div
	class="flex-1 max-h-full overflow-y-auto bg-gray-50 dark:bg-gray-900"
	bind:this={mainPageContainer}
>
	<div class="max-w-4xl mx-auto px-4 py-8">
		<!-- Child Selection -->
		{#if childProfiles && childProfiles.length > 0}
			<div class="mb-8">
				<div
					class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6"
				>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
						Select Your Profile
					</h2>
					<div class="grid gap-3" style={`grid-template-columns: ${getChildGridTemplate()}`}>
						{#each childProfiles as c, i}
							<div class="relative group flex flex-col">
								<button
									type="button"
									class={`w-full px-6 py-4 rounded-full transition-all duration-200 ${i === selectedChildIndex ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg ring-2 ring-blue-400/50 transform scale-105' : 'bg-gradient-to-r from-gray-700 to-gray-600 text-white ring-1 ring-gray-500/30 hover:from-gray-600 hover:to-gray-500 hover:ring-gray-400/50 hover:scale-102'}`}
									on:click={() => selectChild(i)}
								>
									<span class="font-medium">{c.name || `Kid ${i + 1}`}</span>
								</button>

								<button
									type="button"
									class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center z-20"
									on:click|stopPropagation={() => deleteChild(i)}
									title="Delete child"
								>
									×
								</button>
							</div>
						{/each}
						<button
							type="button"
							class="px-6 py-4 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 shadow-lg ring-1 ring-gray-300/30 dark:ring-gray-600/30 hover:bg-gray-300 dark:hover:bg-gray-600 hover:ring-gray-400/50 dark:hover:ring-gray-500/50 hover:scale-105 transition-all duration-200"
							on:click={addNewProfile}
						>
							<span class="font-medium">+ Add Profile</span>
						</button>
					</div>
				</div>
			</div>
		{:else}
			<!-- Empty State -->
			<div class="mb-8">
				<div
					class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8 text-center"
				>
					<div
						class="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4"
					>
						<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							></path>
						</svg>
					</div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
						No Child Profiles Yet
					</h2>
					<p class="text-gray-600 dark:text-gray-300 mb-6">
						Create your first child profile to get started.
					</p>
					<button
						type="button"
						class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
						on:click={addNewProfile}
					>
						+ Add Your First Child Profile
					</button>
				</div>
			</div>
		{/if}

		<!-- Profile Display (Read-only when not editing) -->
		{#if childProfiles.length > 0 && selectedChildIndex >= 0 && !showForm}
			<div
				class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8"
			>
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
						<p class="text-gray-900 dark:text-white">
							{childProfiles[selectedChildIndex]?.name || 'Not specified'}
						</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Age</div>
						<p class="text-gray-900 dark:text-white">
							{childProfiles[selectedChildIndex]?.child_age || 'Not specified'}
						</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
							Gender
						</div>
						<p class="text-gray-900 dark:text-white">
							{childProfiles[selectedChildIndex]?.child_gender || 'Not specified'}
						</p>
					</div>
					<div>
						<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
							Characteristics & Interests
						</div>
						<p class="text-gray-900 dark:text-white whitespace-pre-wrap">
							{childProfiles[selectedChildIndex]?.child_characteristics || 'Not specified'}
						</p>
					</div>
					{#if showResearchFields}
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Only Child
							</div>
							<p class="text-gray-900 dark:text-white">
								{childProfiles[selectedChildIndex]?.is_only_child === true
									? 'Yes'
									: childProfiles[selectedChildIndex]?.is_only_child === false
										? 'No'
										: 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Child Has Used AI Tools
							</div>
							<p class="text-gray-900 dark:text-white">
								{childProfiles[selectedChildIndex]?.child_has_ai_use || 'Not specified'}
							</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Contexts of AI Use
							</div>
							<p class="text-gray-900 dark:text-white">{joinContextsForDisplay()}</p>
						</div>
						<div>
							<div class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
								Parent LLM Monitoring Level
							</div>
							<p class="text-gray-900 dark:text-white">
								{childProfiles[selectedChildIndex]?.parent_llm_monitoring_level || 'Not specified'}
							</p>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Profile Form -->
		{#if showForm && isEditing}
			<div
				class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8"
			>
				<form on:submit|preventDefault={saveChildProfile} class="space-y-6">
					<div class="space-y-6">
						<h3 class="text-xl font-semibold text-gray-900 dark:text-white">Child Information</h3>

						<div>
							<label
								for="childName"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
							>
								Name <span class="text-red-500">*</span>
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
							<label
								for="childAge"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
							>
								Age <span class="text-red-500">*</span>
							</label>
							<select
								id="childAge"
								bind:value={childAge}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							>
								<option value="">Select age</option>
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
							<label
								for="childGender"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
							>
								Gender <span class="text-red-500">*</span>
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
								<option value="Other">Other</option>
								<option value="Prefer not to say">Prefer not to say</option>
							</select>
							{#if childGender === 'Other'}
								<input
									type="text"
									bind:value={childGenderOther}
									placeholder="Please specify the gender"
									class="w-full mt-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
									required
								/>
							{/if}
						</div>

						<!-- Personality Traits Selection -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Personality Traits <span class="text-red-500">*</span>
							</label>
							<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
								Select personality traits and choose specific characteristics from one or more
								traits that describe your child.
							</p>

							<div class="space-y-3 mb-4">
								{#each personalityTraits as trait}
									<div
										class="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700"
									>
										<button
											type="button"
											on:click={() => toggleTrait(trait.id)}
											class="w-full p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors rounded-lg"
										>
											<div class="text-left flex-1">
												<div
													class="font-medium text-gray-900 dark:text-white flex items-center space-x-2"
												>
													<span>{trait.name}</span>
													{#if trait.subCharacteristics.some( (sub) => selectedSubCharacteristics.includes(sub.id) )}
														<span
															class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
														>
															{trait.subCharacteristics.filter((sub) =>
																selectedSubCharacteristics.includes(sub.id)
															).length} selected
														</span>
													{/if}
												</div>
												<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
													{trait.description}
												</div>
											</div>
											<div class="ml-2 flex-shrink-0">
												<svg
													class="w-5 h-5 text-gray-500 transition-transform {expandedTraits.has(
														trait.id
													)
														? 'transform rotate-180'
														: ''}"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M19 9l-7 7-7-7"
													></path>
												</svg>
											</div>
										</button>

										{#if expandedTraits.has(trait.id)}
											<div
												class="px-4 pb-4 space-y-2 border-t border-gray-200 dark:border-gray-600 pt-4"
											>
												<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
													Select characteristics that apply:
												</p>
												{#each trait.subCharacteristics as subChar}
													<label
														class="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer transition-colors"
													>
														<input
															type="checkbox"
															bind:group={selectedSubCharacteristics}
															value={subChar.id}
															class="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
														/>
														<div class="flex-1">
															<div class="font-medium text-gray-900 dark:text-white">
																{subChar.name}
															</div>
															<div class="text-sm text-gray-600 dark:text-gray-400">
																{subChar.description}
															</div>
														</div>
													</label>
												{/each}
											</div>
										{/if}
									</div>
								{/each}
							</div>

							{#if selectedSubCharacteristics.length > 0}
								<div
									class="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg mb-4"
								>
									<div class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
										Selected: {selectedSubCharacteristics.length} characteristic{selectedSubCharacteristics.length !==
										1
											? 's'
											: ''}
									</div>
									<div class="text-xs text-blue-700 dark:text-blue-300">
										{getSelectedSubCharacteristicNames().join(', ')}
									</div>
								</div>
							{/if}

							<div>
								<label
									for="childCharacteristics"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								>
									Additional Characteristics & Interests <span class="text-red-500">*</span>
								</label>
								<textarea
									id="childCharacteristics"
									bind:value={childCharacteristics}
									rows="3"
									placeholder="Add any additional details about your child's personality, interests, learning style, etc."
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
								></textarea>
							</div>
						</div>

						<!-- Research Fields (Conditional) -->
						{#if showResearchFields}
							<div class="pt-2">
								<div class="mb-4">
									<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Is this child an only child? <span class="text-red-500">*</span>
									</div>
									<div class="space-y-2">
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={isOnlyChild}
												value="yes"
												class="mr-3"
											/>Yes</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={isOnlyChild}
												value="no"
												class="mr-3"
											/>No</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={isOnlyChild}
												value="prefer_not_to_say"
												class="mr-3"
											/>Prefer not to say</label
										>
									</div>
								</div>

								<div class="mb-4">
									<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Has this child used ChatGPT or similar AI tools? <span class="text-red-500"
											>*</span
										>
									</div>
									<div class="space-y-2">
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={childHasAIUse}
												value="yes"
												class="mr-3"
											/>Yes</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={childHasAIUse}
												value="no"
												class="mr-3"
											/>No</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={childHasAIUse}
												value="unsure"
												class="mr-3"
											/>Not sure</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={childHasAIUse}
												value="prefer_not_to_say"
												class="mr-3"
											/>Prefer not to say</label
										>
									</div>
								</div>

								{#if childHasAIUse === 'yes'}
									<div class="mb-4">
										<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											In what contexts has this child used these tools? <span class="text-red-500"
												>*</span
											>
										</div>
										<div class="space-y-2">
											<label class="flex items-center"
												><input
													type="checkbox"
													bind:group={childAIUseContexts}
													value="school_homework"
													class="mr-3"
												/>For school or homework</label
											>
											<label class="flex items-center"
												><input
													type="checkbox"
													bind:group={childAIUseContexts}
													value="general_knowledge"
													class="mr-3"
												/>For general knowledge or casual questions</label
											>
											<label class="flex items-center"
												><input
													type="checkbox"
													bind:group={childAIUseContexts}
													value="games_chatting"
													class="mr-3"
												/>For playing games or chatting with the AI</label
											>
											<label class="flex items-center"
												><input
													type="checkbox"
													bind:group={childAIUseContexts}
													value="personal_advice"
													class="mr-3"
												/>For advice on personal or social issues</label
											>
											<label class="flex items-center"
												><input
													type="checkbox"
													bind:group={childAIUseContexts}
													value="other"
													class="mr-3"
												/>Other</label
											>
										</div>
										{#if childAIUseContexts.includes('other')}
											<input
												type="text"
												bind:value={childAIUseContextsOther}
												placeholder="Please specify the context"
												class="w-full mt-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
												required
											/>
										{/if}
									</div>
								{/if}

								<div class="mb-2">
									<div class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										Have you monitored or adjusted your child's use of Large Language Models like
										ChatGPT? <span class="text-red-500">*</span>
									</div>
									<div class="space-y-2">
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={parentLLMMonitoringLevel}
												value="active_rules"
												class="mr-3"
											/>Yes — I actively monitor and set rules/limits</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={parentLLMMonitoringLevel}
												value="occasional_guidance"
												class="mr-3"
											/>Yes — occasional reminders or guidance</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={parentLLMMonitoringLevel}
												value="plan_to"
												class="mr-3"
											/>Not yet, but I plan to</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={parentLLMMonitoringLevel}
												value="no_monitoring"
												class="mr-3"
											/>No — I have not monitored or adjusted</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={parentLLMMonitoringLevel}
												value="other"
												class="mr-3"
											/>Other</label
										>
										<label class="flex items-center"
											><input
												type="radio"
												bind:group={parentLLMMonitoringLevel}
												value="prefer_not_to_say"
												class="mr-3"
											/>Prefer not to say</label
										>
									</div>
									{#if parentLLMMonitoringLevel === 'other'}
										<input
											type="text"
											bind:value={parentLLMMonitoringOther}
											placeholder="Please specify how you have monitored or adjusted your child's AI use"
											class="w-full mt-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
											required
										/>
									{/if}
								</div>
							</div>
						{/if}
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
	</div>
</div>
