<script lang="ts">
	import {
		personalityTraits,
		type PersonalityTrait,
		type SubCharacteristic
	} from '$lib/data/personalityTraits';

	// Two-way bindings for use in exit survey or child profile form
	export let selectedSubCharacteristics: string[] = [];
	export let additionalInfo: string = '';

	// When true, show required asterisk on labels (e.g. ChildProfileForm). Exit survey can use false.
	export let required: boolean = false;

	// Local UI state: which Big 5 sections are expanded
	let expandedTraits: Set<string> = new Set();

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
</script>

<div>
	<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
		Personality Traits {#if required}<span class="text-red-500">*</span>{/if}
	</label>
	<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
		Select personality traits and choose specific characteristics from one or more traits that
		describe your child.
	</p>

	<div class="space-y-3 mb-4">
		{#each personalityTraits as trait}
			<div class="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700">
				<button
					type="button"
					on:click={() => toggleTrait(trait.id)}
					class="w-full p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors rounded-lg"
				>
					<div class="text-left flex-1">
						<div class="font-medium text-gray-900 dark:text-white flex items-center space-x-2">
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
							class="w-5 h-5 text-gray-500 transition-transform {expandedTraits.has(trait.id)
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
					<div class="px-4 pb-4 space-y-2 border-t border-gray-200 dark:border-gray-600 pt-4">
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
			for="childPersonalityAdditionalInfo"
			class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
		>
			Additional Characteristics & Interests {#if required}<span class="text-red-500">*</span>{/if}
		</label>
		<textarea
			id="childPersonalityAdditionalInfo"
			bind:value={additionalInfo}
			rows="3"
			placeholder="Add any additional details about your child's personality, interests, learning style, etc."
			class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
		></textarea>
	</div>
</div>
