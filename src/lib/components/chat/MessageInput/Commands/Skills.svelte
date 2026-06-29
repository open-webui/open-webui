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

	const escapeTooltipText = (value = '') =>
		String(value)
			.replaceAll('&', '&amp;')
			.replaceAll('<', '&lt;')
			.replaceAll('>', '&gt;')
			.replaceAll('"', '&quot;')
			.replaceAll("'", '&#39;');

	const getTooltipContent = (skill) => {
		const name = escapeTooltipText(skill.name);
		const description = escapeTooltipText(skill.description);

		return `<div class="max-w-80 whitespace-normal text-left leading-snug">
			<span class="break-words font-medium">${name}</span>${description ? `: <span class="break-words opacity-80">${description}</span>` : ''}
		</div>`;
	};
</script>

<div class="px-2 text-xs text-gray-500 py-1">
	{$i18n.t('Skills')}
</div>

{#if filteredItems.length > 0}
	{#each filteredItems as skill, skillIdx}
		<Tooltip
			content={getTooltipContent(skill)}
			placement="top-start"
			tippyOptions={{ maxWidth: '20rem' }}
		>
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
				<div class="flex w-full min-w-0 items-center text-black dark:text-gray-100">
					<div class="flex items-center justify-center size-5 mr-2 shrink-0">
						<Keyframes className="size-4" />
					</div>
					<div class="truncate min-w-0 flex-1">
						{skill.name}
					</div>
					<div class="ml-2 max-w-24 shrink-0 truncate text-xs text-gray-500">
						{skill.id}
					</div>
				</div>
			</button>
		</Tooltip>
	{/each}
{/if}
