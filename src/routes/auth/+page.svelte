<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

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
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import HYULogo36 from '$lib/components/icons/HYULogo36.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
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
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

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

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
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
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

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

<div class="w-full h-screen max-h-[100dvh] relative overflow-hidden" id="auth-page">
	<!-- Background with gradient -->
	<div
		class="w-full h-full absolute top-0 left-0 dark:hidden"
		style="background: radial-gradient(64.28% 58.24% at 50% 0%, #FDFEFE 0%, #E8EAF3 100%);"
	></div>
	<div
		class="w-full h-full absolute top-0 left-0 hidden dark:block"
		style="background: radial-gradient(64.28% 58.24% at 50% 0%, #27282C 0%, #1A1B1C 100%);"
	></div>

	<!-- Ellipse decorations -->
	<div
		class="absolute opacity-70 pointer-events-none"
		style="
			width: 660px;
			height: 660px;
			left: calc(50% - 330px - 313px);
			top: calc(50% - 330px + 110px);
			background: radial-gradient(118.05% 73.83% at 107.62% 47.45%, #076EF4 0%, rgba(7, 110, 244, 0) 83.09%);
			filter: blur(50px);
			transform: rotate(-30deg);
		"
	></div>
	<div
		class="absolute opacity-70 pointer-events-none"
		style="
			width: 432px;
			height: 432px;
			left: calc(50% - 216px + 131px);
			top: calc(50% - 216px - 369px);
			background: radial-gradient(99.77% 99.77% at 100.51% 46.42%, #076EF4 0%, rgba(7, 110, 244, 0) 62.41%);
			filter: blur(30px);
			transform: rotate(152.04deg);
		"
	></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div
			class="fixed min-h-screen w-full flex justify-center items-center font-base z-50 text-gray-950 dark:text-gray-50"
			id="auth-container"
		>
			<div class="w-full px-4 sm:px-10 min-h-screen flex flex-col justify-center items-center py-10 gap-20">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="w-full max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>
							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<!-- Header Section -->
					<div class="flex flex-col items-center gap-5 sm:gap-10">
						<!-- Logo and Title -->
						<div class="flex flex-col items-center gap-4">
							<div class="flex items-center gap-1 sm:gap-4">
								<div class="w-[43px] h-[43px] sm:w-[72px] sm:h-[72px] flex items-center justify-center scale-[1.2] sm:scale-[2] origin-center">
									<HYULogo36 />
								</div>
								<span class="text-title-4 sm:text-title-1 tracking-tight">HYU AI Tutoring Assistant</span>
							</div>
						</div>
						<!-- Welcome Messages -->
						<div class="flex flex-col items-center gap-1 sm:gap-3">
							<p class="text-body-4-medium sm:text-body-2-medium text-center">
								AI 기반 공업수학 튜터링 지원센터에 오신 것을 환영합니다.
							</p>
							<p class="text-title-4 sm:text-title-1 text-center">
								공업수학 전 과정을 AI와 함께 마스터하세요!
							</p>
						</div>
					</div>

					<!-- Login Card -->
					<div
						class="login-card w-full max-w-[343px] sm:max-w-[360px] p-5 sm:p-6 rounded-[20px] flex flex-col items-center gap-4 relative"
					>

						<!-- Lock Icon Circle -->
						<div
							class="icon-circle w-[80px] h-[80px] sm:w-[100px] sm:h-[100px] rounded-full flex items-center justify-center"
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 sm:w-16 sm:h-16 text-gray-950 dark:text-gray-50" viewBox="0 0 24 24" fill="currentColor">
								<path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6h2c0-1.66 1.34-3 3-3s3 1.34 3 3v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm0 12H6V10h12v10zm-6-3c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/>
							</svg>
						</div>

						<!-- Title and Caption -->
						<div class="flex flex-col items-center w-full">
							<h2 class="text-title-3 sm:text-title-2 text-center">바로 시작하기</h2>
						</div>

						<!-- Login Form -->
						<form
							class="flex flex-col w-full gap-3"
							on:submit={(e) => {
								e.preventDefault();
								submitHandler();
							}}
						>
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
								{#if mode === 'signup'}
									<div class="flex flex-col gap-1">
										<label for="name" class="text-body-4-medium text-left">{$i18n.t('Name')}</label>
										<input
											bind:value={name}
											type="text"
											id="name"
											class="w-full px-4 py-2.5 text-body-4 rounded-xl bg-white/50 dark:bg-gray-800/50 border border-gray-200/50 dark:border-gray-600/50 outline-none focus:border-[#076EF4] transition placeholder:text-gray-400"
											autocomplete="name"
											placeholder={$i18n.t('Enter Your Full Name')}
											required
										/>
									</div>
								{/if}

								{#if mode === 'ldap'}
									<div class="flex flex-col gap-1">
										<label for="username" class="text-body-4-medium text-left">{$i18n.t('Username')}</label>
										<input
											bind:value={ldapUsername}
											type="text"
											class="w-full px-4 py-2.5 text-body-4 rounded-xl bg-white/50 dark:bg-gray-800/50 border border-gray-200/50 dark:border-gray-600/50 outline-none focus:border-[#076EF4] transition placeholder:text-gray-400"
											autocomplete="username"
											name="username"
											id="username"
											placeholder={$i18n.t('Enter Your Username')}
											required
										/>
									</div>
								{:else}
									<div class="flex flex-col gap-1">
										<label for="email" class="text-body-4-medium text-left">{$i18n.t('Email')}</label>
										<input
											bind:value={email}
											type="email"
											id="email"
											class="w-full px-4 py-2.5 text-body-4 rounded-xl bg-white/50 dark:bg-gray-800/50 border border-gray-200/50 dark:border-gray-600/50 outline-none focus:border-[#076EF4] transition placeholder:text-gray-400"
											autocomplete="email"
											name="email"
											placeholder={$i18n.t('Enter Your Email')}
											required
										/>
									</div>
								{/if}

								<div class="flex flex-col gap-1">
									<label for="password" class="text-body-4-medium text-left">{$i18n.t('Password')}</label>
									<SensitiveInput
										bind:value={password}
										type="password"
										id="password"
										inputClassName="w-full px-4 py-2.5 text-body-4 rounded-xl bg-white/50 dark:bg-gray-800/50 border border-gray-200/50 dark:border-gray-600/50 outline-none focus:border-[#076EF4] transition placeholder:text-gray-400"
										placeholder={$i18n.t('Enter Your Password')}
										autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
										name="password"
										required
										on:keydown={(e) => {
											if (e.key === 'Enter') {
												e.preventDefault();
												submitHandler();
											}
										}}
									/>
								</div>

								{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
									<div class="flex flex-col gap-1">
										<label for="confirm-password" class="text-body-4-medium text-left">{$i18n.t('Confirm Password')}</label>
										<SensitiveInput
											bind:value={confirmPassword}
											type="password"
											id="confirm-password"
											inputClassName="w-full px-4 py-2.5 text-body-4 rounded-xl bg-white/50 dark:bg-gray-800/50 border border-gray-200/50 dark:border-gray-600/50 outline-none focus:border-[#076EF4] transition placeholder:text-gray-400"
											placeholder={$i18n.t('Confirm Your Password')}
											autocomplete="new-password"
											name="confirm-password"
											required
											on:keydown={(e) => {
												if (e.key === 'Enter') {
													e.preventDefault();
													submitHandler();
												}
											}}
										/>
									</div>
								{/if}

								<!-- Login Button -->
								<button
									class="flex items-center justify-center gap-2 px-5 sm:px-7 py-1.5 sm:py-2 mt-2 rounded-full text-body-3-medium sm:text-body-2-medium text-white transition hover:opacity-90"
									style="background: #076EF4;"
									type="submit"
								>
									<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="currentColor">
										<path d="M11 7L9.6 8.4l2.6 2.6H2v2h10.2l-2.6 2.6L11 17l5-5-5-5zm9 12h-8v2h8c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-8v2h8v14z"/>
									</svg>
									<span>
										{#if mode === 'ldap'}
											{$i18n.t('Authenticate')}
										{:else if mode === 'signin'}
											{$i18n.t('Sign in')}
										{:else if $config?.onboarding ?? false}
											{$i18n.t('Create Admin Account')}
										{:else}
											{$i18n.t('Create Account')}
										{/if}
									</span>
								</button>

								{#if $config?.features.enable_signup && !($config?.onboarding ?? false) && mode !== 'ldap'}
									<div class="text-body-4 text-center text-gray-700 dark:text-gray-300">
										{mode === 'signin'
											? $i18n.t("Don't have an account?")
											: $i18n.t('Already have an account?')}
										<button
											class="font-medium underline text-[#076EF4]"
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
						</form>

						<!-- Divider -->
						<div class="w-full border-t border-gray-200/20 dark:border-gray-600/30 my-2"></div>

						<!-- Hanyang SSO Button (Dummy) -->
						<div class="flex flex-col items-center gap-2 w-full">
							<button
								class="flex items-center justify-center gap-2 px-5 sm:px-7 py-1.5 sm:py-2 rounded-full text-body-3-medium sm:text-body-2-medium text-white transition hover:opacity-90 w-full"
								style="background: #004D87;"
								type="button"
								on:click={() => {
									toast.info('한양대학교 SSO 연동 준비 중입니다.');
								}}
							>
								<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 sm:w-6 sm:h-6" viewBox="0 0 24 24" fill="currentColor">
									<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
								</svg>
								<span>한양대학교 SSO 로그인</span>
							</button>
							<p class="text-caption text-gray-700 dark:text-gray-300">
								(https://api.hanyang.ac.kr 와 연결)
							</p>
						</div>

						<!-- OAuth Providers -->
						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="inline-flex items-center justify-center w-full">
								<hr class="w-24 h-px border-0 bg-gray-200/50 dark:bg-gray-600/30" />
								<span class="px-3 text-body-4 text-gray-700 dark:text-gray-300">{$i18n.t('or')}</span>
								<hr class="w-24 h-px border-0 bg-gray-200/50 dark:bg-gray-600/30" />
							</div>
							<div class="flex flex-col space-y-2 w-full">
								{#if $config?.oauth?.providers?.google}
									<button
										class="flex justify-center items-center bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 transition w-full rounded-full font-medium text-caption sm:text-body-4 py-2 sm:py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-4 sm:size-5 mr-2">
											<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/><path fill="none" d="M0 0h48v48H0z"/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										class="flex justify-center items-center bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 transition w-full rounded-full font-medium text-caption sm:text-body-4 py-2 sm:py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-4 sm:size-5 mr-2">
											<rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										class="flex justify-center items-center bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 transition w-full rounded-full font-medium text-caption sm:text-body-4 py-2 sm:py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-4 sm:size-5 mr-2">
											<path fill="currentColor" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										class="flex justify-center items-center bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 transition w-full rounded-full font-medium text-caption sm:text-body-4 py-2 sm:py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4 sm:size-5 mr-2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: $config?.oauth?.providers?.oidc ?? 'SSO' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.feishu}
									<button
										class="flex justify-center items-center bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-700/50 border border-gray-200/50 dark:border-gray-600/50 transition w-full rounded-full font-medium text-caption sm:text-body-4 py-2 sm:py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
										}}
									>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
									</button>
								{/if}
							</div>
						{/if}

						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<button
								class="text-caption sm:text-body-4 text-center underline text-gray-700 dark:text-gray-300"
								type="button"
								on:click={() => {
									if (mode === 'ldap')
										mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
									else mode = 'ldap';
								}}
							>
								{mode === 'ldap' ? $i18n.t('Continue with Email') : $i18n.t('Continue with LDAP')}
							</button>
						{/if}
					</div>

					{#if $config?.metadata?.login_footer}
						<div class="max-w-3xl mx-auto">
							<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
								{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.login-card {
		background: rgba(253, 254, 254, 0.7);
		box-shadow: 4px 4px 20px rgba(0, 0, 0, 0.1);
		backdrop-filter: blur(20px);
	}

	:global(.dark) .login-card {
		background: rgba(39, 40, 44, 0.5);
	}

	.icon-circle {
		background: rgba(206, 212, 229, 0.2);
		box-shadow: 4px 4px 20px rgba(0, 0, 0, 0.1), inset 2px 2px 16px rgba(206, 212, 229, 0.12);
		backdrop-filter: blur(10px);
	}

	:global(.dark) .icon-circle {
		background: rgba(113, 122, 143, 0.3);
	}
</style>
