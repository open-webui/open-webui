<script>
	import { toast } from 'svelte-sonner';

	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { getSessionUser, ldapUserSignIn, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config, socket, user, WEBUI_NAME } from '$lib/stores';

	import { generateInitialsImage } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

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

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(error);
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
			toast.error(error);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	let onboarding = false;

	onMount(async () => {
		if ($user !== undefined) {
			await goto('/');
		}
		await checkOauthCallback();

		loaded = true;
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] text-white relative">
	<div
		class="w-full h-full absolute top-0 left-0 bg-gradient-to-b from-blue-500 to-blue-100 dark:from-gray-900 dark:to-gray-800"></div>

	{#if loaded}
		<div class="fixed top-5 left-5 z-50">
			<div class="flex space-x-2 items-center">
				<img
					crossorigin="anonymous"
					src="{WEBUI_BASE_URL}/static/favicon.png"
					class="w-8 rounded-full"
					alt="logo"
				/>
				<span class="text-xl font-bold text-white">
					{$WEBUI_NAME}
				</span>
			</div>
		</div>

		<div
			class="absolute top-0 left-0 flex min-h-screen w-full sm:items-center justify-center font-primary z-50 text-white"
		>
			<div
				class="bg-white/90 dark:bg-gray-900/80 shadow-lg rounded-lg px-12 py-10 text-center w-full sm:max-w-md flex flex-col">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="mt-10">
						<div
							class="flex items-center justify-center gap-3 text-lg sm:text-xl font-semibold dark:text-gray-300"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>
							<Spinner />
						</div>
					</div>
				{:else}
					<h2 class="text-2xl font-bold text-gray-700 dark:text-white mb-4">
						{#if $config?.onboarding ?? false}
							{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
						{:else if mode === 'ldap'}
							{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
						{:else if mode === 'signin'}
							{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
						{:else}
							{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
						{/if}
					</h2>

					<form
						class="flex flex-col space-y-4"
						on:submit={(e) => {
					e.preventDefault();
					submitHandler();
				}}
					>
						{#if mode === 'signup'}
							<div>
								<label class="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">{$i18n.t('Name')}</label>
								<input
									bind:value={name}
									type="text"
									class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
									placeholder={$i18n.t('Enter Your Full Name')}
									required
								/>
							</div>
						{/if}

						{#if mode === 'ldap'}
							<div>
								<label
									class="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">{$i18n.t('Username')}</label>
								<input
									bind:value={ldapUsername}
									type="text"
									class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
									required
								/>
							</div>
						{:else}
							<div>
								<label
									class="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">{$i18n.t('Email')}</label>
								<input
									bind:value={email}
									type="email"
									class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
									required
								/>
							</div>
						{/if}

						<div>
							<label
								class="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">{$i18n.t('Password')}</label>
							<input
								bind:value={password}
								type="password"
								class="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
								required
							/>
						</div>

						<button
							class="bg-primary-500 hover:bg-primary-700 text-white py-2 px-4 rounded-lg font-medium transition dark:bg-blue-600 dark:hover:bg-blue-700"
							type="submit"
						>
							{mode === 'signin'
								? $i18n.t('Sign in')
								: ($config?.onboarding ?? false)
									? $i18n.t('Create Admin Account')
									: $i18n.t('Create Account')}
						</button>

						{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
							<div class="text-sm text-gray-600 dark:text-gray-300 text-center mt-4">
								{mode === 'signin'
									? $i18n.t("Don't have an account?")
									: $i18n.t('Already have an account?')}
								<button
									class="font-medium text-blue-500 underline hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-600 ml-1"
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
					</form>
				{/if}
			</div>
		</div>
	{/if}
</div>