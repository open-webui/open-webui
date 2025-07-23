<script>
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

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

	const querystringValue = (key) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

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

	let onboarding = false;

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
					logo.src = '/static/favicon-dark.png';
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

<div class="w-full text-white relative">
	{#if loaded}
		<div class="login flex bg-circle min-h-screen w-full flex justify-center">
			<div class="login__left hidden sm:block w-[40%] bg-login bg-cover bg-top"></div>
			<div class="login__right p-[16px] flex-1 flex items-center justify-center text-center">
				<div class="login-box bg-white p-[32px] shadow-custom w-full md:w-[440px] rounded-[24px]">
					{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
						<div class=" my-auto w-full">
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
						<div class=" w-full">
							<div class="login__sso">
								{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
									{#if $config?.oauth?.providers?.google}
										<button
											class="cursor-pointer w-full px-[8px] py-[16px] rounded-[8px] bg-primary-400 text-[14px] leading-[24px] font-medium text-center mb-[32px] block text-neutrals-white"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.microsoft}
										<button
											class="cursor-pointer w-full px-[8px] py-[16px] rounded-[8px] bg-primary-400 text-[14px] leading-[24px] font-medium text-center mb-[32px] block text-neutrals-white"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.github}
										<button
											class="cursor-pointer w-full px-[8px] py-[16px] rounded-[8px] bg-primary-400 text-[14px] leading-[24px] font-medium text-center mb-[32px] block text-neutrals-white"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.oidc}
										<button
											class="cursor-pointer w-full px-[8px] py-[16px] rounded-[8px] bg-primary-400 text-[14px] leading-[24px] font-medium text-center mb-[32px] block text-neutrals-white"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}

									<hr class="w-full h-px border-0 mb-[32px] bg-neutrals-100" />
								{/if}
							</div>
							<form
								class=" flex flex-col justify-center"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								<div class="mb-[48px] text-2xl font-medium">
									<img
										id="main-logo"
										class="w-full h-full max-h-[60px] object-contain"
										src="/logo.png"
										alt="logo"
										crossorigin="anonymous"
									/>
								</div>
								<!--<div class="mb-1">
								<div class="mb-[48px] text-2xl font-medium">
									<img
										id="main-logo"
										class="w-full h-full max-h-[60px] object-contain"
										src="/logo.png"
										alt="logo"
										crossorigin="anonymous"
									/>
								</div>

								<div class="mt-5 text-lg font-medium" style="color: #424750;">
									Your AI-Powered Assistant for Smarter Government Services
								</div>

								{#if $config?.onboarding ?? false}
									<div class="mt-1 text-xs font-medium text-gray-600 dark:text-gray-500">
										ⓘ {$WEBUI_NAME}
										{$i18n.t(
											'does not make any external connections, and your data stays securely on your locally hosted server.'
										)}
									</div>
								{/if}
							</div>-->

								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									<div class="flex flex-col mt-4">
										{#if mode === 'signup'}
											<div class="mb-4">
												<label
													for="name"
													class="text-[14px] leading-[22px] font-medium text-left mb-1 block text-neutrals-700"
												>
													{$i18n.t('Name')}
												</label>
												<input
													bind:value={name}
													type="text"
													id="name"
													class="text-[14px] leading-[22px] w-full p-[8px] pl-[16px] rounded-[6px] bg-neutrals-50 text-neutrals-400"
													autocomplete="name"
													placeholder={$i18n.t('Enter Your Full Name')}
													required
												/>
											</div>
										{/if}

										{#if mode === 'ldap'}
											<div class="mb-4">
												<label
													for="username"
													class="text-[14px] leading-[22px] font-medium text-left mb-1 block text-neutrals-700"
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
													class="text-[14px] leading-[22px] font-medium text-left mb-1 block text-neutrals-700"
												>
													{$i18n.t('Email')} address
												</label>
												<input
													bind:value={email}
													type="email"
													id="email"
													class="appearance-none text-[14px] leading-[22px] w-full p-[8px] pl-[16px] rounded-[6px] bg-neutrals-50 text-neutrals-400 invalid:border-red-500 invalid:focus:ring-red-500"
													autocomplete="email"
													name="email"
													placeholder={$i18n.t('Enter Your Email')}
													required
												/>
											</div>
										{/if}

										<div class="mb-4">
											<label
												for="password"
												class="text-[14px] leading-[22px] font-medium text-left mb-1 block text-neutrals-700"
											>
												{$i18n.t('Password')}
											</label>
											<input
												bind:value={password}
												type="password"
												id="password"
												class="text-[14px] leading-[22px] w-full p-[8px] pl-[16px] rounded-[6px] bg-neutrals-50 text-neutrals-400"
												placeholder={$i18n.t('Enter Your Password')}
												autocomplete="current-password"
												name="current-password"
												required
											/>
										</div>
									</div>
								{/if}
								<div class="mt-4">
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
										{#if mode === 'ldap'}
											<button
												class="cursor-pointer text-[16px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-neutrals-black bg-neutrals-50"
												type="submit"
											>
												{$i18n.t('Authenticate')}
											</button>
										{:else}
											<button
												class="cursor-pointer text-[16px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-neutrals-black bg-neutrals-50"
												type="submit"
											>
												{mode === 'signin'
													? $i18n.t('Sign in')
													: ($config?.onboarding ?? false)
														? $i18n.t('Create Admin Account')
														: $i18n.t('Create Account')}
											</button>

											{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
												<div class=" mt-4 text-sm text-center">
													{mode === 'signin'
														? $i18n.t("Don't have an account?")
														: $i18n.t('Already have an account?')}

													<button
														class="cursor-pointer text-[16px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-neutrals-black bg-neutrals-50"
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
										{/if}
									{/if}
								</div>
							</form>

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div class="mt-2">
									<button
										class="cursor-pointer text-[16px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-neutrals-black bg-neutrals-50"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										<span
											>{mode === 'ldap'
												? $i18n.t('Continue with Email')
												: $i18n.t('Continue with LDAP')}</span
										>
									</button>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
