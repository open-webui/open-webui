<script>
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getFreelancerProfile } from '$lib/apis/marketplace';
	import { mobile, showSidebar, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let freelancer = null;
	let loaded = false;

	const getRatingStars = (rating) => {
		const normalized = Math.max(0, Math.min(5, Number(rating) || 0));
		const rounded = Math.round(normalized);
		return `${'★'.repeat(rounded)}${'☆'.repeat(5 - rounded)}`;
	};

	onMount(async () => {
		const freelancerId = $page.params.id;
		try {
			freelancer = await getFreelancerProfile(localStorage.token, freelancerId);
		} catch (error) {
			console.error('Failed to load freelancer profile', error);
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
							<a class="min-w-fit transition text-gray-500 hover:text-gray-800 dark:hover:text-white" href="/projects">
								{$i18n.t('Marketplace')}
							</a>
							<span class="text-gray-500">/</span>
							<span class="min-w-fit text-black dark:text-white">
								{$i18n.t('Freelancer Profile')}
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
			<div class="max-w-3xl mx-auto">
				{#if freelancer}
					<div class="bg-white dark:bg-gray-850 rounded-2xl p-8 mb-8 border border-gray-100 dark:border-gray-800 shadow-sm">
						<div class="flex items-start gap-4">
							<img
								src={freelancer.profile_image_url || '/user.png'}
								class="size-16 object-cover rounded-full"
								alt="Freelancer profile"
								draggable="false"
							/>
							<div class="flex-1">
								<h1 class="text-3xl font-bold dark:text-white">{freelancer.name || 'Freelancer'}</h1>
								<div class="flex gap-3 mt-3 text-sm items-center flex-wrap">
									<span class="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg capitalize dark:text-sky-300 text-sky-600">{freelancer.role || 'Freelancer'}</span>
									<span class="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg capitalize {freelancer.status === 'available' ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-300'}">{freelancer.status || 'offline'}</span>
									<span class="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg text-amber-600 dark:text-amber-400">{getRatingStars(freelancer.rating)} {Number(freelancer.rating || 0).toFixed(1)}/5</span>
								</div>
							</div>
						</div>
						<hr class="my-6 border-gray-100 dark:border-gray-800" />

						<div class="mb-6">
							<h2 class="text-lg font-semibold dark:text-white mb-2">{$i18n.t('Experience / Skills')}</h2>
							{#if freelancer.skills && freelancer.skills.length > 0}
								<div class="flex flex-wrap gap-2">
									{#each freelancer.skills as skill}
										<span class="px-3 py-1 text-sm rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-200">{skill}</span>
									{/each}
								</div>
							{:else}
								<p class="text-gray-500">{$i18n.t('No skills added yet.')}</p>
							{/if}
						</div>

						<div>
							<h2 class="text-lg font-semibold dark:text-white mb-2">{$i18n.t('Bio')}</h2>
							<p class="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{freelancer.bio || $i18n.t('No bio provided yet.')}</p>
						</div>
					</div>
				{:else}
					<div class="text-center py-12 text-gray-500">
						{$i18n.t('Freelancer profile not found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
