<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import { showSettings, activeUserIds, USAGE_POOL, mobile, showSidebar, user } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { userSignOut } from '$lib/apis/auths';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'max-w-[240px]';

	let showShortcuts = false;

	const dispatch = createEventDispatcher();
</script>

<ShortcutsModal bind:show={showShortcuts} />

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
			class="w-full {className} text-sm rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary"
			sideOffset={4}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					await showSettings.set(true);
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="w-5 h-5"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
						/>
					</svg>
				</div>
				<div class=" self-center truncate">{$i18n.t('Settings')}</div>
			</button>

			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					dispatch('show', 'archived-chat');
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Archived Chats')}</div>
			</button>

			{#if role === 'admin'}
				<a
					class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					href="/playground"
					on:click={() => {
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M14.25 9.75 16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z"
							/>
						</svg>
					</div>
					<div class=" self-center truncate">{$i18n.t('Playground')}</div>
				</a>

				<a
					class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					href="/admin"
					on:click={() => {
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</div>
					<div class=" self-center truncate">{$i18n.t('Admin Panel')}</div>
				</a>
			{/if}

			{#if help}
				<hr class=" border-gray-100 dark:border-gray-800 my-1 p-0" />

				<!-- {$i18n.t('Help')} -->
				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					id="chat-share-button"
					on:click={() => {
						window.open('https://docs.openwebui.com', '_blank');
					}}
				>
					<QuestionMarkCircle className="size-5" />
					<div class="flex items-center">{$i18n.t('Documentation')}</div>
				</DropdownMenu.Item>

				<!-- Releases -->
				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					id="menu-item-releases"
					on:click={() => {
						window.open('https://github.com/open-webui/open-webui/releases', '_blank');
					}}
				>
					<Map className="size-5" />
					<div class="flex items-center">{$i18n.t('Releases')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					id="chat-share-button"
					on:click={() => {
						showShortcuts = !showShortcuts;
						show = false;
					}}
				>
					<Keyboard className="size-5" />
					<div class="flex items-center">{$i18n.t('Keyboard shortcuts')}</div>
				</DropdownMenu.Item>
			{/if}

			<hr class=" border-gray-100 dark:border-gray-800 my-1 p-0" />

			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-5 h-5"
					>
						<path
							fill-rule="evenodd"
							d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z"
							clip-rule="evenodd"
						/>
						<path
							fill-rule="evenodd"
							d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center truncate">{$i18n.t('Sign Out')}</div>
			</button>

			{#if $activeUserIds?.length > 0}
				<hr class=" border-gray-100 dark:border-gray-800 my-1 p-0" />

				<Tooltip
					content={$USAGE_POOL && $USAGE_POOL.length > 0
						? `${$i18n.t('Running')}: ${$USAGE_POOL.join(', ')} ✨`
						: ''}
				>
					<div class="flex rounded-md py-1 px-3 text-xs gap-2.5 items-center">
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
								{$activeUserIds?.length}
							</span>
						</div>
					</div>
				</Tooltip>
			{/if}

			<!-- <DropdownMenu.Item class="flex items-center py-1.5 px-3 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
