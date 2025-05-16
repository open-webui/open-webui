<script lang="ts">
	import { tags } from '$lib/stores';
	import CloseTagIcon from '../icons/CloseTagIcon.svelte';
    import { getContext } from 'svelte';
    import { onClickOutside } from '$lib/utils';

    const i18n = getContext('i18n');

	export let selected = [];
	export let placeholder = 'Add category...';

	let input = '';
	let showDropdown = false;
	let inputElement;

    let isFocused = false;
    $: emptyInputPlaceholderVisible = !isFocused && selected?.length < 1;


	const tagColors = ['#272A6A', '#044B49', '#2F074F', '#27456A', '#0C2E18', '#47074F', '#6A2738'];

	const tagColorMap = new Map();

	function getTagColor(tagName: string) {
		if (!tagColorMap.has(tagName)) {
			const color = tagColors[tagColorMap.size % tagColors.length];
			tagColorMap.set(tagName, color);
		}
		return tagColorMap.get(tagName);
	}

	$: available = $tags.filter(
		(tag) =>
			!selected.some((s) => s.name === tag.name) &&
			tag.name.toLowerCase().includes(input.toLowerCase())
	);

	function addTag(tagName: string) {
		const trimmed = tagName.trim();
		if (!trimmed || selected.includes(trimmed)) return;
		selected = [...selected, { name: trimmed }];
		input = '';
		showDropdown = false;
	}

	function handleKeyDown(e) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addTag(input);
			inputElement?.blur();
		} else if (e.key === 'Backspace' && input === '' && selected?.length > 0) {
			selected = selected?.slice(0, -1);
		}
	}
</script>

<div
	class="relative w-full"
	use:onClickOutside={() => {
		showDropdown = false;
		input = '';
	}}
>
	<button
        type="button"
		class={`${isFocused ? 'border' : ''} border-lightGray-400 dark:border-customGray-700 w-full flex flex-wrap items-center gap-2 bg-lightGray-300 dark:bg-customGray-900 rounded-md px-2.5 pb-[9px] ${selected?.length > 0 ? 'pt-[22px]' : 'pt-[11px]'}`}
		on:click={() => {
            inputElement.focus();
            emptyInputPlaceholderVisible = false;
        }}
	>
        {#if selected?.length > 0}
        <div class="absolute top-1 text-xs text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('Category')}</div>
        {/if}
        {#if emptyInputPlaceholderVisible}
        <div class="flex items-center absolute justify-between pr-2.5 w-[calc(100%-10px)] bg-lightGray-300 dark:bg-customGray-900">
            <p class="text-sm text-lightGray-100 dark:text-customGray-100">{$i18n.t('Category')}</p>
            <p class="text-xs text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('E.g. Finance or Marketing or Name of project')}</p>
        </div>
        {/if}
		{#if selected}
			{#each selected as tag, i}
				<span
					style="background-color: {getTagColor(tag.name)}"
					class="px-2 py-1 rounded-lg text-sm leading-none text-white dark:text-customGray-100 flex items-center"
				>
					{tag.name}
					<button
						type="button"
						class="ml-1 hover:text-white"
						on:click={() => (selected = selected.filter((_, idx) => idx !== i))}
					>
					<CloseTagIcon/>
					</button>
				</span>
			{/each}
		{/if}

		<input
			bind:this={inputElement}
			bind:value={input}
			{placeholder}
			on:focus={() => {
                showDropdown = true;
                isFocused = true;
            }}
		    on:blur={() => {
                if(selected?.length < 1) {
                    setTimeout(() => {
                    isFocused = false;
                }, 200)
                }else{
                    isFocused = false;
                }    
            }}
			on:keydown={handleKeyDown}
			class={`flex-1 min-w-[8ch] outline-none placeholder:text-xs placeholder:text-lightGray-100/50 dark:placeholder:text-customGray-100/50 text-sm bg-transparent py-1`}
		/>
        </button>

	{#if showDropdown && (available?.length > 0 || input)}
		<div
			class="max-h-60 overflow-y-auto absolute left-0 right-0 -mt-1 bg-lightGray-300 dark:bg-customGray-900 px-1 py-2 border-l border-b border-r border-lightGray-400 dark:border-customGray-700 rounded-b-lg z-10"
		>
        <hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2"/>
        <div class="px-3">
			{#each available as tag}
				<div
					class="px-2 py-1 rounded-lg text-sm w-fit cursor-pointer mb-2 text-white dark:text-customGray-100"
					style="background-color: {getTagColor(tag.name)}"
					on:click={() => addTag(tag.name)}
				>
					{tag.name}
				</div>
			{/each}

			{#if input && !$tags.find((t) => t.name.toLowerCase() === input.toLowerCase())}
				<button
					class="px-3 py-2 text-sm text-lightGray-100 dark:text-customGray-100 cursor-pointer hover:bg-gray-100 dark:hover:bg-customGray-800"
					on:click={() => addTag(input)}
				>
                    {$i18n.t('Add')} "{input}"
            </button>
			{/if}
        </div>
		</div>
	{/if}
</div>
