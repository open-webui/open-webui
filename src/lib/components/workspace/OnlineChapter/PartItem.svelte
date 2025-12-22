<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { DropdownMenu } from 'bits-ui';
	import ChevronDown from '../../icons/ChevronDown.svelte';
	import EllipsisVertical from '../../icons/EllipsisVertical.svelte';
	import GarbageBin from '../../icons/GarbageBin.svelte';
	import Pencil from '../../icons/Pencil.svelte';
	import Plus from '../../icons/Plus.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	interface Chapter {
		id: string;
		partId: string;
		name: string;
		description: string;
		linkedKnowledgeGroups: string[];
	}

	interface Part {
		id: string;
		name: string; // API: title
		chapters: Chapter[];
	}

	export let part: Part;
	export let isExpanded: boolean = false;

	let showMenu = false;
</script>

<div class="w-full">
	<!-- Part Header -->
	<div
		class="flex items-center w-full px-2 py-2 hover:bg-gray-50 dark:hover:bg-gray-850/50 rounded-xl transition group"
	>
		<!-- Expand/Collapse Button -->
		<button
			class="p-1 mr-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition text-gray-900 dark:text-gray-100"
			on:click={() => dispatch('toggle')}
		>
			<ChevronDown
				className="size-4 transition-transform duration-200 {isExpanded ? '' : '-rotate-90'}"
			/>
		</button>

		<!-- Part Icon -->
		<div
			class="size-10 shrink-0 flex justify-center items-center bg-primary-100 dark:bg-primary-500/20 text-primary-500 rounded-xl mr-3"
		>
			<svg class="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
				/>
			</svg>
		</div>

		<!-- Part Info -->
		<button class="flex-1 text-left min-w-0" on:click={() => dispatch('toggle')}>
			<div class="font-medium text-sm text-gray-900 dark:text-white truncate">{part.name}</div>
			<div class="text-xs text-gray-500">
				<span>{part.chapters.length} {$i18n.t('chapters')}</span>
			</div>
		</button>

		<!-- Menu -->
		<div
			class="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
			on:click|stopPropagation
		>
			<button
				class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition text-gray-900 dark:text-gray-100"
				title={$i18n.t('챕터 추가')}
				on:click={() => dispatch('addChapter')}
			>
				<Plus className="size-4" />
			</button>

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

	<!-- Chapters (slot) -->
	{#if isExpanded}
		<div transition:slide={{ duration: 200 }}>
			<slot />
		</div>
	{/if}
</div>
