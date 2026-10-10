<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { skills } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext<any>('i18n');

	import { getSkillById, getSkills, updateSkillById } from '$lib/apis/skills';
	import { page } from '$app/stores';

	import SkillEditor from '$lib/components/workspace/Skills/SkillEditor.svelte';

	let skill: any = null;
	let disabled = false;

	$: skillId = $page.url.searchParams.get('id');

	const onSubmit = async (_skill: any) => {
		const updatedSkill = await updateSkillById(localStorage.token, skillId!, _skill);

		if (updatedSkill) {
			toast.success($i18n.t('Skill updated successfully'));
			await skills.set(await getSkills(localStorage.token));
			skill = updatedSkill;
		}
		return updatedSkill;
	};

	onMount(async () => {
		if (skillId) {
			const _skill = await getSkillById(localStorage.token, skillId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (_skill) {
				disabled = !_skill.write_access;
				skill = _skill;
			} else {
				goto('/workspace/skills');
			}
		} else {
			goto('/workspace/skills');
		}
	});
</script>

{#if skill}
	<SkillEditor {skill} {onSubmit} {disabled} edit />
{/if}
