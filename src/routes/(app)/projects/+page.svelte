<script>
	import { getContext, onMount } from 'svelte';
	import { getProjects, getHelpRequests } from '$lib/apis/marketplace';
	import { mobile, showSidebar, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');
	
	let projects = [];
	let helpRequests = [];
	let loaded = false;

	const getHelpRequestTitle = (request) => {
		if (request?.title) return request.title;
		if (request?.message) {
			const firstLine = String(request.message).split('\n')[0].trim();
			if (firstLine.length <= 60) return firstLine;
			return `${firstLine.slice(0, 60)}...`;
		}
		return 'Help Request';
	};

	onMount(async () => {
		try {
			projects = await getProjects(localStorage.token);
		} catch (error) {
			console.error("Failed to load projects", error);
		}

		try {
			helpRequests = await getHelpRequests(localStorage.token);
		} catch (error) {
			console.error("Failed to load help requests", error);
		}

		loaded = true;
	});
</script>

{#if loaded}
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
			<div class=" flex items-center">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
					<div class="">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
						>
							<a class="min-w-fit transition" href="/projects">
								{$i18n.t('Marketplace Projects')}
							</a>
						</div>
					</div>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="w-[240px]"
								role={$user?.role}
								help={true}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="User Menu"
								>
									<div class=" self-center">
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-6 object-cover rounded-full"
											alt="User profile"
											draggable="false"
										/>
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container px-4 py-8">
			<div class="max-w-4xl mx-auto">
				<div class="flex justify-between items-center mb-6">
					<h1 class="text-2xl font-bold dark:text-white">{$i18n.t('Projects & Requests')}</h1>
					<a href="/projects/new" class="bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 px-4 py-2 rounded-lg text-sm font-medium transition">
						{$i18n.t('Post Project')}
					</a>
				</div>

				{#if projects.length === 0 && helpRequests.length === 0}
					<div class="text-center py-12 text-gray-500">
						{$i18n.t('No projects or requests found yet.')}
					</div>
				{:else}
					{#if projects.length > 0}
						<h2 class="text-lg font-semibold dark:text-white mb-3">{$i18n.t('Projects')}</h2>
						<div class="grid gap-4">
							{#each projects as project}
								<a href="/projects/{project.id}" class="block p-6 rounded-2xl bg-white dark:bg-gray-850 shadow-sm border border-gray-100 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-600 transition">
									<h2 class="text-lg font-semibold dark:text-white">{project.title}</h2>
									<p class="text-sm text-gray-500 mt-2 line-clamp-2">{project.description}</p>
									<div class="mt-4 flex gap-4 text-xs font-medium text-gray-400">
										<span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800">✨ ${project.budget}</span>
										<span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 capitalize dark:text-sky-300 text-sky-600">{project.status}</span>
									</div>
								</a>
							{/each}
						</div>
					{/if}

					{#if helpRequests.length > 0}
						<h2 class="text-lg font-semibold dark:text-white mt-8 mb-3">{$i18n.t('Help Requests')}</h2>
						<div class="grid gap-4">
							{#each helpRequests as request}
								<a href="/help-requests/{request.id}" class="block p-6 rounded-2xl bg-white dark:bg-gray-850 shadow-sm border border-gray-100 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-600 transition">
									<h3 class="text-lg font-semibold dark:text-white">{getHelpRequestTitle(request)}</h3>
									<p class="text-sm text-gray-500 mt-2 line-clamp-2">{request.message}</p>
									<div class="mt-4 flex gap-4 text-xs font-medium text-gray-400 items-center">
										<span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 capitalize dark:text-amber-300 text-amber-600">{request.status ?? 'pending'}</span>
										{#if request.requester?.name}
											<span>{$i18n.t('By')} {request.requester.name}</span>
										{/if}
									</div>
								</a>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}
