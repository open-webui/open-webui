<script>
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getHelpRequestById, respondToHelpRequest } from '$lib/apis/marketplace';
	import { mobile, showSidebar, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let helpRequest = null;
	let loaded = false;
	let responding = false;

	const getRequestTitle = (request) => {
		if (request?.title) return request.title;
		if (request?.message) {
			const firstLine = String(request.message).split('\n')[0].trim();
			if (firstLine.length <= 60) return firstLine;
			return `${firstLine.slice(0, 60)}...`;
		}
		return 'Help Request';
	};

	onMount(async () => {
		const requestId = $page.params.id;
		try {
			helpRequest = await getHelpRequestById(localStorage.token, requestId);
		} catch (error) {
			console.error('Failed to load help request details', error);
		}
		loaded = true;
	});

	const handleRespond = async () => {
		if (!helpRequest) return;
		responding = true;
		try {
			const updated = await respondToHelpRequest(localStorage.token, $page.params.id, {
				status: 'responded'
			});
			if (updated) {
				helpRequest = { ...helpRequest, ...updated };
				toast.success($i18n.t('Response submitted successfully!'));
			}
		} catch (error) {
			toast.error(`Error: ${error}`);
		}
		responding = false;
	};
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
							<a class="min-w-fit transition text-gray-500 hover:text-gray-800 dark:hover:text-white" href="/projects">
								{$i18n.t('Marketplace')}
							</a>
							<span class="text-gray-500">/</span>
							<span class="min-w-fit text-black dark:text-white">
								{$i18n.t('Help Request')}
							</span>
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
				{#if helpRequest}
					<div class="bg-white dark:bg-gray-850 rounded-2xl p-8 mb-8 border border-gray-100 dark:border-gray-800 shadow-sm">
						<h1 class="text-3xl font-bold dark:text-white mb-2">{getRequestTitle(helpRequest)}</h1>
						<div class="flex gap-4 text-sm mt-4 text-gray-500 items-center">
							<span class="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg capitalize">
								<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Status')}:</span>
								<span class="text-amber-600 dark:text-amber-400"> {helpRequest.status ?? 'pending'}</span>
							</span>
							{#if helpRequest.requester?.name}
								<span>{$i18n.t('By')} {helpRequest.requester.name}</span>
							{/if}
						</div>
						<hr class="my-6 border-gray-100 dark:border-gray-800" />
						<h2 class="text-lg font-semibold dark:text-white mb-3">{$i18n.t('Description')}</h2>
						<div class="prose dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
							{helpRequest.message}
						</div>
					</div>

					<div class="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-2xl border border-blue-100 dark:border-blue-900/50">
						<h3 class="text-xl font-bold text-blue-900 dark:text-blue-100 mb-4">{$i18n.t('Respond')}</h3>
						<p class="text-sm text-blue-800 dark:text-blue-200 mb-4">
							{$i18n.t('Mark this request as responded to start working with the requester.')}
						</p>
						<button
							type="button"
							on:click={handleRespond}
							disabled={responding || helpRequest.status === 'responded'}
							class="px-6 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
						>
							{#if responding}
								{$i18n.t('Submitting...')}
							{:else if helpRequest.status === 'responded'}
								{$i18n.t('Already Responded')}
							{:else}
								{$i18n.t('Respond to Request')}
							{/if}
						</button>
					</div>
				{:else}
					<div class="text-center py-12 text-gray-500">
						{$i18n.t('Help request not found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
