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
	class="login min-h-screen w-full flex justify-center relative"
	style="background: url('/background.png') bottom / cover no-repeat, radial-gradient(93.48% 68.59% at 40.87% 70.12%, rgba(7, 45, 90, 0.03) 37.67%, rgba(7, 45, 90, 0.25) 100%), radial-gradient(70.94% 58.43% at 27.53% 86.82%, rgba(7, 45, 90, 0.20) 0%, rgba(7, 45, 90, 0.00) 100%), linear-gradient(0deg, rgba(3, 25, 51, 0.20) 0%, rgba(3, 25, 51, 0.20) 100%), #010E1D;"
>
	{#if loaded}
		{#if showInitialScreen}
			<div class="relative w-full h-full flex flex-col">
				<!-- Login using Credentials button in top right corner -->
				<div class="absolute top-4 right-4 z-10">
					<button
						type="button"
						class="text-sm text-blue-200 cursor-pointer hover:text-blue-100 bg-transparent border-none p-2"
						on:click={() => (showInitialScreen = false)}
					>
						Login using Credentials
					</button>
				</div>

				<!-- Main content shifted upward -->
				<div class="flex-1 flex items-start justify-center min-h-screen pt-20">
					<div class="flex flex-col items-center text-center max-w-md w-full px-4">
						<img id="logo" src="/splash.png" alt="GovGPT Logo" class="w-full max-w-[312px] mb-2" />
						<h1 class="text-3xl lg:text-5xl font-bold mb-2 gradient-text">GovGPT</h1>
						<p class="text-xl text-gray-300 mb-4">Amplifying Government Potential</p>
						<p class="text-sm text-gray-400 mb-4">Use your work email to log in & get started!</p>
						<button
							on:click={() => {}}
							class="text-gray-800 font-medium py-2 px-6 transition"
							style="border-radius: 12px; background: linear-gradient(90deg, #A5C7E6 0%, #CEE7FF 38.94%, #A5C7E6 100%); box-shadow: 6px 3px 8px 0px #BFDBF6 inset;"
						>
							Log in using SSO
						</button>
						<p class="mt-2 text-xs text-gray-500">
							By continuing, you agree to our <button
								on:click={() => {
									navigateToTerms();
								}}
								class="text-blue-400 hover:text-blue-300 underline bg-transparent border-none p-0 cursor-pointer"
								>Terms</button
							>
							and have read our
							<button
								on:click={() => {
									navigateToPrivacy();
								}}
								class="text-blue-400 hover:text-blue-300 underline bg-transparent border-none p-0 cursor-pointer"
								>Privacy Policy</button
							>.
						</p>
					</div>

					<!-- <div class="flex-1 flex items-center justify-center">
					<div class="flex flex-col items-center text-center max-w-md w-full px-4">
						<img id="logo" src="/splash.png" alt="GovGPT Logo" class="w-full max-w-[312px] mb-4" />

						<div class="text-center mb-6">
							<h1 class="text-4xl lg:text-2xl text-white font-bold mb-2"> GovGPT</h1>
							<p class="text-xl text-white mb-6">Amplifying Government Potential</p>
						</div>

						<p class="text-md mb-6 text-white">Use your work email to log in & get started!</p>

						<button
							on:click={() => (showInitialScreen = false)}
							class="bg-blue-200 text-gray-800 font-medium py-2 px-6 rounded-lg hover:bg-blue-300 transition"
						>
							Log in using SSO
						</button>
					</div>
				</div> -->
					<div class="fixed bottom-0 left-0 right-0 text-center text-xs bg-[#072d5a] py-3 z-50">
						<strong class="text-white">Disclaimer:</strong>
						<span class="text-gray-400"
							>GovGPT is powered by artificial intelligence and may occasionally produce incorrect
							or outdated responses. Please verify critical information from official sources or
							consult your department head for confirmation.</span
						>
					</div>
				</div>
			</div>
		{:else}
			<div class="login min-h-screen w-full flex justify-center relative">
				<!-- Login using SSO button in top right corner -->
				<div class="absolute top-4 right-4 z-30">
					<button
						type="button"
						class="text-sm text-blue-200 cursor-pointer hover:text-blue-100 bg-transparent border-none p-2"
						on:click={() => (showInitialScreen = true)}
					>
						Login using SSO
					</button>
				</div>

				<div class="login__right z-20 p-4 flex-1 flex items-center justify-center text-center">
					<div class="login-box p-8 w-full md:w-[440px] rounded-2xl">
						<form
							class="flex flex-col justify-center"
							on:submit={(e) => {
								e.preventDefault();
								submitHandler();
							}}
						>
							<div class="mb-12 text-2xl font-medium">
								<p class="text-white">Login with your email address</p>
							</div>
							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								<div class="flex flex-col mt-4">
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
												class="text-[14px] leading-[22px] font-medium text-left mb-1 block text-white"
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
											class="text-[14px] leading-[22px] font-medium text-left mb-1 block text-white"
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
											class="cursor-pointer text-[16px] leading-[24px] w-full p-[8px] pl-[16px] rounded-[8px] text-white bg-[#004280]"
											type="submit"
										>
											{mode === 'signin' ? $i18n.t('Sign in') : $i18n.t('Create Account')}
										</button>
									{/if}
								{/if}
							</div>

							<!-- <div class="mt-4">
								<button
									type="button"
									on:click={() => (showInitialScreen = true)}
									class="text-sm w-full text-blue-200 hover:text-blue-100 underline"
								>
									Login using SSO
								</button>
							</div> -->
							<div
								class="fixed bottom-0 left-0 right-0 text-center text-xs text-white bg-[#072d5a] py-3 z-50"
							>
								<strong>Disclaimer:</strong> GovGPT is powered by artificial intelligence and may occasionally
								produce incorrect or outdated responses. Please verify critical information from official
								sources or consult your department head for confirmation.
							</div>
						</form>
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>
