<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { getSessionUser, userSignOut } from '$lib/apis/auths';

	import { showSettings, mobile, showSidebar, showShortcuts, user, config } from '$lib/stores';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import Code from '$lib/components/icons/Code.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
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
			class="w-full {className}  rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg text-sm"
			sideOffset={4}
			side="top"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			{#if profile}
				<div class=" flex gap-3.5 w-full p-2.5 items-center">
					<div class=" items-center flex shrink-0">
						<img
							src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
							class=" size-10 object-cover rounded-full"
							alt="profile"
						/>
					</div>

					<div class=" flex flex-col w-full flex-1">
						<div class="font-medium line-clamp-1 pr-2">
							{$user.name}
						</div>

						<div class=" flex items-center gap-2">
							{#if $user?.is_active ?? true}
								<div>
									<span class="relative flex size-2">
										<span
											class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
										/>
										<span class="relative inline-flex rounded-full size-2 bg-green-500" />
									</span>
								</div>

								<span class="text-xs"> {$i18n.t('Active')} </span>
							{:else}
								<div>
									<span class="relative flex size-2">
										<span class="relative inline-flex rounded-full size-2 bg-gray-500" />
									</span>
								</div>

								<span class="text-xs"> {$i18n.t('Away')} </span>
							{/if}
						</div>
					</div>
				</div>

				{#if $user?.status_emoji || $user?.status_message}
					<div class="mx-1">
						<button
							class="mb-1 w-full gap-2 px-2.5 py-1.5 rounded-xl bg-gray-50 dark:text-white dark:bg-gray-900/50 text-black transition text-xs flex items-center"
							type="button"
							on:click={() => {
								show = false;
								showUserStatusModal = true;
							}}
						>
							{#if $user?.status_emoji}
								<div class=" self-center shrink-0">
									<Emoji className="size-4" shortCode={$user?.status_emoji} />
								</div>
							{/if}

							<Tooltip
								content={$user?.status_message}
								className=" self-center line-clamp-2 flex-1 text-left"
							>
								{$user?.status_message}
							</Tooltip>

							<div class="self-start">
								<Tooltip content={$i18n.t('Clear status')}>
									<button
										type="button"
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
										<XMark className="size-4 opacity-50" strokeWidth="2" />
									</button>
								</Tooltip>
							</div>
						</button>
					</div>
				{:else}
					<div class="mx-1">
						<button
							class="mb-1 w-full px-3 py-1.5 gap-1 rounded-xl bg-gray-50 dark:text-white dark:bg-gray-900/50 text-black transition text-xs flex items-center justify-center"
							type="button"
							on:click={() => {
								show = false;
								showUserStatusModal = true;
							}}
						>
							<div class=" self-center">
								<FaceSmile className="size-4" strokeWidth="1.5" />
							</div>
							<div class=" self-center truncate">{$i18n.t('Update your status')}</div>
						</button>
					</div>
				{/if}

				<hr class=" border-gray-50/30 dark:border-gray-800/30 my-1.5 p-0" />
			{/if}

			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={async () => {
					show = false;

					await showSettings.set(true);

					if ($mobile) {
						await tick();
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<Settings className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Settings')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={async () => {
					show = false;

					dispatch('show', 'archived-chat');

					if ($mobile) {
						await tick();

						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Archived Chats')}</div>
			</DropdownMenu.Item>

			{#if role === 'admin'}
				<DropdownMenu.Item
					as="a"
					href="/playground"
					class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition select-none"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<Code className="size-5" strokeWidth="1.5" />
					</div>
					<div class=" self-center truncate">{$i18n.t('Playground')}</div>
				</DropdownMenu.Item>
				<DropdownMenu.Item
					as="a"
					href="/admin"
					class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition select-none"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<UserGroup className="w-5 h-5" strokeWidth="1.5" />
					</div>
					<div class=" self-center truncate">{$i18n.t('Admin Panel')}</div>
				</DropdownMenu.Item>
			{/if}

			{#if help}
				<hr class=" border-gray-50/30 dark:border-gray-800/30 my-1 p-0" />

				<!-- {$i18n.t('Help')} -->

				{#if $user?.role === 'admin'}
					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex gap-3 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://docs.openwebui.com"
					>
						<QuestionMarkCircle className="size-5" />
						<div class="flex items-center">{$i18n.t('Documentation')}</div>
					</DropdownMenu.Item>

					<!-- Releases -->
					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex gap-3 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://github.com/open-webui/open-webui/releases"
					>
						<Map className="size-5" />
						<div class="flex items-center">{$i18n.t('Releases')}</div>
					</DropdownMenu.Item>
				{/if}

				<DropdownMenu.Item
					class="flex gap-3 items-center py-1.5 px-3 text-sm select-none w-full  hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition cursor-pointer"
					id="chat-share-button"
					on:click={async () => {
						show = false;
						showShortcuts.set(!$showShortcuts);

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<Keyboard className="size-5" />
					<div class="flex items-center">{$i18n.t('Keyboard shortcuts')}</div>
				</DropdownMenu.Item>
			{/if}

			<hr class=" border-gray-50/30 dark:border-gray-800/30 my-1 p-0" />

			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<SignOut className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Sign Out')}</div>
			</DropdownMenu.Item>

			{#if showActiveUsers && ($config?.features?.enable_public_active_users_count || role === 'admin') && usage}
				{#if usage?.user_count}
					<hr class=" border-gray-50/30 dark:border-gray-800/30 my-1 p-0" />

					<Tooltip
						content={usage?.model_ids && usage?.model_ids.length > 0
							? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
							: ''}
					>
						<div
							class="flex rounded-xl py-1 px-3 text-xs gap-2.5 items-center"
							on:mouseenter={() => {
								if ($config?.features?.enable_public_active_users_count || role === 'admin') {
									getUsageInfo();
								}
							}}
						>
							<div class=" flex items-center">
								<span class="relative flex size-2">
									<span
										class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
									/>
									<span class="relative inline-flex rounded-full size-2 bg-green-500" />
								</span>
							</div>

							<div class=" ">
								<span class="">
									{$i18n.t('Active Users')}:
								</span>
								<span class=" font-semibold">
									{usage?.user_count}
								</span>
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
