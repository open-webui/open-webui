<script lang="ts">
  import { getContext, onMount } from 'svelte';
  import { toast } from 'svelte-sonner';
  import Spinner from '$lib/components/common/Spinner.svelte';
  import { getMCPAllowlist, setMCPAllowlist } from '$lib/apis/configs';

  const i18n = getContext('i18n') as any;

  let allowlistText = '';
  let loading = true;
  let saving = false;

  onMount(async () => {
    await loadAllowlist();
  });

  async function loadAllowlist() {
    loading = true;
    try {
      // Add timeout to prevent hanging
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout')), 10000)
      );
      
      // Check if we're in browser context before accessing localStorage
      if (typeof window === 'undefined') {
        allowlistText = '';
        return;
      }
      
      const res = await Promise.race([
        getMCPAllowlist(localStorage.token),
        timeoutPromise
      ]);
      
      const list = res?.MCP_SERVER_ALLOWLIST ?? [];
      allowlistText = Array.isArray(list) ? list.join('\n') : '';
    } catch (e) {
      console.error('MCP Allowlist load error:', e);
      // Set default empty state instead of staying in loading forever
      allowlistText = '';
      if (e.message === 'Request timeout') {
        toast.error(i18n.t('Request timeout - please try again'));
      } else {
        toast.error(i18n.t('Failed to load allowlist'));
      }
    } finally {
      loading = false;
    }
  }

  async function saveAllowlist() {
    saving = true;
    try {
      // Check if we're in browser context before accessing localStorage
      if (typeof window === 'undefined') {
        return;
      }

      const list = allowlistText
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
      
      // Add timeout to prevent hanging
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout')), 10000)
      );
      
      await Promise.race([
        setMCPAllowlist(localStorage.token, list),
        timeoutPromise
      ]);
      
      toast.success(i18n.t('Allowlist saved successfully'));
    } catch (e) {
      console.error('MCP Allowlist save error:', e);
      if (e.message === 'Request timeout') {
        toast.error(i18n.t('Request timeout - please try again'));
      } else {
        toast.error(i18n.t('Failed to save allowlist'));
      }
    } finally {
      saving = false;
    }
  }
</script>

<form class="flex flex-col h-full justify-between text-sm" on:submit|preventDefault={saveAllowlist}>
  <div class="overflow-y-scroll scrollbar-hidden h-full">
    <div class="mb-3">
      <div class="mb-2.5 text-base font-medium">{i18n.t('MCP Servers')}</div>

      <hr class="border-gray-100 dark:border-gray-850 my-2" />

      <div class="mb-2.5 flex flex-col w-full justify-between">
        <div class="font-medium mb-1">{i18n.t('Allowlist')}</div>
        {#if loading}
          <div class="flex h-32 justify-center items-center"><Spinner className="size-6" /></div>
        {:else}
          <label class="text-xs text-gray-500 mb-1">{i18n.t('Allowed MCP domains (one per line)')}</label>
          <textarea class="w-full h-40 p-2 border rounded bg-transparent" bind:value={allowlistText} placeholder="example.com\napi.mycorp.internal" />
        {/if}
        <div class="my-1.5 text-xs text-gray-500">
          {i18n.t('Restrict which MCP server domains can be connected to from this instance.')}
        </div>
      </div>
    </div>
  </div>

  <div class="flex justify-end pt-3 text-sm font-medium">
    <button class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-60" type="submit" disabled={saving}>
      {saving ? i18n.t('Saving...') : i18n.t('Save')}
    </button>
  </div>
</form> 