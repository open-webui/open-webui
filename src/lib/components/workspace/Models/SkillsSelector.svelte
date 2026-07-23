<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	import { getContext } from 'svelte';

	type Skill = {
		id: string;
		name?: string;
		description?: string;
		is_active?: boolean;
	};

	export let skills: Skill[] = [];
	export let selectedSkillIds: string[] = [];

	const i18n = getContext('i18n') as any;

	$: activeSkills = skills.filter((skill) => skill.is_active !== false);
	$: selectedSkills = activeSkills.filter((skill) => selectedSkillIds.includes(skill.id));

	const toggleSkill = (skill: Skill) => {
		selectedSkillIds = selectedSkillIds.includes(skill.id)
			? selectedSkillIds.filter((id) => id !== skill.id)
			: [...selectedSkillIds, skill.id];
	};
</script>

<div>
	<div class="flex w-full items-center gap-2 mb-1">
		<div class=" self-center text-xs text-gray-500">{$i18n.t('Skills')}</div>

		{#if activeSkills.length > 0}
			<TypeaheadSelector
				id="model-skills-selector"
				items={activeSkills}
				selectedIds={selectedSkillIds}
				placeholder={$i18n.t('Search skills')}
				triggerLabel={$i18n.t('Select Skill')}
				emptyLabel={$i18n.t('No skills found')}
				variant="dropdown"
				on:select={(e) => {
					toggleSkill(e.detail);
				}}
				on:enableall={(e) => {
					selectedSkillIds = [
						...new Set([...selectedSkillIds, ...e.detail.map((skill) => skill.id)])
					];
				}}
			/>
		{/if}
	</div>

	<div class="flex flex-col mb-1">
		{#if activeSkills.length > 0}
			<div class=" flex items-center flex-wrap mt-1">
				{#each selectedSkills as skill, skillIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state="checked"
								on:change={(e) => {
									if (e.detail === 'unchecked') {
										selectedSkillIds = selectedSkillIds.filter((id) => id !== skill.id);
									}
								}}
							/>
						</div>

						<Tooltip content={skill.description ?? skill.id}>
							<div class=" py-0.5 text-xs capitalize">
								{skill.name}
							</div>
						</Tooltip>
					</div>
				{/each}

				{#if selectedSkills.length > 0}
					<button
						type="button"
						class="py-0.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
						on:click={() => {
							selectedSkillIds = [];
						}}
					>
						{$i18n.t('Disable all')}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<div class=" text-xs dark:text-gray-700">
		{$i18n.t('To select skills here, add them to the "Skills" workspace first.')}
	</div>
</div>
