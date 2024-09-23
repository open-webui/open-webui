<script>
	import { onMount, tick, setContext } from 'svelte';
	import { config, user, theme, WEBUI_NAME, settings } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { Toaster, toast } from 'svelte-sonner';

	import { getBackendConfig } from '$lib/apis';
	import { getSessionUser } from '$lib/apis/auths';

	import '../tailwind.css';
	import '../app.css';

	import 'tippy.js/dist/tippy.css';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import i18n, { initI18n } from '$lib/i18n';

	setContext('i18n', i18n);

	let loaded = false;

	const getUserDefaultPrompt = async (userInfo) => {
		let _settings = JSON.parse(localStorage.getItem('settings') ?? '{}');
		_settings.system = `I am one user. My name is ${userInfo.name ?? ''}, I am the ${userInfo.title ?? '_'} at MBZUAI. My phone number is ${userInfo.phone ?? '_'}. My email address is ${userInfo.email ?? ''}. My ID is ${userInfo.id ?? '_'}`
		await settings.set({ ...$settings, ..._settings });
		localStorage.setItem('settings', JSON.stringify($settings))
	}

	onMount(async () => {
		theme.set(localStorage.theme);
		// Check Backend Status
		const backendConfig = await getBackendConfig();

		if (backendConfig) {
			// Save Backend Status to Store
			await config.set(backendConfig);
			if ($config.default_locale) {
				initI18n($config.default_locale);
			} else {
				initI18n();
			}

			// await WEBUI_NAME.set(backendConfig.name);
			console.log(backendConfig);

			if ($config) {
				if (localStorage.token) {
					// Get Session User Info
					const sessionUser = await getSessionUser(localStorage.token).catch((error) => {
						toast.error(error);
						return null;
					});

					if (sessionUser) {
						// Save Session User to Store
						await user.set(sessionUser);
						// await getUserDefaultPrompt(sessionUser)
					} else {
						// Redirect Invalid Session User to /auth Page
						// comment out this because already have 401 redirect in fetchApi in /lib/utils/index.ts
						// localStorage.removeItem('token');
						// await goto('/auth');
					}
				} else {
					// await goto('/login');
				}
			}
		} else {
			// Redirect to /error when Backend Not Detected
			await goto(`/error`);
		}

		await tick();

		document.getElementById('splash-screen')?.remove();
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$WEBUI_NAME}</title>
	<link rel="icon" href="{WEBUI_BASE_URL}/static/favicon.ico" />

	<!-- rosepine themes have been disabled as it's not up to date with our latest version. -->
	<!-- feel free to make a PR to fix if anyone wants to see it return -->
	<!-- <link rel="stylesheet" type="text/css" href="/themes/rosepine.css" />
	<link rel="stylesheet" type="text/css" href="/themes/rosepine-dawn.css" /> -->
</svelte:head>

{#if loaded}
	<slot />
{/if}

<Toaster richColors position="top-center" closeButton />
