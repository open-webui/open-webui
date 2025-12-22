<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Folder from '../../icons/Folder.svelte';
	import ItemMenu from './ItemMenu.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let folder: {
		id: string;
		name: string;
		itemCount: number;
		totalSize: number;
		createdAt: number;
		updatedAt: number;
	};
	export let viewMode: 'list' | 'grid' = 'list';
	export let formatFileSize: (bytes: number) => string;
</script>

{#if viewMode === 'list'}
	<button
		class="flex items-center w-full px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-850/50 rounded-2xl transition group"
		on:click={() => dispatch('click', folder)}
	>
		<!-- Folder Icon -->
		<div class="size-12 shrink-0 flex justify-center items-center bg-warning-100 dark:bg-warning-500/20 text-warning-500 rounded-xl mr-3">
			<Folder className="size-6" />
		</div>

		<!-- Folder Info -->
		<div class="flex-1 min-w-0 text-left">
			<div class="font-medium text-sm truncate text-gray-900 dark:text-white">{folder.name}</div>
			<div class="text-xs text-gray-500 flex gap-2">
				<span>{folder.itemCount} {$i18n.t('items')}</span>
				<span>•</span>
				<span>{formatFileSize(folder.totalSize)}</span>
			</div>
		</div>

		<!-- Menu -->
		<div class="opacity-0 group-hover:opacity-100 transition-opacity" on:click|stopPropagation>
			<ItemMenu
				on:delete={() => dispatch('delete', folder)}
			/>
		</div>
	</button>
{:else}
	<!-- Grid View -->
	<button
		class="flex flex-col items-center p-4 hover:bg-gray-50 dark:hover:bg-gray-850/50 rounded-2xl transition group relative"
		on:click={() => dispatch('click', folder)}
	>
		<!-- Menu Button (absolute positioned) -->
		<div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity" on:click|stopPropagation>
			<ItemMenu
				on:delete={() => dispatch('delete', folder)}
			/>
		</div>

		<!-- Folder Icon -->
		<div class="size-16 shrink-0 flex justify-center items-center bg-warning-100 dark:bg-warning-500/20 text-warning-500 rounded-xl mb-2">
			<Folder className="size-8" />
		</div>

		<!-- Folder Info -->
		<div class="w-full text-center">
			<div class="font-medium text-sm truncate text-gray-900 dark:text-white">{folder.name}</div>
			<div class="text-xs text-gray-500">
				{folder.itemCount} {$i18n.t('items')}
			</div>
		</div>
	</button>
{/if}
