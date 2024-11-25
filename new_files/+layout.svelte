<script lang="ts">
    import { io } from 'socket.io-client';
    import { spring } from 'svelte/motion';
    import '$lib/styles/fonts.css';
    import '$lib/styles/style.css';
    import gsap from 'gsap';
    import ScrollTrigger from 'gsap/ScrollTrigger';

    import { onMount, setContext } from 'svelte';
    import {
        config,
        user,
        theme,
        WEBUI_NAME,
        mobile,
        socket,
        activeUserCount,
        USAGE_POOL
    } from '$lib/stores';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { Toaster } from 'svelte-sonner';

    import { getBackendConfig } from '$lib/apis';
    import { getSessionUser } from '$lib/apis/auths';

    import '../tailwind.css';
    import '../app.css';
    import 'tippy.js/dist/tippy.css';

    import { WEBUI_BASE_URL } from '$lib/constants';
    import { currentLang, t, createMockI18n } from '$lib/landing/translations';
    import { initI18n } from '$lib/i18n';
    import i18n, { isLoading } from '$lib/i18n';

    // Initialize i18n first thing
    setContext('i18n', $page.url.pathname === '/landing' ? createMockI18n() : i18n);
    initI18n().then(() => i18nReady = true);

    let appReady = false;
    let configReady = false;
    let i18nReady = false;

    const BREAKPOINT = 768;
    const publicPaths = ['/landing', '/auth'];

    let isInitializing = true;
    let isLandingPage = $page.url.pathname === '/landing';

    // Function to wait for i18n to initialize
    const waitForI18n = async () => {
        let attempts = 0;
        const maxAttempts = 10;
        while (!i18n.isInitialized && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            attempts++;
        }
        return i18n.isInitialized;
    };

    const onResize = () => {
        mobile.set(window.innerWidth < BREAKPOINT);
    };

    const setupSocket = () => {
        const _socket = io(WEBUI_BASE_URL || '', {
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            randomizationFactor: 0.5,
            path: '/ws/socket.io',
            auth: { token: localStorage.token }
        });

        socket.set(_socket);

        _socket.on('connect_error', (err) => {
            console.log('connect_error', err);
        });

        _socket.on('connect', () => {
            console.log('connected', _socket.id);
        });

        _socket.on('user-count', (data) => {
            console.log('user-count', data);
            activeUserCount.set(data.count);
        });

        _socket.on('usage', (data) => {
            console.log('usage', data);
            USAGE_POOL.set(data['models']);
        });
    };

    onMount(() => {
        // Register GSAP plugins
        gsap.registerPlugin(ScrollTrigger);

        // Watch for page changes (no i18n initialization needed)
        const unsubscribe = page.subscribe(($page) => {
            isLandingPage = $page.url.pathname === '/landing';
        });

        if (isLandingPage) {
            document.getElementById('splash-screen')?.remove();
            isInitializing = false;
            WEBUI_NAME.set('Cicero');
            const savedLang = localStorage.getItem('preferredLanguage');
            if (savedLang) {
                currentLang.set(savedLang);
            }
            appReady = true;
            configReady = true;
            return unsubscribe;
        }

        const initApp = async () => {
            try {
                // Handle auth first
                const sessionUser = localStorage.token 
                    ? await getSessionUser(localStorage.token).catch(() => null) 
                    : null;

                if (sessionUser) {
                    await user.set(sessionUser);
                    
                    // Then get config after we have valid session
                    const backendConfig = await getBackendConfig();
                    if (backendConfig) {
                        await config.set(backendConfig);
                        await WEBUI_NAME.set(backendConfig.name);
                        configReady = true;
                        setupSocket();

                        // Set app ready before navigation
                        isInitializing = false;
                        appReady = true;
                        document.getElementById('splash-screen')?.remove();

                        // Handle theme and mobile state
                        theme.set(localStorage.theme || '');
                        mobile.set(window.innerWidth < BREAKPOINT);
                        window.addEventListener('resize', onResize);

                        // Navigate after everything is ready
                        if ($page.url.pathname === '/' || $page.url.pathname === '/landing') {
                            await goto('/workspace', { replaceState: true });
                        }
                    } else {
                        if (!publicPaths.includes($page.url.pathname)) {
                            window.location.href = '/error';
                        }
                    }
                } else {
                    if (localStorage.token) {
                        localStorage.removeItem('token');
                    }
                    
                    // Set states before redirecting
                    isInitializing = false;
                    appReady = true;
                    document.getElementById('splash-screen')?.remove();

                    if (!publicPaths.includes($page.url.pathname)) {
                        window.location.href = '/landing';
                    }
                }
            } catch (error) {
                console.error('Error during initialization:', error);
                if (!publicPaths.includes($page.url.pathname)) {
                    window.location.href = '/error';
                }
            }
        };

        initApp();
        return unsubscribe;
    });
</script>

{#if !appReady}
    <div class="flex h-screen w-screen items-center justify-center bg-white dark:bg-gray-900">
        <div class="flex flex-col items-center gap-4">
            <div class="loading loading-spinner loading-lg"></div>
            <div class="text-lg">
                Loading
                {#if !isLandingPage && !i18nReady}
                    ... (Initializing translations)
                {/if}
            </div>
        </div>
    </div>
{:else}
    <slot />
{/if}

{#if $page.url.pathname !== '/landing'}
    <Toaster
        theme={$theme === 'dark' ? 'dark' : 'light'}
        position="bottom-center"
        expand={false}
        richColors
    />
{/if}