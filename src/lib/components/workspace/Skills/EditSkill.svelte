<script lang="ts">
	import { getPageContext } from '$lib/utils/page';
	const { goto, url: pageUrl } = getPageContext();

	import { toast } from 'svelte-sonner';

	import { skills } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext<any>('i18n');

	import { getSkillById, getSkills, updateSkillById } from '$lib/apis/skills';

	import SkillEditor from '$lib/components/workspace/Skills/SkillEditor.svelte';

	let skill: any = null;
	let disabled = false;

	$: skillId = $pageUrl.searchParams.get('id');

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
	import PageTitle from '$lib/components/common/PageTitle.svelte';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<PageTitle title={(skill?.name || $i18n.t('Edit Skill')) + ' / ' + $WEBUI_NAME} />

{#if skill}
	<SkillEditor {skill} {onSubmit} {disabled} edit />
{/if}
