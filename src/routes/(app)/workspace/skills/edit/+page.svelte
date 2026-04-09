<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { skills } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { getSkillById, getSkills, updateSkillById } from '$lib/apis/skills';
	import { page } from '$app/stores';

	import SkillEditor from '$lib/components/workspace/Skills/SkillEditor.svelte';

	let skill = null;
	let disabled = false;

	$: skillId = $page.url.searchParams.get('id');

	const onSubmit = async (_skill) => {
		const updatedSkill = await updateSkillById(localStorage.token, skillId, _skill).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (updatedSkill) {
			toast.success($i18n.t('Skill updated successfully'));
			await skills.set(await getSkills(localStorage.token));
			skill = {
				id: updatedSkill.id,
				name: updatedSkill.name,
				description: updatedSkill.description,
				content: updatedSkill.content,
				is_active: updatedSkill.is_active,
				access_grants: updatedSkill?.access_grants === undefined ? [] : updatedSkill?.access_grants
			};
		}
	};

	onMount(async () => {
		if (skillId) {
			const _skill = await getSkillById(localStorage.token, skillId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (_skill) {
				disabled = !_skill.write_access ?? true;
				skill = {
					id: _skill.id,
					name: _skill.name,
					description: _skill.description,
					content: _skill.content,
					is_active: _skill.is_active,
					access_grants: _skill?.access_grants === undefined ? [] : _skill?.access_grants
				};
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
