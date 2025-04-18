<script lang="ts">
  import { keplerWallet } from '$lib/contexts/KeplerWalletContext';
  import { toast } from 'svelte-sonner';

  const handleConnect = async () => {
    try {
      await keplerWallet.connect();
      toast.success('Wallet connected successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to connect wallet');
    }
  };

  const handleDisconnect = async () => {
    try {
      await keplerWallet.disconnect();
      toast.success('Wallet disconnected successfully');
    } catch (error) {
      toast.error('Failed to disconnect wallet');
    }
  };

  const state = keplerWallet.state;
</script>

{#if $state.isConnected}
  <div class="flex items-center gap-2">
    <span class="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[140px]">
      {$state.address}
    </span>
    <button
      class="text-sm px-2 py-1 rounded-lg bg-red-100 hover:bg-red-200 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-700 dark:text-red-400 transition"
      on:click={handleDisconnect}
    >
      Disconnect
    </button>
  </div>
{:else}
  <button
    class="text-sm px-2 py-1 rounded-lg bg-blue-100 hover:bg-blue-200 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-400 transition"
    on:click={handleConnect}
  >
    Connect Kepler
  </button>
{/if} 