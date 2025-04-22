<script lang="ts">
    import { sessionExpired } from '$lib/stores';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { WEBUI_BASE_URL } from '$lib/constants';
    import Modal from '$lib/components/common/Modal.svelte';
    import { getContext } from 'svelte';

    const i18n = getContext('i18n');

    let isOpen = false;
    sessionExpired.subscribe((value) => {
        isOpen = value;
    });

    function redirectToLogin() {
        sessionExpired.set(false);
        const currentUrl = `${$page.url.pathname}${$page.url.search}`;
        const encodedUrl = encodeURIComponent(currentUrl);
        goto(`${WEBUI_BASE_URL}/auth?redirect=${encodedUrl}`, { replaceState: true });
    }

</script>

<Modal size="sm" bind:show={isOpen}>
    {#if isOpen}
    <div>
        <div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
            <div class=" text-lg font-medium self-center font-primary">
                {$i18n.t('(Session Expired)')}
            </div>
            <!-- <button class="self-center" on:click={closeModal}> ... X SVG ... </button> -->

        </div>

        <div class="flex flex-col w-full px-4 pb-4 dark:text-gray-200">
            <div class="flex flex-col items-center text-center w-full">
        <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="h-10 w-10 text-destructive mb-3" >
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>

        <div class="text-sm text-muted-foreground text-center mb-4">
          {$i18n.t('(Your session has expired. Please log in again to continue. You may want to copy any unsaved work before proceeding.)')}
                </div>

                <div class="flex justify-center pt-3 text-sm font-medium gap-1.5">
          <button
            class="px-3.5 py-1.5 text-sm font-medium bg-destructive hover:bg-destructive/90 text-destructive-foreground transition rounded-full flex flex-row space-x-1 items-center"
            type="button"
            on:click={redirectToLogin}
          >
            {$i18n.t('(Log In Again)')}
          </button>
                </div>
      </div>
        </div>
    </div>
 {/if}
</Modal>
