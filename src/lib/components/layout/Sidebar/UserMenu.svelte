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
	import Support from '$lib/components/icons/Support.svelte';

    const i18n = getContext('i18n');

    export let show = false;
    export let role = '';
    export let help = false;
    export let className = 'max-w-[240px]';

    let showShortcuts = false;
    let currentLanguage = 'en-US';

    const dispatch = createEventDispatcher();

    // Track language state for UI updates
    let isLanguageSwitching = false;
    
    // Reactive statement to track current language
    $: if ($i18n?.language) {
        currentLanguage = $i18n.language;
    }

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
                'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
            );
        }
    };

    const saveSettings = async (updated: any) => {
        console.log(updated);
        await settings.set({ ...$settings, ...updated });
        await models.set(await getModels());
        await updateUserSettings(localStorage.token, { ui: $settings });
    };
    
    const getModels = async () => {
        return await _getModels(
            localStorage.token,
            $config?.features?.enable_direct_connections && ($settings?.connections ?? null)
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

   
    const handleLanguageSwitch = async () => {
        if (isLanguageSwitching) return; // Prevent double clicks
        
        try {
            isLanguageSwitching = true;
            const currentLang = currentLanguage || 'en-US';
            const newLang = currentLang === 'en-US' ? 'ar' : 'en-US';
            
            // Update local state immediately for instant UI feedback
            currentLanguage = newLang;
            
           
            localStorage.setItem('locale', newLang);
            
            
            changeLanguage(newLang);
            
            // Update user settings on server if logged in
            if (localStorage.token) {
                await updateUserSettings(localStorage.token, { 
                    ui: { ...$settings, locale: newLang } 
                });
            }
            
            // Small delay to ensure everything updates properly
            await new Promise(resolve => setTimeout(resolve, 150));
        } catch (error) {
            console.error('Language switching error:', error);
            // Revert language on error
            currentLanguage = currentLanguage === 'en-US' ? 'ar' : 'en-US';
        } finally {
            isLanguageSwitching = false;
        }
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
			class="w-full {className} rounded-[8px] z-50 bg-light-bg dark:border dark:border-gray-800 text-label-primary shadow-custom font-primary"
			sideOffset={1}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex justify-between items-center border-b border-gray-100 dark:border-transparent px-[16px] py-[11px] w-full transition cursor-pointer hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
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
				class="flex px-[16px] py-[11px] w-full items-center justify-between border-b border-gray-100 dark:border-transparent hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
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
							: 'bg-neutrals-50 dark:bg-gray-500'} rounded-full peer duration-300"
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
                class="flex px-[16px] py-[11px] w-full items-center justify-between border-b border-gray-100 dark:border-transparent hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
            >
                <label for="theme-toggle" class="flex items-center gap-[8px] text-[17px] leading-[22px]">
                    {$i18n?.t?.('Theme') || 'Theme'}
                </label>
                <label class="relative inline-flex items-center cursor-pointer">
                    <input
                        id="theme-toggle"
                        type="checkbox"
                        bind:checked={isOnThemeToggle}
                        on:change={() => themeChangeHandler(isOnThemeToggle ? 'light' : 'dark')}
                        class="sr-only peer"
                    />
                    <div
                        class="w-[40px] h-[20px] {isOnThemeToggle
                            ? 'bg-neutrals-green'
                            : 'bg-neutrals-50 dark:bg-gray-500'} rounded-full peer duration-300"
                    >
                        <div
                            class="flex items-center justify-center absolute {isOnThemeToggle
                                ? 'left-[1px]'
                                : 'right-[1px]'} top-[1px] bg-neutrals-white w-[18px] h-[18px] rounded-full transition-transform duration-300 peer-checked:translate-x-5"
                        ></div>
                    </div>
                </label>
            </div>
            
            {#if role === 'admin'}
                <button
                    class="flex justify-between items-center border-b border-gray-100 dark:border-transparent px-[16px] py-[11px] w-full transition hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
                    on:click={async () => {
                        await showSettings.set(true);
                        show = false;

                        if ($mobile) {
                            showSidebar.set(false);
                        }
                    }}
                >
                    <div class="self-center truncate gap-[8px] text-[17px] leading-[22px]">
                        {$i18n?.t?.('Settings') || 'Settings'}
                    </div>
                    <div class="self-center mr-3">
                        <Settings className="w-5 h-5" />
                    </div>
                </button>
            {/if}
            
            <button
                class="flex justify-between items-center border-b border-gray-100 dark:border-transparent px-[16px] py-[11px] w-full transition hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
                on:click={() => {
                    dispatch('show', 'archived-chat');
                    show = false;

                    if ($mobile) {
                        showSidebar.set(false);
                    }
                }}
            >
                <div class="self-center truncate gap-[8px] text-[17px] leading-[22px]">
                    {$i18n?.t?.('Archived Chats') || 'Archived Chats'}
                </div>
                <div class="self-center mr-3">
                    <ArchiveBox className="size-5" />
                </div>
            </button>

            {#if role === 'admin'}
                <button
                    class="flex justify-between items-center border-b border-gray-100 dark:border-transparent px-[16px] py-[11px] w-full transition hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
                    on:click={() => {
                        goto('/playground');
                        show = false;

                        if ($mobile) {
                            showSidebar.set(false);
                        }
                    }}
                >
                    <div class="self-center truncate gap-[8px] text-[17px] leading-[22px]">
                        {$i18n?.t?.('Playground') || 'Playground'}
                    </div>
                    <div class="self-center mr-3">
                        <Code className="size-5" />
                    </div>
                </button>

                <button
                    class="flex justify-between items-center border-b border-gray-100 dark:border-transparent px-[16px] py-[11px] w-full transition hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
                    on:click={() => {
                        goto('/admin');
                        show = false;

                        if ($mobile) {
                            showSidebar.set(false);
                        }
                    }}
                >
                    <div class="self-center truncate gap-[8px] text-[17px] leading-[22px]">
                        {$i18n?.t?.('Admin Panel') || 'Admin Panel'}
                    </div>
                    <div class="self-center mr-3">
                        <UserGroup className="w-5 h-5" />
                    </div>
                </button>
            {/if}

            {#if help}
                <hr class="border-gray-100 dark:border-gray-800 my-1 p-0" />

                <DropdownMenu.Item
                    class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gradient-bg-2 dark:hover:bg-gray-850 rounded-md transition"
                    id="documentation-link"
                    on:click={() => {
                        window.open('https://docs.openwebui.com', '_blank');
                        show = false;
                    }}
                >
                    <QuestionMarkCircle className="size-5" />
                    <div class="flex items-center gap-[8px] text-[17px] leading-[22px]">
                        {$i18n?.t?.('Documentation') || 'Documentation'}
                    </div>
                </DropdownMenu.Item>

                <DropdownMenu.Item
                    class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gradient-bg-2 dark:hover:bg-gray-850 rounded-md transition"
                    id="releases-link"
                    on:click={() => {
                        window.open('https://github.com/open-webui/open-webui/releases', '_blank');
                        show = false;
                    }}
                >
                    <Map className="size-5" />
                    <div class="flex items-center">
                        {$i18n?.t?.('Releases') || 'Releases'}
                    </div>
                </DropdownMenu.Item>

                <DropdownMenu.Item
                    class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gradient-bg-2 dark:hover:bg-gray-850 rounded-md transition"
                    id="shortcuts-button"
                    on:click={() => {
                        showShortcuts = !showShortcuts;
                        show = false;
                    }}
                >
                    <Keyboard className="size-5" />
                    <div class="flex items-center">
                        {$i18n?.t?.('Keyboard shortcuts') || 'Keyboard shortcuts'}
                    </div>
                </DropdownMenu.Item>
            {/if}

            {#if role === 'admin'}
                <button
                    class="flex px-[16px] justify-between items-center border-b border-gray-100 dark:border-transparent py-[11px] w-full transition hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
                    on:click={() => {
                        goto('/playground');
                    }}
                >
                    <div class="self-center truncate gap-[8px] text-[17px] leading-[22px]">
                        {$i18n?.t?.('Support') || 'Support'}
                    </div>
                    <div class="self-center mr-3">
                        <Support className="w-5 h-5" />
                    </div>
                </button>
            {/if}

            <button
                class="flex px-[16px] justify-between items-center border-b border-gray-100 dark:border-transparent py-[11px] w-full transition hover:bg-gradient-bg-2 dark:hover:bg-gray-850"
                on:click={async () => {
                    const res = await userSignOut();
                    user.set(null);
                    localStorage.removeItem('token');

                    if (res?.redirect_url) {
                        location.href = res.redirect_url;
                    } else {
                        location.href = '/auth';
                    }
                    show = false;
                }}
            >
                <div class="self-center truncate gap-[8px] text-[17px] leading-[22px]">
                    {$i18n?.t?.('Sign Out') || 'Sign Out'}
                </div>
                <div class="self-center mr-3">
                    <SignOut className="w-5 h-5" />
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
