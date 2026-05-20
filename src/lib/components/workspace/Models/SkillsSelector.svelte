<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { getContext, onDestroy, onMount } from 'svelte';

	import { getSkillItems } from '$lib/apis/skills';

	type SkillItem = {
		id: string;
		name: string;
		description?: string | null;
	} & Record<string, unknown>;

	export let selectedSkillIds: string[] = [];

	let _skills: Record<string, SkillItem> = {};
	let loaded = false;
	let loading = false;
	let page = 1;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let total: number | null = null;
	let previousQuery = query;
	let loadRequestId = 0;

	const i18n = getContext('i18n');

	const loadSkillItems = async () => {
		if (!loaded) return;

		const requestId = ++loadRequestId;
		const requestPage = page;
		const requestQuery = query;

		loading = true;
		try {
			const res = await getSkillItems(localStorage.token, requestQuery, null, requestPage).catch(
				() => null
			);
			const skills = (res?.items ?? []) as SkillItem[];

			if (requestId !== loadRequestId || requestPage !== page || requestQuery !== query) {
				return;
			}

			total = res?.total ?? skills.length;
			_skills = skills.reduce((acc: Record<string, SkillItem>, skill) => {
				acc[skill.id] = skill;
				return acc;
			}, {});
		} finally {
			if (requestId === loadRequestId && requestPage === page && requestQuery === query) {
				loading = false;
			}
		}
	};

	const toggleSkill = (skillId: string, checked: boolean) => {
		if (checked) {
			selectedSkillIds = Array.from(new Set([...selectedSkillIds, skillId]));
		} else {
			selectedSkillIds = selectedSkillIds.filter((id) => id !== skillId);
		}
	};

	$: if (loaded && query !== previousQuery) {
		previousQuery = query;
		loadRequestId += 1;
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page === 1) {
				loadSkillItems();
			} else {
				page = 1;
			}
		}, 300);
	}

	$: if (loaded && page) {
		loadSkillItems();
	}

	onMount(() => {
		loaded = true;
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<div>
	<div class="flex w-full justify-between gap-2 mb-1">
		<div class=" self-center text-xs font-medium text-gray-500">{$i18n.t('Skills')}</div>

		<div
			class="flex items-center min-w-0 w-44 rounded-xl bg-gray-50 dark:bg-gray-850 px-2 py-1 text-gray-500"
		>
			<Search className="size-3.5 shrink-0" />
			<input
				class="w-full min-w-0 bg-transparent px-1.5 text-xs outline-hidden text-gray-700 dark:text-gray-200"
				bind:value={query}
				aria-label={$i18n.t('Search Skills')}
				placeholder={$i18n.t('Search Skills')}
			/>
			{#if query}
				<button
					class="rounded-full p-0.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					type="button"
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						query = '';
					}}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			{/if}
		</div>
	</div>

	<div class="flex flex-col mb-1">
		{#if loading}
			<div class="flex h-8 items-center">
				<Spinner className="size-4" />
			</div>
		{:else if Object.keys(_skills).length > 0}
			<div class=" flex items-center flex-wrap">
				{#each Object.keys(_skills) as skill}
					<div class=" flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={selectedSkillIds.includes(skill) ? 'checked' : 'unchecked'}
								on:change={(e) => {
									toggleSkill(skill, e.detail === 'checked');
								}}
							/>
						</div>

						<Tooltip content={_skills[skill]?.description ?? _skills[skill].id}>
							<div class=" py-0.5 text-sm w-full capitalize font-medium">
								{_skills[skill].name}
							</div>
						</Tooltip>
					</div>
				{/each}
			</div>

			{#if total !== null && total > 30}
				<div class="flex justify-start">
					<Pagination bind:page count={total} perPage={30} />
				</div>
			{/if}
		{:else if query}
			<div class="py-1 text-xs text-gray-500">
				{$i18n.t('No skills found')}
			</div>
		{/if}
	</div>

	{#if selectedSkillIds.length > 0}
		<div class="mb-1 flex flex-wrap items-center gap-1.5">
			{#each selectedSkillIds as skillId}
				<div
					class="flex max-w-full items-center gap-1 rounded-xl bg-gray-50 px-2 py-1 text-xs dark:bg-gray-850"
				>
					<Tooltip content={skillId}>
						<div class="max-w-40 truncate text-gray-700 dark:text-gray-200">
							{_skills[skillId]?.name ?? skillId}
						</div>
					</Tooltip>

					<button
						class="rounded-full p-0.5 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:hover:bg-gray-800 dark:hover:text-gray-100 transition"
						type="button"
						aria-label={$i18n.t('Remove skill')}
						on:click={() => {
							toggleSkill(skillId, false);
						}}
					>
						<XMark className="size-3" strokeWidth="2" />
					</button>
				</div>
			{/each}
		</div>
	{/if}

	<div class=" text-xs dark:text-gray-700">
		{$i18n.t('To select skills here, add them to the "Skills" workspace first.')}
	</div>
</div>
