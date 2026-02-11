<script lang="ts">
	import Fuse from 'fuse.js';

	import { getContext } from 'svelte';
	import { skills } from '$lib/stores';
	import { getSkillList } from '$lib/apis/skills';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Keyframes from '$lib/components/icons/Keyframes.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	export let filteredItems = [];

	let _skills = [];

	const loadSkills = async () => {
		if ($skills) {
			_skills = $skills;
		} else {
			_skills = await getSkillList(localStorage.token);
			skills.set(_skills);
		}
	};

	loadSkills();

	$: fuse = new Fuse(
		(_skills ?? []).filter((s) => s.enabled !== false),
		{
			keys: ['name', 'id', 'meta.description'],
			threshold: 0.5
		}
	);

	$: filteredItems = query
		? fuse.search(query).map((e) => e.item)
		: (_skills ?? []).filter((s) => s.enabled !== false);

	$: if (query) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		const skill = filteredItems[selectedIdx];
		if (skill) {
			onSelect({ type: 'skill', data: skill });
		}
	};
</script>

<div class="px-2 text-xs text-gray-500 py-1">
	{$i18n.t('Skills')}
</div>

{#if filteredItems.length > 0}
	{#each filteredItems as skill, skillIdx}
		<Tooltip content={skill.id} placement="top-start">
			<button
				class="px-2.5 py-1.5 rounded-xl w-full text-left {skillIdx === selectedIdx
					? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					onSelect({ type: 'skill', data: skill });
				}}
				on:mousemove={() => {
					selectedIdx = skillIdx;
				}}
				on:focus={() => {}}
				data-selected={skillIdx === selectedIdx}
			>
				<div class="flex text-black dark:text-gray-100 line-clamp-1">
					<div class="flex items-center justify-center size-5 mr-2 shrink-0">
						<Keyframes className="size-4" />
					</div>
					<div class="truncate">
						{skill.name}
					</div>
					{#if skill.meta?.description}
						<div class="ml-2 text-xs text-gray-500 truncate">
							{skill.meta.description}
						</div>
					{/if}
				</div>
			</button>
		</Tooltip>
	{/each}
{/if}
