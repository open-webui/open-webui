<script>
	import { getContext, tick, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';

	const i18n = getContext('i18n');

	let selectedTab;
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		selectedTab = ['leaderboard', 'feedback'].includes(tabFromPath) ? tabFromPath : 'leaderboard';
	}

	$: if (selectedTab) {
		// scroll to selectedTab
		scrollToTab(selectedTab);
	}

	const scrollToTab = (tabId) => {
		const tabElement = document.getElementById(tabId);
		if (tabElement) {
			tabElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
		}
	};

	let loaded = false;

	onMount(async () => {
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

		// Scroll to the selected tab on mount
		scrollToTab(selectedTab);
	});
</script>

{#if loaded}
	<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
		<div
			id="users-tabs-container"
			class="tabs mx-2 sm:mx-[16px] lg:mx-0 lg:px-[16px] flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-50 dark:text-gray-200 text-sm font-normal text-left scrollbar-none"
		>
			<a
				id="leaderboard"
				href="/admin/evaluations/leaderboard"
				draggable="false"
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition select-none {selectedTab ===
				'leaderboard'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			>
				<div class=" self-center">{$i18n.t('Leaderboard')}</div>
			</a>

			<a
				id="feedback"
				href="/admin/evaluations/feedback"
				draggable="false"
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition select-none {selectedTab ===
				'feedback'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			>
				<div class=" self-center">{$i18n.t('Feedback')}</div>
			</a>
		</div>

		<div class="flex-1 mt-1 lg:mt-0 px-[16px] lg:pr-[16px] lg:pl-0 overflow-y-scroll">
			{#if selectedTab === 'leaderboard'}
				<Leaderboard />
			{:else if selectedTab === 'feedback'}
				<Feedbacks />
			{/if}
		</div>
	</div>
{/if}
