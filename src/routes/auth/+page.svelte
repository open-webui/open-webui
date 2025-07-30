<script>
	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';
	import { generateInitialsImage } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Visible from '$lib/components/icons/visible.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let loaded = false;
	let showInitialScreen = true;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';
	let name = '';
	let email = '';
	let password = '';
	let ldapUsername = '';
	let showPassword = false;

	const querystringValue = (key) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
	};
	// Navigate to terms page
	function navigateToTerms() {
		goto('/terms');
	}

	// Navigate to privacy policy page
	function navigateToPrivacy() {
		goto('/privacy');
	}

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
		if (!$page.url.hash) return;
		const hash = $page.url.hash.substring(1);
		if (!hash) return;
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) return;
		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) return;
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();
		loaded = true;
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		}
	});
</script>

<svelte:head>
	<title>{`${$WEBUI_NAME}`}</title>
</svelte:head>

<div class=" dark login min-h-screen w-full flex justify-center relative">
	{#if loaded}
		<div class="relative w-full h-full flex flex-col">
			<!-- Login using Credentials button in top right corner -->

			<div id="splash-screen" class="login">
				{#if showInitialScreen}
					<div class="relative w-full h-full flex flex-col">
						<div class="absolute top-[28px] right-[28px] z-10">
							<button
								type="button"
								class="text-[14px] text-[#CEE7FF] leading-normal font-medium cursor-pointer"
								on:click={() => (showInitialScreen = false)}
							>
								{$i18n.t('Login using Credentials')}
							</button>
						</div>
						<div class="splash-content">
							<div class="logo-container">
								<img src="/GovGPT.gif" alt="GovGPT Logo" class="logo-image" />
							</div>
							<img src="/GovGPT-background.gif" alt="GovGPT Logo" class="logo-image-bottom" />
							<div class="title-container">
								<h1 class="govgpt-title">GovGPT</h1>
							</div>
							<div class="tagline-container">
								<p class="tagline">{$i18n.t('Amplifying Government Potential')}</p>
							</div>
							<p
								class="hidden sm:block mb-[30px] text-typography-titles text-[16px] leading-[24px]"
							>
								{$i18n.t('Use your work email to log in & get started!')}
							</p>
							<div class="absolute sm:static bottom-[20px]">
								<button
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
									}}
									class="mb-[24px] text-[14px] text-[rgba(7, 45, 90, 0.88)] py-[6px] pl-[8px] pr-[16px] w-[334px] h-[48px] rounded-[12px] bg-[linear-gradient(90deg,_#A5C7E6_0%,_#CEE7FF_38.94%,_#A5C7E6_100%)] shadow-[inset_6px_3px_8px_0_#BFDBF6]"
								>
									{$i18n.t('Log in using SSO')}
								</button>
								<p class="text-typography-titles text-[12px] leading-[16px] max-w-[240px] mx-auto">
									{$i18n.t('By continuing, you agree to our')}
									<button
										on:click={() => {
											navigateToTerms();
										}}
										class="text-[#89B7FF] underline cursor-pointer">{$i18n.t('Terms')}</button
									>
									{$i18n.t('and have read our')}
									<button
										on:click={() => {
											navigateToPrivacy();
										}}
										class="text-[#89B7FF] underline cursor-pointer"
										>{$i18n.t('Privacy Policy')}</button
									>.
								</p>
							</div>
						</div>
					</div>
				{:else}
					<div class="login min-h-screen w-full flex justify-center relative">
						<!-- Login using SSO button in top right corner -->
						<div class="absolute top-[28px] right-[28px] z-30">
							<button
								type="button"
								class="text-sm text-blue-200 cursor-pointer hover:text-blue-100 bg-transparent border-none p-2"
								on:click={() => (showInitialScreen = true)}
							>
								{$i18n.t('Login using SSO')}
							</button>
						</div>

						<div class="login__right z-20 p-4 flex-1 flex items-center justify-center">
							<div class="login-box w-full max-w-[365px] rounded-2xl">
								<form
									class="flex flex-col justify-center"
									on:submit={(e) => {
										e.preventDefault();
										submitHandler();
									}}
								>
									<div
										class="text-center mb-[34px] text-[20px] leading-[34px] text-typography-titles"
									>
										{$i18n.t('Login with your email address')}
									</div>
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
										<div class="flex flex-col mt-4">
											{#if mode === 'ldap'}
												<div class="mb-4">
													<label
														for="username"
														class="text-left pb-[8px] text-[14px] leading-[22px] font-medium text-typography-titles"
													>
														{$i18n.t('Username')}
													</label>
													<input
														bind:value={ldapUsername}
														type="text"
														class="text-[14px] leading-[22px] w-full p-[8px] pl-[16px] border rounded-[6px] bg-neutrals-50 text-neutrals-400"
														autocomplete="username"
														name="username"
														id="username"
														placeholder={$i18n.t('Enter Your Username')}
														required
													/>
												</div>
											{:else}
												<div class="mb-4">
													<label
														for="email"
														class=" text-left pb-[8px] text-[14px] leading-[22px] font-medium text-typography-titles"
													>
														{$i18n.t('Email address')}
													</label>
													<input
														bind:value={email}
														type="email"
														id="email"
														class="appearance-none text-[14px] leading-[22px] w-full p-[8px] pl-[16px] rounded-[6px] bg-[#010E1D] text-neutrals-400 invalid:border-red-500 invalid:focus:ring-red-500"
														autocomplete="email"
														name="email"
														placeholder={$i18n.t('Email or phone number')}
														required
													/>
												</div>
											{/if}
											<div class="mb-4">
												<label
													for="password"
													class="text-left pb-[8px] text-[14px] leading-[22px] font-medium text-typography-titles"
												>
													{$i18n.t('Password')}
												</label>
												<div class="relative">
													{#if showPassword}
														<input
															bind:value={password}
															type="text"
															id="password"
															class="text-[14px] leading-[22px] w-full p-[8px] pl-[16px] pr-[48px] rounded-[6px] bg-[#010E1D] text-neutrals-400"
															placeholder={$i18n.t('Enter Your Password')}
															autocomplete="current-password"
															name="current-password"
															required
														/>
													{:else}
														<input
															bind:value={password}
															type="password"
															id="password"
															class="text-[14px] leading-[22px] w-full p-[8px] pl-[16px] pr-[48px] rounded-[6px] bg-[#010E1D] text-neutrals-400"
															placeholder={$i18n.t('Enter Your Password')}
															autocomplete="current-password"
															name="current-password"
															required
														/>
													{/if}
													<button
														type="button"
														class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
														on:click={() => (showPassword = !showPassword)}
													>
														<Visible className="w-5 h-5" />
													</button>
												</div>
											</div>
										</div>
									{/if}
									<div class="mt-4 w-full max-w-[365px] absolute sm:static bottom-[20px]">
										{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
											{#if mode === 'ldap'}
												<button
													class="cursor-pointer text-[14px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-[rgba(7, 45, 90, 0.88)] bg-[linear-gradient(90deg,_#A5C7E6_0%,_#CEE7FF_38.94%,_#A5C7E6_100%)] shadow-[inset_6px_3px_8px_0_#BFDBF6]"
													type="submit"
												>
													{$i18n.t('Authenticate')}
												</button>
											{:else}
												<button
													class="mb-[24px] cursor-pointer text-[14px] leading-[24px] py-[6px] pl-[8px] pr-[16px] w-full h-[48px] rounded-[12px] text-[rgba(7, 45, 90, 0.88)] bg-[linear-gradient(90deg,_#A5C7E6_0%,_#CEE7FF_38.94%,_#A5C7E6_100%)] shadow-[inset_6px_3px_8px_0_#BFDBF6]"
													type="submit"
												>
													{mode === 'signin' ? $i18n.t('Sign in') : $i18n.t('Create Account')}
												</button>
											{/if}
										{/if}
										<p
											class="block sm:hidden text-typography-titles text-[12px] leading-[16px] max-w-[240px] mx-auto"
										>
											{$i18n.t('By continuing, you agree to our')}
											<button
												on:click={() => {
													navigateToTerms();
												}}
												class="text-[#89B7FF] underline cursor-pointer">{$i18n.t('Terms')}</button
											>
											{$i18n.t('and have read our')}
											<button
												on:click={() => {
													navigateToPrivacy();
												}}
												class="text-[#89B7FF] underline cursor-pointer"
												>{$i18n.t('Privacy Policy')}</button
											>.
										</p>
									</div>
								</form>
							</div>
						</div>
						<img src="/GovGPT-background.gif" alt="GovGPT Logo" class="logo-image-bottom" />
					</div>
				{/if}
				<div
					class="p-[16px] hidden sm:block fixed bottom-0 left-0 right-0 text-center text-typography-subtext text-[10px] leading-[16px] bg-[#072D5A] z-50"
				>
					<span class="text-typography-titles">{$i18n.t('Disclaimer')}:</span>
					{$i18n.t(
						'GovGPT is powered by artificial intelligence and may occasionally produce incorrect or outdated responses. Please verify critical information from official sources or consult your department head for confirmation.'
					)}
				</div>
			</div>
		</div>
	{/if}
</div>
