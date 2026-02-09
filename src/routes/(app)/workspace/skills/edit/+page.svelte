<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount, getContext } from 'svelte';

	import { skills } from '$lib/stores';
	import { getSkillById, getSkills, updateSkillById } from '$lib/apis/skills';
	import SkillEditor from '$lib/components/workspace/Skills/SkillEditor.svelte';

	const i18n = getContext('i18n');

	let skill = null;
	let disabled = false;

	const onSubmit = async (_skill) => {
		const res = await updateSkillById(localStorage.token, _skill.id, _skill).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Skill updated successfully'));
			await skills.set(await getSkills(localStorage.token));
			await goto('/workspace/skills');
		}
	};

	onMount(async () => {
		const id = $page.url.searchParams.get('id');
		if (!id) {
			goto('/workspace/skills');
			return;
		}

		const _skill = await getSkillById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!_skill) {
			goto('/workspace/skills');
			return;
		}

		disabled = !(_skill.write_access ?? false);
		skill = {
			id: _skill.id,
			name: _skill.name,
			content: _skill.content,
			meta: _skill.meta ?? {},
			activation: _skill.activation ?? { mode: 'manual' },
			effects: _skill.effects ?? {},
			is_active: _skill.is_active ?? true,
			priority: _skill.priority ?? 0,
			access_control: _skill.access_control === undefined ? {} : _skill.access_control
		};
	});
</script>

{#if skill}
	<SkillEditor {skill} {onSubmit} {disabled} edit />
{/if}
