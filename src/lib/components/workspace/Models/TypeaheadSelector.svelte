<script lang="ts">
	import ModelSettingsLabel from './ModelSettingsLabel.svelte';
	import { resolveLocalizedResource } from '$lib/utils/localizedContent';
	import { createEventDispatcher, getContext, tick } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import TTSVoiceInput from './TTSVoiceInput.svelte';
	import ModelSettingToggle from './ModelSettingToggle.svelte';

	type Item = {
		id: string;
		is_global?: boolean;
		name?: string;
		description?: string;
		meta?: {
			description?: string;
			toggle?: boolean;
		};
	};

	export let items: Item[] = [];
	export let placeholder = '';
	export let triggerLabel = '';
	export let emptyLabel = '';
	export let label = '';
	export let description = '';
	export let emptyHint = '';
	export let workspaceHref = '';
	export let disabled = false;
	export let id = 'typeahead-selector';
	export let className = 'w-full';
	export let selectedIds: string[] | null = null;
	export let defaultIds: string[] | null = null;
	export let variant: 'inline' | 'dropdown' = 'inline';

	const i18n: any = getContext('i18n');

	const dispatch = createEventDispatcher<{
		select: Item;
		enableall: Item[];
		clear: void;
	}>();
	let value = '';
	let show = false;
	let dropdown: Dropdown;
	let inputElement: HTMLInputElement | null = null;
	let valueElement: HTMLElement | null = null;

	$: if (disabled && show) show = false;
	$: query = value.trim().toLowerCase();
	$: matchedItems = (items ?? []).filter((item) => {
		const id = item.id.toLowerCase();
		const name = (item.name ?? '').toLowerCase();
		const description = (item.description ?? item.meta?.description ?? '').toLowerCase();

		return (
			query === '' ||
			id.includes(query) ||
			name.includes(query) ||
			description.includes(query) ||
			resolveLocalizedResource(item, $i18n.language).toLowerCase().includes(query) ||
			resolveLocalizedResource(item, $i18n.language, 'description').toLowerCase().includes(query)
		);
	});

	$: selectedItems = [
		...new Set([
			...items.filter((item) => item.is_global).map((item) => item.id),
			...(selectedIds ?? [])
		])
	].map((id) => items.find((item) => item.id === id) ?? { id, name: id });
	$: sortedItems = [...matchedItems].sort(
		(a, b) =>
			Number(b.is_global || selectedIds?.includes(b.id) || false) -
			Number(a.is_global || selectedIds?.includes(a.id) || false)
	);
	$: summary = selectedItems
		.slice(0, 3)
		.map((item) => resolveLocalizedResource(item, $i18n.language))
		.join(', ');
	$: if (variant === 'dropdown' && show) {
		tick().then(() => inputElement?.focus());
	}

	const selectItem = (item: Item) => {
		if (disabled || item.is_global) return;
		dispatch('select', item);
		if (selectedIds === null) {
			show = false;
			value = '';
		} else {
			inputElement?.focus();
		}
	};

	const enableItems = () => {
		if (disabled) return;
		dispatch(
			'enableall',
			matchedItems.filter((item) => !item.is_global)
		);
		inputElement?.focus();
	};
</script>

{#if variant === 'dropdown'}
	<Dropdown
		bind:this={dropdown}
		anchorElement={valueElement}
		bind:show
		onOpenChange={(state) => {
			if (disabled) show = false;
			if (!state) {
				value = '';
			}
		}}
	>
		<button
			type="button"
			{disabled}
			aria-expanded={show}
			aria-label={label || triggerLabel || placeholder}
			class={label
				? 'grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal disabled:cursor-default sm:grid-cols-[8rem_minmax(0,1fr)_auto]'
				: 'flex min-w-0 items-center bg-transparent text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}
		>
			{#if label}
				<span class="text-gray-600 dark:text-gray-400"
					><ModelSettingsLabel {label} {description} /></span
				>
				<span
					bind:this={valueElement}
					class="flex min-w-0 items-center gap-1 text-gray-900 dark:text-gray-100"
				>
					<span class="min-w-0 [overflow-wrap:anywhere]">{summary || $i18n.t('None')}</span>
					{#if selectedItems.length > 3}<span class="shrink-0 text-gray-500"
							>+{selectedItems.length - 3}</span
						>{/if}
				</span>
				<ChevronRight className="size-3 text-gray-400" />
			{:else}<span class="truncate">{triggerLabel || placeholder}</span>{/if}
		</button>

		<div slot="content">
			<div
				class="flex w-96 max-w-[calc(100vw-2rem)] flex-col rounded-xl border border-gray-200 bg-white p-1 text-gray-900 shadow-lg dark:border-gray-800 dark:bg-gray-850 dark:text-gray-100"
			>
				<div class="flex items-center gap-2 px-2 py-1">
					<Search className="size-3.5 text-gray-500" />
					<input
						bind:this={inputElement}
						bind:value
						id={`${id}-input`}
						aria-label={placeholder}
						class="min-w-0 w-full bg-transparent py-0.5 text-xs placeholder:text-gray-500 dark:placeholder:text-gray-400 outline-hidden"
						type="text"
						{placeholder}
						autocomplete="off"
					/>
				</div>

				<div class="flex max-h-64 flex-col gap-0.5 overflow-y-auto">
					{#if selectedIds !== null && matchedItems.some((item) => !item.is_global)}
						<button
							type="button"
							class="min-h-7 w-full rounded-xl px-2 py-1 text-left text-xs text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
							on:click={enableItems}
						>
							<span class="truncate"
								>{$i18n.t('Enable all ({{COUNT}})', {
									COUNT: matchedItems.filter((item) => !item.is_global).length
								})}</span
							>
						</button>
					{/if}

					{#if matchedItems.length === 0}
						<div class="px-3 py-4 text-xs leading-5 text-gray-500 dark:text-gray-400">
							{emptyLabel || placeholder}
							{#if items.length === 0 && emptyHint}<p class="mt-1 leading-5">
									{emptyHint}
								</p>{/if}
						</div>
					{:else}
						{#each sortedItems as item (item.id)}
							<button
								type="button"
								class="flex min-h-7 w-full items-center justify-between gap-2 rounded-xl px-2 py-1 text-left text-xs hover:bg-gray-50 dark:hover:bg-gray-800 selected-command-option-button"
								disabled={disabled || item.is_global}
								aria-pressed={item.is_global || (selectedIds?.includes(item.id) ?? false)}
								on:click={() => {
									selectItem(item);
								}}
							>
								<span class="min-w-0 flex-1 truncate"
									>{resolveLocalizedResource(item, $i18n.language)}</span
								>
								{#if item.is_global}<span class="text-[0.6875rem] text-gray-500"
										>{$i18n.t('Global')}</span
									>{/if}
								{#if item.is_global || (selectedIds !== null && selectedIds.includes(item.id))}
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
							{#if defaultIds !== null && item.meta?.toggle && (item.is_global || selectedIds?.includes(item.id))}
								<div class="pb-1 pl-5 pr-1">
									<ModelSettingToggle
										label={$i18n.t('Start enabled in new chats')}
										checked={defaultIds.includes(item.id)}
										{disabled}
										on:change={(e) => {
											defaultIds = e.detail
												? [...new Set([...(defaultIds ?? []), item.id])]
												: (defaultIds ?? []).filter((id) => id !== item.id);
										}}
									/>
								</div>
							{/if}
						{/each}
					{/if}
				</div>

				<div
					class="mt-1 flex items-center justify-between gap-3 px-2 py-1.5 text-xs text-gray-500 dark:text-gray-400"
				>
					{#if selectedIds?.length}<button
							type="button"
							{disabled}
							on:click={() => dispatch('clear')}
							class="hover:text-gray-900 dark:hover:text-gray-100">{$i18n.t('Clear')}</button
						>{/if}
					<div class="ml-auto flex items-center gap-3">
						{#if workspaceHref}<a
								href={workspaceHref}
								target="_blank"
								rel="noreferrer"
								class="hover:text-gray-900 dark:hover:text-gray-100">{$i18n.t('Manage')}</a
							>{/if}
						<button
							type="button"
							class="hover:text-gray-900 dark:hover:text-gray-100"
							on:click={() => dropdown.close()}>{$i18n.t('Done')}</button
						>
					</div>
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
