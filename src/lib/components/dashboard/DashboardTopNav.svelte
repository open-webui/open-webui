<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import HYULogo36 from '$lib/components/icons/HYULogo36.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import DashboardToggleSwitch from './DashboardToggleSwitch.svelte';

	const i18n = getContext('i18n');
</script>

<nav
	class="w-full px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900/50 backdrop-blur-xl"
>
	<div class="flex items-center justify-between w-full">
		<!-- Left: University Logo + Title -->
		<div class="flex items-center gap-4">
			<a
				href="https://hanyang.ac.kr/"
				class="flex items-center rounded-xl size-10 justify-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition"
				draggable="false"
			>
				<HYULogo36 />
			</a>
			<h1 class="text-lg font-semibold text-gray-900 dark:text-gray-50">
				{$i18n.t('HYU AI Tutoring Assistant')}
			</h1>
		</div>

		<!-- Right: Toggle Switch + User Profile -->
		<div class="flex items-center gap-4">
			<DashboardToggleSwitch activeMode="dashboard" />

			{#if $user}
				<UserMenu role={$user?.role}>
					<div
						class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition cursor-pointer"
					>
						<img
							src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
							class="size-8 object-cover rounded-full"
							alt="Profile"
						/>
						<div class="flex flex-col">
							<span class="text-sm font-medium text-gray-900 dark:text-gray-50">
								{$user?.name}
							</span>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								{$user?.role}
							</span>
						</div>
					</div>
				</UserMenu>
			{/if}
		</div>
	</div>
</nav>
