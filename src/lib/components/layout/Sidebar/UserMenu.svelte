<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';

	import { showSettings, mobile, showSidebar, showShortcuts, user, theme } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import TooltipButton from '$lib/components/common/TooltipButton.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import Code from '$lib/components/icons/Code.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'w-[160px]';

	const dispatch = createEventDispatcher();

	let usage = null;
	let showThemeSubmenu = false;

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

	$: if (show) {
		getUsageInfo();
	}

	// Close theme submenu when main menu closes
	$: if (!show) {
		showThemeSubmenu = false;
	}

	const applyTheme = (_theme) => {
		let themeToApply = _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark') {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
		}
	};

	const themeChangeHandler = (_theme) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		applyTheme(_theme);
		showThemeSubmenu = false;
	};

	const getThemeLabel = (themeValue) => {
		switch (themeValue) {
			case 'system':
				return '시스템 기본';
			case 'light':
				return '라이트 모드';
			case 'dark':
				return '다크 모드';
			default:
				return '다크 모드';
		}
	};
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
			class="{className} flex flex-col items-start p-5 gap-2 bg-gray-50 dark:bg-[rgba(113,122,143,0.3)] shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px] rounded-[20px] rounded-bl-[4px] z-50 text-gray-900 dark:text-white text-sm border-0"
			sideOffset={4}
			side="top"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<!-- Theme Toggle Button -->
			<div class="w-full relative">
				<TooltipButton
					label={getThemeLabel($theme)}
					variant="toggle"
					on:click={() => {
						showThemeSubmenu = !showThemeSubmenu;
					}}
				>
					<svg slot="icon" width="16" height="16" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path
							d="M11.0002 3.66667C7.31833 3.66667 4.3335 6.6515 4.3335 10.3333C4.3335 14.0152 7.31833 17 11.0002 17C14.682 17 17.6668 14.0152 17.6668 10.3333C17.6668 9.99617 17.6442 9.66417 17.6002 9.33883C17.0168 10.2478 16.0127 10.8517 14.8613 10.8517C13.0738 10.8517 11.6252 9.403 11.6252 7.6155C11.6252 6.464 12.2292 5.45983 13.1382 4.87633C12.8128 4.83233 12.4808 4.80967 12.1437 4.80967"
							class="stroke-gray-900 dark:stroke-[#FDFEFE]"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>
				</TooltipButton>

				<!-- Theme Submenu -->
				{#if showThemeSubmenu}
					<div
						class="absolute left-0 bottom-full mb-2 w-full flex flex-col p-2 gap-1 bg-gray-50 dark:bg-gray-800 rounded-md shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-md dark:backdrop-blur-md z-50"
						transition:fade={{ duration: 100 }}
					>
						<button
						class="flex items-center gap-2 w-full px-2 py-1.5 rounded-lg text-sm text-left hover:bg-white/20 transition {$theme === 'system' ? 'bg-white/20' : ''}"
						on:click={() => themeChangeHandler('system')}
						>
							<svg width="16" height="16" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<rect x="3" y="4" width="14" height="10" rx="1" class="stroke-current" stroke-width="1.5"/>
								<path d="M7 17H13" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M10 14V17" class="stroke-current" stroke-width="1.5"/>
							</svg>
							<span class="text-gray-900 dark:text-[#FDFEFE]">시스템 기본</span>
						</button>
						<button
						class="flex items-center gap-2 w-full px-2 py-1.5 rounded-lg text-sm text-left hover:bg-white/20 transition {$theme === 'light' ? 'bg-white/20' : ''}"
						on:click={() => themeChangeHandler('light')}
						>
							<svg width="16" height="16" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<circle cx="10" cy="10" r="4" class="stroke-current" stroke-width="1.5"/>
								<path d="M10 2V4" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M10 16V18" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M18 10H16" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M4 10H2" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M15.66 4.34L14.24 5.76" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M5.76 14.24L4.34 15.66" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M15.66 15.66L14.24 14.24" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
								<path d="M5.76 5.76L4.34 4.34" class="stroke-current" stroke-width="1.5" stroke-linecap="round"/>
							</svg>
							<span class="text-gray-900 dark:text-[#FDFEFE]">라이트 모드</span>
						</button>
						<button
						class="flex items-center gap-2 w-full px-2 py-1.5 rounded-lg text-sm text-left hover:bg-white/20 transition {$theme === 'dark' ? 'bg-white/20' : ''}"
						on:click={() => themeChangeHandler('dark')}
						>
							<svg width="16" height="16" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path
									d="M10 3C6.68629 3 4 5.68629 4 9C4 12.3137 6.68629 15 10 15C13.3137 15 16 12.3137 16 9C16 8.7 15.98 8.4 15.94 8.1C15.4 8.9 14.5 9.4 13.5 9.4C11.84 9.4 10.5 8.06 10.5 6.4C10.5 5.4 11 4.5 11.8 3.96C11.54 3.92 11.27 3.9 11 3.9"
									class="stroke-current"
									stroke-width="1.5"
									stroke-linecap="round"
									stroke-linejoin="round"
								/>
							</svg>
							<span class="text-gray-900 dark:text-[#FDFEFE]">다크 모드</span>
						</button>
					</div>
				{/if}
			</div>

			<!-- Help Button -->
			<TooltipButton
				label="도움말"
				on:click={async () => {
					show = false;
					window.open('https://docs.openwebui.com', '_blank');
					if ($mobile) {
						await tick();
						showSidebar.set(false);
					}
				}}
			>
				<svg slot="icon" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path
						d="M10 18C14.4183 18 18 14.4183 18 10C18 5.58172 14.4183 2 10 2C5.58172 2 2 5.58172 2 10C2 14.4183 5.58172 18 10 18Z"
						class="stroke-current"
						stroke-width="1.5"
					/>
					<path
						d="M10 14V14.01"
						class="stroke-current"
						stroke-width="2"
						stroke-linecap="round"
					/>
					<path
						d="M10 11C10 9 11.5 8.5 12 8C12.5 7.5 12.5 6 11.5 5.5C10.5 5 9.5 5.5 9 6"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
					/>
				</svg>
			</TooltipButton>

			<!-- Logout Button -->
			<TooltipButton
				label="로그아웃"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<svg slot="icon" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path
						d="M7.5 17.5H4.16667C3.72464 17.5 3.30072 17.3244 2.98816 17.0118C2.67559 16.6993 2.5 16.2754 2.5 15.8333V4.16667C2.5 3.72464 2.67559 3.30072 2.98816 2.98816C3.30072 2.67559 3.72464 2.5 4.16667 2.5H7.5"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
					<path
						d="M13.3335 14.1667L17.5002 10L13.3335 5.83333"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
					<path
						d="M17.5 10H7.5"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
				</svg>
			</TooltipButton>

			<!-- Admin Only Section -->
			{#if role === 'admin'}
				<hr class="border-white/20 my-1 p-0 w-full" />

				<DropdownMenu.Item
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-caption"
					on:click={async () => {
						show = false;

						await showSettings.set(true);

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<Settings className="w-5 h-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Settings')}</span>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-sm"
					on:click={async () => {
						show = false;

						dispatch('show', 'archived-chat');

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<ArchiveBox className="size-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Archived Chats')}</span>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					as="a"
					href="/playground"
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none text-sm"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<Code className="size-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Playground')}</span>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					as="a"
					href="/admin"
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none text-sm"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<UserGroup className="w-5 h-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Admin Panel')}</span>
				</DropdownMenu.Item>

				{#if help}
					<hr class="border-white/20 my-1 p-0 w-full" />

					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none cursor-pointer text-sm"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://docs.openwebui.com"
					>
						<QuestionMarkCircle className="size-5" />
						<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Documentation')}</span>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none cursor-pointer text-sm"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://github.com/open-webui/open-webui/releases"
					>
						<Map className="size-5" />
						<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Releases')}</span>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none cursor-pointer text-sm"
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
						<span class="text-gray-900 dark:text-[#FDFEFE]">{$i18n.t('Keyboard shortcuts')}</span>
					</DropdownMenu.Item>
				{/if}

				{#if usage}
					{#if usage?.user_ids?.length > 0}
						<hr class="border-white/20 my-1 p-0 w-full" />

						<Tooltip
							content={usage?.model_ids && usage?.model_ids.length > 0
								? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
								: ''}
						>
							<div
								class="flex rounded-xl py-1 px-3 text-sm gap-2.5 items-center"
								on:mouseenter={() => {
									getUsageInfo();
								}}
							>
								<div class="flex items-center">
									<span class="relative flex size-2">
										<span
											class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
										/>
										<span class="relative inline-flex rounded-full size-2 bg-green-500" />
									</span>
								</div>

								<div>
									<span class="text-gray-900 dark:text-[#FDFEFE]">
										{$i18n.t('Active Users')}:
									</span>
									<span class="font-semibold text-gray-900 dark:text-[#FDFEFE]">
										{usage?.user_ids?.length}
									</span>
								</div>
							</div>
						</Tooltip>
					{/if}
				{/if}
			{/if}
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
