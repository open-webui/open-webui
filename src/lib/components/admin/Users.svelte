<script>
	import { getContext, onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { adminGroupCount, adminUserCount, config, user } from '$lib/stores';
	import { page } from '$app/stores';
	import { getGroups } from '$lib/apis/groups';
	import { getUsers } from '$lib/apis/users';
	import { formatNumber } from '$lib/utils';

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
	$: usersSeatLimit = $config?.license_metadata?.seats ?? null;
	$: usersCountExceeded = usersSeatLimit !== null && ($adminUserCount ?? 0) > usersSeatLimit;
	$: formattedUserCount =
		$adminUserCount === null
			? null
			: usersSeatLimit !== null
				? `${formatNumber($adminUserCount)} of ${formatNumber(usersSeatLimit)}`
				: formatNumber($adminUserCount);
	$: formattedGroupCount = $adminGroupCount === null ? null : formatNumber($adminGroupCount);

	const loadCounts = async () => {
		const [usersRes, groupsRes] = await Promise.all([
			getUsers(localStorage.token, undefined, 'created_at', 'asc', 1).catch(() => null),
			getGroups(localStorage.token).catch(() => null)
		]);

		adminUserCount.set(usersRes?.total ?? null);
		adminGroupCount.set(Array.isArray(groupsRes) ? groupsRes.length : null);
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		await loadCounts();
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
	<div class="flex flex-col lg:flex-row w-full h-full pb-2">
		<div
			id="users-tabs-container"
			class="tabs mx-2 px-2 sm:mx-2.5 lg:mx-0 lg:px-2.5 flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-0 lg:flex-col lg:flex-none lg:w-50 dark:text-gray-200 text-sm font-normal text-left scrollbar-none"
		>
			<a
				id="overview"
				href="/admin/users/overview"
				draggable="false"
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex items-center gap-1.5 text-right transition select-none {selectedTab ===
				'overview'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			>
				<div class=" self-center">{$i18n.t('Overview')}</div>
				{#if formattedUserCount !== null}
					<div
						class="self-center text-sm {usersCountExceeded
							? `text-red-500 ${selectedTab === 'overview' ? '' : 'opacity-50'}`
							: 'opacity-60'}"
					>
						{formattedUserCount}
					</div>
				{/if}
			</a>

			<a
				id="groups"
				href="/admin/users/groups"
				draggable="false"
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex items-center gap-1.5 text-right transition select-none {selectedTab ===
				'groups'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			>
				<div class=" self-center">{$i18n.t('Groups')}</div>
				{#if formattedGroupCount !== null}
					<div class="self-center text-sm opacity-60">
						{formattedGroupCount}
					</div>
				{/if}
			</a>
		</div>

		<div class="flex-1 px-3.5 lg:pr-[16px] lg:pl-0 overflow-y-scroll">
			{#if selectedTab === 'overview'}
				<UserList />
			{:else if selectedTab === 'groups'}
				<Groups />
			{/if}
		</div>
	</div>
{/if}
