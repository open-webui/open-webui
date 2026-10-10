<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	type Skill = {
		id: string;
		name?: string;
		description?: string;
		is_active?: boolean;
	};
	const i18n = getContext<any>('i18n');
	export let skills: Skill[] = [];
	export let selectedSkillIds: string[] = [];
	export let disabled = false;
</script>

<TypeaheadSelector
	id="model-skillsselector"
	label={$i18n.t('Skills')}
	items={skills.filter((skill) => skill.is_active !== false)}
	selectedIds={selectedSkillIds}
	{disabled}
	placeholder={$i18n.t('Search skills')}
	emptyLabel={$i18n.t('No skills found')}
	emptyHint={$i18n.t('Add skills in the Skills workspace.')}
	workspaceHref={$user?.role === 'admin' || $user?.permissions?.workspace?.skills
		? '/workspace/skills'
		: ''}
	variant="dropdown"
	on:select={(e) => {
		selectedSkillIds = selectedSkillIds.includes(e.detail.id)
			? selectedSkillIds.filter((id) => id !== e.detail.id)
			: [...selectedSkillIds, e.detail.id];
	}}
	on:enableall={(e) => {
		selectedSkillIds = [...new Set([...selectedSkillIds, ...e.detail.map((item) => item.id)])];
	}}
	on:clear={() => (selectedSkillIds = [])}
/>
