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

	export let selectedSkillId = null;

	// When filteredItems loads AND selectedSkillId is set (from draft restore), highlight the matching skill
	$: if (filteredItems.length > 0 && selectedSkillId !== null) {
		const idx = filteredItems.findIndex((item) => `${item.id}|${item.name}` === selectedSkillId);
		if (idx !== -1) {
			selectedIdx = idx;
		}
	}

	// Reset selectedSkillId when user actively searches (query changes AND skills already loaded).
	// Don't clear if filteredItems is still empty — that means skills haven't loaded yet
	// and selectedSkillId should be preserved for when they do (draft restore scenario).
	$: if (query && filteredItems.length > 0) {
		selectedSkillId = null;
	}

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
