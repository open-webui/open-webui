<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	// Event Dispatcher
	type PaginatorEvent = {
		amount: number;
		page: number;
	};
	const dispatch = createEventDispatcher<PaginatorEvent>();

	// Props
	/** Pass the page setting object. */
	export let settings = { page: 0, limit: 5, size: 0, amounts: [1, 2, 5, 10] };
	/** Sets selection and buttons to disabled state on-demand. */
	export let disabled = false;
	/** Show Previous and Next buttons. */
	export let showPreviousNextButtons = true;
	/** Show First and Last buttons. */
	export let showFirstLastButtons = false;
	/** Displays a numeric row of page buttons. */
	export let showNumerals = false;
	/** Maximum number of active page siblings in the numeric row.*/
	export let maxNumerals = 1;
	/** Provide classes to set flexbox justification. */
	export let justify: string = 'justify-between';

	// Props (select)
	/** Set the text for the amount selection input. */
	export let amountText = 'Items';

	// Props (buttons)
	/** Provide arbitrary classes to the active page buttons. */
	export let active: string = 'bg-gray-100 dark:bg-gray-700';
	/*** Set the base button classes. */
	export let buttonClasses: string = '!px-3 !py-1.5';

	/** Set the label for the pages separator. */
	export let separatorText = 'of';

	// Base Classes
	const cBase = 'flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-4';
	const cLabel = 'w-full md:w-auto';

	// Local
	let lastPage = Math.max(0, Math.ceil(settings.size / settings.limit - 1));
	let controlPages: number[] = getNumerals();

	function onChangeLength(): void {
		/** @event {{ length: number }} amount - Fires when the amount selection input changes.  */
		dispatch('amount', settings.limit);

		lastPage = Math.max(0, Math.ceil(settings.size / settings.limit - 1));

		// ensure page in limit range
		if (settings.page > lastPage) {
			settings.page = lastPage;
		}

		controlPages = getNumerals();
	}

	function gotoPage(page: number) {
		if (page < 0) return;

		settings.page = page;
		/** @event {{ page: number }} page Fires when the next/back buttons are pressed. */
		dispatch('page', settings.page);
		controlPages = getNumerals();
	}

	// Full row - no ellipsis
	function getFullNumerals() {
		const pages = [];
		for (let index = 0; index <= lastPage; index++) {
			pages.push(index);
		}
		return pages;
	}

	function getNumerals() {
		if (lastPage <= maxNumerals * 2 + 1) return getFullNumerals();

		const pages = [];
		const isWithinLeftSection = settings.page < maxNumerals + 2;
		const isWithinRightSection = settings.page > lastPage - (maxNumerals + 2);

		pages.push(0);
		if (!isWithinLeftSection) pages.push(-1);

		if (isWithinLeftSection || isWithinRightSection) {
			// mid section - with only one ellipsis
			const sectionStart = isWithinLeftSection ? 1 : lastPage - (maxNumerals + 2);
			const sectionEnd = isWithinRightSection ? lastPage - 1 : maxNumerals + 2;
			for (let i = sectionStart; i <= sectionEnd; i++) {
				pages.push(i);
			}
		} else {
			// mid section - with both ellipses
			for (let i = settings.page - maxNumerals; i <= settings.page + maxNumerals; i++) {
				pages.push(i);
			}
		}

		if (!isWithinRightSection) pages.push(-1);
		pages.push(lastPage);

		return pages;
	}

	function updateSize(size: number) {
		lastPage = Math.max(0, Math.ceil(size / settings.limit - 1));
		controlPages = getNumerals();
	}

	// State
	$: classesButtonActive = (page: number) => {
		return page === settings.page ? `${active}` : '';
	};
	$: maxNumerals, onChangeLength();
	$: updateSize(settings.size);

	// Reactive Classes
	$: classesBase = `${cBase} ${justify} ${$$props.class ?? ''}`;
</script>

<div class={classesBase}>
	<!-- Select Amount -->
	{#if settings.amounts.length}
		<select
			bind:value={settings.limit}
			on:change={onChangeLength}
			class="dark:bg-gray-900 w-fit pr-8 rounded py-2 px-2 text-sm bg-transparent outline-none"
			{disabled}
		>
			{#each settings.amounts as amount}
				<option value={amount}>{amount} {amountText}</option>
			{/each}
		</select>
	{/if}
	<!-- Controls -->
	<div>
		<!-- Button: First -->
		{#if showFirstLastButtons}
			<button
				type="button"
				class={buttonClasses}
				on:click={() => {
					gotoPage(0);
				}}
				disabled={disabled || settings.page === 0}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 512 512"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						d="M41.4 233.4c-12.5 12.5-12.5 32.8 0 45.3l160 160c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L109.3 256 246.6 118.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-160 160zm352-160l-160 160c-12.5 12.5-12.5 32.8 0 45.3l160 160c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L301.3 256 438.6 118.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0z"
					/>
				</svg>
			</button>
		{/if}
		<!-- Button: Back -->
		{#if showPreviousNextButtons}
			<button
				type="button"
				aria-label="Previous Page"
				class={buttonClasses}
				on:click={() => {
					gotoPage(settings.page - 1);
				}}
				disabled={disabled || settings.page === 0}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 448 512"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						d="M9.4 233.4c-12.5 12.5-12.5 32.8 0 45.3l160 160c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L109.2 288 416 288c17.7 0 32-14.3 32-32s-14.3-32-32-32l-306.7 0L214.6 118.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-160 160z"
					/>
				</svg>
			</button>
		{/if}
		<!-- Center -->
		{#if showNumerals === false}
			<!-- Details -->
			<button type="button" class="{buttonClasses} !text-sm">
				{settings.page * settings.limit + 1}-{Math.min(
					settings.page * settings.limit + settings.limit,
					settings.size
				)}&nbsp;<span class="opacity-50">{separatorText} {settings.size}</span>
			</button>
		{:else}
			<!-- Numeric Row -->
			{#each controlPages as page}
				<button
					type="button"
					{disabled}
					class="{buttonClasses} {classesButtonActive(page)}"
					on:click={() => gotoPage(page)}
				>
					{page >= 0 ? page + 1 : '...'}
				</button>
			{/each}
		{/if}
		<!-- Button: Next -->
		{#if showPreviousNextButtons}
			<button
				type="button"
				class={buttonClasses}
				on:click={() => {
					gotoPage(settings.page + 1);
				}}
				disabled={disabled || (settings.page + 1) * settings.limit >= settings.size}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 448 512"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						d="M438.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L338.8 224 32 224c-17.7 0-32 14.3-32 32s14.3 32 32 32l306.7 0L233.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l160-160z"
					/>
				</svg>
			</button>
		{/if}
		<!-- Button: last -->
		{#if showFirstLastButtons}
			<button
				type="button"
				class={buttonClasses}
				on:click={() => {
					gotoPage(lastPage);
				}}
				disabled={disabled || (settings.page + 1) * settings.limit >= settings.size}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 512 512"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						d="M470.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L402.7 256 265.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l160-160zm-352 160l160-160c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L210.7 256 73.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0z"
					/>
				</svg>
			</button>
		{/if}
	</div>
</div>
