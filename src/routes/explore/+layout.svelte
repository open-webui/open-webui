<script lang="ts">
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import IonosLogo from '$lib/IONOS/components/icons/IonosLogo.svelte';
	import Footer from '$lib/IONOS/components/Footer.svelte';
	import PrivacySlogan from '$lib/IONOS/components/PrivacySlogan.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import FilledUserAvatar from '$lib/IONOS/components/icons/FilledUserAvatar.svelte';

	import {
		user,
		showSidebar
	} from '$lib/stores';
</script>

<div class="flex flex-row w-full justify-between bg-gray-100">
	{#if $user !== undefined}
		<Sidebar />
	{/if}
	<div class="h-[100vh] overflow-scroll">
		<nav class="fixed z-30 {($user !== undefined) ? ($showSidebar ? 'w-[calc(100%-260px)]' : 'w-[calc(100%-60px)]') : 'w-full' } px-1.5 py-4 -mb-8 pt-10 flex items-center drag-region transition-width duration-200 ease-in-out">
			<div
				class=" bg-gradient-to-b from-gray-100 from-30% to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-10 -top-6 z-[-1] blur"
			></div>

			<div class=" flex w-full mx-auto px-1 pt-0.5 bg-transparent">
				<div class="flex justify-between items-center w-full">
					<div
						class="items-center flex flex-1 h-10 overflow-hidden py-0.5"
					>
						<a href="/">
							<IonosLogo className={"h-6"} />
						</a>
					</div>

					<PrivacySlogan />

					<div class="self-center flex flex-none items-center text-gray-600 dark:text-gray-400">
						{#if $user !== undefined}
							<UserMenu
								className="max-w-[200px]"
								role={$user?.role}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="User Menu"
								>
									<div class="text-blue-800 self-center">
										<FilledUserAvatar />
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</nav>
		<div class="flex flex-col pt-20 mt-10">
			<div class="grow">
				<slot />
			</div>
			<div>
				<Footer />
			</div>
		</div>
</div>
</div>

<style>
	/* Override this style from app.html */
	:global(html[lang]) {
		overflow-y: visible !important;
	}
</style>
