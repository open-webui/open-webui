<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { tags } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import Check from '$lib/components/icons/Check.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let label = '';
	let showTagInput = false;
	let tagName = '';

	const addTagHandler = async () => {
		tagName = tagName.trim();
		if (tagName !== '') {
			dispatch('add', tagName);
			tagName = '';
			showTagInput = false;
		} else {
			toast.error($i18n.t(`Invalid Tag`));
		}
	};
</script>

<div class="px-0.5 flex {showTagInput ? 'flex-row-reverse' : ''}">
	{#if showTagInput}
		<div class="flex items-center">
			<input
				bind:value={tagName}
				class=" px-2 cursor-pointer self-center text-xs h-fit bg-transparent outline-hidden line-clamp-1 w-[6.5rem]"
				placeholder={$i18n.t('Add a tag')}
				aria-label={$i18n.t('Add a tag')}
				list="tagOptions"
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						addTagHandler();
					}
				}}
			/>
			<datalist id="tagOptions">
				{#each $tags as tag}
					<option value={tag.name} />
				{/each}
			</datalist>

			<button type="button" aria-label={$i18n.t('Save Tag')} on:click={addTagHandler}>
				<Check className="w-3 h-3" />
			</button>
		</div>
	{/if}

	<button
		class=" cursor-pointer self-center p-0.5 flex h-fit items-center dark:hover:bg-gray-700 rounded-full transition border dark:border-gray-600 border-dashed"
		type="button"
		aria-label={$i18n.t('Add Tag')}
		on:click={() => {
			showTagInput = !showTagInput;
		}}
	>
		<div class=" m-auto self-center">
			<Plus className="w-3 h-3 {showTagInput ? 'rotate-45' : ''} transition-all transform" />
		</div>
	</button>

	{#if label && !showTagInput}
		<span class="text-xs pl-2 self-center">{label}</span>
	{/if}
</div>
