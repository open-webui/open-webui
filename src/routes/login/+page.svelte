<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite } from '$lib/apis/auths';
    
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import { WEBUI_NAME, config, user, socket, toastVisible, toastMessage, toastType, showToast, company, companyConfig } from '$lib/stores';
    import { getSessionUser, userSignIn, getCompanyDetails, getCompanyConfig } from '$lib/apis/auths';

	import Plus from '$lib/components/icons/Plus.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';
	import ShowPassIcon from '$lib/components/icons/ShowPassIcon.svelte';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import HidePassIcon from '$lib/components/icons/HidePassIcon.svelte';

	const i18n = getContext('i18n');

	let email = '';
	let password = '';
    let showPassword = false;
	
	let loading = false;

	onMount(() => {
		
	})

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			showToast('success', `You're now logged in.`);
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			goto('/');
		}
	};

	const signInHandler = async () => {
        loading = true;
		const sessionUser = await userSignIn(email, password).catch((error) => {
			// toast.error(`${error}`);
            showToast('error',error)
			loading = false;
			return null;
		});

		await setSessionUser(sessionUser);
		
		const [companyInfo, companyConfigInfo] = await Promise.all([
			getCompanyDetails(sessionUser.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			}),
			getCompanyConfig(sessionUser.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			})
		]);

		if (companyInfo) {
			company.set(companyInfo);
		}

		if (companyConfigInfo) {
			console.log(companyConfigInfo);
			companyConfig.set(companyConfigInfo);
		}
        loading = false;
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

	onMount(async () => {
        if ($user !== undefined) {
			await goto('/');
		}
		await checkOauthCallback();
    });
	let logoSrc = '/logo_dark_transparent.png';

	onMount(() => {
		const isDark = localStorage.getItem('theme') === 'dark';
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_light_transparent.png';
	});

	$: console.log($config?.oauth?.providers?.google);
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />
<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh] px-4 text-white relative bg-lightGray-300 dark:bg-customGray-900"
>
    <div></div>
	<form
		class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-full md:w-[31rem] py-5 px-5 md:py-7 md:px-24"
		on:submit={(e) => {
			e.preventDefault();
			signInHandler();
		}}
	>	
        <div class="self-center flex flex-col items-center mb-5">
            <div>
                <img crossorigin="anonymous" src={logoSrc} class=" w-10 mb-5" alt="logo" />
            </div>
            <div class="font-medium mb-2.5 text-lightGray-100 dark:text-customGray-100">{$i18n.t('Welcome to')} Beyond Chat</div>
            <div class="font-medium text-center text-xs text-[#8A8B8D] dark:text-customGray-300">{$i18n.t('Sign in to continue')}</div>
        </div>
		<div class="flex-1 mb-2.5">
			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if email}
					<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
						{$i18n.t('Email address')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${email ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 dark:text-white placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('Email address')}
					bind:value={email}
                    type="email"
                    autocomplete="email"
					name="email"
					required
				/>
			</div>
		</div>
	
		<div class="flex flex-col w-full mb-1">
			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if password}
					<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
						{$i18n.t('Password')}
					</div>
				{/if}
				{#if showPassword}
					<input
						class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} text-lightGray-100 w-full h-12 bg-transparent dark:text-white placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none pr-10`}
						type="text"
						bind:value={password}
						placeholder={$i18n.t('Password')}
						autocomplete="current-password"
                        name="password"
						required
					/>
				{:else}
					<input
						class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} text-lightGray-100 w-full h-12 bg-transparent dark:text-white placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none pr-10`}
						type="password"
						bind:value={password}
						placeholder={$i18n.t('Password')}
						autocomplete="current-password"
                        name="current-password"
						required
					/>
				{/if}

				<button
					type="button"
					class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-500 dark:text-white"
					on:click={() => (showPassword = !showPassword)}
					tabindex="-1"
				>
				{#if showPassword}
					<HidePassIcon/>
				{:else}
					<ShowPassIcon/>
				{/if}
				</button>
			</div>
		</div>
        <div class="flex justify-end mb-2.5">
            <a href="/reset-password" class="font-medium text-customBlue-500 text-xs">{$i18n.t('Forgot password?')}</a>
        </div>
        <button
			class="font-medium text-xs w-full h-10 px-3 py-2 transition rounded-lg {loading
				? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border border-lightGray-400 dark:border-customGray-700'
				: 'bg-lightGray-300 hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border border-lightGray-400 dark:border-customGray-700'} flex justify-center items-center"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Login')}
			{#if loading}
				<div class="ml-1.5 self-center">
					<LoaderIcon/>
				</div>
			{/if}
		</button>
		<div class="mt-5 text-xs text-lightGray-100 dark:text-customGray-300">
			{$i18n.t(`Don't have an account?`)}
			<a href="/company-register" class="font-medium text-customBlue-500">{$i18n.t('Register now')}</a>
		</div>
        <!-- <hr class=" border-gray-50 dark:border-customGray-700 mb-2 mt-6" />
        <div class="text-xs dark:text-customGray-300 text-center font-medium mb-2.5">Or</div>
        <div class="flex flex-col space-y-2">
            {#if $config?.oauth?.providers?.google}
                <button
                    class="mb-2.5 h-10 flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 transition w-full rounded-lg font-medium text-xs py-2.5 border border-customGray-700"
                    on:click={() => {
                        window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
                    }}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-4 mr-3">
                        <path
                            fill="#EA4335"
                            d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
                        /><path
                            fill="#4285F4"
                            d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
                        /><path
                            fill="#FBBC05"
                            d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
                        /><path
                            fill="#34A853"
                            d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
                        /><path fill="none" d="M0 0h48v48H0z" />
                    </svg>
                    <span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
                </button>
            {/if}
            {#if $config?.oauth?.providers?.microsoft}
                <button
                    class="mb-2.5 h-10 flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 transition w-full rounded-lg font-medium text-xs py-2.5 border border-customGray-700"
                    on:click={() => {
                        window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
                    }}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-4 mr-3">
                        <rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
                            x="1"
                            y="11"
                            width="9"
                            height="9"
                            fill="#00a4ef"
                        /><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
                            x="11"
                            y="11"
                            width="9"
                            height="9"
                            fill="#ffb900"
                        />
                    </svg>
                    <span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span>
                </button>
            {/if}
		</div> -->
	</form>
    
    <div class="self-center text-xs text-customGray-300 dark:text-customGray-100 pb-5 text-center">By using this service, you agree to our <a href="/">Terms</a> and <a href="/">Conditions</a>.</div>
</div>
