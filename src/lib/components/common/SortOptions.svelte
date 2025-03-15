<script context="module" lang="ts">
	export type SortDirection = 'asc' | 'desc' | 'none';
	
	export interface SortState {
		field: string;
		direction: SortDirection;
		initialLoad: boolean;
	}

	export function sortItems<T>(items: T[], sortState: SortState): T[] {
		if (sortState.initialLoad || sortState.direction === 'none') {
			return [...items];
		}
		
		return [...items].sort((a, b) => {
			const valueA = getNestedValue(a, sortState.field);
			const valueB = getNestedValue(b, sortState.field);
			
			const compareA = typeof valueA === 'string' ? valueA.toLowerCase() : valueA;
			const compareB = typeof valueB === 'string' ? valueB.toLowerCase() : valueB;
			
			const comparableA = compareA as string | number | boolean | Date;
			const comparableB = compareB as string | number | boolean | Date;
			
			if (sortState.direction === 'asc') {
				return comparableA > comparableB ? 1 : comparableA < comparableB ? -1 : 0;
			} else {
				return comparableA < comparableB ? 1 : comparableA > comparableB ? -1 : 0;
			}
		});
	}

	function getNestedValue(obj: unknown, path: string): unknown {
		if (!obj) return '';
		if (!path) return obj;
		
		const keys = path.split('.');
		let value = obj as Record<string, unknown>;
		
		for (const key of keys) {
			if (value === null || value === undefined || typeof value !== 'object') {
				return '';
			}
			value = value[key] as Record<string, unknown>;
		}
		
		return value === null || value === undefined ? '' : value;
	}
</script>

<script lang="ts">
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import { getContext, createEventDispatcher, tick } from 'svelte';
	import type { Readable } from 'svelte/store';
	import { onMount } from 'svelte';
	
	interface I18nStore extends Readable<{
		t: (key: string) => string;
	}> {}
	
	const i18n = getContext<I18nStore>('i18n');
	const dispatch = createEventDispatcher<{
		change: { sortedItems: any[]; sortState: SortState };
	}>();
	
	export let sortState: SortState = {
		field: '',
		direction: 'none',
		initialLoad: true
	};
	
	export let items: any[] = [];
	export let options: { value: string; label: string }[] = [];
	
	export let sortedItems: any[] = [];
	
	export let isSorting: boolean = false;
	
	$: if (options.length > 0 && sortState.initialLoad) {
		sortState.field = options[0].value;
	}
	
	onMount(() => {
		if (options.length > 0 && sortState.field === '') {
			sortState.field = options[0].value;
		}
	});
	
	$: if (items && items.length >= 0) {
		sortedItems = sortItems(items, sortState);
	}
	
	$: if (sortedItems) {
		dispatch('change', { sortedItems, sortState });
	}
	
	function changeSortField(field: string) {
		isSorting = true;
		
		sortState.initialLoad = false;
		
		if (sortState.field === field) {
			if (sortState.direction === 'asc') {
				sortState.direction = 'desc';
			} else if (sortState.direction === 'desc') {
				sortState.direction = 'none';
			} else {
				sortState.direction = 'asc';
			}
		} else {
			sortState.field = field;
			sortState.direction = 'asc';
		}
		
		tick().then(() => {
			isSorting = false;
		});
	}
</script>

<div class="flex items-center space-x-2 mr-2">
	<div class="text-sm text-gray-500 dark:text-gray-300">{$i18n.t('Sort by')}:</div>
	<div class="flex space-x-1">
		{#each options as option}
			<button
				class="px-2 py-1 text-xs rounded-lg {sortState.field === option.value ? 'bg-gray-100 dark:bg-gray-700' : 'hover:bg-gray-50 dark:hover:bg-gray-800'} transition"
				on:click={() => changeSortField(option.value)}
			>
				{option.label}
				{#if sortState.field === option.value}
					<span class="ml-1">
						{#if sortState.direction === 'asc'}
							<ChevronUp className="w-3 h-3 inline" />
						{:else if sortState.direction === 'desc'}
							<ChevronDown className="w-3 h-3 inline" />
						{:else}
							<span class="text-xs text-gray-400">•</span>
						{/if}
					</span>
				{/if}
			</button>
		{/each}
	</div>
</div> 