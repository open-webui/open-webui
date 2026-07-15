<script>
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { page } from '$app/stores';

	import UserList from './Users/UserList.svelte';
	import Groups from './Users/Groups.svelte';

	const i18n = getContext('i18n');

	let selectedTab;
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		selectedTab = ['overview', 'groups'].includes(tabFromPath) ? tabFromPath : 'overview';
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

		// Scroll to the selected tab on mount
		scrollToTab(selectedTab);
	});
</script>

<div class="flex flex-col w-full h-full pb-2">
	<div
		id="users-tabs-container"
		class="mx-2 sm:mx-[16px] flex flex-row overflow-x-auto gap-2.5 max-w-full dark:text-gray-200 text-sm font-normal text-left scrollbar-none"
	>
		<a
			id="overview"
			href="/admin/users/overview"
			draggable="false"
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition select-none {selectedTab ===
			'overview'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
		>
			<div class=" self-center">{$i18n.t('Overview')}</div>
		</a>

		<a
			id="groups"
			href="/admin/users/groups"
			draggable="false"
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition select-none {selectedTab ===
			'groups'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
		>
			<div class=" self-center">{$i18n.t('Groups')}</div>
		</a>
	</div>

	<div class="flex-1 mt-1 px-[16px] overflow-y-scroll">
		{#if selectedTab === 'overview'}
			<UserList />
		{:else if selectedTab === 'groups'}
			<Groups />
		{/if}
	</div>
</div>
