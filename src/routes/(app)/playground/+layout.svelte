<script lang="ts">
    import { onMount, getContext } from 'svelte';
    import { WEBUI_NAME, showSidebar, functions, user } from '$lib/stores'; // user importiert
    import MenuLines from '$lib/components/icons/MenuLines.svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation'; // goto importiert
    import Spinner from '$lib/components/common/Spinner.svelte'; // Spinner importiert

    const i18n = getContext('i18n');

    let accessChecked = false;
    let hasAccess = false;

    // Zugriff prüfen, wenn sich der User-Store ändert
    user.subscribe(currentUser => {
        if (currentUser !== null && currentUser !== undefined) {
            hasAccess = (currentUser?.role === 'admin') || (currentUser?.permissions?.features?.playground_access ?? false);
            accessChecked = true;
            if (!hasAccess) {
                goto('/'); // Umleiten, wenn kein Zugriff
            }
        } else if (currentUser === null) {
             accessChecked = true;
             hasAccess = false;
             goto('/auth'); // Umleiten, wenn ausgeloggt
        }
    });

    // Fallback-Prüfung beim Mounten
    onMount(() => {
         if (!accessChecked && $user !== null && $user !== undefined) {
             hasAccess = ($user?.role === 'admin') || ($user?.permissions?.features?.playground_access ?? false);
             accessChecked = true;
             if (!hasAccess) {
                 goto('/');
             }
         } else if ($user === null) {
             goto('/auth');
         }
    });
</script>

<svelte:head>
    <title>
        {$i18n.t('Playground')} • {$WEBUI_NAME}
    </title>
</svelte:head>

{#if !accessChecked}
    <div class="flex h-full w-full items-center justify-center">
        <Spinner />
    </div>
{:else if hasAccess}
    <div
        class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
            ? 'md:max-w-[calc(100%-260px)]'
            : ''} max-w-full"
    >
        <nav class="   px-2.5 pt-1 backdrop-blur-xl w-full drag-region">
            <div class=" flex items-center">
                <div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
                    <button
                        id="sidebar-toggle-button"
                        class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
                        on:click={() => {
                            showSidebar.set(!$showSidebar);
                        }}
                        aria-label="Toggle Sidebar"
                    >
                        <div class=" m-auto self-center">
                            <MenuLines />
                        </div>
                    </button>
                </div>

                <div class=" flex w-full">
                    <div
                        class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1"
                    >
                        <a
                            class="min-w-fit rounded-full p-1.5 {['/playground', '/playground/'].includes(
                                $page.url.pathname
                            )
                                ? ''
                                : 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
                            href="/playground">{$i18n.t('Chat')}</a
                        >

                        <a
                            class="min-w-fit rounded-full p-1.5 {$page.url.pathname.includes(
                                '/playground/completions'
                            )
                                ? ''
                                : 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
                            href="/playground/completions">{$i18n.t('Completions')}</a
                        >
                    </div>
                </div>
            </div>
        </nav>

        <div class=" flex-1 max-h-full overflow-y-auto">
            <slot />
        </div>
    </div>
 {:else}
     <div class="flex h-full w-full items-center justify-center">
        <p>Access Denied.</p>
     </div>
{/if}
