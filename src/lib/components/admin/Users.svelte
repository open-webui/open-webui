<script>
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import UserList from './Users/UserList.svelte';
	import Groups from './Users/Groups.svelte';

	const i18n = getContext('i18n');

	let selectedTab = 'overview';

	onMount(() => {
		const containerElement = document.getElementById('users-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}
	});
</script>

<div class="flex flex-col w-full h-full">
	<div
		id="users-tabs-container"
		class="tabs flex mb-2 gap-3 flex-row overflow-x-auto max-w-full dark:text-white text-sm font-medium text-left scrollbar-none border-b dark:border-gray-800"
	>
		<button
			class="pb-1.5 min-w-fit flex text-right transition border-b-2 {selectedTab === 'overview'
				? ' dark:border-white'
				: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				selectedTab = 'overview';
			}}
		>
			<div class=" self-center">{$i18n.t('Overview')}</div>
		</button>

		<button
			class=" pb-1.5 min-w-fit flex text-right transition border-b-2 {selectedTab === 'groups'
				? ' dark:border-white'
				: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				selectedTab = 'groups';
			}}
		>
			<div class=" self-center">{$i18n.t('Groups')}</div>
		</button>
	</div>

	<div class="flex-1 overflow-y-scroll">
		{#if selectedTab === 'overview'}
			<UserList />
		{:else if selectedTab === 'groups'}
			<Groups />
		{/if}
	</div>
</div>
