<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { DropdownMenu } from 'bits-ui';
	import type { PromptGroupWithMappings, PersonaPrompt } from '$lib/apis/prompt-groups';
	import { getGroupPrompts, isToolType } from '$lib/apis/prompt-groups';

	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import PromptItem from './PromptItem.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let group: PromptGroupWithMappings;
	export let prompts: PersonaPrompt[] = [];
	export let expanded = false;
	export let isDefault = false;

	let showDropdown = false;
	let loading = false;
	let loaded = false;
	let groupPrompts: PersonaPrompt[] = [];

	// Load prompts for this group
	const loadGroupPrompts = async () => {
		if (loaded) return; // Already loaded
		loading = true;
		try {
			groupPrompts = await getGroupPrompts(localStorage.token, group.id);
		} catch (error) {
			console.error('Failed to load group prompts:', error);
			// Fallback to mapping-based approach
			groupPrompts = group.mappings
				.map((m) => prompts.find((p) => p.command === m.prompt_command))
				.filter((p): p is PersonaPrompt => p !== null);
		}
		loading = false;
		loaded = true;
	};

	// Load prompts on mount to show counts in header
	onMount(() => {
		loadGroupPrompts();
	});

	// Export function to reload prompts (called after adding/removing)
	export const reloadPrompts = () => {
		loaded = false;
		groupPrompts = [];
		loadGroupPrompts();
	};

	// Group prompts by type for display
	$: basePrompts = groupPrompts.filter((p) => p.prompt_type === 'base');
	$: proficiencyPrompts = groupPrompts.filter((p) => p.prompt_type === 'proficiency');
	$: stylePrompts = groupPrompts.filter((p) => p.prompt_type === 'style');
	$: toolPrompts = groupPrompts.filter((p) => isToolType(p.prompt_type));
	$: generalPrompts = groupPrompts.filter((p) => p.prompt_type === null);
</script>

<div class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
	<!-- Group Header -->
	<button
		type="button"
		class="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
		on:click={() => (expanded = !expanded)}
	>
		<!-- Expand/Collapse Icon -->
		<div class="shrink-0 text-gray-400">
			{#if expanded}
				<ChevronDown className="size-4" />
			{:else}
				<ChevronRight className="size-4" />
			{/if}
		</div>

		<!-- Group Icon -->
		<div class="shrink-0 w-8 h-8 flex items-center justify-center bg-blue-100 dark:bg-blue-900/30 rounded-lg">
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4 text-blue-600 dark:text-blue-400">
				<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
			</svg>
		</div>

		<!-- Group Info -->
		<div class="flex-1 min-w-0 text-left">
			<div class="flex items-center gap-2">
				<span class="font-medium text-sm text-gray-900 dark:text-white truncate">
					{group.name}
				</span>
				{#if isDefault}
					<span class="text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300">
						{$i18n.t('기본')}
					</span>
				{/if}
			</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 flex gap-2">
				{#if groupPrompts.length > 0}
					<span class="px-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
						{groupPrompts.length}개 프롬프트
					</span>
					{#if basePrompts.length > 0}
						<span class="px-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">base: {basePrompts.length}</span>
					{/if}
					{#if proficiencyPrompts.length > 0}
						<span class="px-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">난이도: {proficiencyPrompts.length}/3</span>
					{/if}
					{#if stylePrompts.length > 0}
						<span class="px-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">스타일: {stylePrompts.length}/3</span>
					{/if}
					{#if toolPrompts.length > 0}
						<span class="px-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded">도구: {toolPrompts.length}</span>
					{/if}
				{:else if !loading}
					<span class="text-gray-400 dark:text-gray-500">{$i18n.t('프롬프트 없음')}</span>
				{/if}
			</div>
		</div>

		<!-- Actions -->
		<div
			class="shrink-0 flex items-center gap-1"
			on:click|stopPropagation
			on:keydown|stopPropagation
			role="group"
		>
			<DropdownMenu.Root bind:open={showDropdown}>
				<DropdownMenu.Trigger>
					<button
						type="button"
						class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
						aria-label={$i18n.t('메뉴')}
					>
						<EllipsisHorizontal className="size-4" />
					</button>
				</DropdownMenu.Trigger>

				<DropdownMenu.Content
					class="w-44 p-1 bg-white dark:bg-gray-850 rounded-lg shadow-lg border border-gray-100 dark:border-gray-800 z-50"
					align="end"
					sideOffset={4}
				>
					<DropdownMenu.Item
						class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition cursor-pointer"
						on:click={() => {
							showDropdown = false;
							dispatch('addPrompt', group);
						}}
					>
						<Plus className="size-4" />
						{$i18n.t('프롬프트 추가')}
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition cursor-pointer"
						on:click={() => {
							showDropdown = false;
							dispatch('edit', group);
						}}
					>
						<Pencil className="size-4" />
						{$i18n.t('그룹 수정')}
					</DropdownMenu.Item>

					{#if !isDefault}
						<DropdownMenu.Item
							class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition cursor-pointer"
							on:click={() => {
								showDropdown = false;
								dispatch('setDefault', group);
							}}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
							</svg>
							{$i18n.t('기본으로 설정')}
						</DropdownMenu.Item>
					{/if}

					<DropdownMenu.Separator class="my-1 h-px bg-gray-100 dark:bg-gray-800" />

					<DropdownMenu.Item
						class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition cursor-pointer"
						on:click={() => {
							showDropdown = false;
							dispatch('delete', group);
						}}
					>
						<GarbageBin className="size-4" />
						{$i18n.t('그룹 삭제')}
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</button>

	<!-- Group Content (Prompts) -->
	{#if expanded}
		<div class="border-t border-gray-200 dark:border-gray-700">
			{#if loading}
				<div class="px-4 py-6 flex justify-center">
					<Spinner className="size-5" />
				</div>
			{:else if groupPrompts.length === 0}
				<div class="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('그룹에 프롬프트가 없습니다')}
					<button
						type="button"
						class="block mx-auto mt-2 text-blue-600 dark:text-blue-400 hover:underline"
						on:click={() => dispatch('addPrompt', group)}
					>
						+ {$i18n.t('프롬프트 추가')}
					</button>
				</div>
			{:else}
				<div class="py-1">
					<!-- General Prompts -->
					{#if generalPrompts.length > 0}
						<div class="px-3 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50">
							{$i18n.t('일반 프롬프트')} (General)
						</div>
						{#each generalPrompts as prompt (prompt.command)}
							<PromptItem
								{prompt}
								inGroup={true}
								on:edit
								on:remove={(e) => dispatch('removePrompt', { group, prompt: e.detail })}
							/>
						{/each}
					{/if}

					<!-- Base Prompts -->
					{#if basePrompts.length > 0}
						<div class="px-3 py-1 text-xs font-medium text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20">
							{$i18n.t('기본 프롬프트')} (Base)
						</div>
						{#each basePrompts as prompt (prompt.command)}
							<PromptItem
								{prompt}
								inGroup={true}
								on:edit
								on:remove={(e) => dispatch('removePrompt', { group, prompt: e.detail })}
							/>
						{/each}
					{/if}

					<!-- Proficiency Prompts -->
					{#if proficiencyPrompts.length > 0}
						<div class="px-3 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20">
							{$i18n.t('난이도 프롬프트')} (Proficiency) - {proficiencyPrompts.length}/3
						</div>
						{#each proficiencyPrompts as prompt (prompt.command)}
							<PromptItem
								{prompt}
								inGroup={true}
								on:edit
								on:remove={(e) => dispatch('removePrompt', { group, prompt: e.detail })}
							/>
						{/each}
					{/if}

					<!-- Style Prompts -->
					{#if stylePrompts.length > 0}
						<div class="px-3 py-1 text-xs font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20">
							{$i18n.t('스타일 프롬프트')} (Style) - {stylePrompts.length}/3
						</div>
						{#each stylePrompts as prompt (prompt.command)}
							<PromptItem
								{prompt}
								inGroup={true}
								on:edit
								on:remove={(e) => dispatch('removePrompt', { group, prompt: e.detail })}
							/>
						{/each}
					{/if}

					<!-- Tool Prompts -->
					{#if toolPrompts.length > 0}
						<div class="px-3 py-1 text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20">
							{$i18n.t('도구 프롬프트')} (Tool) - {toolPrompts.length}
						</div>
						{#each toolPrompts as prompt (prompt.command)}
							<PromptItem
								{prompt}
								inGroup={true}
								on:edit
								on:remove={(e) => dispatch('removePrompt', { group, prompt: e.detail })}
							/>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>
