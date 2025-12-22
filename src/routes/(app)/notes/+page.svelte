<script>
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import dayjs from '$lib/dayjs';
	import { mobile, showArchivedChats, showSidebar, user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { createNoteHandler } from '$lib/components/notes/utils';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Notes from '$lib/components/notes/Notes.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	let loaded = false;

	onMount(async () => {
		if (
			$page.url.searchParams.get('content') !== null ||
			$page.url.searchParams.get('title') !== null
		) {
			const title = $page.url.searchParams.get('title') ?? dayjs().format('YYYY-MM-DD');
			const content = $page.url.searchParams.get('content') ?? '';

			const res = await createNoteHandler(title, content);

			if (res) {
				goto(`/notes/${res.id}`);
			}
			return;
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
							<a class="min-w-fit transition" href="/notes">
								{$i18n.t('Notes')}
							</a>
						</div>
					</div>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="max-w-[240px]"
								role={$user?.role}
								help={true}
								on:show={(e) => {
									if (e.detail === 'archived-chat') {
										showArchivedChats.set(true);
									}
								}}
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

		<div class=" flex-1 max-h-full overflow-y-auto @container">
			<Notes />
		</div>
	</div>
{/if}
