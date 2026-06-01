<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { getSkillItems } from '$lib/apis/skills';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Keyframes from '$lib/components/icons/Keyframes.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	export let filteredItems = [];

	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			getItems();
		}, 200);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	const getItems = async () => {
		const res = await getSkillItems(localStorage.token, query).catch(() => null);
		if (res) {
			filteredItems = res.items;
		}
	};

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
		<Tooltip content={skill.description || skill.name} placement="top-start">
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
				<div class="flex text-black dark:text-gray-100 line-clamp-1 items-center">
					<div class="flex items-center justify-center size-5 mr-2 shrink-0">
						<Keyframes className="size-4" />
					</div>
					<div class="truncate">
						{skill.name}
					</div>
					<div class="ml-2 text-xs text-gray-500 truncate">
						{skill.id}
					</div>
				</div>
			</button>
		</Tooltip>
	{/each}
{/if}
