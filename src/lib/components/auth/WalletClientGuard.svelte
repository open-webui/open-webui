<script lang="ts">
  import { hooks } from "svelte-preprocess-react";
  import { createWalletClient, custom, isAddress, publicActions } from "viem";
  import { useWallets, type ConnectedWallet } from "@privy-io/react-auth";
  import { walletClient } from "../../stores/login_stores";
  import { mainnet } from "viem/chains";

  const privyWalletsStore = hooks(() => useWallets());

  let loading = true;

  async function initWalletClient(wallet: ConnectedWallet) {
    const ethereumProvider = await wallet.getEthereumProvider();

    if (!isAddress(wallet.address)) {
      console.error("wallet.address is not an address", wallet.address);
      return;
    }

    const _walletClient = createWalletClient({
      account: wallet.address,
      chain: mainnet,
      transport: custom(ethereumProvider),
    }).extend(publicActions);

    walletClient.set(_walletClient);
    loading = false;
  }

  $: if ($privyWalletsStore && $privyWalletsStore.wallets) {
    initWalletClient($privyWalletsStore.wallets[0]);
  }
</script>

{#if !loading && $walletClient}
  <slot />
{/if}
