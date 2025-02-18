<script lang="ts">
  import { hooks } from "svelte-preprocess-react";
  import { usePrivy, useWallets, useSolanaWallets } from "@privy-io/react-auth";
  import { toast } from 'svelte-sonner';
  import { goto } from '$app/navigation';
  import { getBackendConfig } from '$lib/apis';
  import { userSignUp, getSessionUser, userSignIn } from '$lib/apis/auths';
  import { generateInitialsImage } from '$lib/utils';
  import { config, user, socket } from '$lib/stores';

  const privyStore = hooks(() => usePrivy());
  const privyWalletsStore = hooks(() => useWallets());
  const solanaWalletsStore = hooks(() => useSolanaWallets());
  console.log("$solanaWalletsStore, $privyWalletsStore, $privyStore",$solanaWalletsStore, $privyWalletsStore, $privyStore);

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
  let isHandlingAuth = false;
  $: if (($solanaWalletsStore || $privyWalletsStore || $privyStore) && !isHandlingAuth) {
    console.log('privy Store:', $solanaWalletsStore, $privyWalletsStore, $privyStore);

    if ($privyStore.authenticated) {
      isHandlingAuth = true;
      // 自动注册和登录
      const handleAutoSignUp = async () => {
        let email = '';
        let name = '';  
        const user = $privyStore.user;
        const linkedType = user.linkedAccounts[0]?.type;
        try {
          // 使用 Privy 用户信息进行注册
          if (linkedType == 'wallet') {
            console.log('Auto sign up for connected wallet');
            email = $solanaWalletsStore.wallets[0].address + '@airie.fun';
            name = $solanaWalletsStore.wallets[0].address;
          } else if (linkedType == "google_oauth") {
            // google oatuth
            console.log('google login');
            email = user?.google?.email;
            name = user?.google?.name || email.split('@')[0] || 'User';
            console.log('google retreive email:', email, name)
          }else if (linkedType == 'passkey') {
            // passkey
            console.log('passkey login');
            account = user?.linkedAccounts[0];
            email = account?.credentialId;
            name = account?.credentialId || email.split('@')[0] || 'User';
          } else {
            email = $privyStore.user?.email?.address || '';
            name = $privyStore.user?.name || email.split('@')[0] || 'User';
          }
          
          
          const sessionUser = await userSignUp(
            name,
            email,
            'privy-auth-' + $privyStore.user?.id, // 使用 Privy ID 作为密码
            generateInitialsImage(name)
          ).catch(async (error) => {
            console.log('Sign up error, trying to get session:', error);
            // 如果注册失败（可能用户已存在），尝试获取现有会话
            return await userSignIn(email, 'privy-auth-' + $privyStore.user?.id).catch(() => null);
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
        class="connect-button"
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
        Log in / Sign up
      </button>
    {/if}
  {/if}
{/if}

<style>
  .connect-button {
    background-color: rgba(255, 255, 255, 0.6);  /* 半透明黑色背景 */
    color: black;
    border: none;
    border-radius: 24px;  /* 圆角效果，创造半圆形外观 */
    padding: 8px 24px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.3s ease;
    backdrop-filter: blur(4px);  /* 毛玻璃效果 */
  }

  .connect-button:hover {
    background-color: rgba(255, 255, 255, 0.8);
    transform: translateY(-2px);
  }

  .connect-button:active {
    transform: translateY(0);
  }
</style>
