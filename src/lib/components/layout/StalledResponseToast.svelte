<script lang="ts">
  import { getContext, createEventDispatcher, onMount } from "svelte";
  import XMark from "../icons/XMark.svelte";

  const dispatch = createEventDispatcher();
  const i18n = getContext("i18n");

  export let onRefresh = () => {
    // default behavior
    location.reload();
  };

  // Optional: persist “dismissed” per session
  let dismissed = false;
  const KEY = "stall_toast_dismissed";
  onMount(() => {
    dismissed = sessionStorage.getItem(KEY) === "1";
  });
  function close() {
    sessionStorage.setItem(KEY, "1");
    dispatch("close");
  }
</script>

{#if !dismissed}
  <div
    class="flex items-start bg-[#FEF7F1] dark:bg-[#1D0C02] border border-[#D58A33] dark:border-[#3B1103] text-[#D46C2B] dark:text-[#ECA067] rounded-lg px-3.5 py-3 text-xs max-w-96 pr-2 w-full shadow-lg"
    role="status"
    aria-live="polite"
  >
    <div class="flex-1 font-medium">
      {$i18n.t('The response looks stalled.')}
      <button
        class="underline"
        on:click={onRefresh}
        aria-label={$i18n.t('Refresh the page')}
      >
        {$i18n.t('Refresh the page')}
      </button>
      {$i18n.t(' or check your connection.')}
    </div>

    <div class="shrink-0 pr-1">
      <button
        class="hover:text-orange-900 dark:hover:text-orange-300 transition"
        on:click={close}
        aria-label={$i18n.t('Dismiss')}
      >
        <XMark />
      </button>
    </div>
  </div>
{/if}
