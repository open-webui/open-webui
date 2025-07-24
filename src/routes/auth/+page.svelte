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

<div
	class=" dark login min-h-screen w-full flex justify-center relative"
	style="background: url('/background.png') bottom / cover no-repeat, radial-gradient(93.48% 68.59% at 40.87% 70.12%, rgba(7, 45, 90, 0.03) 37.67%, rgba(7, 45, 90, 0.25) 100%), radial-gradient(70.94% 58.43% at 27.53% 86.82%, rgba(7, 45, 90, 0.20) 0%, rgba(7, 45, 90, 0.00) 100%), linear-gradient(0deg, rgba(3, 25, 51, 0.20) 0%, rgba(3, 25, 51, 0.20) 100%), #010E1D;"
>
	{#if loaded}
		{#if showInitialScreen}
			<div class="relative w-full h-full flex flex-col">
				<!-- Login using Credentials button in top right corner -->
				<div class="absolute top-[28px] right-[28px] z-10">
					<button
						type="button"
						class="text-[14px] text-[#CEE7FF] cursor-pointer"
						on:click={() => (showInitialScreen = false)}
					>
						Login using Credentials
					</button>
				</div>

				<div class="flex-1 flex items-start justify-center min-h-screen pt-20">
					<div class="flex flex-col items-center text-center max-w-md w-full px-4">
						<div>
							<img
								id="logo"
								src="/loginLogo.png"
								alt="GovGPT Logo"
								class="w-full max-w-[312px] mb-2"
							/>
						</div>

						<div style="margin-top:-40px">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="191"
								height="38"
								viewBox="0 0 191 38"
								fill="none"
							>
								<path
									d="M26.6044 12.1106C26.2611 11.0334 25.7995 10.0687 25.2195 9.21644C24.6513 8.35233 23.9706 7.61843 23.1776 7.01474C22.3845 6.39921 21.4789 5.93164 20.4609 5.61204C19.4548 5.29244 18.348 5.13263 17.1406 5.13263C15.0928 5.13263 13.2462 5.65939 11.6009 6.71289C9.95549 7.76639 8.65341 9.31114 7.6946 11.3471C6.74763 13.3713 6.27415 15.8511 6.27415 18.7868C6.27415 21.7342 6.75355 24.2259 7.71236 26.2619C8.67117 28.2979 9.98509 29.8426 11.6541 30.8961C13.3232 31.9496 15.223 32.4764 17.3537 32.4764C19.3305 32.4764 21.0528 32.0739 22.5206 31.269C24.0002 30.4641 25.1425 29.3277 25.9474 27.8599C26.7642 26.3803 27.1726 24.6402 27.1726 22.6397L28.593 22.9061H18.1882V18.3784H32.4815V22.5154C32.4815 25.5694 31.8305 28.2209 30.5284 30.47C29.2382 32.7072 27.4508 34.4354 25.1662 35.6547C22.8935 36.8739 20.2893 37.4835 17.3537 37.4835C14.063 37.4835 11.1747 36.7259 8.68892 35.2108C6.21496 33.6956 4.28551 31.5472 2.90057 28.7654C1.51563 25.9719 0.823154 22.6575 0.823154 18.8223C0.823154 15.9222 1.22562 13.318 2.03054 11.0098C2.83546 8.70153 3.96591 6.74248 5.42188 5.13263C6.88968 3.51095 8.61198 2.27397 10.5888 1.4217C12.5774 0.557587 14.7495 0.125531 17.1051 0.125531C19.0701 0.125531 20.8989 0.415541 22.5916 0.995559C24.2962 1.57558 25.8113 2.39826 27.1371 3.4636C28.4747 4.52894 29.5814 5.79551 30.4574 7.26332C31.3333 8.71928 31.9252 10.335 32.233 12.1106H26.6044ZM50.008 37.5368C47.4512 37.5368 45.2199 36.9508 43.3141 35.7789C41.4083 34.6071 39.9287 32.9676 38.8752 30.8606C37.8217 28.7536 37.2949 26.2915 37.2949 23.4743C37.2949 20.6452 37.8217 18.1712 38.8752 16.0524C39.9287 13.9335 41.4083 12.2882 43.3141 11.1163C45.2199 9.94442 47.4512 9.35849 50.008 9.35849C52.5648 9.35849 54.7961 9.94442 56.7019 11.1163C58.6077 12.2882 60.0873 13.9335 61.1408 16.0524C62.1943 18.1712 62.7211 20.6452 62.7211 23.4743C62.7211 26.2915 62.1943 28.7536 61.1408 30.8606C60.0873 32.9676 58.6077 34.6071 56.7019 35.7789C54.7961 36.9508 52.5648 37.5368 50.008 37.5368ZM50.0257 33.0801C51.6829 33.0801 53.056 32.6421 54.1451 31.7662C55.2341 30.8902 56.039 29.7243 56.5598 28.2683C57.0925 26.8123 57.3588 25.2084 57.3588 23.4565C57.3588 21.7164 57.0925 20.1184 56.5598 18.6625C56.039 17.1947 55.2341 16.0169 54.1451 15.1291C53.056 14.2413 51.6829 13.7974 50.0257 13.7974C48.3567 13.7974 46.9718 14.2413 45.8709 15.1291C44.7819 16.0169 43.9711 17.1947 43.4384 18.6625C42.9176 20.1184 42.6571 21.7164 42.6571 23.4565C42.6571 25.2084 42.9176 26.8123 43.4384 28.2683C43.9711 29.7243 44.7819 30.8902 45.8709 31.7662C46.9718 32.6421 48.3567 33.0801 50.0257 33.0801ZM90.5502 9.7136L80.6603 36.9863H74.9785L65.0708 9.7136H70.7704L77.6774 30.7008H77.9615L84.8507 9.7136H90.5502ZM120.075 12.1106C119.732 11.0334 119.27 10.0687 118.69 9.21644C118.122 8.35233 117.441 7.61843 116.648 7.01474C115.855 6.39921 114.95 5.93164 113.932 5.61204C112.925 5.29244 111.819 5.13263 110.611 5.13263C108.564 5.13263 106.717 5.65939 105.072 6.71289C103.426 7.76639 102.124 9.31114 101.165 11.3471C100.218 13.3713 99.7449 15.8511 99.7449 18.7868C99.7449 21.7342 100.224 24.2259 101.183 26.2619C102.142 28.2979 103.456 29.8426 105.125 30.8961C106.794 31.9496 108.694 32.4764 110.824 32.4764C112.801 32.4764 114.523 32.0739 115.991 31.269C117.471 30.4641 118.613 29.3277 119.418 27.8599C120.235 26.3803 120.643 24.6402 120.643 22.6397L122.064 22.9061H111.659V18.3784H125.952V22.5154C125.952 25.5694 125.301 28.2209 123.999 30.47C122.709 32.7072 120.921 34.4354 118.637 35.6547C116.364 36.8739 113.76 37.4835 110.824 37.4835C107.534 37.4835 104.645 36.7259 102.16 35.2108C99.6857 33.6956 97.7562 31.5472 96.3713 28.7654C94.9863 25.9719 94.2939 22.6575 94.2939 18.8223C94.2939 15.9222 94.6963 13.318 95.5012 11.0098C96.3062 8.70153 97.4366 6.74248 98.8926 5.13263C100.36 3.51095 102.083 2.27397 104.059 1.4217C106.048 0.557587 108.22 0.125531 110.576 0.125531C112.541 0.125531 114.37 0.415541 116.062 0.995559C117.767 1.57558 119.282 2.39826 120.608 3.4636C121.945 4.52894 123.052 5.79551 123.928 7.26332C124.804 8.71928 125.396 10.335 125.704 12.1106H120.075ZM132.417 36.9863V0.622691H145.379C148.208 0.622691 150.551 1.13761 152.41 2.16743C154.268 3.19726 155.659 4.60588 156.582 6.39329C157.506 8.16886 157.967 10.1693 157.967 12.3947C157.967 14.6319 157.5 16.6442 156.565 18.4316C155.641 20.2072 154.245 21.6158 152.374 22.6575C150.516 23.6873 148.178 24.2022 145.361 24.2022H136.447V19.5502H144.864C146.651 19.5502 148.101 19.2425 149.214 18.627C150.326 17.9996 151.143 17.1473 151.664 16.0701C152.185 14.993 152.445 13.7678 152.445 12.3947C152.445 11.0216 152.185 9.80238 151.664 8.73704C151.143 7.6717 150.321 6.83718 149.196 6.23349C148.083 5.62979 146.616 5.32795 144.793 5.32795H137.903V36.9863H132.417ZM162.106 5.3457V0.622691H190.249V5.3457H178.903V36.9863H173.434V5.3457H162.106Z"
									fill="url(#paint0_linear_2592_8001)"
								/>
								<defs>
									<linearGradient
										id="paint0_linear_2592_8001"
										x1="-2"
										y1="18.4863"
										x2="193"
										y2="18.4863"
										gradientUnits="userSpaceOnUse"
									>
										<stop stop-color="#9DB7FB" />
										<stop offset="1" stop-color="#4174F8" />
									</linearGradient>
								</defs>
							</svg>
						</div>
						<p class="mb-[49px] text-center text-typography-titles text-[16px] leading-[37px]">
							Amplifying Government Potential
						</p>
						<p class="hidden sm:block mb-[30px] text-typography-titles text-[16px] leading-[24px]">
							Use your work email to log in & get started!
						</p>
						<div class="absolute sm:static bottom-[20px]">
							<button
								on:click={() => {}}
								class="mb-[24px] text-[14px] text-[rgba(7, 45, 90, 0.88)] py-[19px] w-[334px] rounded-[12px] bg-[linear-gradient(90deg,_#A5C7E6_0%,_#CEE7FF_38.94%,_#A5C7E6_100%)] shadow-[inset_6px_3px_8px_0_#BFDBF6]"
							>
								Log in using SSO
							</button>
							<p class="text-typography-titles text-[10px] leading-[16px]">
								By continuing, you agree to our <button
									on:click={() => {
										navigateToTerms();
									}}
									class="text-[#89B7FF] underline cursor-pointer">Terms</button
								>
								and have read our
								<button
									on:click={() => {
										navigateToPrivacy();
									}}
									class="text-[#89B7FF] underline cursor-pointer">Privacy Policy</button
								>.
							</p>
						</div>
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
						Login using SSO
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
								class="text-center mb-[34px] text-[20px] leading-[34px] text-typography-titles font-Inter_SemiBold"
							>
								Login with your email address
							</div>
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								<div class="flex flex-col mt-4">
									{#if mode === 'ldap'}
										<div class="mb-4">
											<label
												for="username"
												class="text-left pb-[8px] text-[14px] leading-[22px] font-medium text-typography-titles font-Inter_Medium"
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
												class=" text-left pb-[8px] text-[14px] leading-[22px] font-medium text-typography-titles font-Inter_Medium"
											>
												{$i18n.t('Email')} address
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
											class="text-left pb-[8px] text-[14px] leading-[22px] font-medium text-typography-titles font-Inter_Medium"
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
											class="cursor-pointer text-[14px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-[rgba(7, 45, 90, 0.88)] bg-[linear-gradient(90deg,_#A5C7E6_0%,_#CEE7FF_38.94%,_#A5C7E6_100%)] shadow-[inset_6px_3px_8px_0_#BFDBF6] font-Inter_Medium"
											type="submit"
										>
											{$i18n.t('Authenticate')}
										</button>
									{:else}
										<button
											class="cursor-pointer text-[14px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-[rgba(7, 45, 90, 0.88)] bg-[linear-gradient(90deg,_#A5C7E6_0%,_#CEE7FF_38.94%,_#A5C7E6_100%)] shadow-[inset_6px_3px_8px_0_#BFDBF6] font-Inter_Medium"
											type="submit"
										>
											{mode === 'signin' ? $i18n.t('Sign in') : $i18n.t('Create Account')}
										</button>
									{/if}
								{/if}
								<p class="block sm:hidden text-typography-titles text-[10px] leading-[16px]">
									By continuing, you agree to our <button
										on:click={() => {
											navigateToTerms();
										}}
										class="text-[#89B7FF] underline cursor-pointer">Terms</button
									>
									and have read our
									<button
										on:click={() => {
											navigateToPrivacy();
										}}
										class="text-[#89B7FF] underline cursor-pointer">Privacy Policy</button
									>.
								</p>
							</div>
						</form>
					</div>
				</div>
			</div>
		{/if}
		<div
			class="p-[16px] hidden sm:block fixed bottom-0 left-0 right-0 text-center text-typography-subtext text-[10px] leading-[16px] bg-[#072D5A] z-50"
		>
			<span class="text-typography-titles">Disclaimer:</span>
			GovGPT is powered by artificial intelligence and may occasionally produce incorrect or outdated
			responses. Please verify critical information from official sources or consult your department
			head for confirmation.
		</div>
	{/if}
</div>
