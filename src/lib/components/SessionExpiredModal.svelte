<script lang="ts">
  import { sessionExpired } from '$lib/stores';
  import Modal from '$lib/components/common/Modal.svelte';
  import { getContext } from 'svelte';
  import { page } from '$app/stores';
  import { WEBUI_BASE_URL } from '$lib/constants';

  const i18n = getContext('i18n');

  let isOpen = false;
  sessionExpired.subscribe((value) => {
    isOpen = value;
  });

  function closeModal() {
    sessionExpired.set(false);
  }

  function redirectToLogin() {
    sessionExpired.set(false);
    const currentUrl = `${$page.url.pathname}${$page.url.search}`;
    const encodedUrl = encodeURIComponent(currentUrl);
    window.location.href = `${WEBUI_BASE_URL}/auth?redirect=${encodedUrl}`;
  }

</script>

<Modal size="sm" bind:show={isOpen}>
  {#if isOpen}
  <div>
    <div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
      <div class=" text-lg font-medium self-center font-primary">
        {$i18n.t('sessionExpiredTitle')}
      </div>
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
          {$i18n.t('sessionExpiredMessage')}
        </div>

        <div class="flex justify-center pt-3 text-sm font-medium gap-1.5">
          <button
            class="px-3.5 py-1.5 text-sm font-medium bg-gray-200 hover:bg-gray-300 text-gray-800 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600 transition rounded-full flex flex-row space-x-1 items-center"
            type="button"
            on:click={closeModal}
          >
            {$i18n.t('sessionExpiredCloseButton')}
          </button>
          <button
            class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
            type="button"
            on:click={redirectToLogin}
          >
            {$i18n.t('sessionExpiredLoginButton')}
          </button>
        </div>
      </div>
    </div>
  </div>
 {/if}
</Modal>
