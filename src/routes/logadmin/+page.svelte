<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { getBackendConfig } from '$lib/apis';
	import { userSignIn } from '$lib/apis/auths';

	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/chat/Footer.svelte';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let loaded = false;
	let email = '';
	let password = '';

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.setItem('token', sessionUser.token);
			}

			$socket?.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			goto('/');
		}
	};

	const signInHandler = async () => {
		try {
			console.log('Starting sign-in process...');

			// Log the API URL being used
			console.log('API URL:', WEBUI_API_BASE_URL);

			// Make a direct fetch call with detailed logging
			const url = `${WEBUI_API_BASE_URL}/auths/signin`;
			console.log('Making request to:', url);

			// First, try to check if the endpoint exists and what methods it accepts
			try {
				const optionsResponse = await fetch(url, {
					method: 'OPTIONS',
					headers: {
						'Content-Type': 'application/json'
					}
				});

				console.log('OPTIONS response status:', optionsResponse.status);
				console.log('OPTIONS response headers:', Object.fromEntries([...optionsResponse.headers]));

				const allowedMethods =
					optionsResponse.headers.get('Allow') ||
					optionsResponse.headers.get('Access-Control-Allow-Methods');
				console.log('Allowed methods:', allowedMethods);
			} catch (optionsError) {
				console.error('OPTIONS request failed:', optionsError);
			}

			// Now make the actual sign-in request
			const response = await fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					email: email,
					password: password
				})
			});

			console.log('Response status:', response.status);
			console.log('Response headers:', Object.fromEntries([...response.headers]));

			// Get the raw text first before trying to parse as JSON
			const rawText = await response.text();
			console.log('Raw response text:', rawText);

			// Only try to parse as JSON if it looks like JSON
			let data;
			if (rawText && (rawText.trim().startsWith('{') || rawText.trim().startsWith('['))) {
				try {
					data = JSON.parse(rawText);
					console.log('Parsed JSON data:', data);
				} catch (parseError) {
					console.error('JSON parse error:', parseError);
					toast.error('Failed to parse server response');
					return;
				}
			} else {
				console.error('Response is not JSON:', rawText);
				toast.error('Server returned an invalid response');
				return;
			}

			// Continue with normal flow if we got valid JSON
			if (data.token) {
				localStorage.setItem('token', data.token);
				await setSessionUser(data);
			} else {
				toast.error(data.detail || 'Authentication failed');
			}
		} catch (error) {
			console.error('Sign-in error:', error);
			toast.error(`${error}`);
		}
	};

	onMount(async () => {
		console.log('API Base URL:', WEBUI_API_BASE_URL);
		if ($user !== undefined) {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Admin Login - {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</title>
</svelte:head>

<Header />
<div class="w-full h-screen max-h-[100dvh] text-white relative">
	<div class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-10 text-black dark:text-white"
		>
			<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
				<div class="my-auto pb-10 w-full dark:text-gray-100">
					<form
						class="flex flex-col justify-center"
						on:submit={(e) => {
							e.preventDefault();
							signInHandler();
						}}
					>
						<div class="mb-1">
							<div class="text-2xl font-medium">
								{$i18n.t(`Admin Login to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
							</div>
						</div>

						<div class="flex flex-col mt-4">
							<div class="mb-2 fr-background">
								<div class="text-sm font-medium text-left mb-1">{$i18n.t('Email')}</div>
								<input
									bind:value={email}
									type="email"
									class="my-0.5 w-full text-sm outline-hidden fr-background-contrast--grey rounded-md p-2"
									autocomplete="email"
									name="email"
									placeholder={$i18n.t('Enter Your Email')}
									required
								/>
							</div>

							<div>
								<div class="text-sm font-medium text-left mb-1">{$i18n.t('Password')}</div>
								<input
									bind:value={password}
									type="password"
									class="my-0.5 w-full text-sm outline-hidden fr-background-contrast--grey rounded-md p-2"
									placeholder={$i18n.t('Enter Your Password')}
									autocomplete="current-password"
									name="current-password"
									required
								/>
							</div>
						</div>

						<div class="mt-5">
							<button
								class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 fr-text-action-high--blue-france fr-border-default--blue-france border-3 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5 hover:bg-gray-700/10"
								type="submit"
							>
								{$i18n.t('Sign in')}
							</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	{/if}

	<div class="w-full fixed bottom-0 left-0 right-0 fr-background-default--grey z-20">
		<Footer />
	</div>
</div>
