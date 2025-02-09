<script lang="ts">
  import { hooks } from "svelte-preprocess-react";
  import { usePrivy, useWallets } from "@privy-io/react-auth";

  const privyStore = hooks(() => usePrivy());
  const privyWalletsStore = hooks(() => useWallets());
</script>

{#if $privyStore}
  {@const { ready, authenticated, login, connectWallet } = $privyStore}
  {#if ready}
    {#if authenticated && $privyWalletsStore && $privyWalletsStore.wallets.length > 0}
      <slot />
    {:else}
      <button
        on:click={() => {
          if (!authenticated) {
            login();
          } else {
            connectWallet();
          }
        }}
      >
        Connect Wallet
      </button>
    {/if}
  {/if}
{/if}
