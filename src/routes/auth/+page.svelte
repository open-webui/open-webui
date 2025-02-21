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
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-10 text-black dark:text-white pt-16"
		>
			<div
				class="container max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-start md:items-center justify-between min-h-[calc(100vh-8rem)] py-8 md:py-0 gap-6 md:gap-12"
			>
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="w-full order-1 md:order-none">
						<div class="pb-6 md:pb-10 w-full">
							<div
								class="flex items-center justify-center gap-3 text-lg sm:text-xl md:text-2xl text-center font-semibold dark:text-gray-200"
							>
								<div>
									{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
								</div>

								<div>
									<Spinner />
								</div>
							</div>
						</div>
					</div>
				{:else}
					<div class="flex flex-col w-full md:w-1/2 gap-8 md:gap-12">
						<div class="order-1 md:order-none">
							<div class="w-full max-w-md mx-auto md:mx-0">
								<div class="pb-6 md:pb-10 w-full dark:text-gray-100">
									<div class="flex flex-col gap-4 md:gap-6 items-center text-center md:text-left">
										<div
											class="text-3xl sm:text-4xl md:text-5xl fr-text-default--grey font-bold text-center md:text-left"
										>
											{$i18n.t("L'IA")}
											<br />
											{$i18n.t('au service')}
											<br />
											{$i18n.t('des agents.')}
										</div>
									</div>
								</div>
							</div>
						</div>

						<div class="order-0 md:order-none w-full flex justify-center md:justify-start">
							<ProconnectButton />
						</div>
					</div>

					<div class="order-2 md:order-none w-full md:w-1/2">
						<div class="w-full max-w-md mx-auto">
							<div class="carousel relative min-h-[220px] sm:min-h-[250px] md:min-h-[300px]">
								{#each carouselItems as item, i}
									{#if currentIndex === i}
										<div
											class="carousel-item flex flex-col gap-4 md:gap-6 absolute w-full"
											in:fly={{ x: 200, duration: 1000, opacity: 1 }}
											out:fly={{ x: -200, duration: 1000, opacity: 0 }}
										>
											<div class="text-left">
												<h2 class="text-xl md:text-2xl font-bold mb-2">
													{$i18n.t(item.title)}
												</h2>
												<p class="text-sm md:text-base text-gray-600 dark:text-gray-300">
													{$i18n.t(item.description)}
												</p>
											</div>
											<div class="w-full h-36 md:h-48 relative">
												<img
													src={item.image}
													alt={$i18n.t(item.title)}
													class="w-full h-full object-contain"
												/>
											</div>
											<div class="flex justify-center gap-2 mt-2 md:mt-4">
												{#each carouselItems as _, i}
													<button
														class="w-2 h-2 rounded-full transition-colors duration-200 {currentIndex ===
														i
															? 'bg-blue-500'
															: 'bg-gray-300 dark:bg-gray-600'}"
														on:click={() => (currentIndex = i)}
														aria-label={$i18n.t('Go to slide {{number}}', {
															number: i + 1
														})}
													/>
												{/each}
											</div>
										</div>
									{/if}
								{/each}
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<div class="w-full fixed bottom-0 left-0 right-0 fr-background-default--grey z-20">
		<Footer />
	</div>
</div>
