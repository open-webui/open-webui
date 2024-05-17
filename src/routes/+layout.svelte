<script>
	import { onMount, tick, setContext } from 'svelte';
	import { config, user, theme, WEBUI_NAME, mobile } from '$lib/stores';
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
	const BREAKPOINT = 768;

	onMount(async () => {
		theme.set(localStorage.theme);

		mobile.set(window.innerWidth < BREAKPOINT);
		const onResize = () => {
			if (window.innerWidth < BREAKPOINT) {
				mobile.set(true);
			} else {
				mobile.set(false);
			}
		};

		window.addEventListener('resize', onResize);

		let backendConfig = null;
		try {
			backendConfig = await getBackendConfig();
			console.log('Backend config:', backendConfig);
		} catch (error) {
			console.error('Error loading backend config:', error);
		}
		// Initialize i18n even if we didn't get a backend config,
		// so `/error` can show something that's not `undefined`.
		initI18n(backendConfig?.default_locale);

		if (backendConfig) {
			// Save Backend Status to Store
			await config.set(backendConfig);

			await WEBUI_NAME.set(backendConfig.name);

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
					} else {
						// Redirect Invalid Session User to /auth Page
						localStorage.removeItem('token');
						await goto('/auth');
					}
				} else {
					await goto('/auth');
				}
			}
		} else {
			// Redirect to /error when Backend Not Detected
			await goto(`/error`);
		}

		await tick();

		document.getElementById('splash-screen')?.remove();
		loaded = true;

		return () => {
			window.removeEventListener('resize', onResize);
		};
	});
</script>

<svelte:head>
	<title>{$WEBUI_NAME}</title>
	<link crossorigin="anonymous" rel="icon" href="{WEBUI_BASE_URL}/static/favicon.png" />

	<!-- rosepine themes have been disabled as it's not up to date with our latest version. -->
	<!-- feel free to make a PR to fix if anyone wants to see it return -->
	<!-- <link rel="stylesheet" type="text/css" href="/themes/rosepine.css" />
	<link rel="stylesheet" type="text/css" href="/themes/rosepine-dawn.css" /> -->
</svelte:head>

{#if loaded}
	<slot />
{/if}

<Toaster richColors position="top-center" />
