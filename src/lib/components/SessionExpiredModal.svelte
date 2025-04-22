<script lang="ts">
  import { sessionExpired } from '$lib/stores';
  import Modal from '$lib/components/common/Modal.svelte';
  import { getContext } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';

  const i18n = getContext('i18n');

  let isOpen = false;
  sessionExpired.subscribe((value) => {
    isOpen = value;
  });

  function closeModal() {
    sessionExpired.set(false);
  }

  function triggerReLogin() {
    sessionExpired.set(false);
    localStorage.removeItem('token');
    const currentUrl = `${$page.url.pathname}${$page.url.search}`;
    const encodedUrl = encodeURIComponent(currentUrl);
    goto(`/auth?redirect=${encodedUrl}`, { replaceState: true });
  }

</script>

<Modal size="sm" bind:show={isOpen}>
  {#if isOpen}
  <div>

    <div class="text-sm text-muted-foreground text-center mb-4">
      {$i18n.t('sessionExpiredMessage')}
    </div>

    <div class="flex justify-center pt-3 text-sm font-medium gap-1.5">
      <button
        class="..."
        type="button"
        on:click={closeModal}
      >
        {$i18n.t('sessionExpiredCloseButton')}
      </button>
      <button
        class="..."
        type="button"
        on:click={triggerReLogin} // Call the renamed function
      >
        {$i18n.t('sessionExpiredLoginButton')}
      </button>
    </div>
  </div>
 {/if}
</Modal>
