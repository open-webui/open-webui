<script lang="ts">
	import { createEventDispatcher, tick } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import TTSVoiceInput from './TTSVoiceInput.svelte';

	type Item = {
		id: string;
		name?: string;
		description?: string;
		meta?: {
			description?: string;
		};
	};

	export let items: Item[] = [];
	export let placeholder = '';
	export let triggerLabel = '';
	export let emptyLabel = '';
	export let id = 'typeahead-selector';
	export let className = 'w-full';
	export let selectedIds: string[] | null = null;
	export let variant: 'inline' | 'dropdown' = 'inline';

	const dispatch = createEventDispatcher<{
		select: Item;
		enableall: Item[];
	}>();
	let value = '';
	let show = false;
	let inputElement: HTMLInputElement | null = null;

	$: query = value.trim().toLowerCase();
	$: matchedItems = (items ?? []).filter((item) => {
		const id = item.id.toLowerCase();
		const name = (item.name ?? '').toLowerCase();
		const description = (item.description ?? item.meta?.description ?? '').toLowerCase();

		return (
			query === '' || id.includes(query) || name.includes(query) || description.includes(query)
		);
	});

	$: if (variant === 'dropdown' && show) {
		tick().then(() => inputElement?.focus());
	}

	const selectItem = (item: Item) => {
		dispatch('select', item);
		show = false;
		value = '';
	};

	const enableItems = () => {
		dispatch('enableall', matchedItems);
		show = false;
		value = '';
	};
</script>

{#if variant === 'dropdown'}
	<Dropdown
		bind:show
		onOpenChange={(state) => {
			if (!state) {
				value = '';
			}
		}}
	>
		<div
			class="flex min-w-0 items-center bg-transparent text-xs text-gray-500 outline-hidden hover:underline dark:text-gray-400"
		>
			<span class="truncate">{triggerLabel || placeholder}</span>
		</div>

		<div slot="content">
			<div
				class="z-[10000] flex w-64 flex-col rounded-xl border border-gray-200 bg-white p-0.5 text-black shadow-lg dark:border-gray-800 dark:bg-gray-850 dark:text-white"
			>
				<div class="flex w-full space-x-1.5 px-1.5 pb-0.5">
					<div class="flex flex-1">
						<div class="self-center mr-1.5">
							<Search className="size-3.5" />
						</div>
						<input
							bind:this={inputElement}
							bind:value
							id={`${id}-input`}
							class="w-full bg-transparent py-0.5 text-[13px] outline-hidden"
							type="text"
							{placeholder}
							autocomplete="off"
						/>
					</div>
				</div>

				<div class="flex max-h-56 flex-col gap-0.5 overflow-y-scroll">
					{#if selectedIds !== null && matchedItems.length > 0}
						<button
							type="button"
							class="h-[1.6875rem] w-full rounded-xl px-2 text-left text-[13px] text-gray-700 transition-colors hover:bg-gray-50/40 hover:text-gray-900 dark:text-gray-200 dark:hover:bg-gray-800/40 dark:hover:text-gray-100"
							on:click={enableItems}
						>
							<span class="truncate">Enable all ({matchedItems.length})</span>
						</button>
					{/if}

					{#if matchedItems.length === 0}
						<div class="pt-4 pb-6 text-center text-xs text-gray-500 dark:text-gray-400">
							{emptyLabel || placeholder}
						</div>
					{:else}
						{#each matchedItems as item (item.id)}
							<button
								type="button"
								class="flex h-[1.6875rem] w-full items-center justify-between gap-2 rounded-xl px-2 text-left text-[13px] transition-colors hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 selected-command-option-button"
								aria-pressed={selectedIds?.includes(item.id) ?? false}
								on:click={() => {
									selectItem(item);
								}}
							>
								<span class="min-w-0 flex-1 truncate">{item.name || item.id}</span>
								{#if selectedIds !== null && selectedIds.includes(item.id)}
									<svg
										class="size-3.5 shrink-0 text-gray-500 dark:text-gray-400"
										aria-hidden="true"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
									>
										<path
											stroke="currentColor"
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="3"
											d="m5 12 4.7 4.5 9.3-9"
										/>
									</svg>
								{/if}
							</button>
						{/each}
					{/if}
				</div>
			</div>
		</div>
	</Dropdown>
{:else}
	<div class="mb-1 block">
		<TTSVoiceInput
			{id}
			voices={items}
			{placeholder}
			{className}
			{selectedIds}
			bind:value
			on:select={(e) => {
				dispatch('select', e.detail);
				if (selectedIds === null) value = '';
			}}
			on:enableall={(e) => dispatch('enableall', e.detail)}
		/>
	</div>
{/if}
