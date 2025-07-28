<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';
	import { changeLanguage, getLanguages } from '$lib/i18n';

	import { getUsage, getModels as _getModels } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';
	import { updateUserSettings } from '$lib/apis/users';

	import {
		config,
		showSettings,
		mobile,
		showSidebar,
		user,
		settings,
		models,
		theme
	} from '$lib/stores';

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
	import MaterialIcon from '$lib/components/common/MaterialIcon.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'max-w-[240px]';

	let showShortcuts = false;

	const dispatch = createEventDispatcher();

	let usage = null;

	let isOnNotification = false;
	let notificationEnabled = false;
	let isOnThemeToggle = true;
	let themeEnabled = false;
	// General
	let themes = ['dark', 'light'];
	let selectedTheme = 'light';
	const toggleNotification = async () => {
		const permission = await Notification.requestPermission();
		if (permission === 'granted') {
			notificationEnabled = !notificationEnabled;
			saveSettings({ notificationEnabled: notificationEnabled });
		} else {
			toast.error(
				$i18n.t(
					'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
				)
			);
		}
	};

	const saveSettings = async (updated) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		await updateUserSettings(localStorage.token, { ui: $settings });
	};
	const getModels = async () => {
		return await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
		);
	};
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

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark') {
			document.documentElement.style.setProperty('--color-gray-800', '#333');
			document.documentElement.style.setProperty('--color-gray-850', '#262626');
			document.documentElement.style.setProperty('--color-gray-900', '#171717');
			document.documentElement.style.setProperty('--color-gray-950', '#0d0d0d');
			document.documentElement.style.setProperty('--Schemes-Surface', '#36383B');
			document.documentElement.style.setProperty('--color-neutrals-800', '#fff');
		} else {
			document.documentElement.style = '';
		}

		themes
			.filter((e) => e !== themeToApply)
			.forEach((e) => {
				e.split(' ').forEach((e) => {
					document.documentElement.classList.remove(e);
				});
			});

		themeToApply.split(' ').forEach((e) => {
			document.documentElement.classList.add(e);
		});

		const metaThemeColor = document.querySelector('meta[name="theme-color"]');
		if (metaThemeColor) {
			if (_theme.includes('system')) {
				const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
					? 'dark'
					: 'light';
				console.log('Setting system meta theme color: ' + systemTheme);
				metaThemeColor.setAttribute('content', systemTheme === 'light' ? '#ffffff' : '#171717');
			} else {
				console.log('Setting meta theme color: ' + _theme);
				metaThemeColor.setAttribute(
					'content',
					_theme === 'dark'
						? '#171717'
						: _theme === 'oled-dark'
							? '#000000'
							: _theme === 'her'
								? '#983724'
								: '#ffffff'
				);
			}
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
		}

		console.log(_theme);
	};

	const themeChangeHandler = (_theme: string) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		applyTheme(_theme);
	};
</script>

<ShortcutsModal bind:show={showShortcuts} />

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
			class="w-full {className} rounded-[8px] z-50 bg-light-bg dark:border dark:border-gray-100 text-label-primary shadow-custom font-primary"
			sideOffset={1}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex justify-between items-center border-b border-gray-100 px-[16px] py-[11px] w-full transition cursor-pointer"
				on:click={() => changeLanguage(document.documentElement.lang === 'en-US' ? 'ar' : 'en-US')}
			>
				<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
					{$i18n.t('Switch to Arabic')}
				</div>
				<div class=" self-center {$mobile ? '' : 'mr-3'} ">
					<MaterialIcon name="translate" size="1.1rem" />
				</div>
			</button>
			{#if role === 'admin'}
			<div
				class="flex px-[16px] py-[11px] w-full items-center justify-between border-b border-gray-100"
			>
				<label class="flex items-center gap-[8px] text-[17px] leading-[22px]">
					{$i18n.t('Notifications')}</label
				>
				<label class="relative inline-flex items-center cursor-pointer">
					<input
						type="checkbox"
						bind:checked={isOnNotification}
						on:change={() => toggleNotification()}
						class="sr-only peer"
					/>
					<div
						class="w-[40px] h-[20px] {isOnNotification
							? 'bg-neutrals-green'
							: 'bg-neutrals-50'} rounded-full peer duration-300"
					>
						<div
							class=" flex items-center justify-center absolute {isOnNotification
								? 'left-[1px]'
								: 'right-[1px]'}  top-[1px] bg-neutrals-white w-[18px] h-[18px] rounded-full transition-transform duration-300 peer-checked:translate-x-5"
						></div>
					</div>
				</label>
			</div>
            {/if}
			<div
				class="flex px-[16px] py-[11px] w-full items-center justify-between border-b border-gray-100"
			>
				<label class="flex items-center gap-[8px] text-[17px] leading-[22px]">
					{$i18n.t('Theme')}</label
				>
				<label class="relative inline-flex items-center cursor-pointer">
					<input
						type="checkbox"
						bind:checked={isOnThemeToggle}
						on:change={() => themeChangeHandler(isOnThemeToggle ? 'light' : 'dark')}
						class="sr-only peer"
					/>
					<div
						class="w-[40px] h-[20px] {isOnThemeToggle
							? 'bg-neutrals-green'
							: 'bg-neutrals-50'} rounded-full peer duration-300"
					>
						<div
							class=" flex items-center justify-center absolute {isOnThemeToggle
								? 'left-[1px]'
								: 'right-[1px]'}  top-[1px] bg-neutrals-white w-[18px] h-[18px] rounded-full transition-transform duration-300 peer-checked:translate-x-5"
						></div>
					</div>
				</label>
			</div>
			{#if role === 'admin'}
				<button
					class="flex justify-between items-center border-b border-gray-100 px-[16px] py-[11px] w-full transition"
					on:click={async () => {
						await showSettings.set(true);
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
						{$i18n.t('Settings')}
					</div>
					<div class=" self-center mr-3">
						<Settings className="w-5 h-5" strokeWidth="1.5" />
					</div>
				</button>
			{/if}
			<button
				class="flex justify-between items-center border-b border-gray-100 px-[16px] py-[11px] w-full transition"
				on:click={() => {
					dispatch('show', 'archived-chat');
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
					{$i18n.t('Archived Chats')}
				</div>
				<div class=" self-center mr-3">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
			</button>

			{#if role === 'admin'}
				<button
					class="flex justify-between items-center border-b border-gray-100 px-[16px] py-[11px] w-full transition"
					on:click={() => {
						goto('/playground');
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
						{$i18n.t('Playground')}
					</div>
					<div class=" self-center mr-3">
						<Code className="size-5" strokeWidth="1.5" />
					</div>
				</button>

				<button
					class="flex justify-between items-center border-b border-gray-100 px-[16px] py-[11px] w-full transition"
					on:click={() => {
						goto('/admin');
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
						{$i18n.t('Admin Panel')}
					</div>
					<div class=" self-center mr-3">
						<UserGroup className="w-5 h-5" strokeWidth="1.5" />
					</div>
				</button>
			{/if}

			{#if help}
				<hr class=" border-gray-100 dark:border-gray-800 my-1 p-0" />

				<!-- {$i18n.t('Help')} -->
				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-neutrals-hover dark:hover:bg-gray-800 rounded-md transition"
					id="chat-share-button"
					on:click={() => {
						window.open('https://docs.openwebui.com', '_blank');
						show = false;
					}}
				>
					<QuestionMarkCircle className="size-5" />
					<div class="flex items-center gap-[8px] text-[17px] leading-[22px]">
						{$i18n.t('Documentation')}
					</div>
				</DropdownMenu.Item>

				<!-- Releases -->
				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-neutrals-hover dark:hover:bg-gray-800 rounded-md transition"
					id="menu-item-releases"
					on:click={() => {
						window.open('https://github.com/open-webui/open-webui/releases', '_blank');
						show = false;
					}}
				>
					<Map className="size-5" />
					<div class="flex items-center">{$i18n.t('Releases')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-neutrals-hover dark:hover:bg-gray-800 rounded-md transition"
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

			{#if role === 'admin'}
				<button
					class="flex px-[16px] justify-between items-center border-b border-gray-100 py-[11px] w-full transition"
					on:on:click={() => {
						goto('/playground');
					}}
				>
					<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
						{$i18n.t('Support')}
					</div>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="20"
							height="20"
							viewBox="0 0 20 20"
							fill="none"
						>
							<path
								d="M10 1.875C8.39303 1.875 6.82214 2.35152 5.486 3.24431C4.14985 4.1371 3.10844 5.40605 2.49348 6.8907C1.87852 8.37535 1.71762 10.009 2.03112 11.5851C2.34463 13.1612 3.11846 14.6089 4.25476 15.7452C5.39106 16.8815 6.8388 17.6554 8.4149 17.9689C9.99099 18.2824 11.6247 18.1215 13.1093 17.5065C14.594 16.8916 15.8629 15.8502 16.7557 14.514C17.6485 13.1779 18.125 11.607 18.125 10C18.1227 7.84581 17.266 5.78051 15.7427 4.25727C14.2195 2.73403 12.1542 1.87727 10 1.875ZM13.0547 12.1711C13.5069 11.5375 13.7499 10.7784 13.7499 10C13.7499 9.22156 13.5069 8.46254 13.0547 7.82891L15.2813 5.60313C16.311 6.83689 16.8751 8.39295 16.8751 10C16.8751 11.607 16.311 13.1631 15.2813 14.3969L13.0547 12.1711ZM7.5 10C7.5 9.50555 7.64663 9.0222 7.92133 8.61107C8.19603 8.19995 8.58648 7.87952 9.04329 7.6903C9.50011 7.50108 10.0028 7.45157 10.4877 7.54804C10.9727 7.6445 11.4181 7.8826 11.7678 8.23223C12.1174 8.58186 12.3555 9.02732 12.452 9.51227C12.5484 9.99723 12.4989 10.4999 12.3097 10.9567C12.1205 11.4135 11.8001 11.804 11.3889 12.0787C10.9778 12.3534 10.4945 12.5 10 12.5C9.33696 12.5 8.70108 12.2366 8.23224 11.7678C7.7634 11.2989 7.5 10.663 7.5 10ZM14.3969 4.71875L12.1711 6.94531C11.5375 6.49312 10.7784 6.25006 10 6.25006C9.22156 6.25006 8.46254 6.49312 7.82891 6.94531L5.60313 4.71875C6.83689 3.68898 8.39296 3.12492 10 3.12492C11.607 3.12492 13.1631 3.68898 14.3969 4.71875ZM4.71875 5.60313L6.94532 7.82891C6.49312 8.46254 6.25006 9.22156 6.25006 10C6.25006 10.7784 6.49312 11.5375 6.94532 12.1711L4.71875 14.3969C3.68899 13.1631 3.12493 11.607 3.12493 10C3.12493 8.39295 3.68899 6.83689 4.71875 5.60313ZM5.60313 15.2812L7.82891 13.0547C8.46254 13.5069 9.22156 13.7499 10 13.7499C10.7784 13.7499 11.5375 13.5069 12.1711 13.0547L14.3969 15.2812C13.1631 16.311 11.607 16.8751 10 16.8751C8.39296 16.8751 6.83689 16.311 5.60313 15.2812Z"
								fill="#36383B"
							/>
						</svg>
					</div>
				</button>
			{/if}

			<button
				class="flex px-[16px] justify-between items-center border-b border-gray-100 py-[11px] w-full transition"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<div class=" self-center truncate gap-[8px] text-[17px] leading-[22px]">
					{$i18n.t('Sign Out')}
				</div>
				<div class=" self-center mr-3">
					<SignOut className="w-5 h-5" strokeWidth="1.5" />
				</div>
			</button>

			<!--{#if usage && role === 'admin'}
				{#if usage?.user_ids?.length > 0}
					<hr class=" border-gray-100 dark:border-gray-800 my-1 p-0" />

					<Tooltip
						content={usage?.model_ids && usage?.model_ids.length > 0
							? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
							: ''}
					>
						<div
							class="flex rounded-md py-1 px-3 text-xs gap-2.5 items-center"
							on:mouseenter={() => {
								getUsageInfo();
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
									{usage?.user_ids?.length}
								</span>
							</div>
						</div>
					</Tooltip>
				{/if}
			{/if}-->

			<!-- <DropdownMenu.Item class="flex items-center py-1.5 px-3 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
