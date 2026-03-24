<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { tick } from 'svelte';

	export let value = '';
	export let options: Array<{ value: string; label: string }> = [];
	export let label = '';
	export let description = '';
	export let disabled = false;

	const dispatch = createEventDispatcher();
	let isOpen = false;
	let container: HTMLDivElement;
	let activeIndex = -1;
	let listboxId = `select-dropdown-${Math.random().toString(36).slice(2)}`;

	const toggleDropdown = async () => {
		if (!disabled) {
			isOpen = !isOpen;
			if (isOpen) {
				setActiveIndexFromValue();
				await tick();
				scrollActiveOptionIntoView();
			}
		}
	};

	const selectOption = (optionValue: string) => {
		value = optionValue;
		isOpen = false;
		activeIndex = options.findIndex((option) => option.value === optionValue);
		dispatch('change', { value: optionValue });
	};

	const getLabel = (val: string) => {
		return options.find((opt) => opt.value === val)?.label || val;
	};

	const setActiveIndexFromValue = () => {
		const selectedIndex = options.findIndex((option) => option.value === value);
		activeIndex = selectedIndex >= 0 ? selectedIndex : options.length > 0 ? 0 : -1;
	};

	const moveActive = (delta: number) => {
		if (options.length === 0) {
			activeIndex = -1;
			return;
		}

		if (activeIndex === -1) {
			activeIndex = 0;
			return;
		}

		activeIndex = (activeIndex + delta + options.length) % options.length;
	};

	const scrollActiveOptionIntoView = () => {
		if (activeIndex < 0) {
			return;
		}

		const optionElement = document.getElementById(`${listboxId}-option-${activeIndex}`);
		optionElement?.scrollIntoView({ block: 'nearest' });
	};

	const openWithKeyboard = async () => {
		if (disabled || isOpen) {
			return;
		}

		isOpen = true;
		setActiveIndexFromValue();
		await tick();
		scrollActiveOptionIntoView();
	};

	const handleTriggerKeydown = async (event: KeyboardEvent) => {
		if (disabled) {
			return;
		}

		if (event.key === 'ArrowDown') {
			event.preventDefault();
			if (!isOpen) {
				await openWithKeyboard();
				return;
			}
			moveActive(1);
			await tick();
			scrollActiveOptionIntoView();
			return;
		}

		if (event.key === 'ArrowUp') {
			event.preventDefault();
			if (!isOpen) {
				await openWithKeyboard();
				return;
			}
			moveActive(-1);
			await tick();
			scrollActiveOptionIntoView();
			return;
		}

		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			if (!isOpen) {
				await openWithKeyboard();
				return;
			}

			if (activeIndex >= 0 && activeIndex < options.length) {
				selectOption(options[activeIndex].value);
			}
			return;
		}

		if (event.key === 'Escape') {
			event.preventDefault();
			isOpen = false;
		}
	};

	const handleClickOutside = (event: MouseEvent) => {
		if (container && !container.contains(event.target as Node)) {
			isOpen = false;
		}
	};

	const handleWindowKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			isOpen = false;
		}
	};
</script>

<div class="relative w-full sm:w-auto" bind:this={container}>
	{#if label || description}
		<div class="mb-1.5">
			{#if label}
				<div class="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</div>
			{/if}
			{#if description}
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{description}</div>
			{/if}
		</div>
	{/if}

	<button
		{disabled}
		type="button"
		on:click={toggleDropdown}
		on:keydown={handleTriggerKeydown}
		aria-haspopup="listbox"
		aria-expanded={isOpen}
		aria-controls={listboxId}
		class="w-full sm:w-auto min-w-[10rem] px-3 py-2 bg-white dark:bg-gray-700/90 border border-gray-200 dark:border-gray-600 rounded-xl shadow-sm outline-none transition-all duration-150 cursor-pointer hover:border-gray-300 dark:hover:border-gray-500 focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400/60 dark:focus:border-blue-500/60 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-between gap-2 text-sm text-gray-900 dark:text-white"
	>
		<span class="truncate">{getLabel(value)}</span>
		<svg
			class="w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform duration-150 {isOpen ? 'rotate-180' : ''}"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m19 9-7 7-7-7" />
		</svg>
	</button>

	{#if isOpen}
		<div
			id={listboxId}
			role="listbox"
			class="absolute top-full left-0 sm:left-auto sm:right-0 mt-2 w-full sm:w-56 max-h-64 overflow-y-auto bg-white/95 dark:bg-gray-700/95 backdrop-blur border border-gray-200 dark:border-gray-600 rounded-xl shadow-lg z-50 p-1"
		>
			{#if options.length === 0}
				<div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No options</div>
			{:else}
				{#each options as option, index}
					<button
						id={`${listboxId}-option-${index}`}
						type="button"
						role="option"
						aria-selected={value === option.value}
						on:mouseenter={() => {
							activeIndex = index;
						}}
						on:click={() => selectOption(option.value)}
						class="w-full text-left px-3 py-2 text-sm rounded-lg transition-colors flex items-center justify-between gap-2 {value === option.value
							? 'bg-blue-50 dark:bg-blue-900/30 text-blue-900 dark:text-blue-100 font-medium'
							: activeIndex === index
								? 'bg-gray-100 dark:bg-gray-600/50 text-gray-900 dark:text-gray-100'
								: 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600/40'}"
					>
						<span class="truncate">{option.label}</span>
						{#if value === option.value}
							<svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
								<path
									fill-rule="evenodd"
									d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<svelte:window on:click={handleClickOutside} on:keydown={handleWindowKeydown} />
