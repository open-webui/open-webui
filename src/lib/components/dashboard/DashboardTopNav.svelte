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
	class="flex flex-row items-start p-5 gap-5 w-full h-20
		bg-[rgba(253,254,254,0.7)] dark:bg-[rgba(39,40,44,0.5)]
		backdrop-blur-[20px]"
>
	<!-- Left: Logo Section -->
	<div class="flex flex-row items-center gap-2 flex-1 h-9">
		<a
			href="https://hanyang.ac.kr/"
			class="flex items-center justify-center size-9 shrink-0"
			draggable="false"
		>
			<HYULogo36 />
		</a>
		<h1 class="text-title-4 tracking-tight text-gray-950 dark:text-[#FDFEFE]">
			{$i18n.t('HYU AI Tutoring Assistant')}
		</h1>
	</div>

	<!-- Right: User Section -->
	<div class="flex flex-row items-center gap-7">
		<DashboardToggleSwitch activeMode="dashboard" />

		{#if $user}
			<UserMenu role={$user?.role}>
				<div class="flex flex-row items-start gap-3 cursor-pointer">
					<!-- User Info -->
					<div class="flex flex-col justify-end items-end">
						<span class="text-body-4-medium text-right text-gray-950 dark:text-[#FDFEFE]">
							{$user?.name}
						</span>
						<span class="text-caption text-right text-gray-700 dark:text-gray-300">
							{$user?.role}
						</span>
					</div>
					<!-- Profile Image -->
					<div class="size-10 shrink-0">
						<img
							src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
							class="size-10 object-cover rounded-full"
							alt="Profile"
						/>
					</div>
				</div>
			</UserMenu>
		{/if}
	</div>
</nav>
