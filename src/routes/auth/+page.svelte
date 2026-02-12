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

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = '/static/favicon-dark.png';

				darkImage.onload = () => {
					logo.src = '/static/favicon-dark.png';
					logo.style.filter = '';
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)';
				};
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

<style>
	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes slideInLeft {
		from {
			opacity: 0;
			transform: translateX(-30px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.8;
		}
	}

	.animate-fade-up {
		animation: fadeInUp 0.6s ease-out forwards;
	}

	.animate-slide-left {
		animation: slideInLeft 0.6s ease-out forwards;
	}

	.stat-card {
		background: rgba(255, 255, 255, 0.15);
		backdrop-filter: blur(10px);
		border: 1px solid rgba(255, 255, 255, 0.3);
		transition: all 0.3s ease;
	}

	.stat-card:hover {
		background: rgba(255, 255, 255, 0.2);
		transform: translateY(-5px);
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
	}

	.input-field {
		transition: all 0.3s ease;
		border: 2px solid #e5e7eb;
		background: white;
	}

	.dark .input-field {
		border-color: #374151;
		background: #1f2937;
	}

	.input-field:focus {
		outline: none;
		border-color: #f97316;
		box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
	}

	.btn-orange {
		background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
	}

	.btn-orange:hover {
		transform: translateY(-2px);
		box-shadow: 0 10px 25px rgba(249, 115, 22, 0.4);
	}

	.btn-orange::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
		transition: left 0.5s;
	}

	.btn-orange:hover::before {
		left: 100%;
	}

	.btn-outline {
		transition: all 0.3s ease;
		border: 2px solid #e5e7eb;
		background: white;
	}

	.dark .btn-outline {
		border-color: #374151;
		background: #1f2937;
	}

	.btn-outline:hover {
		border-color: #f97316;
		background: rgba(249, 115, 22, 0.05);
	}

	.tab-button {
		transition: all 0.3s ease;
		position: relative;
	}

	.tab-button.active {
		background: #f97316;
		color: white;
	}

	.tab-button:not(.active):hover {
		background: rgba(249, 115, 22, 0.1);
	}

	.logo-glow {
		filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.5));
	}

	.orange-gradient {
		background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
	}

	.auth-card {
		background: white;
		border-radius: 24px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
	}

	.dark .auth-card {
		background: #1f2937;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
	}

	.building-bg {
		object-fit: cover;
		object-position: center;
	}
</style>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] flex overflow-hidden">
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-50" />

	{#if loaded}
		<!-- Left Panel - Orange with Building Background -->
		<div class="hidden lg:flex lg:w-1/2 text-white p-12 flex-col justify-between relative overflow-hidden">
			<!-- Background Image -->
			<div class="absolute inset-0">
				<!-- Replace this src with your actual building image path in /static folder -->
				<!-- For now, using a base64 or external URL as fallback -->
				<div class="w-full h-full bg-gradient-to-br from-cyan-600 to-cyan-800 building-bg"></div>
			</div>
			
			<!-- Orange Overlay -->
			<div class="absolute inset-0 orange-gradient opacity-85"></div>
			
			<!-- Gradient Overlay for better text readability -->
			<div class="absolute inset-0 bg-gradient-to-br from-orange-600/50 via-orange-500/30 to-transparent"></div>

			<!-- Content -->
			<div class="relative z-10 animate-slide-left">
				<!-- Logo -->
				<div class="flex items-center space-x-3 mb-16">
					<div class="bg-white/20 backdrop-blur-sm p-3 rounded-2xl logo-glow">
						<img
							id="logo"
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/splash.png"
							class="w-8 h-8 rounded-lg"
							alt="logo"
						/>
					</div>
					<span class="text-2xl font-bold">{$WEBUI_NAME}</span>
				</div>

				<!-- Welcome Message -->
				<div class="mb-12">
					<h1 class="text-5xl font-bold mb-4">
						{#if mode === 'signin'}
							Welcome Back
						{:else if mode === 'signup'}
							Get Started
						{:else}
							Welcome Back
						{/if}
					</h1>
					<p class="text-xl text-white/90">
						{#if $config?.onboarding ?? false}
							Create your admin account to continue
						{:else}
							{mode === 'signin' ? 'Sign in to continue' : 'Create your account to get started'}
						{/if}
					</p>
				</div>

				<!-- Stats Grid -->
				{#if !($config?.onboarding ?? false)}
					<div class="grid grid-cols-2 gap-4">
						<div class="stat-card rounded-2xl p-6">
							<div class="text-sm text-white/80 mb-1">Active Users</div>
							<div class="text-3xl font-bold">10K+</div>
						</div>
						<div class="stat-card rounded-2xl p-6">
							<div class="text-sm text-white/80 mb-1">Conversations</div>
							<div class="text-3xl font-bold">50K+</div>
						</div>
						<div class="stat-card rounded-2xl p-6">
							<div class="text-sm text-white/80 mb-1">Uptime</div>
							<div class="text-3xl font-bold">99.9%</div>
						</div>
						<div class="stat-card rounded-2xl p-6">
							<div class="text-sm text-white/80 mb-1">Support</div>
							<div class="text-3xl font-bold">24/7</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer Info -->
			{#if $config?.onboarding ?? false}
				<div class="relative z-10 bg-white/15 backdrop-blur-md rounded-2xl p-4 border border-white/30">
					<p class="text-sm text-white/95">
						<span class="font-semibold">🔒 Secure & Private:</span> {$WEBUI_NAME}
						{$i18n.t('does not make any external connections, and your data stays securely on your locally hosted server.')}
					</p>
				</div>
			{/if}
		</div>

		<!-- Right Panel - Auth Form -->
		<div class="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 bg-gray-50 dark:bg-gray-900">
			<div class="w-full max-w-md animate-fade-up">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="auth-card p-8 sm:p-10">
						<div class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold text-gray-900 dark:text-gray-100">
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>
							<div>
								<Spinner />
							</div>
						</div>
					</div>
				{:else}
					<div class="auth-card p-8 sm:p-10">
						<!-- Mobile Logo -->
						<div class="lg:hidden flex items-center justify-center mb-8">
							<div class="bg-orange-500/10 p-3 rounded-2xl">
								<img
									crossorigin="anonymous"
									src="{WEBUI_BASE_URL}/static/splash.png"
									class="w-10 h-10 rounded-lg"
									alt="logo"
								/>
							</div>
						</div>

						<!-- Header -->
						<div class="text-center mb-8">
							<h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
								{#if mode === 'signin'}
									Welcome Back
								{:else if mode === 'signup'}
									{($config?.onboarding ?? false) ? 'Get Started' : 'Create Account'}
								{:else}
									Sign in with LDAP
								{/if}
							</h2>
							<p class="text-gray-600 dark:text-gray-400">
								{#if $config?.onboarding ?? false}
									Create your admin account
								{:else}
									{mode === 'signin' ? 'Sign in to continue' : 'Fill in your details to get started'}
								{/if}
							</p>
						</div>

						<!-- Tabs for Email/Phone (if needed) -->
						{#if ($config?.features.enable_login_form || $config?.features.enable_ldap) && mode !== 'ldap'}
							<div class="flex gap-2 mb-6 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl">
								<button
									class="tab-button active flex-1 py-2.5 rounded-lg font-medium text-sm"
									type="button"
								>
									Email
								</button>
							</div>
						{/if}

						<form
							class="space-y-5"
							on:submit={(e) => {
								e.preventDefault();
								submitHandler();
							}}
						>
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								{#if mode === 'signup'}
									<div>
										<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
											{$i18n.t('Full Name')}
										</label>
										<input
											bind:value={name}
											type="text"
											class="input-field w-full px-4 py-3 rounded-xl text-sm text-gray-900 dark:text-gray-100"
											autocomplete="name"
											placeholder={$i18n.t('Enter Your Full Name')}
											required
										/>
									</div>
								{/if}

								{#if mode === 'ldap'}
									<div>
										<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
											{$i18n.t('Username')}
										</label>
										<input
											bind:value={ldapUsername}
											type="text"
											class="input-field w-full px-4 py-3 rounded-xl text-sm text-gray-900 dark:text-gray-100"
											autocomplete="username"
											name="username"
											placeholder={$i18n.t('Enter Your Username')}
											required
										/>
									</div>
								{:else}
									<div>
										<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
											{$i18n.t('Email')}
										</label>
										<input
											bind:value={email}
											type="email"
											class="input-field w-full px-4 py-3 rounded-xl text-sm text-gray-900 dark:text-gray-100"
											autocomplete="email"
											name="email"
											placeholder="name@example.com"
											required
										/>
									</div>
								{/if}

								<div>
									<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
										{$i18n.t('Password')}
									</label>
									<input
										bind:value={password}
										type="password"
										class="input-field w-full px-4 py-3 rounded-xl text-sm text-gray-900 dark:text-gray-100"
										placeholder="••••••••"
										autocomplete="current-password"
										name="current-password"
										required
									/>
								</div>
							{/if}

							<!-- Submit Button -->
							<button
								class="btn-orange w-full py-3.5 rounded-xl font-semibold text-white text-sm shadow-lg"
								type="submit"
							>
								{#if mode === 'ldap'}
									{$i18n.t('Authenticate')}
								{:else if mode === 'signin'}
									{$i18n.t('Sign In')}
								{:else}
									{($config?.onboarding ?? false) ? $i18n.t('Create Admin Account') : $i18n.t('Create Account')}
								{/if}
							</button>

							<!-- Toggle Sign In/Up -->
							{#if $config?.features.enable_signup && !($config?.onboarding ?? false) && mode !== 'ldap'}
								<div class="text-center text-sm text-gray-600 dark:text-gray-400">
									{mode === 'signin'
										? $i18n.t("Don't have an account?")
										: $i18n.t('Already have an account?')}
									<button
										class="font-semibold text-orange-500 hover:text-orange-600 ml-1"
										type="button"
										on:click={() => {
											if (mode === 'signin') {
												mode = 'signup';
											} else {
												mode = 'signin';
											}
										}}
									>
										{mode === 'signin' ? $i18n.t('Sign Up') : $i18n.t('Sign In')}
									</button>
								</div>
							{/if}
						</form>

						<!-- OAuth Providers -->
						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="relative my-6">
								<div class="absolute inset-0 flex items-center">
									<div class="w-full border-t border-gray-300 dark:border-gray-700"></div>
								</div>
								<div class="relative flex justify-center text-sm">
									<span class="px-4 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
										{$i18n.t('Or continue with')}
									</span>
								</div>
							</div>

							<div class="space-y-3">
								{#if $config?.oauth?.providers?.google}
									<button
										class="btn-outline flex justify-center items-center w-full py-3 rounded-xl font-medium text-sm text-gray-700 dark:text-gray-200"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="w-5 h-5 mr-3">
											<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
											<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
											<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
											<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
										</svg>
										{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}
									</button>
								{/if}

								{#if $config?.oauth?.providers?.microsoft}
									<button
										class="btn-outline flex justify-center items-center w-full py-3 rounded-xl font-medium text-sm text-gray-700 dark:text-gray-200"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="w-5 h-5 mr-3">
											<rect x="1" y="1" width="9" height="9" fill="#f25022"/>
											<rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
											<rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
											<rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
										</svg>
										{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}
									</button>
								{/if}

								{#if $config?.oauth?.providers?.github}
									<button
										class="btn-outline flex justify-center items-center w-full py-3 rounded-xl font-medium text-sm text-gray-700 dark:text-gray-200"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-5 h-5 mr-3">
											<path fill="currentColor" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"/>
										</svg>
										{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}
									</button>
								{/if}

								{#if $config?.oauth?.providers?.oidc}
									<button
										class="btn-outline flex justify-center items-center w-full py-3 rounded-xl font-medium text-sm text-gray-700 dark:text-gray-200"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 mr-3">
											<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"/>
										</svg>
										{$i18n.t('Continue with {{provider}}', { provider: $config?.oauth?.providers?.oidc ?? 'SSO' })}
									</button>
								{/if}
							</div>
						{/if}

						<!-- LDAP Toggle -->
						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<div class="mt-6 text-center">
								<button
									class="text-sm text-gray-600 dark:text-gray-400 hover:text-orange-500 dark:hover:text-orange-400 font-medium transition"
									type="button"
									on:click={() => {
										if (mode === 'ldap')
											mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
										else mode = 'ldap';
									}}
								>
									{mode === 'ldap' ? $i18n.t('Continue with Email') : $i18n.t('Continue with LDAP')}
								</button>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>