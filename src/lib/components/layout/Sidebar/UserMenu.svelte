<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';
	import { getActiveUsers, getUserById } from '$lib/apis/users';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { showSettings, mobile, showSidebar, showShortcuts, user } from '$lib/stores';

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
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();

	type ActiveUserInfo = {
		id: string;
		name?: string | null;
		email?: string | null;
		profile_image_url?: string | null;
	};

	let usage = null;
	let showActiveUsersList = false;
	let activeUsers: ActiveUserInfo[] = [];
	let loadingActiveUsers = false;
	let activeUsersError: string | null = null;
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

	const loadActiveUsers = async () => {
		loadingActiveUsers = true;
		activeUsersError = null;
		activeUsers = [];

		try {
			const res = await getActiveUsers(localStorage.token);
			const userIds = res?.user_ids ?? [];

			if (userIds.length > 0) {
				const details = await Promise.all(
					userIds.map(async (id) => {
						const info = await getUserById(localStorage.token, id).catch((error) => {
							console.error('Error fetching user info:', error);
							return null;
						});

						if (!info) {
							return null;
						}

						const {
							id: infoId,
							name = null,
							email = null,
							profile_image_url = null
						} = info as ActiveUserInfo;

						return {
							id: infoId ?? id,
							name,
							email,
							profile_image_url
						} satisfies ActiveUserInfo;
					})
				);

				activeUsers = details.filter((entry): entry is ActiveUserInfo => Boolean(entry));
			} else {
				activeUsers = [];
			}
		} catch (error) {
			console.error('Error loading active users:', error);
			activeUsersError = typeof error === 'string' ? error : error?.detail ?? `${error}`;
		} finally {
			loadingActiveUsers = false;
		}
	};

	$: if (show) {
		getUsageInfo();
	} else {
		showActiveUsersList = false;
	}
</script>

<ShortcutsModal bind:show={$showShortcuts} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className}  rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg text-sm"
			sideOffset={4}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
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
				<hr class=" border-gray-50 dark:border-gray-800 my-1 p-0" />

				<!-- {$i18n.t('Help')} -->

				{#if $user?.role === 'admin'}
					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition"
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
						class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition"
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
					class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full  hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition cursor-pointer"
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

			<hr class=" border-gray-50 dark:border-gray-800 my-1 p-0" />

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

			{#if usage}
				{#if usage?.user_ids?.length > 0}
					<hr class=" border-gray-50 dark:border-gray-800 my-1 p-0" />

					<Tooltip
						content={usage?.model_ids && usage?.model_ids.length > 0
							? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
							: ''}
					>
						<button
							type="button"
							class="flex w-full rounded-xl py-1 px-3 text-xs gap-2.5 items-center transition hover:bg-gray-50 dark:hover:bg-gray-800"
							on:mouseenter={() => {
								getUsageInfo();
							}}
							on:click={async () => {
								showActiveUsersList = !showActiveUsersList;
								if (showActiveUsersList) {
									await loadActiveUsers();
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

							<div class="flex items-center gap-1">
								<span class="">
									{$i18n.t('Active Users')}:
								</span>
								<span class=" font-semibold">
									{usage?.user_ids?.length ?? 0}
								</span>
							</div>

							<div class="ml-auto text-gray-400">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									class="size-3.5 transition-transform {showActiveUsersList ? 'rotate-180' : ''}"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6" />
								</svg>
							</div>
						</button>
					</Tooltip>

					{#if showActiveUsersList}
						<div class="mt-1 max-h-56 overflow-y-auto rounded-xl bg-gray-50 dark:bg-gray-900/60 px-3 py-2 text-left">
							{#if loadingActiveUsers}
								<div class="flex items-center gap-2 py-2 text-gray-500 dark:text-gray-300">
									<Spinner className="size-4" />
									<span>{$i18n.t('Loading...')}</span>
								</div>
							{:else if activeUsersError}
								<div class="py-2 text-sm text-red-500">{activeUsersError}</div>
							{:else if activeUsers.length > 0}
								<ul class="space-y-1">
									{#each activeUsers as activeUser}
										<li class="flex items-center gap-2 rounded-lg bg-white dark:bg-gray-800 px-2 py-1">
											<img
												src={activeUser.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
												alt={activeUser.name ?? activeUser.email ?? activeUser.id}
												class="size-7 rounded-full object-cover"
												draggable="false"
											/>
											<div class="flex flex-col">
												<span class="text-sm font-medium text-gray-700 dark:text-gray-200">
													{activeUser.name ?? activeUser.email ?? activeUser.id}
												</span>
												{#if activeUser.email && activeUser.name}
													<span class="text-[11px] text-gray-500 dark:text-gray-400">{activeUser.email}</span>
												{/if}
											</div>
										</li>
									{/each}
								</ul>
							{:else}
								<div class="py-2 text-sm text-gray-500 dark:text-gray-300">
									{$i18n.t('No results found')}
								</div>
							{/if}
						</div>
					{/if}
				{/if}
			{/if}

			<!-- <DropdownMenu.Item class="flex items-center py-1.5 px-3 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
