<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { getSessionUser, userSignOut } from '$lib/apis/auths';

	import { mobile, showSidebar, showShortcuts, user, config } from '$lib/stores';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';
	import FaceSmile from '$lib/components/icons/FaceSmile.svelte';
	import UserStatusModal from './UserStatusModal.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { updateUserStatus } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';

	export let profile = false;
	export let help = false;

	export let className = 'max-w-[240px]';

	export let showActiveUsers = true;

	let showUserStatusModal = false;

	const dispatch = createEventDispatcher();

	let usage = null;
	const getUsageInfo = async () => {
		const res = await getUsage(localStorage.token).catch((error) => {
			console.error('Error fetching usage info:', error);
		});

		if (res) {
			usage = res;
		} else {
			usage = null;
		}
	};

	const handleDropdownChange = (state: boolean) => {
		dispatch('change', state);

		// Fetch usage info when dropdown opens, if user has permission
		if (state && ($config?.features?.enable_public_active_users_count || role === 'admin')) {
			getUsageInfo();
		}
	};
</script>

<ShortcutsModal bind:show={$showShortcuts} />
<UserStatusModal
	bind:show={showUserStatusModal}
	onSave={async () => {
		user.set(await getSessionUser(localStorage.token));
	}}
/>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<DropdownMenu.Root bind:open={show} onOpenChange={handleDropdownChange}>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className} rounded-2xl px-1.5 py-1.5 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-xl text-sm"
			sideOffset={4}
			side="top"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			{#if profile}
				<div class="flex gap-3 w-full px-2.5 py-3 items-center">
					<div class="items-center flex shrink-0">
						<img
							src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
							class="size-11 object-cover rounded-full ring-2 ring-gray-100 dark:ring-gray-700"
							alt="profile"
						/>
					</div>

					<div class="flex flex-col w-full flex-1 min-w-0">
						<div class="font-semibold text-base line-clamp-1 pr-2 text-gray-900 dark:text-white">
							{$user.name}
						</div>

						<div class="flex items-center gap-1.5 mt-0.5">
							{#if $user?.is_active ?? true}
								<span class="relative flex size-2">
									<span
										class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
									/>
									<span class="relative inline-flex rounded-full size-2 bg-green-500" />
								</span>
								<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Active')}</span>
							{:else}
								<span class="relative flex size-2">
									<span class="relative inline-flex rounded-full size-2 bg-gray-400" />
								</span>
								<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Away')}</span>
							{/if}
						</div>
					</div>
				</div>

				{#if $user?.status_emoji || $user?.status_message}
					<div class="mx-1.5 mb-1">
						<button
							class="w-full gap-2.5 px-3 py-2 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition text-xs flex items-center"
							type="button"
							on:click={() => {
								show = false;
								showUserStatusModal = true;
							}}
						>
							{#if $user?.status_emoji}
								<div class="self-center shrink-0">
									<Emoji className="size-4" shortCode={$user?.status_emoji} />
								</div>
							{/if}

							<Tooltip
								content={$user?.status_message}
								className="self-center line-clamp-2 flex-1 text-left"
							>
								{$user?.status_message}
							</Tooltip>

							<div class="self-center">
								<Tooltip content={$i18n.t('Clear status')}>
									<button
										type="button"
										class="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
										on:click={async (e) => {
											e.preventDefault();
											e.stopPropagation();
											e.stopImmediatePropagation();

											const res = await updateUserStatus(localStorage.token, {
												status_emoji: '',
												status_message: ''
											});

											if (res) {
												toast.success($i18n.t('Status cleared successfully'));
												user.set(await getSessionUser(localStorage.token));
											} else {
												toast.error($i18n.t('Failed to clear status'));
											}
										}}
									>
										<XMark className="size-3.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" strokeWidth="2" />
									</button>
								</Tooltip>
							</div>
						</button>
					</div>
				{:else}
					<div class="mx-1.5 mb-1">
						<button
							class="w-full px-3 py-2 gap-2 rounded-xl bg-gray-50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition text-xs flex items-center justify-center"
							type="button"
							on:click={() => {
								show = false;
								showUserStatusModal = true;
							}}
						>
							<FaceSmile className="size-4" strokeWidth="1.5" />
							<span class="truncate">{$i18n.t('Update your status')}</span>
						</button>
					</div>
				{/if}

				<hr class="border-gray-100 dark:border-gray-800 mx-2 my-1.5" />
			{/if}

			<DropdownMenu.Item
				class="flex items-center gap-3 rounded-xl py-2 px-2.5 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={async () => {
					show = false;

					// 跳转到统一设置页面
					await goto('/settings/user-general');

					if ($mobile) {
						await tick();
						showSidebar.set(false);
					}
				}}
			>
				<div class="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-700">
					<Settings className="size-4 text-gray-600 dark:text-gray-300" strokeWidth="1.5" />
				</div>
				<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Settings')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex items-center gap-3 rounded-xl py-2 px-2.5 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={async () => {
					show = false;

					dispatch('show', 'archived-chat');

					if ($mobile) {
						await tick();

						showSidebar.set(false);
					}
				}}
			>
				<div class="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-700">
					<ArchiveBox className="size-4 text-gray-600 dark:text-gray-300" strokeWidth="1.5" />
				</div>
				<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Archived Chats')}</div>
			</DropdownMenu.Item>

			{#if help}
				<hr class="border-gray-100 dark:border-gray-800 mx-2 my-1.5" />

				{#if $user?.role === 'admin'}
					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex items-center gap-3 rounded-xl py-2 px-2.5 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition select-none cursor-pointer"
						on:click={() => {
							show = false;
						}}
						href="https://docs.openwebui.cn"
					>
						<div class="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-700">
							<QuestionMarkCircle className="size-4 text-gray-600 dark:text-gray-300" />
						</div>
						<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Documentation')}</div>
					</DropdownMenu.Item>

				{/if}

				<DropdownMenu.Item
					class="flex items-center gap-3 rounded-xl py-2 px-2.5 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition select-none cursor-pointer"
					on:click={async () => {
						show = false;
						showShortcuts.set(!$showShortcuts);

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<div class="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-700">
						<Keyboard className="size-4 text-gray-600 dark:text-gray-300" />
					</div>
					<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Keyboard shortcuts')}</div>
				</DropdownMenu.Item>
			{/if}

			<hr class="border-gray-100 dark:border-gray-800 mx-2 my-1.5" />

			<DropdownMenu.Item
				class="flex items-center gap-3 rounded-xl py-2 px-2.5 w-full hover:bg-red-50 dark:hover:bg-red-900/20 transition cursor-pointer group"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<div class="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-700 group-hover:bg-red-100 dark:group-hover:bg-red-900/30 transition">
					<SignOut className="size-4 text-gray-600 dark:text-gray-300 group-hover:text-red-600 dark:group-hover:text-red-400 transition" strokeWidth="1.5" />
				</div>
				<div class="text-sm font-medium text-gray-700 dark:text-gray-200 group-hover:text-red-600 dark:group-hover:text-red-400 transition">{$i18n.t('Sign Out')}</div>
			</DropdownMenu.Item>

			{#if showActiveUsers && ($config?.features?.enable_public_active_users_count || role === 'admin') && usage}
				{#if usage?.user_count}
					<hr class="border-gray-100 dark:border-gray-800 mx-2 my-1.5" />

					<Tooltip
						content={usage?.model_ids && usage?.model_ids.length > 0
							? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
							: ''}
					>
						<div
							class="flex items-center gap-2.5 rounded-xl py-2 px-2.5 mx-0.5 bg-gray-50/50 dark:bg-gray-800/30"
							on:mouseenter={() => {
								if ($config?.features?.enable_public_active_users_count || role === 'admin') {
									getUsageInfo();
								}
							}}
						>
							<div class="flex items-center">
								<span class="relative flex size-2">
									<span
										class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
									></span>
									<span class="relative inline-flex rounded-full size-2 bg-green-500"></span>
								</span>
							</div>

							<div class="text-xs text-gray-600 dark:text-gray-400">
								<span>{$i18n.t('Active Users')}:</span>
								<span class="font-semibold text-gray-800 dark:text-gray-200 ml-1">{usage?.user_count}</span>
							</div>
						</div>
					</Tooltip>
				{/if}
			{/if}

			<!-- <DropdownMenu.Item class="flex items-center py-1.5 px-3 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
