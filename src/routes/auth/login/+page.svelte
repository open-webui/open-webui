<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
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
		} else {
			await signInHandler();
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

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

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
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
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
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<div class="w-full h-screen max-h-[100dvh] bg-white dark:bg-black">
	<div class="w-full h-full flex items-center justify-center">
		<div class="w-full max-w-md px-8">
			{#if loaded}
				<!-- Logo -->
				<div class="flex justify-center mb-8">
					<img
						id="logo"
						crossorigin="anonymous"
						src="{WEBUI_BASE_URL}/static/splash.png"
						class="w-16 h-16 rounded-full"
						alt="logo"
					/>
				</div>

				<!-- Title -->
				<div class="text-center mb-8">
					<h1 class="text-2xl font-bold text-black dark:text-white mb-2">
						Sign in to your account
					</h1>
				</div>

				<!-- Login Form -->
				<form
					class="space-y-6"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					{#if mode === 'ldap'}
						<div>
							<label for="username" class="block text-sm font-medium text-black dark:text-white mb-2">
								Username
							</label>
							<input
								id="username"
								bind:value={ldapUsername}
								type="text"
								class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-black dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="Enter your username"
								required
							/>
						</div>
					{:else}
						<div>
							<label for="email" class="block text-sm font-medium text-black dark:text-white mb-2">
								Email
							</label>
							<input
								id="email"
								bind:value={email}
								type="email"
								class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-black dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								placeholder="Enter your email"
								required
							/>
						</div>
					{/if}

					<div>
						<div class="flex justify-between items-center mb-2">
							<label for="password" class="block text-sm font-medium text-black dark:text-white">
								Password
							</label>
							<button
								type="button"
								class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
								on:click={() => goto('/auth/forgot-password')}
							>
								Forgot?
							</button>
						</div>
						<input
							id="password"
							bind:value={password}
							type="password"
							class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-black dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							placeholder="Enter your password"
							required
						/>
					</div>

					<button
						type="submit"
						class="w-full bg-gray-800 dark:bg-gray-700 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-900 dark:hover:bg-gray-600 transition-colors"
					>
						Sign In
					</button>
				</form>

				<!-- Sign Up Link -->
				<div class="text-center mt-6">
					<span class="text-sm text-gray-600 dark:text-gray-400">
						Don't have an account?
					</span>
					<button
						type="button"
						class="ml-1 text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
						on:click={() => goto('/auth/signup')}
					>
						Sign Up
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>

