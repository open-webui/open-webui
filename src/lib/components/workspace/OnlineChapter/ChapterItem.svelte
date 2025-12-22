<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { DropdownMenu } from 'bits-ui';
	import EllipsisVertical from '../../icons/EllipsisVertical.svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';
	import Pencil from '../../icons/Pencil.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	interface Chapter {
		id: string;
		partId: string;
		name: string; // 예: "1. 1계 상미분방정식 (First-Order ODEs)"
		description: string; // 예: "1계 미분방정식의 기본 개념과 해법을 학습합니다."
		linkedKnowledgeGroups: string[];
	}

	interface KnowledgeGroup {
		id: string;
		name: string;
		itemCount: number;
	}

	export let chapter: Chapter;
	export let isLast: boolean = false;
	export let knowledgeGroups: KnowledgeGroup[] = [];
	export let getKnowledgeGroupName: (id: string) => string;

	let showMenu = false;

	$: linkedGroups = chapter.linkedKnowledgeGroups
		.map((id) => knowledgeGroups.find((g) => g.id === id))
		.filter(Boolean);
</script>

<div class="relative flex items-start w-full pl-4 py-1.5 group">
	<!-- Tree connector line -->
	<div class="absolute left-0 top-0 h-full flex items-center">
		<div
			class="w-4 h-px bg-gray-200 dark:bg-gray-700"
			style="margin-top: {isLast ? '-50%' : '0'}"
		></div>
	</div>

	<!-- Chapter Content -->
	<div
		class="flex-1 flex items-start px-2 py-2 hover:bg-gray-50 dark:hover:bg-gray-850/50 rounded-xl transition"
	>
		<!-- Chapter Icon -->
		<div
			class="size-8 shrink-0 flex justify-center items-center bg-blue-100 dark:bg-blue-500/20 text-blue-500 rounded-lg mr-3"
		>
			<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
				/>
			</svg>
		</div>

		<!-- Chapter Info -->
		<div class="flex-1 min-w-0">
			<div class="font-medium text-sm text-gray-900 dark:text-white">
				{chapter.name}
			</div>
			{#if chapter.description}
				<div class="text-xs text-gray-500 truncate mt-0.5">
					{chapter.description}
				</div>
			{/if}
			{#if linkedGroups.length > 0}
				<div class="flex flex-wrap gap-1 mt-1.5">
					{#each linkedGroups.slice(0, 3) as group}
						<span
							class="text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full"
						>
							{group?.name}
						</span>
					{/each}
					{#if linkedGroups.length > 3}
						<span class="text-xs text-gray-500">+{linkedGroups.length - 3}</span>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Menu -->
		<div class="opacity-0 group-hover:opacity-100 transition-opacity" on:click|stopPropagation>
			<DropdownMenu.Root bind:open={showMenu}>
				<DropdownMenu.Trigger>
					<button
						class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition text-gray-900 dark:text-gray-100"
					>
						<EllipsisVertical className="size-4" />
					</button>
				</DropdownMenu.Trigger>

				<DropdownMenu.Content
					class="bg-white dark:bg-gray-850 rounded-xl shadow-lg border border-gray-100 dark:border-gray-800 py-1 min-w-[140px] z-50"
					align="end"
					sideOffset={4}
				>
					<DropdownMenu.Item
						class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition"
						on:click={() => {
							showMenu = false;
							dispatch('edit');
						}}
					>
						<Pencil className="size-4" />
						<span>{$i18n.t('수정')}</span>
					</DropdownMenu.Item>
					<DropdownMenu.Item
						class="flex items-center gap-2 px-3 py-2 text-sm text-error-500 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition"
						on:click={() => {
							showMenu = false;
							dispatch('delete');
						}}
					>
						<GarbageBin className="size-4" />
						<span>{$i18n.t('삭제')}</span>
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>
