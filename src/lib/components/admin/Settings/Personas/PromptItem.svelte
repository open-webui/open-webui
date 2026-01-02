<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { DropdownMenu } from 'bits-ui';
	import type { PersonaPrompt, PromptType } from '$lib/apis/prompt-groups';

	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let prompt: PersonaPrompt;
	export let showOrder = false;
	export let order: number | null = null;
	export let inGroup = false;

	let showDropdown = false;

	const getTypeBadge = (type: PromptType) => {
		switch (type) {
			case 'base':
				return { text: 'base', class: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' };
			case 'proficiency':
				return { text: 'proficiency', class: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' };
			case 'style':
				return { text: 'style', class: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' };
			case 'tool':
				return { text: 'tool', class: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' };
			default:
				return { text: 'general', class: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
		}
	};

	const getPersonaValueLabel = (type: PromptType, value: string | null): string => {
		if (!value) return '';

		if (type === 'proficiency') {
			switch (value) {
				case '1': return '초급 (하)';
				case '2': return '중급 (중)';
				case '3': return '고급 (상)';
				default: return value;
			}
		} else if (type === 'style') {
			switch (value) {
				case 'diagnosis': return '학생 진단 브리핑';
				case 'feedback': return '학습 향상 피드백';
				case 'selfdirected': return '자기주도 학습 유도';
				default: return value;
			}
		}
		return value;
	};

	$: badge = getTypeBadge(prompt.prompt_type);
	$: personaLabel = getPersonaValueLabel(prompt.prompt_type, prompt.persona_value);
</script>

<div class="group flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg transition {inGroup ? 'ml-6' : ''}">
	<!-- Order badge (if in group) -->
	{#if showOrder && order !== null}
		<div class="shrink-0 w-6 h-6 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded text-xs font-medium text-gray-500 dark:text-gray-400">
			{order}
		</div>
	{/if}

	<!-- Prompt icon -->
	<div class="shrink-0 w-8 h-8 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg">
		<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4 text-gray-500 dark:text-gray-400">
			<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
		</svg>
	</div>

	<!-- Content -->
	<div class="flex-1 min-w-0">
		<div class="flex items-center gap-2">
			<span class="font-medium text-sm text-gray-900 dark:text-white truncate">
				{prompt.title}
			</span>
			<span class="text-xs px-1.5 py-0.5 rounded {badge.class}">
				{badge.text}
			</span>
			{#if personaLabel}
				<span class="text-xs text-gray-500 dark:text-gray-400">
					({personaLabel})
				</span>
			{/if}
			{#if prompt.prompt_type === 'tool' && prompt.tool_priority !== undefined && prompt.tool_priority > 0}
				<span class="text-xs px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400">
					P:{prompt.tool_priority}
				</span>
			{/if}
		</div>
		<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
			{prompt.command}
			{#if prompt.prompt_type === 'tool' && prompt.tool_description}
				<span class="ml-2 text-amber-600 dark:text-amber-400">• {prompt.tool_description}</span>
			{/if}
		</div>
	</div>

	<!-- Actions -->
	<div class="shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
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
				class="w-36 p-1 bg-white dark:bg-gray-850 rounded-lg shadow-lg border border-gray-100 dark:border-gray-800 z-50"
				align="end"
				sideOffset={4}
			>
				<DropdownMenu.Item
					class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition cursor-pointer"
					on:click={() => {
						showDropdown = false;
						dispatch('edit', prompt);
					}}
				>
					<Pencil className="size-4" />
					{$i18n.t('편집')}
				</DropdownMenu.Item>

				{#if inGroup}
					<DropdownMenu.Item
						class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition cursor-pointer"
						on:click={() => {
							showDropdown = false;
							dispatch('remove', prompt);
						}}
					>
						<GarbageBin className="size-4" />
						{$i18n.t('그룹에서 제거')}
					</DropdownMenu.Item>
				{:else}
					<DropdownMenu.Item
						class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition cursor-pointer"
						on:click={() => {
							showDropdown = false;
							dispatch('delete', prompt);
						}}
					>
						<GarbageBin className="size-4" />
						{$i18n.t('삭제')}
					</DropdownMenu.Item>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</div>
