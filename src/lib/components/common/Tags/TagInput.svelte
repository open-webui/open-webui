<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let suggestionTags = [];
	export let disabled = false;

	let tagName = '';
	let showInput = false;
	let inputElement: HTMLInputElement;

	const addTagHandler = async () => {
		tagName = tagName.trim();
		if (tagName !== '') {
			dispatch('add', tagName);
			tagName = '';
		}
	};

	const openInput = () => {
		showInput = true;
		setTimeout(() => inputElement?.focus(), 0);
	};

	const closeInput = () => {
		if (tagName.trim() === '') {
			showInput = false;
		}
	};
</script>

{#if disabled}
	<!-- hidden when disabled -->
{:else if showInput}
	<div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-200/80 dark:bg-gray-700">
		<span class="text-gray-500 dark:text-blue-400">+</span>
		<input
			bind:this={inputElement}
			bind:value={tagName}
			class="w-20 text-sm bg-transparent outline-hidden text-gray-700 dark:text-blue-400 placeholder:text-gray-400 dark:placeholder:text-blue-400/50"
			placeholder={$i18n.t('Add tag')}
			aria-label={$i18n.t('Add a tag')}
			list="tagOptions"
			on:keydown={(event) => {
				if (event.key === 'Enter' || event.key === ' ') {
					event.preventDefault();
					addTagHandler();
				} else if (event.key === 'Escape') {
					tagName = '';
					showInput = false;
				}
			}}
			on:blur={closeInput}
		/>
	</div>
{:else}
	<button
		type="button"
		class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-200/80 dark:bg-gray-700 text-gray-500 dark:text-blue-400 text-sm font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
		on:click={openInput}
	>
		<span>+</span>
		<span>{$i18n.t('Add Tag')}</span>
	</button>
{/if}

{#if suggestionTags.length > 0}
	<datalist id="tagOptions">
		{#each suggestionTags as tag}
			<option value={tag.name} />
		{/each}
	</datalist>
{/if}
