<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { getPrompts } from '$lib/apis/prompts';
	import { getSkillItems } from '$lib/apis/skills';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};
	export let canCompact = false;
	export let compactDisabled = false;
	export let canStatus = false;
	export let contextPercent = 0;

	let selectedIdx = 0;
	export let filteredItems = [];

	let prompts = [];
	let skills = [];
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	$: contextCirclePercent = Math.min(Math.max(0, Math.round(contextPercent)), 100);
	$: contextCircleOffset = 50.27 * (1 - contextCirclePercent / 100);

	$: commandItems = [
		...(canCompact && 'compact'.startsWith(query.toLowerCase())
			? [{ type: 'command', data: { id: 'compact' } }]
			: []),
		...(canStatus && 'status'.startsWith(query.toLowerCase())
			? [{ type: 'command', data: { id: 'status' } }]
			: [])
	];

	$: filteredPrompts = prompts
		.filter((p) => p.command.toLowerCase().includes(query.toLowerCase()))
		.sort((a, b) => a.name.localeCompare(b.name));

	$: filteredItems = [
		...commandItems,
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
		if (item?.type === 'command' && item.data?.id === 'compact' && compactDisabled) {
			return;
		}
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

{#if commandItems.length > 0}
	<div class="app-muted mb-0.5 px-2 pt-1 pb-0.5 text-[0.625rem] leading-none">
		{$i18n.t('Commands')}
	</div>

	{#each commandItems as item, commandIdx}
		{#if item.data.id === 'compact'}
			<Tooltip content="Shorten older messages so this chat can keep going." placement="top">
				<button
					type="button"
					aria-label="Compact: shorten older messages so this chat can keep going."
					class="slash-command-row flex items-center gap-2 w-full h-6 px-2 rounded-xl text-xs text-left transition-colors duration-75
						{commandIdx === selectedIdx ? 'app-interactive-active' : ''} disabled:opacity-50"
					disabled={compactDisabled}
					on:mousedown={(e) => e.preventDefault()}
					on:click={() => {
						if (!compactDisabled) {
							onSelect(item);
						}
					}}
					on:mouseenter={() => {
						selectedIdx = commandIdx;
					}}
					on:focus={() => {}}
					data-selected={commandIdx === selectedIdx}
				>
					<span class="app-icon-muted flex items-center justify-center w-4 shrink-0">
						<svg class="size-3.5 -rotate-90" viewBox="0 0 20 20" aria-hidden="true">
							<circle
								cx="10"
								cy="10"
								r="8"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								class="opacity-20"
							/>
							<circle
								cx="10"
								cy="10"
								r="8"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-dasharray="50.27"
								style={`stroke-dashoffset: ${contextCircleOffset};`}
							/>
						</svg>
					</span>
					<span class="flex-1 min-w-0 flex items-baseline gap-1.5 overflow-hidden">
						<span class="truncate">Compact</span>
						<span class="app-muted text-[0.625rem] truncate shrink-0">
							{contextCirclePercent}% full
						</span>
					</span>
				</button>
			</Tooltip>
		{:else if item.data.id === 'status'}
			<Tooltip content="Check what is running in this chat." placement="top">
				<button
					type="button"
					aria-label="Status: check what is running in this chat."
					class="slash-command-row flex items-center gap-2 w-full h-6 px-2 rounded-xl text-xs text-left transition-colors duration-75
						{commandIdx === selectedIdx ? 'app-interactive-active' : ''}"
					on:mousedown={(e) => e.preventDefault()}
					on:click={() => {
						onSelect(item);
					}}
					on:mouseenter={() => {
						selectedIdx = commandIdx;
					}}
					on:focus={() => {}}
					data-selected={commandIdx === selectedIdx}
				>
					<span class="app-icon-muted flex items-center justify-center w-4 shrink-0">
						<svg
							class="size-3.5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="M12 14l4-4" />
							<path d="M3.34 19a10 10 0 1 1 17.32 0" />
						</svg>
					</span>
					<span class="flex-1 min-w-0 flex items-baseline gap-1.5 overflow-hidden">
						<span class="truncate">Status</span>
						<span class="app-muted text-[0.625rem] truncate shrink-0">
							Check what is running in this chat.
						</span>
					</span>
				</button>
			</Tooltip>
		{/if}
	{/each}
{/if}

{#if filteredPrompts.length > 0}
	<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
		{$i18n.t('Prompts')}
	</div>

	{#each filteredPrompts as promptItem, promptIdx}
		{@const itemIdx = commandItems.length + promptIdx}
		<Tooltip content={promptItem.name} placement="top-start">
			<button
				class="flex h-[1.6875rem] w-full items-center gap-1.5 rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {itemIdx ===
				selectedIdx
					? 'bg-gray-50/40 dark:bg-gray-800/40 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					onSelect({ type: 'prompt', data: promptItem });
				}}
				on:mousemove={() => {
					selectedIdx = itemIdx;
				}}
				on:focus={() => {}}
				data-selected={itemIdx === selectedIdx}
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
		{@const itemIdx = commandItems.length + filteredPrompts.length + skillIdx}
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
