<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { getPrompts } from '$lib/apis/prompts';
	import { getSkillItems } from '$lib/apis/skills';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	export let filteredItems = [];

	let prompts = [];
	let skills = [];
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	$: filteredPrompts = prompts
		.filter((p) => p.command.toLowerCase().includes(query.toLowerCase()))
		.sort((a, b) => a.name.localeCompare(b.name));

	$: filteredItems = [
		...filteredPrompts.map((data) => ({ type: 'prompt', data })),
		...skills.map((data) => ({ type: 'skill', data }))
	];

	$: if (query) {
		selectedIdx = 0;
	}

	$: selectedIdx = Math.min(selectedIdx, Math.max(filteredItems.length - 1, 0));

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
		const [promptRes, skillRes] = await Promise.all([
			getPrompts(localStorage.token).catch(() => null),
			getSkillItems(localStorage.token, query).catch(() => null)
		]);

		if (promptRes) {
			prompts = promptRes;
		}

		skills = skillRes?.items ?? [];
	};

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		const item = filteredItems[selectedIdx];
		if (item) {
			onSelect(item);
		}
	};

	const escapeTooltipText = (value = '') =>
		String(value)
			.replaceAll('&', '&amp;')
			.replaceAll('<', '&lt;')
			.replaceAll('>', '&gt;')
			.replaceAll('"', '&quot;')
			.replaceAll("'", '&#39;');

	const getSkillTooltipContent = (skill) => {
		const name = escapeTooltipText(skill.name);
		const description = escapeTooltipText(skill.description);

		return `<div class="max-w-80 whitespace-normal text-left leading-snug">
			<span class="break-words font-normal">${name}</span>${description ? `: <span class="break-words opacity-80">${description}</span>` : ''}
		</div>`;
	};
</script>

{#if filteredPrompts.length > 0}
	<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
		{$i18n.t('Prompts')}
	</div>

	{#each filteredPrompts as promptItem, promptIdx}
		<Tooltip content={promptItem.name} placement="top-start">
			<button
				class="flex h-[1.6875rem] w-full items-center gap-1.5 rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {promptIdx ===
				selectedIdx
					? 'bg-gray-50/40 dark:bg-gray-800/40 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					onSelect({ type: 'prompt', data: promptItem });
				}}
				on:mousemove={() => {
					selectedIdx = promptIdx;
				}}
				on:focus={() => {}}
				data-selected={promptIdx === selectedIdx}
			>
				<span class="shrink-0 font-normal text-black dark:text-gray-100">
					{promptItem.command}
				</span>

				<span class="min-w-0 truncate text-xs text-gray-500 dark:text-gray-400">
					{promptItem.name}
				</span>
			</button>
		</Tooltip>
	{/each}
{/if}

{#if skills.length > 0}
	<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
		{$i18n.t('Skills')}
	</div>

	{#each skills as skill, skillIdx}
		{@const itemIdx = filteredPrompts.length + skillIdx}
		<Tooltip
			content={getSkillTooltipContent(skill)}
			placement="top-start"
			tippyOptions={{ maxWidth: '20rem' }}
		>
			<button
				class="flex h-[1.6875rem] w-full items-center rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {itemIdx ===
				selectedIdx
					? 'bg-gray-50/40 dark:bg-gray-800/40 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					onSelect({ type: 'skill', data: skill });
				}}
				on:mousemove={() => {
					selectedIdx = itemIdx;
				}}
				on:focus={() => {}}
				data-selected={itemIdx === selectedIdx}
			>
				<div class="flex w-full min-w-0 items-center text-black dark:text-gray-100">
					<div class="mr-2 flex size-4.5 shrink-0 items-center justify-center">
						<Cube className="size-3.5" />
					</div>
					<div class="truncate min-w-0 flex-1">
						{skill.name}
					</div>
					<div class="ml-2 max-w-24 shrink-0 truncate text-xs text-gray-500 dark:text-gray-400">
						{skill.id}
					</div>
				</div>
			</button>
		</Tooltip>
	{/each}
{/if}
