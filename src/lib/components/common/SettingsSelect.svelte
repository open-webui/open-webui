<script lang="ts">
	import { afterUpdate, createEventDispatcher, onMount } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';

	// Native <select> popups cannot be themed in Firefox, so the visible list is regular DOM.

	type SettingsSelectValue = string | number | boolean;
	type SettingsSelectItem = {
		value: SettingsSelectValue;
		label: string;
		disabled: boolean;
	};

	export let value: SettingsSelectValue = '';
	export let id = '';
	export let name = '';
	export let ariaLabel = '';
	export let placeholder = '';
	export let required = false;
	export let disabled = false;
	export let className = 'w-fit max-w-full';
	export let selectClassName = '';

	const dispatch = createEventDispatcher();

	let hiddenSelect: HTMLSelectElement | null = null;
	let triggerEl: HTMLButtonElement | null = null;
	let show = false;
	let triggerWidth = 0;
	let items: SettingsSelectItem[] = [];

	const isSameValue = (itemValue: SettingsSelectValue, selected: SettingsSelectValue) =>
		itemValue === selected || String(itemValue) === String(selected);

	$: selectedItem = items.find((item) => isSameValue(item.value, value));
	$: selectedLabel = selectedItem?.label || placeholder || String(value ?? '');

	const optionValue = (option: HTMLOptionElement): SettingsSelectValue => {
		if ('__value' in option) {
			return (option as HTMLOptionElement & { __value: SettingsSelectValue }).__value;
		}

		const raw = option.value;
		if (typeof value === 'number' && raw !== '' && !Number.isNaN(Number(raw))) {
			return Number(raw);
		}
		if (typeof value === 'boolean') {
			if (raw === 'true') return true;
			if (raw === 'false') return false;
		}
		return raw;
	};

	const itemsSignature = (next: SettingsSelectItem[]) =>
		next
			.map(
				(item) =>
					`${typeof item.value}:${String(item.value)}\0${item.label}\0${item.disabled ? 1 : 0}`
			)
			.join('\n');

	const syncItems = () => {
		if (!hiddenSelect) return;

		const next = Array.from(hiddenSelect.options).map((option) => ({
			value: optionValue(option),
			label: (option.textContent ?? '').replace(/\s+/g, ' ').trim(),
			disabled: option.disabled
		}));

		if (itemsSignature(next) !== itemsSignature(items)) {
			items = next;
		}
	};

	afterUpdate(syncItems);

	onMount(() => {
		const onKeydown = (event: KeyboardEvent) => {
			if (event.key !== 'Escape' || !show) return;
			event.preventDefault();
			event.stopImmediatePropagation();
			show = false;
		};
		window.addEventListener('keydown', onKeydown, true);
		return () => window.removeEventListener('keydown', onKeydown, true);
	});

	const measureTrigger = () => {
		if (triggerEl) {
			triggerWidth = triggerEl.getBoundingClientRect().width;
		}
	};

	const onOpenChange = (state: boolean) => {
		if (disabled) {
			show = false;
			return;
		}
		if (state) {
			measureTrigger();
		}
	};

	const selectOption = (item: SettingsSelectItem) => {
		if (item.disabled || disabled) return;
		value = item.value;
		show = false;
		dispatch('change', value);
		triggerEl?.focus();
	};
</script>

<div class="relative inline-flex {disabled ? 'pointer-events-none opacity-50' : ''} {className}">
	<select
		bind:this={hiddenSelect}
		bind:value
		name={name || undefined}
		{required}
		{disabled}
		tabindex="-1"
		aria-hidden="true"
		class="hidden"
	>
		<slot />
	</select>

	<Dropdown bind:show align="end" maxHeight="18rem" {onOpenChange}>
		<button
			bind:this={triggerEl}
			{...$$restProps}
			id={id || undefined}
			type="button"
			{disabled}
			aria-label={ariaLabel || undefined}
			aria-haspopup="listbox"
			aria-expanded={show}
			title={placeholder || undefined}
			class="focus-ring relative h-7 w-full max-w-full truncate rounded-lg border border-gray-100/50 !bg-gray-50/40 ps-2.5 pe-8 text-left text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 disabled:opacity-50 dark:border-white/[0.04] dark:!bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500 {selectClassName}"
		>
			<span class="block min-w-0 truncate">{selectedLabel}</span>
			<ChevronDown
				className="pointer-events-none absolute end-2 top-1/2 size-3.5 -translate-y-1/2 text-gray-400 dark:text-gray-500"
				strokeWidth="2"
			/>
		</button>

		<div slot="content" style={triggerWidth ? `min-width: ${triggerWidth}px` : undefined}>
			<DropdownMenu>
				{#each items as item}
					<button
						type="button"
						disabled={item.disabled}
						class={isSameValue(item.value, value) ? '' : 'text-gray-500 dark:text-gray-400'}
						on:click={() => selectOption(item)}
					>
						<span class="min-w-0 truncate {item.disabled ? 'opacity-50' : ''}">{item.label}</span>
					</button>
				{/each}
			</DropdownMenu>
		</div>
	</Dropdown>
</div>
