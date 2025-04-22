<script lang="ts">
    import { sessionExpired } from '$lib/stores';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { WEBUI_BASE_URL } from '$lib/constants';
    import { getContext, onMount, onDestroy } from 'svelte';
    import { fade } from 'svelte/transition';

    const i18n = getContext('i18n');

    let isOpen = false;
    const unsubscribe = sessionExpired.subscribe((value) => { // Store unsubscribe speichern
        isOpen = value;
    if (typeof document !== 'undefined') {
      document.body.style.overflow = value ? 'hidden' : '';
    }
    });

  onDestroy(() => {
    unsubscribe();
    if (typeof document !== 'undefined') {
      document.body.style.overflow = '';
    }
  });

    function redirectToLogin() {
        sessionExpired.set(false);
        const currentUrl = `${$page.url.pathname}${$page.url.search}`;
        const encodedUrl = encodeURIComponent(currentUrl);
        goto(`${WEBUI_BASE_URL}/auth?redirect=${encodedUrl}`, { replaceState: true });
    }

</script>

{#if isOpen}
    <div
        class="fixed inset-0 z-[9999] flex items-center justify-center p-3"
    transition:fade={{ duration: 150 }}
    >
    <div class="absolute inset-0 bg-black/60"></div>

        <div
            class="relative z-10 w-full max-w-sm rounded-2xl bg-white p-5 dark:bg-gray-900 shadow-xl"
        >
            <div class=" flex justify-center text-center mb-3">
                <div class=" text-lg font-medium font-primary dark:text-gray-100">
                    {$i18n.t('(Session Expired)')}
                </div>
            </div>

            <div class="text-center dark:text-gray-200">
        <div class="flex justify-center mb-3">
           <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="h-10 w-10 text-destructive">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </div>
        <div id="dialog-description" class="text-sm text-muted-foreground mb-4">
           {$i18n.t('(Your session has expired. Please log in again to continue. You may want to copy any unsaved work before proceeding.)')}
              </div>
      </div>

      <div class="flex justify-center">
        <button
          class="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 transition rounded-full flex flex-row items-center"
          on:click={redirectToLogin}
        >
          {$i18n.t('(Log In Again)')}
        </button>
      </div>
        </div>
    </div>
{/if}

<style>
:global(body.modal-open) {
  overflow: hidden;
}
</style>
