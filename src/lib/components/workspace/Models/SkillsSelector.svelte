<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext, onMount } from 'svelte';

	export let skills = [];

	let _skills = {};
	let searchQuery = '';

	export let selectedSkillIds: string[] = [];

	const i18n = getContext('i18n');

	$: filteredSkillKeys = Object.keys(_skills).filter((id) => {
		if (!searchQuery.trim()) return true;
		const q = searchQuery.toLowerCase();
		return _skills[id].name?.toLowerCase().includes(q) || _skills[id].id?.toLowerCase().includes(q);
	});

	onMount(() => {
		_skills = skills.reduce((acc, skill) => {
			acc[skill.id] = {
				...skill,
				selected: selectedSkillIds.includes(skill.id)
			};

			return acc;
		}, {});
	});
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Skills')}</div>
	</div>

	{#if Object.keys(_skills).length > 10}
		<div class="mb-2">
			<input
				class="w-full text-sm bg-transparent outline-none border border-gray-100 dark:border-gray-800 rounded-lg px-3 py-1.5 placeholder-gray-400"
				type="text"
				placeholder={$i18n.t('Search skills...')}
				bind:value={searchQuery}
			/>
		</div>
	{/if}

	<div class="flex flex-col mb-1">
		{#if skills.length > 0}
			<div class=" flex items-center flex-wrap">
				{#each filteredSkillKeys as skill, skillIdx}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={_skills[skill].selected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									_skills[skill].selected = e.detail === 'checked';
									selectedSkillIds = Object.keys(_skills).filter((s) => _skills[s].selected);
								}}
							/>
						</div>

						<Tooltip content={_skills[skill]?.description ?? _skills[skill].id}>
							<div class=" py-0.5 text-sm w-full capitalize font-medium">
								{_skills[skill].name}
							</div>
						</Tooltip>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<div class=" text-xs dark:text-gray-700">
		{$i18n.t('To select skills here, add them to the "Skills" workspace first.')}
	</div>
</div>
