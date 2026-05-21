<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let placeholder = '';
	export let value = '';
	export let showClearButton = false;

	export let onFocus: () => void = () => {};
	export let onKeydown: (e: KeyboardEvent) => void = () => {};

	const clearSearchInput = () => {
		value = '';
		dispatch('input');
	};
</script>

<div class="px-1 mb-1 flex justify-center space-x-2 relative z-10" id="search-container">
	<div class="flex w-full rounded-xl" id="chat-search">
		<div class="self-center py-2 rounded-l-xl bg-transparent dark:text-gray-300">
			<Search />
		</div>

		<input
			id="search-input"
			class="w-full rounded-r-xl py-1.5 pl-2.5 text-sm bg-transparent dark:text-gray-300 outline-hidden"
			placeholder={placeholder ? placeholder : $i18n.t('Search')}
			autocomplete="off"
			bind:value
			on:input={() => {
				dispatch('input');
			}}
			on:focus={() => {
				onFocus();
			}}
			on:keydown={onKeydown}
		/>

		{#if showClearButton && value}
			<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
				<button
					class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					on:click={clearSearchInput}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			</div>
		{/if}
	</div>
</div>
