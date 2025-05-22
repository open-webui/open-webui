<script lang="ts">
	// Import declaration file for Matomo analytics
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

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
	const _paq = window._paq;

	interface SessionUser {
		token: string;
		id: string;
		email: string;
		name: string;
		role: string;
		profile_image_url: string;
	}

	let loaded = false;
	let name = '';
	let email = '';
	let password = '';
	let onboarding = false;

	// Carousel state
	let currentIndex = 0;
	const carouselItems = [
		{
			title: $i18n.t('Ask your questions'),
			description: $i18n.t('Assistant IA answers your everyday questions.'),
			image: '/assets/illustrations/question.svg'
		},
		{
			title: $i18n.t('Integrate your documents'),
			description: $i18n.t('Assistant IA helps you chat with your documents.'),
			image: '/assets/illustrations/file-search.svg'
		},
		{
			title: $i18n.t('AI ❤️ Internet'),
			description: $i18n.t('Assistant IA can use the internet to answer your questions.'),
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

	const querystringValue = (key: string) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser: SessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.setItem('token', sessionUser.token);
			}

			$socket?.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);

			_paq.push(['trackEvent', 'Auth', 'OAuth Login Success']);
		} else {
			_paq.push(['trackEvent', 'Auth', 'OAuth Login Failed']);
		}
	};

	const signUpHandler = async () => {
		try {
			const sessionUser = await userSignUp(
				name,
				email,
				password,
				generateInitialsImage(name)
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await setSessionUser(sessionUser);
		} catch (error) {
			console.error('Sign-up error:', error);
			const errorMsg = error instanceof Error ? error.message : String(error);
			toast.error(`Sign-up error: ${errorMsg}`);
		}
	};

	const submitHandler = async () => {
		await signUpHandler();
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

		_paq.push(['trackEvent', 'Auth', 'OAuth Login Success']);
	};

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = '/static/favicon-dark.png';

				darkImage.onload = () => {
					(logo as HTMLImageElement).src = '/static/favicon-dark.png';
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

		_paq.push(['trackPageView', 'Auth Page']);

		// UTM tracking is now handled in +layout.svelte
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<Header />
<!-- Main container -->
<div class="w-full h-[100dvh] text-white overflow-auto">
	<!-- Background -->
	<div class="w-full h-full fixed top-0 left-0 bg-white dark:bg-black -z-10"></div>

	<!-- Drag region -->
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div class="min-h-full w-full flex flex-col">
			<div class="flex-1 flex items-center">
				<div class="w-full flex justify-center font-primary text-black dark:text-white py-20">
					<div class="w-full px-10 flex flex-col text-center">
						<div class="w-full dark:text-gray-100">
							{#if $config?.onboarding}
								<form
									class="w-full max-w-md mx-auto bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden p-6"
									on:submit={(e) => {
										e.preventDefault();
										submitHandler();
									}}
								>
									<div class="text-center mb-6">
										<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
											{$i18n.t(`Create Admin Account`)}
										</h1>
										<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
											{$i18n.t('Please fill in the details below to create your admin account.')}
										</p>
									</div>

									<div class="flex flex-col space-y-4">
										<div class="flex flex-col space-y-2">
											<label
												for="name"
												class="text-left text-sm font-medium text-gray-700 dark:text-gray-300"
											>
												{$i18n.t('Name')}
											</label>
											<input
												id="name"
												bind:value={name}
												type="text"
												class="px-3 text-left py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:text-white"
												autocomplete="name"
												placeholder={$i18n.t('Enter Your Full Name')}
												required
											/>
										</div>

										<div class="flex flex-col space-y-2">
											<label
												for="email"
												class="text-sm font-medium text-left text-gray-700 dark:text-gray-300"
											>
												{$i18n.t('Email')}
											</label>
											<input
												id="email"
												bind:value={email}
												type="email"
												class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:text-white"
												autocomplete="email"
												name="email"
												placeholder={$i18n.t('Enter Your Email')}
												required
											/>
										</div>

										<div class="flex flex-col space-y-2">
											<label
												for="password"
												class="text-sm font-medium text-left text-gray-700 dark:text-gray-300"
											>
												{$i18n.t('Password')}
											</label>
											<input
												id="password"
												bind:value={password}
												type="password"
												class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:text-white"
												placeholder={$i18n.t('Choose a Strong Password')}
												autocomplete="new-password"
												name="new-password"
												required
											/>
										</div>
									</div>

									<button
										type="submit"
										class="w-full mt-6 flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white fr-background-action-high--blue-france focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
									>
										{$i18n.t('Create Admin Account')}
									</button>
								</form>
							{:else}
								<div
									class="flex flex-col md:flex-row w-full gap-8 md:gap-16 items-center justify-center"
								>
									<!-- Left column - Login content -->
									<div class="flex flex-col w-full md:w-1/2 gap-4 items-center justify-center">
										<!-- Title section -->
										<div class="">
											<div class="w-full max-w-md mx-auto">
												<div class="pb-4 w-full dark:text-gray-100 text-center">
													<div class="flex flex-col gap-3 items-center text-center">
														<div
															class="text-2xl sm:text-4xl md:text-5xl fr-text-default--grey font-bold text-center"
														>
															{@html $i18n.t('ai_for_public_services').replace(/\n/g, '<br />')}
														</div>
													</div>
												</div>
											</div>
										</div>

										<!-- Login button -->
										<div class="w-full flex justify-center">
											<ProconnectButton
												on:click={() =>
													_paq.push(['trackEvent', 'Auth', 'ProConnect Button Click'])}
											/>
										</div>
									</div>

									<!-- Right column - Carousel -->
									<div class="w-full md:w-1/2 hidden md:block">
										<div class="w-full max-w-md mx-auto">
											<!-- Carousel container -->
											<div
												class="carousel flex flex-col justify-between min-h-[350px] h-[350px] sm:min-h-[400px] sm:h-[400px] md:min-h-[450px] md:h-[450px] overflow-hidden"
											>
												{#each carouselItems as item, i}
													{#if currentIndex === i}
														<!-- Carousel item -->
														<div
															class="carousel-item flex flex-col gap-4 md:gap-6 w-full h-full"
															in:fly={{ x: 200, duration: 1000, opacity: 1 }}
															out:fly={{ x: -200, duration: 1000, opacity: 0 }}
														>
															<!-- Carousel text content -->
															<div class="text-center">
																<h2 class="text-xl md:text-2xl font-bold mb-2">
																	{$i18n.t(item.title)}
																</h2>
																<p class="text-sm md:text-base text-gray-600 dark:text-gray-300">
																	{$i18n.t(item.description)}
																</p>
															</div>
															<!-- Carousel image -->
															<div class="flex-1 flex items-center justify-center">
																<img
																	src={item.image}
																	alt={$i18n.t(item.title)}
																	class="max-h-56 sm:max-h-64 md:max-h-72 w-auto object-contain"
																/>
															</div>
															<!-- Carousel navigation dots -->
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
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<!-- Footer -->
			<div class="w-full fr-background-default--grey">
				<Footer />
			</div>
		</div>
	{:else}
		<div class="w-full h-full flex justify-center items-center font-primary">
			<Spinner />
		</div>
	{/if}
</div>
