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

			// Log the request details
			console.log('Request payload:', { email, password: '***' });

			// Make a direct fetch call instead of using the userSignIn function
			console.log('Making direct API call to:', `${WEBUI_API_BASE_URL}/auths/signin`);

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

			console.log('Response status:', response.status);
			console.log('Response headers:', Object.fromEntries([...response.headers]));

			// Get the raw text first
			const rawText = await response.text();
			console.log('Raw response text:', rawText);

			// Try to parse as JSON if it looks like JSON
			let data;
			if (rawText && rawText.trim().startsWith('{')) {
				try {
					data = JSON.parse(rawText);
					console.log('Parsed JSON data:', data);
				} catch (parseError) {
					console.error('JSON parse error:', parseError);
					toast.error('Failed to parse server response');
					return null;
				}
			} else {
				console.error('Response is not JSON:', rawText);
				toast.error('Server returned an invalid response');
				return null;
			}

			if (!response.ok) {
				toast.error(data.detail || `Error: ${response.status}`);
				return null;
			}

			// Continue with the normal flow
			if (data.token) {
				localStorage.setItem('token', data.token);
			}

			await setSessionUser(data);
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
<div>
	<h1>Admin Login</h1>
</div>