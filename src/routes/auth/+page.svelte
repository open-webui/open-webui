<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/chat/Footer.svelte';
	import ProconnectButton from '$lib/components/auth/ProconnectButton.svelte';

	import { fade, fly } from 'svelte/transition';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loaded = false;
	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';
	let ldapUsername = '';
	let password = '';

	// Carousel state
	let currentIndex = 0;
	const carouselItems = [
		{
			title: 'Posez vos questions',
			description: 'Albert répond à vos question au quotidien.',
			image: '/assets/illustrations/question.svg'
		},
		{
			title: 'Intégrez vos documents',
			description: 'Albert vous aide à discuter avec vos documents.',
			image: '/assets/illustrations/file-search.svg'
		},
		{
			title: 'IA ❤️ Internet',
			description: 'Albert peut utiliser internet pour répondre à vos questions.',
			image: '/assets/illustrations/internet.svg'
		}
	];

	const nextSlide = () => {
		currentIndex = (currentIndex + 1) % carouselItems.length;
	};

	const previousSlide = () => {
		currentIndex = (currentIndex - 1 + carouselItems.length) % carouselItems.length;
	};

	// Auto-advance carousel
	let carouselInterval: ReturnType<typeof setInterval>;
	onMount(() => {
		carouselInterval = setInterval(nextSlide, 7000);
		return () => clearInterval(carouselInterval);
	});

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

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		console.log('Submit Handler', mode);
		if (mode === 'ldap') {
			await ldapSignInHandler();
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

		localStorage.setItem('token', token);

		const sessionUser = await getSessionUser().catch((error) => {
			localStorage.removeItem('token'); // Clear token if getSessionUser fails
			toast.error(error);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		$socket?.emit('user-join', { auth: { token: sessionUser.token } });
		await user.set(sessionUser);
		await config.set(await getBackendConfig());
		goto('/');
	};

	let onboarding = false;

	onMount(async () => {
		if ($user !== undefined) {
			await goto('/');
		}

		await checkOauthCallback();

		loaded = true;
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await ldapSignInHandler();
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
		mode = $config?.features.enable_ldap ? 'ldap' : 'signin';
	}}
/>
<Header />
<div class="w-full h-screen max-h-[100dvh] text-white relative">
	<div class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if !loaded || !$i18n?.isInitialized}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center items-center font-primary z-10"
		>
			<Spinner />
		</div>
	{:else}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-10 text-black dark:text-white"
		>
			<div class="container max-w-6xl mx-auto px-4 flex items-center justify-between min-h-screen">
				<div class="w-full max-w-md">
					{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
						<div class="pb-10 w-full">
							<div
								class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold dark:text-gray-200"
							>
								<div>
									{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
								</div>

								<div>
									<Spinner />
								</div>
							</div>
						</div>
					{:else}
						<div class="pb-10 w-full dark:text-gray-100">
							<div class="flex flex-col gap-6 items-center text-center">
								<div class="text-5xl fr-text-default--grey font-bold text-center">
									{$i18n.t("L'IA")}
									<br />
									{$i18n.t('au service')}
									<br />
									{$i18n.t('des agents.')}
								</div>
								<ProconnectButton />
							</div>
						</div>
					{/if}
					<!-- {#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="inline-flex items-center justify-center w-full">
								<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
								<span class="px-3 text-sm font-medium text-gray-900 dark:text-white bg-transparent"
									>{$i18n.t('or')}</span
								>
								<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
							</div>
							<div class="flex flex-col space-y-2">
								{#if $config?.oauth?.providers?.google}
									<button
										class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-6 mr-3">
											<path
												fill="#EA4335"
												d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
											/><path
												fill="#4285F4"
												d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
											/><path
												fill="#FBBC05"
												d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
											/><path
												fill="#34A853"
												d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
											/><path fill="none" d="M0 0h48v48H0z" />
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-6 mr-3">
											<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
												x="1"
												y="11"
												width="9"
												height="9"
												fill="#00a4ef"
											/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
												x="11"
												y="11"
												width="9"
												height="9"
												fill="#ffb900"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-6 mr-3">
											<path
												fill="currentColor"
												d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-6 mr-3"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
											/>
										</svg>

										<span
											>{$i18n.t('Continue with {{provider}}', {
												provider: $config?.oauth?.providers?.oidc ?? 'SSO'
											})}</span
										>
									</button>
								{/if}
							</div>
						{/if} -->
				</div>

				<div class="w-full max-w-md">
					<div class="carousel relative min-h-[300px]">
						{#each carouselItems as item, i}
							{#if currentIndex === i}
								<div
									class="carousel-item flex flex-col gap-6 absolute w-full"
									in:fly={{ x: 200, duration: 1000, opacity: 1 }}
									out:fly={{ x: -200, duration: 1000, opacity: 0 }}
								>
									<div class="text-left">
										<h2 class="text-2xl font-bold mb-2">{$i18n.t(item.title)}</h2>
										<p class="text-gray-600 dark:text-gray-300">{$i18n.t(item.description)}</p>
									</div>
									<div class="w-full h-48 relative">
										<img
											src={item.image}
											alt={$i18n.t(item.title)}
											class="w-full h-full object-contain"
										/>
									</div>
									<div class="flex justify-center gap-2 mt-4">
										{#each carouselItems as _, i}
											<button
												class="w-2 h-2 rounded-full transition-colors duration-200 {currentIndex ===
												i
													? 'bg-blue-500'
													: 'bg-gray-300 dark:bg-gray-600'}"
												on:click={() => (currentIndex = i)}
												aria-label={$i18n.t('Go to slide {{number}}', { number: i + 1 })}
											/>
										{/each}
									</div>
								</div>
							{/if}
						{/each}
					</div>
				</div>
			</div>
		</div>
	{/if}

	<div class="w-full fixed bottom-0 left-0 right-0 fr-background-default--grey z-20">
		<Footer />
	</div>
</div>
