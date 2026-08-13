<script lang="ts">
	import TagList from './Tags/TagList.svelte';
	import { getContext, createEventDispatcher, tick } from 'svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	type Tag = { name: string };

	export let tags: Tag[] = [];
	export let suggestionTags: (Tag | string | null | undefined)[] = [];
	export let disabled = false;

	let inputValue = '';
	let inputElement: HTMLInputElement | null = null;
	let popupElement: HTMLDivElement | null = null;
	let suggestionsOpen = false;

	$: tagNames = new Set((tags ?? []).map((tag) => tag.name.toLowerCase()));
	$: filteredSuggestionTags = (suggestionTags ?? [])
		.map((tag) => (typeof tag === 'string' ? tag : (tag?.name ?? '')).trim())
		.filter(
			(name) =>
				name &&
				!tagNames.has(name.toLowerCase()) &&
				name.toLowerCase().includes(inputValue.trim().toLowerCase())
		)
		.slice(0, 8);
	$: if (suggestionsOpen && filteredSuggestionTags.length > 0) {
		tick().then(positionPopup);
	}

	const portal = (node: HTMLElement) => {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	};

	const positionPopup = () => {
		if (!inputElement || !popupElement) return;
		const rect = inputElement.getBoundingClientRect();
		popupElement.style.top = `${rect.bottom + 4}px`;
		popupElement.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - 200))}px`;
	};

	const addTag = (tagName = inputValue) => {
		const value = tagName.trim();
		if (value !== '') {
			if (!tagNames.has(value.toLowerCase())) {
				dispatch('add', value);
			}
			inputValue = '';
		}

		suggestionsOpen = false;
	};

	const handlePointerDown = (event: PointerEvent) => {
		if (!suggestionsOpen) return;

		const target = event.target as Node;
		if (inputElement?.contains(target) || popupElement?.contains(target)) {
			return;
		}

		suggestionsOpen = false;
	};
</script>

<svelte:window
	on:pointerdown={handlePointerDown}
	on:scroll|capture={positionPopup}
	on:resize={positionPopup}
/>

<div class="flex flex-wrap items-center gap-1 w-full">
	<TagList
		{tags}
		{disabled}
		on:delete={(e) => {
			dispatch('delete', e.detail);
		}}
	/>

	{#if !disabled}
		<div class="flex-1 min-w-24">
			<input
				bind:this={inputElement}
				bind:value={inputValue}
				class="w-full {tags.length > 0
					? 'px-0.5'
					: ''} text-xs bg-transparent outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-500"
				placeholder={$i18n.t('Add a tag...')}
				role="combobox"
				aria-autocomplete="list"
				aria-expanded={suggestionsOpen && filteredSuggestionTags.length > 0}
				autocomplete="off"
				on:focus={() => {
					suggestionsOpen = true;
					positionPopup();
				}}
				on:input={() => {
					suggestionsOpen = true;
					positionPopup();
				}}
				on:keydown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						addTag();
					} else if (event.key === 'Escape') {
						suggestionsOpen = false;
					}
				}}
				on:blur={() => {
					setTimeout(() => {
						if (!popupElement?.contains(document.activeElement)) {
							suggestionsOpen = false;
						}
					}, 0);
				}}
			/>

			{#if suggestionsOpen && filteredSuggestionTags.length > 0}
				<div
					use:portal
					bind:this={popupElement}
					class="fixed w-48 max-h-48 overflow-y-auto rounded-2xl border border-gray-200 bg-white p-0.5 shadow-lg dark:border-gray-800 dark:bg-gray-850"
					role="listbox"
					style="z-index: 9999; top: 0; left: 0;"
				>
					{#each filteredSuggestionTags as tag (tag)}
						<button
							type="button"
							class="flex w-full items-center rounded-xl px-2 py-[5px] text-left text-xs text-gray-700 transition-colors hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
							role="option"
							on:mousedown={(event) => {
								event.preventDefault();
							}}
							on:click={() => {
								addTag(tag);
							}}
						>
							<span class="truncate">{tag}</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
