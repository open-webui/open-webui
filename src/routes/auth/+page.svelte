<script>
	import { goto } from '$app/navigation';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { page } from '$app/stores';
	import { getBackendConfig } from '$lib/apis';

	const i18n = getContext('i18n');

	let loaded = false;
	let mode = 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';
	let ldapPassword = '';

	$: showSwitchButtonForSignInForm =  ($config?.features.enable_ldap_form && mode !== 'ldap') || ($config?.features.enable_login_form && mode === 'ldap');

	$: showOtherSignInMethods = Object.keys($config?.oauth?.providers ?? {}).length > 0 ||  showSwitchButtonForSignInForm;

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			goto('/');
		}
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, ldapPassword).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap'){
			await ldapSignInHandler();
		}
		else if (mode === 'signin') {
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
			toast.error(error);
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
		loaded = true;
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div class="fixed m-10 z-50">
		<div class="flex space-x-2">
			<div class=" self-center">
				<img
					crossorigin="anonymous"
					src="{WEBUI_BASE_URL}/static/favicon.png"
					class=" w-8 rounded-full"
					alt="logo"
				/>
			</div>
		</div>
	</div>

	<div class=" bg-white dark:bg-gray-950 min-h-screen w-full flex justify-center font-primary">
		<!-- <div class="hidden lg:flex lg:flex-1 px-10 md:px-16 w-full bg-yellow-50 justify-center">
			<div class=" my-auto pb-16 text-left">
				<div>
					<div class=" font-semibold text-yellow-600 text-4xl">
						{$i18n.t('Get up and running with')} <br /> {$i18n.t('large language models, locally.')}
					</div>

					<div class="mt-2 text-yellow-600 text-xl">
						{$i18n.t('Run Llama 2, Code Llama, and other models. Customize and create your own.')}
					</div>
				</div>
			</div>
		</div> -->

		<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
			{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
				<div class=" my-auto pb-10 w-full">
					<div
						class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold dark:text-gray-200"
					>
						<div>
							{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
						</div>

						<div>
							<Spinner />
						</div>
					</div>
				</div>
			{:else}
				<div class="  my-auto pb-10 w-full dark:text-gray-100">
					<form
						class=" flex flex-col justify-center"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div class="mb-1">
							<div class=" text-2xl font-medium">
								{#if mode === 'signin'}
									{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else if mode === 'ldap'}
									{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
								{:else}
									{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
								{/if}
							</div>

							{#if mode === 'signup'}
								<div class=" mt-1 text-xs font-medium text-gray-500">
									ⓘ {$WEBUI_NAME}
									{$i18n.t(
										'does not make any external connections, and your data stays securely on your locally hosted server.'
									)}
								</div>
							{/if}
						</div>

						{#if $config?.features.enable_ldap_form && mode === 'ldap'}
						<div class="flex flex-col mt-4">
							<div class="mb-2">
								<div class=" text-sm font-medium text-left mb-1">
									{$i18n.t('Username')}
								</div>
								<input
									bind:value={ldapUsername}
									type="text"
									class=" px-5 py-3 rounded-2xl w-full text-sm outline-none border dark:border-none dark:bg-gray-900"
									autocomplete="username"
									placeholder={$i18n.t('Enter Your Username')}
									required
								/>
							</div>

							<div>
								<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Password')}</div>
								<input
									bind:value={ldapPassword}
									type="password"
									class=" px-5 py-3 rounded-2xl w-full text-sm outline-none border dark:border-none dark:bg-gray-900"
									placeholder={$i18n.t('Enter Your Password')}
									autocomplete="current-password"
									required
								/>
							</div>

							<div class="mt-5">
								<button
									class=" bg-gray-900 hover:bg-gray-800 w-full rounded-2xl text-white font-medium text-sm py-3 transition"
									type="submit"
								>
									{$i18n.t('Authenticate')}
								</button>
							</div>
						</div>
						{/if}

						{#if $config?.features.enable_login_form && mode !== 'ldap'}
							<div class="flex flex-col mt-4">
								{#if mode === 'signup'}
									<div>
										<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Name')}</div>
										<input
											bind:value={name}
											type="text"
											class=" px-5 py-3 rounded-2xl w-full text-sm outline-none border dark:border-none dark:bg-gray-900"
											autocomplete="name"
											placeholder={$i18n.t('Enter Your Full Name')}
											required
										/>
									</div>

									<hr class=" my-3 dark:border-gray-900" />
								{/if}

								<div class="mb-2">
									<div class=" text-sm font-medium text-left mb-1">
										{$i18n.t('Email')}
									</div>
									<input
										bind:value={email}
										type="email"
										class=" px-5 py-3 rounded-2xl w-full text-sm outline-none border dark:border-none dark:bg-gray-900"
										autocomplete="email"
										placeholder={$i18n.t('Enter Your Email')}
										required
									/>
								</div>

								<div>
									<div class=" text-sm font-medium text-left mb-1">{$i18n.t('Password')}</div>

									<input
										bind:value={password}
										type="password"
										class=" px-5 py-3 rounded-2xl w-full text-sm outline-none border dark:border-none dark:bg-gray-900"
										placeholder={$i18n.t('Enter Your Password')}
										autocomplete="current-password"
										required
									/>
								</div>
							</div>
						{/if}

						{#if $config?.features.enable_login_form && mode !== 'ldap'}
							<div class="mt-5">
								<button
									class=" bg-gray-900 hover:bg-gray-800 w-full rounded-2xl text-white font-medium text-sm py-3 transition"
									type="submit"
								>
									{mode === 'signin' ? $i18n.t('Sign in') : $i18n.t('Create Account')}
								</button>

								{#if $config?.features.enable_signup}
									<div class=" mt-4 text-sm text-center">
										{mode === 'signin'
											? $i18n.t("Don't have an account?")
											: $i18n.t('Already have an account?')}

										<button
											class=" font-medium underline"
											type="button"
											on:click={() => {
												if (mode === 'signin') {
													mode = 'signup';
												} else {
													mode = 'signin';
												}
											}}
										>
											{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
										</button>
									</div>
								{/if}
							</div>
						{/if}
					</form>

					{#if showOtherSignInMethods}
						<div class="inline-flex items-center justify-center w-full">
							<hr class="w-64 h-px my-8 bg-gray-200 border-0 dark:bg-gray-700" />
							{#if $config?.features.enable_login_form}
								<span
									class="absolute px-3 font-medium text-gray-900 -translate-x-1/2 bg-white left-1/2 dark:text-white dark:bg-gray-950"
									>{$i18n.t('or')}</span
								>
							{/if}
						</div>
						<div class="flex flex-col space-y-2">
							{#if $config?.oauth?.providers?.google}
								<button
									class="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
									}}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-6 mr-3">
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
									class="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
									}}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-6 mr-3">
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
							{#if $config?.oauth?.providers?.oidc}
								<button
									class="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-6 mr-3"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
										/>
									</svg>

									<span
										>{$i18n.t('Continue with {{provider}}', {
											provider: $config?.oauth?.providers?.oidc ?? 'SSO'
										})}</span
									>
								</button>
							{/if}
							{#if showSwitchButtonForSignInForm}
								<button
								class="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition"
								on:click={() => {
									if(mode === 'ldap') mode = 'signin';
									else mode = 'ldap';
								}}
								>
									{#if mode === 'ldap'}
										<svg 
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24" 
											fill="none" 
											stroke-width="1.5"
											stroke="currentColor"
											class="size-6 mr-3"
										>
											<path 
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M4 7.00005L10.2 11.65C11.2667 12.45 12.7333 12.45 13.8 11.65L20 7" stroke="#000000" 
												stroke-width="2"
											/>
											<rect x="3" y="5" width="18" height="14" rx="2" stroke="#000000" stroke-width="2" stroke-linecap="round"/>
										</svg>
									{:else}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-6 mr-3"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
											/>
										</svg>
									{/if}
									<span>{mode === 'ldap' ? $i18n.t('Continue with Email') : $i18n.t('Continue with LDAP')}</span>
								</button>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.font-mona {
		font-family:
			'Mona Sans',
			-apple-system,
			'Inter',
			ui-sans-serif,
			system-ui,
			'Segoe UI',
			Roboto,
			Ubuntu,
			Cantarell,
			'Noto Sans',
			sans-serif,
			'Helvetica Neue',
			Arial,
			'Apple Color Emoji',
			'Segoe UI Emoji',
			'Segoe UI Symbol',
			'Noto Color Emoji';
	}
</style>
