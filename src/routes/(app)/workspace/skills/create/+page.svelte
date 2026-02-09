<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { skills } from '$lib/stores';
	import { getContext } from 'svelte';

	import { createNewSkill, getSkills } from '$lib/apis/skills';
	import SkillEditor from '$lib/components/workspace/Skills/SkillEditor.svelte';

	const i18n = getContext('i18n');

	const onSubmit = async (_skill) => {
		const res = await createNewSkill(localStorage.token, _skill).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Skill created successfully'));
			await skills.set(await getSkills(localStorage.token));
			await goto('/workspace/skills');
		}
	};
</script>

<SkillEditor {onSubmit} />
