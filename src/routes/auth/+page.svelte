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
	@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Inter:wght@400;500;600&display=swap');

	* {
		font-family: 'Nunito', sans-serif;
	}

	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(24px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes slideInLeft {
		from {
			opacity: 0;
			transform: translateX(-40px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@keyframes blobFloat1 {
		0%, 100% { transform: translate(0, 0) scale(1); }
		33% { transform: translate(20px, -15px) scale(1.05); }
		66% { transform: translate(-10px, 20px) scale(0.97); }
	}

	@keyframes blobFloat2 {
		0%, 100% { transform: translate(0, 0) scale(1); }
		33% { transform: translate(-25px, 10px) scale(1.04); }
		66% { transform: translate(15px, -20px) scale(0.98); }
	}

	@keyframes blobFloat3 {
		0%, 100% { transform: translate(0, 0) scale(1); }
		33% { transform: translate(10px, 25px) scale(0.96); }
		66% { transform: translate(-20px, -10px) scale(1.06); }
	}

	@keyframes decorFloat {
		0%, 100% { transform: translateY(0); opacity: 0.6; }
		50% { transform: translateY(-8px); opacity: 0.9; }
	}

	.animate-fade-up {
		animation: fadeInUp 0.7s cubic-bezier(0.22, 1, 0.36, 1) forwards;
	}

	.animate-slide-left {
		animation: slideInLeft 0.7s cubic-bezier(0.22, 1, 0.36, 1) forwards;
	}

	/* LEFT PANEL */
	.left-panel {
		position: relative;
		overflow: hidden;
		background: linear-gradient(145deg, #f97316 0%, #fb923c 32%, #ea580c 68%, #c2410c 100%);
		border-radius: 12px;
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
	}

	/* Blurred blob shapes */
	.blob {
		position: absolute;
		border-radius: 50%;
		filter: blur(60px);
		opacity: 0.55;
	}

	.blob-1 {
		width: 380px;
		height: 380px;
		background: radial-gradient(circle, #fde68a 0%, #f59e0b 60%, transparent 100%);
		top: -80px;
		left: -80px;
		animation: blobFloat1 8s ease-in-out infinite;
	}

	.blob-2 {
		width: 320px;
		height: 320px;
		background: radial-gradient(circle, #fed7aa 0%, #fb923c 50%, transparent 100%);
		bottom: -60px;
		right: -60px;
		animation: blobFloat2 10s ease-in-out infinite;
	}

	.blob-3 {
		width: 260px;
		height: 260px;
		background: radial-gradient(circle, #fff7ed 0%, #fdba74 50%, transparent 100%);
		top: 45%;
		left: 35%;
		animation: blobFloat3 12s ease-in-out infinite;
	}

	.blob-4 {
		width: 200px;
		height: 200px;
		background: radial-gradient(circle, #dc2626 0%, #b91c1c 50%, transparent 100%);
		top: 20%;
		right: -30px;
		animation: blobFloat1 9s ease-in-out infinite reverse;
		opacity: 0.35;
	}

	/* Decorative dots grid */
	.dots-grid {
		position: absolute;
		top: 20px;
		right: 30px;
		display: grid;
		grid-template-columns: repeat(5, 8px);
		gap: 6px;
		opacity: 0.35;
	}

	.dot {
		width: 4px;
		height: 4px;
		border-radius: 50%;
		background: white;
	}

	/* Decorative line circles */
	.deco-circle {
		position: absolute;
		border-radius: 50%;
		border: 1.5px solid rgba(255,255,255,0.35);
		animation: decorFloat 4s ease-in-out infinite;
	}

	/* Decorative cross / plus */
	.deco-plus {
		position: absolute;
		color: rgba(255,255,255,0.45);
		font-size: 22px;
		font-weight: 300;
		line-height: 1;
		animation: decorFloat 5s ease-in-out infinite;
	}

	/* Wavy SVG lines */
	.wavy-lines {
		position: absolute;
		bottom: 0;
		left: 0;
		width: 100%;
		opacity: 0.18;
		pointer-events: none;
	}

	/* Logo badge */
	.logo-badge {
		background: rgba(255, 255, 255, 0.22);
		border: 1px solid rgba(255, 255, 255, 0.72);
		border-radius: 8px;
		padding: 8px 12px;
		display: flex;
		align-items: center;
		gap: 10px;
	}

	/* RIGHT PANEL */
	.right-panel {
		background: transparent;
	}

	.dark .right-panel {
		background: transparent;
	}

	/* Input */
	.auth-input {
		width: 100%;
		padding: 12px 44px;
		border-radius: 999px;
		border: 1px solid #d9dde3;
		background: #f3f4f6;
		font-size: 14px;
		color: #111827;
		transition: all 0.25s ease;
		outline: none;
		font-family: 'Nunito', sans-serif;
	}

	.dark .auth-input {
		border-color: #374151;
		background: #1f2937;
		color: #f9fafb;
	}

	.auth-input:focus {
		border-color: #fb923c;
		background: #fff;
		box-shadow: 0 0 0 3px rgba(251, 146, 60, 0.18);
	}

	.dark .auth-input:focus {
		background: #1f2937;
	}

	.input-wrap {
		position: relative;
	}

	.input-icon {
		position: absolute;
		left: 16px;
		top: 50%;
		transform: translateY(-50%);
		color: #9ca3af;
		width: 16px;
		height: 16px;
	}

	/* Checkbox */
	.checkbox-custom {
		width: 16px;
		height: 16px;
		border-radius: 4px;
		border: 1.5px solid #d1d5db;
		appearance: none;
		cursor: pointer;
		transition: all 0.2s;
		background: white;
		position: relative;
	}

	.checkbox-custom:checked {
		background: #f97316;
		border-color: #f97316;
	}

	.checkbox-custom:checked::after {
		content: '';
		position: absolute;
		left: 4px;
		top: 1px;
		width: 5px;
		height: 8px;
		border: 2px solid white;
		border-top: none;
		border-left: none;
		transform: rotate(45deg);
	}

	/* Submit button */
	.btn-submit {
		width: 100%;
		padding: 14px;
		border-radius: 999px;
		background: linear-gradient(135deg, #ff7a17 0%, #fb5f00 100%);
		color: white;
		font-weight: 800;
		font-size: 15px;
		letter-spacing: 0.02em;
		border: none;
		cursor: pointer;
		transition: all 0.3s ease;
		position: relative;
		overflow: hidden;
		font-family: 'Nunito', sans-serif;
	}

	.btn-submit:hover {
		transform: translateY(-1px);
		box-shadow: 0 10px 24px rgba(251, 95, 0, 0.34);
	}

	.btn-submit::after {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.18) 50%, transparent 100%);
		transform: translateX(-100%);
		transition: transform 0.5s ease;
	}

	.btn-submit:hover::after {
		transform: translateX(100%);
	}

	/* OAuth button */
	.btn-oauth {
		width: 100%;
		padding: 12px 20px;
		border-radius: 999px;
		border: 1.5px solid #e5e7eb;
		background: white;
		font-size: 14px;
		font-weight: 600;
		color: #374151;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		transition: all 0.25s ease;
		font-family: 'Nunito', sans-serif;
	}

	.dark .btn-oauth {
		border-color: #374151;
		background: #1f2937;
		color: #d1d5db;
	}

	.btn-oauth:hover {
		border-color: #f97316;
		background: #fff7ed;
		box-shadow: 0 4px 15px rgba(249, 115, 22, 0.15);
	}

	.dark .btn-oauth:hover {
		background: #292524;
	}

	/* Divider */
	.divider {
		display: flex;
		align-items: center;
		gap: 12px;
		margin: 20px 0;
	}

	.divider-line {
		flex: 1;
		height: 1px;
		background: #e5e7eb;
	}

	.dark .divider-line {
		background: #374151;
	}

	.divider-text {
		font-size: 13px;
		color: #9ca3af;
		white-space: nowrap;
		font-weight: 500;
	}

	/* Link */
	.link-orange {
		color: #f97316;
		font-weight: 700;
		cursor: pointer;
		transition: color 0.2s;
		background: none;
		border: none;
		font-family: 'Nunito', sans-serif;
		font-size: inherit;
	}

	.link-orange:hover {
		color: #ea580c;
	}

	/* Auth card (right side) */
	.auth-card-inner {
		width: 100%;
		max-width: 430px;
	}

	/* Heading */
	.auth-title {
		font-size: 50px;
		font-weight: 900;
		color: #111827;
		margin-bottom: 6px;
		line-height: 1.05;
	}

	.dark .auth-title {
		color: #f9fafb;
	}

	.auth-subtitle {
		font-size: 14px;
		color: #6b7280;
		font-weight: 500;
	}

	.dark .auth-subtitle {
		color: #9ca3af;
	}

	/* Form label */
	.form-label {
		display: block;
		font-size: 13px;
		font-weight: 700;
		color: #374151;
		margin-bottom: 6px;
		font-family: 'Nunito', sans-serif;
	}

	.dark .form-label {
		color: #d1d5db;
	}

	/* Welcome badge on left */
	.welcome-badge {
		background: rgba(255,255,255,0.15);
		backdrop-filter: blur(8px);
		border: 1px solid rgba(255,255,255,0.3);
		border-radius: 999px;
		padding: 6px 16px;
		display: inline-block;
		font-size: 13px;
		font-weight: 600;
		color: rgba(255,255,255,0.9);
		margin-bottom: 16px;
	}

	/* Security note */
	.security-note {
		background: rgba(255,255,255,0.12);
		backdrop-filter: blur(8px);
		border: 1px solid rgba(255,255,255,0.25);
		border-radius: 16px;
		padding: 14px 16px;
	}

	@media (max-width: 1023px) {
		.auth-title {
			font-size: 40px;
		}
	}

	@media (max-width: 640px) {
		.auth-title {
			font-size: 34px;
		}
	}
</style>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full min-h-screen bg-white dark:bg-white flex items-center justify-center overflow-hidden p-4 sm:p-8">
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-50" />

	{#if loaded}
		<div class="w-full max-w-[1180px] h-[calc(100dvh-2rem)] max-h-[760px] flex items-stretch gap-8 lg:gap-12">
		<!-- ========== LEFT PANEL ========== -->
		<div class="hidden lg:flex lg:w-[48%] left-panel p-6 text-white">
			<div class="blob blob-1"></div>
			<div class="blob blob-2"></div>
			<div class="blob blob-3"></div>
			<div class="blob blob-4"></div>

			<div class="dots-grid">
				{#each Array(20) as _}
					<div class="dot"></div>
				{/each}
			</div>

			<svg class="wavy-lines" viewBox="0 0 600 400" fill="none" xmlns="http://www.w3.org/2000/svg" style="height:180px;">
				<path d="M-20 300 Q80 240 160 280 Q240 320 320 260 Q400 200 480 240 Q560 280 640 220" stroke="white" stroke-width="2" fill="none"/>
				<path d="M-20 340 Q80 280 160 320 Q240 360 320 300 Q400 240 480 280 Q560 320 640 260" stroke="white" stroke-width="1.5" fill="none" opacity="0.7"/>
			</svg>

			<div class="w-full animate-slide-left flex flex-col relative z-10">
				<div class="logo-badge mb-14">
					<img
						id="logo"
						crossorigin="anonymous"
						src="{WEBUI_BASE_URL}/static/splash.png"
						class="w-9 h-9 rounded-lg"
						alt="logo"
					/>
					<span class="text-3xl font-extrabold tracking-wide">{$WEBUI_NAME}</span>
				</div>

				<h1 class="font-black mb-2 leading-tight text-[48px]">
					{#if mode === 'signup'}
						Get Started!
					{:else}
						Welcome to {$WEBUI_NAME}!
					{/if}
				</h1>

				<p class="text-white/90 font-semibold text-lg max-w-[340px] leading-relaxed">
					{#if $config?.onboarding ?? false}
						Create your admin account to continue using {$WEBUI_NAME}.
					{:else if mode === 'signin'}
						You can sign in to access with your existing account.
					{:else}
						Fill in your details to create your new account.
					{/if}
				</p>
			</div>
		</div>

		<!-- ========== RIGHT PANEL ========== -->
		<div class="w-full lg:w-[52%] right-panel flex items-center justify-center p-2 sm:p-6 lg:p-10">
			<div class="auth-card-inner animate-fade-up">

				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold text-gray-900 dark:text-gray-100">
						<div>{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</div>
						<div><Spinner /></div>
					</div>
				{:else}

					<!-- Mobile logo -->
					<div class="lg:hidden flex items-center gap-3 mb-8">
						<div style="background:rgba(249,115,22,0.12);border-radius:14px;padding:10px;">
							<img crossorigin="anonymous" src="{WEBUI_BASE_URL}/static/splash.png" class="w-8 h-8 rounded-lg" alt="logo" />
						</div>
						<span class="text-xl font-extrabold text-gray-900 dark:text-white">{$WEBUI_NAME}</span>
					</div>

					<!-- Title -->
					<div class="mb-8">
						<h2 class="auth-title">
							{#if mode === 'signin'}
								Sign In
							{:else if mode === 'signup'}
								{($config?.onboarding ?? false) ? 'Get Started' : 'Create Account'}
							{:else}
								Sign in with LDAP
							{/if}
						</h2>
						<p class="auth-subtitle">
							{#if $config?.onboarding ?? false}
								Set up your admin account to begin
							{:else if mode === 'signin'}
								Enter your credentials to continue
							{:else}
								Fill in your details to get started
							{/if}
						</p>
					</div>

					<!-- Form -->
					<form
						class="space-y-4"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						{#if $config?.features.enable_login_form || $config?.features.enable_ldap}

							{#if mode === 'signup'}
								<div>
									<label class="form-label">{$i18n.t('Full Name')}</label>
									<div class="input-wrap">
										<svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
										</svg>
										<input
											bind:value={name}
											type="text"
											class="auth-input"
											autocomplete="name"
											placeholder={$i18n.t('Enter Your Full Name')}
											required
										/>
									</div>
								</div>
							{/if}

							{#if mode === 'ldap'}
								<div>
									<label class="form-label">{$i18n.t('Username')}</label>
									<div class="input-wrap">
										<svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
										</svg>
										<input
											bind:value={ldapUsername}
											type="text"
											class="auth-input"
											autocomplete="username"
											name="username"
											placeholder={$i18n.t('Enter Your Username')}
											required
										/>
									</div>
								</div>
							{:else}
								<div>
									<label class="form-label">{$i18n.t('Email')}</label>
									<div class="input-wrap">
										<svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
										</svg>
										<input
											bind:value={email}
											type="email"
											class="auth-input"
											autocomplete="email"
											name="email"
											placeholder="Username or email"
											required
										/>
									</div>
								</div>
							{/if}

							<div>
								<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
									<label class="form-label" style="margin-bottom:0;">{$i18n.t('Password')}</label>
									{#if mode === 'signin'}
										<button type="button" class="link-orange" style="font-size:12px;">Forgot password?</button>
									{/if}
								</div>
								<div class="input-wrap">
									<svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
									</svg>
									<input
										bind:value={password}
										type="password"
										class="auth-input"
										placeholder="••••••••"
										autocomplete="current-password"
										name="current-password"
										required
									/>
								</div>
							</div>

							<!-- Remember me -->
							{#if mode === 'signin'}
								<div style="display:flex;align-items:center;gap:8px;">
									<input type="checkbox" class="checkbox-custom" id="remember" />
									<label for="remember" style="font-size:13px;color:#6b7280;font-weight:600;cursor:pointer;">Remember me</label>
								</div>
							{/if}
						{/if}

						<!-- Submit -->
						<div style="padding-top:4px;">
							<button class="btn-submit" type="submit">
								{#if mode === 'ldap'}
									{$i18n.t('Authenticate')}
								{:else if mode === 'signin'}
									{$i18n.t('Sign In')}
								{:else}
									{($config?.onboarding ?? false) ? $i18n.t('Create Admin Account') : $i18n.t('Create Account')}
								{/if}
							</button>
						</div>

						<!-- Toggle -->
						{#if !($config?.onboarding ?? false) && mode !== 'ldap'}
							<div style="text-align:center;font-size:14px;color:#6b7280;padding-top:4px;">
								{mode === 'signin' ? "New here?" : 'Already have an account?'}
								<button
									class="link-orange"
									style="margin-left:4px;"
									type="button"
									on:click={() => {
										mode = mode === 'signin' ? 'signup' : 'signin';
									}}
								>
									{mode === 'signin' ? $i18n.t('Create an Account') : $i18n.t('Sign In')}
								</button>
							</div>
						{/if}
					</form>

					<!-- OAuth -->
					{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
						<div class="divider">
							<div class="divider-line"></div>
							<span class="divider-text">{$i18n.t('Or continue with')}</span>
							<div class="divider-line"></div>
						</div>

						<div class="space-y-3">
							{#if $config?.oauth?.providers?.google}
								<button class="btn-oauth" on:click={() => { window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`; }}>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" style="width:18px;height:18px;">
										<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
										<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
										<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
										<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
									</svg>
									{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}
								</button>
							{/if}

							{#if $config?.oauth?.providers?.microsoft}
								<button class="btn-oauth" on:click={() => { window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`; }}>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" style="width:18px;height:18px;">
										<rect x="1" y="1" width="9" height="9" fill="#f25022"/>
										<rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
										<rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
										<rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
									</svg>
									{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}
								</button>
							{/if}

							{#if $config?.oauth?.providers?.github}
								<button class="btn-oauth" on:click={() => { window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`; }}>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width:18px;height:18px;">
										<path fill="currentColor" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"/>
									</svg>
									{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}
								</button>
							{/if}

							{#if $config?.oauth?.providers?.oidc}
								<button class="btn-oauth" on:click={() => { window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`; }}>
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:18px;height:18px;">
										<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"/>
									</svg>
									{$i18n.t('Continue with {{provider}}', { provider: $config?.oauth?.providers?.oidc ?? 'SSO' })}
								</button>
							{/if}
						</div>
					{/if}

					<!-- LDAP toggle -->
					{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
						<div style="margin-top:20px;text-align:center;">
							<button
								class="link-orange"
								style="font-size:13px;"
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

				{/if}
			</div>
		</div>
		</div>
	{/if}
</div>