<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { getBackendConfig } from '$lib/apis';
	import { userSignIn, getSessionUser } from '$lib/apis/auths';

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
			console.log('Session user data:', sessionUser);
			toast.success($i18n.t(`You're now logged in.`));

			if (sessionUser.token) {
				// Store token in localStorage
				localStorage.setItem('token', sessionUser.token);
				console.log('Token saved to localStorage:', sessionUser.token);
			} else {
				console.error('No token found in session user data');
				toast.error($i18n.t('Authentication error: No token received'));
				return;
			}

			try {
				// Verify token works by attempting to get session user
				const verifiedUser = await getSessionUser();
				console.log('Token verification successful:', verifiedUser);

				// Update socket connection with token
				$socket?.emit('user-join', { auth: { token: sessionUser.token } });

				// Update stores
				await user.set(sessionUser);
				await config.set(await getBackendConfig());

				// Navigate to home
				goto('/');
			} catch (error) {
				console.error('Token verification failed:', error);
				const errorMessage = error instanceof Error ? error.message : String(error);
				toast.error($i18n.t('Authentication error: {{message}}', { message: errorMessage }));
				localStorage.removeItem('token');
			}
		}
	};

	const signInHandler = async () => {
		try {
			console.log('[DEBUG] Starting sign-in process...');

			// Log the request details
			console.log('[DEBUG] Request payload:', { email, password: '***' });

			// Make a direct fetch call instead of using the userSignIn function
			console.log('[DEBUG] API Base URL:', WEBUI_API_BASE_URL);
			console.log('[DEBUG] Making API call to:', `${WEBUI_API_BASE_URL}/auths/signin`);

			const response = await fetch(`${WEBUI_API_BASE_URL}/auths/signin`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					email: email,
					password: password
				})
			});

			console.log('[DEBUG] Response status:', response.status);
			console.log('[DEBUG] Response status text:', response.statusText);
			console.log('[DEBUG] Response headers:', Object.fromEntries([...response.headers]));

			// Get the raw text first
			const rawText = await response.text();
			console.log('[DEBUG] Raw response content length:', rawText?.length || 0);
			console.log('[DEBUG] Raw response first 200 chars:', rawText?.substring(0, 200));

			// Check if the response is empty
			if (!rawText || rawText.trim() === '') {
				console.error('[DEBUG] Empty response received');
				toast.error('Empty response received from server');
				return null;
			}

			// Try to parse as JSON if it looks like JSON
			let data;
			try {
				// First check if it's a valid JSON format before parsing
				if (rawText.trim().startsWith('{') || rawText.trim().startsWith('[')) {
					console.log('[DEBUG] Response appears to be JSON, attempting to parse');
					data = JSON.parse(rawText);
					console.log('[DEBUG] Parsed JSON data:', data);
				} else {
					console.error(
						'[DEBUG] Response is not JSON format. First char:',
						rawText.trim().charAt(0)
					);
					console.error('[DEBUG] Raw text content type check:', {
						isString: typeof rawText === 'string',
						startsWithOpenBrace: rawText.trim().startsWith('{'),
						startsWithOpenBracket: rawText.trim().startsWith('['),
						firstFewChars: rawText
							.substring(0, 20)
							.split('')
							.map((c) => c.charCodeAt(0))
					});
					toast.error('Server returned an invalid response format');
					return null;
				}
			} catch (parseError) {
				console.error('[DEBUG] JSON parse error:', parseError);
				// Type guard for error object
				const errorMsg = parseError instanceof Error ? parseError.message : String(parseError);
				const errorStack = parseError instanceof Error ? parseError.stack : undefined;
				const errorName = parseError instanceof Error ? parseError.name : undefined;

				console.error('[DEBUG] JSON parse error details:', {
					name: errorName,
					message: errorMsg,
					stack: errorStack
				});

				// If there's a position in the error, show the problematic part of the text
				let position = null;
				if (errorMsg && typeof errorMsg === 'string') {
					const match = errorMsg.match(/position (\d+)/);
					position = match?.[1];
				}

				if (position) {
					const pos = Number.parseInt(position, 10);
					console.error('[DEBUG] Text around error position:', {
						before: rawText.substring(Math.max(0, pos - 20), pos),
						errorChar: rawText.substring(pos, pos + 1),
						after: rawText.substring(pos + 1, pos + 21)
					});
				}

				toast.error(`Failed to parse server response: ${errorMsg}`);
				return null;
			}

			if (!response.ok) {
				console.error('[DEBUG] Response not OK:', data);
				toast.error(data.detail || `Error: ${response.status}`);
				return null;
			}

			// Explicitly check for token before proceeding
			if (!data.token) {
				console.error('[DEBUG] No token in response data');
				toast.error($i18n.t('Authentication error: No token in response'));
				return null;
			}

			await setSessionUser(data);
		} catch (error) {
			console.error('[DEBUG] Sign-in error:', error);
			// Type guard for error object
			const errorMsg = error instanceof Error ? error.message : String(error);
			const errorStack = error instanceof Error ? error.stack : undefined;
			const errorName = error instanceof Error ? error.name : undefined;

			console.error('[DEBUG] Sign-in error details:', {
				name: errorName,
				message: errorMsg,
				stack: errorStack
			});
			toast.error(`Sign-in error: ${errorMsg}`);
		}
	};

	onMount(async () => {
		console.log('API Base URL:', WEBUI_API_BASE_URL);

		// Check if user is already logged in
		try {
			const existingToken = localStorage.getItem('token');
			if (existingToken) {
				const sessionUser = await getSessionUser();
				if (sessionUser) {
					console.log('User already logged in');
					await goto('/');
					return;
				}
			}
		} catch (error) {
			console.log('Not logged in:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
			console.log('Login error details:', errorMessage);
			// Clear any invalid tokens
			localStorage.removeItem('token');
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Admin Login - {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</title>
</svelte:head>

<Header />

<!-- Main container -->
<div class="w-full min-h-screen flex items-center justify-center pt-16 pb-8 px-4">
	<div
		class="w-full max-w-md mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden p-6"
	>
		<div class="text-center mb-6">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Admin Login</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
				Login with your administrator credentials
			</p>
		</div>

		<form on:submit|preventDefault={signInHandler} class="flex flex-col space-y-4">
			<div class="flex flex-col space-y-2">
				<label for="email" class="text-sm font-medium text-gray-700 dark:text-gray-300">
					{$i18n.t('Email')}
				</label>
				<input
					type="email"
					id="email"
					bind:value={email}
					required
					class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:text-white"
					placeholder="admin@example.com"
				/>
			</div>

			<div class="flex flex-col space-y-2">
				<label for="password" class="text-sm font-medium text-gray-700 dark:text-gray-300">
					{$i18n.t('Password')}
				</label>
				<input
					type="password"
					id="password"
					bind:value={password}
					required
					class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:text-white"
				/>
			</div>

			<button
				type="submit"
				class="w-full mt-4 flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
			>
				{$i18n.t('Login')}
			</button>
		</form>
	</div>
</div>
