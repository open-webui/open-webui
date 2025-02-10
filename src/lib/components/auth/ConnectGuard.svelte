<script lang="ts">
  import { hooks } from "svelte-preprocess-react";
  import { usePrivy, useWallets } from "@privy-io/react-auth";
  import { read } from "$app/server";
  import { toast } from 'svelte-sonner';
  import { goto } from '$app/navigation';
  import { getBackendConfig } from '$lib/apis';
  import { userSignUp, getSessionUser } from '$lib/apis/auths';
  import { generateInitialsImage } from '$lib/utils';
  import { config, user, socket } from '$lib/stores';

  const privyStore = hooks(() => usePrivy());
  const privyWalletsStore = hooks(() => useWallets());
  console.log("$privyWalletsStore, $privyStore", $privyWalletsStore, $privyStore);

  const setSessionUser = async (sessionUser) => {
    console.log("setSessionUser", sessionUser);
    if (sessionUser) {
      console.log(sessionUser);
      toast.success('You\'re now logged in.');
      if (sessionUser.token) {
        localStorage.token = sessionUser.token;
      }

      $socket.emit('user-join', { auth: { token: sessionUser.token } });
      await user.set(sessionUser);
      await config.set(await getBackendConfig());
      goto('/');
    }
  };

  // 监听认证状态并自动处理注册和登录
  $: if ($privyWalletsStore || $privyStore) {
    console.log('privy Store:', $privyWalletsStore, $privyStore);
    if ($privyStore.authenticated) {
      // 如果已认证但没有连接钱包，自动连接钱包
      // if (!$privyWalletsStore?.wallets?.length) {
      //   console.log('Auto connecting wallet for authenticated user');
      //   $privyStore.connectWallet();
      // }
      
      // 自动注册和登录
      const handleAutoSignUp = async () => {
        try {
          // 使用 Privy 用户信息进行注册
          const email = $privyStore.user?.email?.address || '';
          const name = $privyStore.user?.name || email.split('@')[0] || 'User';
          
          const sessionUser = await userSignUp(
            name,
            email,
            'privy-auth-' + $privyStore.user?.id, // 使用 Privy ID 作为密码
            generateInitialsImage(name)
          ).catch(async (error) => {
            console.log('Sign up error, trying to get session:', error);
            // 如果注册失败（可能用户已存在），尝试获取现有会话
            return await getSessionUser().catch(() => null);
          });
          console.log('Auto sign up result:', sessionUser);
          await setSessionUser(sessionUser);
        } catch (error) {
          console.error('Auto sign up failed:', error);
          toast.error(`Authentication failed: ${error}`);
        }
      };

      handleAutoSignUp();
    }
  }
</script>

{#if $privyStore}
  {@const { ready, authenticated, login, connectWallet, logout } = $privyStore}
  {#if ready}
    {#if authenticated && $privyWalletsStore && $privyWalletsStore.wallets.length > 0}
      <slot />
    {:else}
      <button
        on:click={() => {
          if (!authenticated) {
            console.log("not authenticated", ready, authenticated, $privyStore, $privyWalletsStore);
            login();
          } else {
            console.log("authenticated", ready, authenticated, $privyStore, $privyWalletsStore);
            // connectWallet();
            logout();
          }
        }}
      >
        Connect Wallet
      </button>
    {/if}
  {/if}
{/if}
