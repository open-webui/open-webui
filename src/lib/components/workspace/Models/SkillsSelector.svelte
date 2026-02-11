<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext, onMount } from 'svelte';

	import { getSkillItems } from '$lib/apis/skills';

	export let selectedSkillIds: string[] = [];

	let _skills: Record<string, any> = {};

	const i18n = getContext('i18n');

	onMount(async () => {
		const res = await getSkillItems(localStorage.token).catch(() => null);
		const skills = res?.items ?? [];
		_skills = skills.reduce((acc: Record<string, any>, skill: any) => {
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

	<div class="flex flex-col mb-1">
		{#if Object.keys(_skills).length > 0}
			<div class=" flex items-center flex-wrap">
				{#each Object.keys(_skills) as skill, skillIdx}
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
