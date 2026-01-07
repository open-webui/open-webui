<script lang="ts">
	import { createEventDispatcher, getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Fuse from 'fuse.js';

	import Modal from '$lib/components/common/Modal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { PersonaPrompt, PromptType } from '$lib/apis/prompt-groups';
	import { isToolType } from '$lib/apis/prompt-groups';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let groupId: string;
	export let existingMappings: string[] = []; // Already added prompt commands
	export let availablePrompts: PersonaPrompt[] = [];

	let searchQuery = '';
	let typeFilter: PromptType | 'all' = 'all';
	let selectedPrompts: Set<string> = new Set();

	// Fuse.js for search
	let fuse: Fuse<PersonaPrompt>;
	let filteredPrompts: PersonaPrompt[] = [];

	$: {
		fuse = new Fuse(availablePrompts, {
			keys: ['title', 'command', 'content'],
			threshold: 0.3
		});
	}

	$: {
		let results = searchQuery
			? fuse.search(searchQuery).map((r) => r.item)
			: availablePrompts;

		if (typeFilter !== 'all') {
			results = results.filter((p) => p.prompt_type === typeFilter);
		}

		filteredPrompts = results;
	}

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

	const getOrderSuggestion = (type: PromptType): number => {
		switch (type) {
			case 'base':
				return 0;
			case 'proficiency':
				return 10;
			case 'style':
				return 20;
			case 'tool':
				return 30;
			default:
				return 50;
		}
	};

	const togglePrompt = (command: string) => {
		if (existingMappings.includes(command)) {
			return; // Already in group, can't toggle
		}

		if (selectedPrompts.has(command)) {
			selectedPrompts.delete(command);
		} else {
			selectedPrompts.add(command);
		}
		selectedPrompts = selectedPrompts; // Trigger reactivity
	};

	const handleSubmit = () => {
		const promptsToAdd = Array.from(selectedPrompts).map((command) => {
			const prompt = availablePrompts.find((p) => p.command === command);
			return {
				command,
				order: prompt ? getOrderSuggestion(prompt.prompt_type) : 30
			};
		});

		dispatch('add', { groupId, prompts: promptsToAdd });
		resetAndClose();
	};

	const resetAndClose = () => {
		searchQuery = '';
		typeFilter = 'all';
		selectedPrompts = new Set();
		dispatch('close');
	};

	$: if (show) {
		selectedPrompts = new Set();
	}
</script>

<Modal bind:show size="md" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="p-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
				{$i18n.t('그룹에 프롬프트 추가')}
			</h3>
			<button
				type="button"
				class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={resetAndClose}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-5"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Search & Filter -->
		<div class="flex gap-2 mb-3">
			<div class="flex-1 flex items-center border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 px-3">
				<Search className="size-4 text-gray-400" />
				<input
					type="text"
					class="flex-1 px-2 py-2 text-sm bg-transparent outline-none"
					placeholder={$i18n.t('프롬프트 검색...')}
					bind:value={searchQuery}
				/>
				{#if searchQuery}
					<button
						type="button"
						class="p-0.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition"
						on:click={() => (searchQuery = '')}
					>
						<XMark className="size-3.5" />
					</button>
				{/if}
			</div>

			<select
				class="px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg outline-none"
				bind:value={typeFilter}
			>
				<option value="all">{$i18n.t('전체')}</option>
				<option value="base">base</option>
				<option value="proficiency">proficiency</option>
				<option value="style">style</option>
				<option value="tool">tool</option>
			</select>
		</div>

		<!-- Order guide -->
		<div class="mb-3 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs text-gray-500 dark:text-gray-400">
			<span class="font-medium">{$i18n.t('Order 가이드')}:</span>
			base=0, proficiency=10, style=20, tool=30 ({$i18n.t('낮은 순서가 먼저 조합됨')})
		</div>

		<!-- Prompt List -->
		<div class="max-h-64 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
			{#if filteredPrompts.length === 0}
				<div class="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
					{$i18n.t('프롬프트가 없습니다')}
				</div>
			{:else}
				{#each filteredPrompts as prompt}
					{@const isExisting = existingMappings.includes(prompt.command)}
					{@const isSelected = selectedPrompts.has(prompt.command)}
					{@const badge = getTypeBadge(prompt.prompt_type)}
					<button
						type="button"
						class="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-800 last:border-b-0 transition
						{isExisting ? 'opacity-50 cursor-not-allowed' : ''}
						{isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
						on:click={() => togglePrompt(prompt.command)}
						disabled={isExisting}
					>
						<!-- Checkbox -->
						<div class="shrink-0">
							<div class="size-4 rounded border-2 flex items-center justify-center transition
								{isExisting ? 'border-gray-300 dark:border-gray-600 bg-gray-200 dark:bg-gray-700' : ''}
								{isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300 dark:border-gray-600'}"
							>
								{#if isSelected || isExisting}
									<svg class="size-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
										<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
									</svg>
								{/if}
							</div>
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
								{#if prompt.persona_value}
									<span class="text-xs text-gray-500 dark:text-gray-400">
										({prompt.persona_value})
									</span>
								{/if}
								{#if isToolType(prompt.prompt_type) && prompt.tool_priority !== undefined && prompt.tool_priority > 0}
									<span class="text-xs px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400">
										P:{prompt.tool_priority}
									</span>
								{/if}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
								{prompt.command}
								{#if isToolType(prompt.prompt_type) && prompt.tool_description}
									<span class="ml-2 text-amber-600 dark:text-amber-400">• {prompt.tool_description}</span>
								{/if}
							</div>
						</div>

						<!-- Status -->
						{#if isExisting}
							<span class="shrink-0 text-xs text-gray-400">{$i18n.t('이미 추가됨')}</span>
						{/if}
					</button>
				{/each}
			{/if}
		</div>

		<!-- Selected count -->
		<div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('선택됨')}: {selectedPrompts.size}개
		</div>

		<!-- Actions -->
		<div class="flex justify-end gap-2 pt-4">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={resetAndClose}
			>
				{$i18n.t('취소')}
			</button>
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={selectedPrompts.size === 0}
				on:click={handleSubmit}
			>
				{$i18n.t('추가')} ({selectedPrompts.size})
			</button>
		</div>
	</div>
</Modal>
