<script>
	import { getContext, onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { page } from '$app/stores';

	import CharityList from './Charities/CharitiesList.svelte';

	const i18n = getContext('i18n');

	let selectedTab = 'overview';

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		loaded = true;

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

<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
	<div
		id="users-tabs-container"
		class=" flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
	>
		<button
			id="overview"
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
			'overview'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				goto('/admin/charities/overview');
			}}
		>
			<div class=" self-center mr-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="size-4"
				>
					<path d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14zm6-7a6 6 0 1 1-12 0 6 6 0 0 1 12 0z" />
					<path
						d="M8 3.5c-1.93 0-3.5 2.01-3.5 4.5s1.57 4.5 3.5 4.5 3.5-2.01 3.5-4.5-1.57-4.5-3.5-4.5zm0 8c-1.38 0-2.5-1.79-2.5-4s1.12-4 2.5-4 2.5 1.79 2.5 4-1.12 4-2.5 4z"
					/>
					<path d="M2.343 4.343a6 6 0 0 1 8.485-2.485m2.485 2.485a6 6 0 0 1-2.485 8.485" />
				</svg>
			</div>
			<div class=" self-center">{$i18n.t('Overview')}</div>
		</button>
	</div>

	<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
		<CharityList />
	</div>
</div>
