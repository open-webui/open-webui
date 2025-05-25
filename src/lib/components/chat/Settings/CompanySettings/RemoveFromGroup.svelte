<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { onClickOutside } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Plus from '$lib/components/icons/Plus.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';

	const i18n = getContext('i18n');

	let showDropdown = false;
	let root;
    const dispatch = createEventDispatcher();
</script>

<div bind:this={root} class="relative h-4" use:onClickOutside={() => (showDropdown = false)}>
	<div
		on:click={(e) => {
			e.stopPropagation();
			showDropdown = !showDropdown;
		}}
	>
		<slot />
	</div>
	{#if showDropdown}
		<div
			class="min-w-[12rem] flex flex-col absolute md:left-0 right-0 bg-lightGray-300 dark:bg-customGray-900 px-2 py-2 border border-lightGray-400 dark:border-customGray-700 rounded-lg z-10"
		>
			<button
				type="button"
				on:click={() => dispatch('removeFromGroup')}
				class="flex gap-2 items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
			>
				<DeleteIcon className="size-3"/>
				<div class="flex items-center">{$i18n.t('Remove from group')}</div>
			</button>
		</div>
	{/if}
</div>
