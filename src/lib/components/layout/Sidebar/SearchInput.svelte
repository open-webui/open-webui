<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import SearchIcon from '$lib/components/icons/Search.svelte';
	import SearchModal from './SearchModal.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let showSearchModal = false;
</script>

<SearchModal bind:show={showSearchModal} />

<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
	<button
		class="flex-grow flex space-x-3 rounded-lg px-2 py-[7px] hover:bg-gray-100 dark:hover:bg-gray-900 transition"
		on:click={() => {
			window._paq?.push(['trackEvent', 'ChatSearch', 'Clicked']);
			showSearchModal = true;
		}}
	>
		<div class="self-center">
			<SearchIcon className="size-[1.1rem]" strokeWidth="2" />
		</div>

		<div class="flex self-center">
			<div class="self-center font-medium text-sm font-primary">{$i18n.t('Search')}</div>
		</div>
	</button>
</div>
