<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features?.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

	// Fix: Add types for function parameters
	const querystringValue = (key: string): string | null => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};
	const setSessionUser = async (sessionUser: any) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket?.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) {
			return;
		}
		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	// Fix: Add fallback for enable_ldap and onboarding
	const enableLdap = $config?.features?.enable_ldap ?? false;
	const onboarding = $config?.onboarding ?? false;
	let onboardingState = onboarding;
	// SSO URL logic
	$: ssoUrl = $config?.oauth?.providers?.oidc
		? `${WEBUI_BASE_URL}/oauth/oidc/login`
		: $config?.oauth?.providers?.google
		? `${WEBUI_BASE_URL}/oauth/google/login`
		: $config?.oauth?.providers?.microsoft
		? `${WEBUI_BASE_URL}/oauth/microsoft/login`
		: $config?.oauth?.providers?.github
		? `${WEBUI_BASE_URL}/oauth/github/login`
		: null;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');
		const mainLogo = document.getElementById('main-logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = '/static/favicon-dark.png';

				darkImage.onload = () => {
					(logo as HTMLImageElement).src = '/static/favicon-dark.png';
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}

		if (mainLogo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				mainLogo.style.filter = 'invert(1)'; // Invert the main logo for dark mode
			} else {
				mainLogo.style.filter = ''; // Reset filter for light mode
			}
		}
	}

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			// Use onboarding constant from config
			// If onboarding UI state is needed, use onboardingState instead
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboardingState}
	getStartedHandler={() => {
		onboardingState = false;
		mode = $config?.features?.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="min-h-screen w-full flex items-stretch bg-surface overflow-clip relative">
  <!-- Gradient overlay (SVG from Figma, placeholder for now) -->
  <div class="absolute left-[-154px] top-[-46px] w-[1748px] h-[1092px] pointer-events-none z-0">
    <!-- TODO: Replace with actual SVG from Figma -->
    <!-- <img src="/static/assets/your-gradient.svg" class="w-full h-full object-cover" alt="gradient" /> -->
  </div>
  <!-- Add the new left image div as per Figma -->
  <div class="hidden lg:block shrink-0 w-[40%] w-max-[600px] h-full relative z-10 bg-login">
  </div>
  <!-- Centered login card -->
  <div class="flex flex-1 items-center justify-center relative p-4 z-20">
    <div class="bg-white rounded-3xl shadow-[0px_48px_96px_0px_rgba(0,0,0,0.08)] p-8 py-12 flex flex-col gap-12 items-center w-full max-w-[440px]">
      <!-- Logo -->
      <div class="flex flex-col items-center gap-6 w-full">
        <div class="relative w-[150px] h-[45px]">
          <img src="/logo.png" alt="GovGPT logo" class="absolute left-0 top-0 w-[110px] h-[45px] object-contain" />
        </div>
      </div>
      <!-- SSO Button (show if any SSO provider) -->
      {#if Object.keys($config?.oauth?.providers ?? {}).length > 0 && ssoUrl}
        <button class="w-full h-12 bg-primary rounded-lg flex items-center justify-center font-heading font-medium text-[16px] text-white"
          type="button"
          on:click={() => { window.location.href = ssoUrl; }}>
          Sign in with SSO
        </button>
		<div class="w-full border-b border-gray-100 py-0"></div>
      {/if}
	  
      <!-- Login form -->
      <form class="flex flex-col gap-8 w-full" on:submit={(e) => { e.preventDefault(); submitHandler(); }}>
        {#if $config?.features?.enable_login_form || enableLdap}
          <div class="flex flex-col gap-4">
            {#if mode === 'signup'}
              <div>
                <label for="name" class="block text-[14px] leading-[22px] font-medium text-left mb-1 text-[#36383b]">{$i18n.t('Name')}</label>
                <input bind:value={name} type="text" id="name" class="w-full p-2.5 rounded-lg bg-[#eceef1] text-[#36383b] text-[14px] leading-[22px]" autocomplete="name" placeholder={$i18n.t('Enter Your Full Name')} required />
              </div>
            {/if}
            {#if mode === 'ldap'}
              <div>
                <label for="username" class="block text-[14px] leading-[22px] font-medium text-left mb-1 text-[#36383b]">{$i18n.t('Username')}</label>
                <input bind:value={ldapUsername} type="text" id="username" class="w-full p-2.5 rounded-lg bg-[#eceef1] text-[#36383b] text-[14px] leading-[22px]" autocomplete="username" name="username" placeholder={$i18n.t('Enter Your Username')} required />
              </div>
            {:else}
              <div>
                <label for="email" class="block text-[14px] leading-[22px] font-medium text-left mb-1 text-[#36383b]">{$i18n.t('Email')} address</label>
                <input bind:value={email} type="email" id="email" class="w-full p-2.5 rounded-lg bg-[#eceef1] text-[#36383b] text-[14px] leading-[22px]" autocomplete="email" name="email" placeholder={$i18n.t('Enter Your Email')} required />
              </div>
            {/if}
            <div>
              <label for="password" class="block text-[14px] leading-[22px] font-medium text-left mb-1 text-[#36383b]">{$i18n.t('Password')}</label>
              <input bind:value={password} type="password" id="password" class="w-full p-2.5 rounded-lg bg-[#eceef1] text-[#36383b] text-[14px] leading-[22px]" placeholder={$i18n.t('Enter Your Password')} autocomplete="current-password" name="current-password" required />
            </div>
          </div>
        {/if}
        <div>
          {#if $config?.features?.enable_login_form || enableLdap}
            <button class="w-full h-12 bg-[#0054f2] rounded-lg flex items-center justify-center font-heading font-medium text-[16px] text-white" type="submit">
              {mode === 'signin' ? $i18n.t('Sign in') : onboarding ? $i18n.t('Create Admin Account') : $i18n.t('Create Account')}
            </button>
            {#if $config?.features?.enable_signup && !onboarding}
              <div class="mt-4 text-sm text-center text-[#6b6d70]">
                {mode === 'signin' ? $i18n.t("Don't have an account?") : $i18n.t('Already have an account?')}
                <button class="ml-2 text-[#0054f2] font-medium underline" type="button" on:click={() => { mode = mode === 'signin' ? 'signup' : 'signin'; }}>
                  {mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
                </button>
              </div>
            {/if}
          {/if}
        </div>
      </form>
      {#if enableLdap && $config?.features?.enable_login_form}
        <div class="mt-2 w-full">
          <button class="w-full h-12 bg-[#eceef1] rounded-lg flex items-center justify-center font-heading font-medium text-[16px] text-[#36383b]" type="button" on:click={() => { mode = mode === 'ldap' ? (onboarding ? 'signup' : 'signin') : 'ldap'; }}>
            {mode === 'ldap' ? $i18n.t('Continue with Email') : $i18n.t('Continue with LDAP')}
          </button>
        </div>
      {/if}
    </div>
  </div>
</div>
