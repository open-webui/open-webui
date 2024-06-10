<script>
	import { goto } from '$app/navigation';
	import { userSignIn, userSignUp } from '$lib/apis/auths';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	const i18n = getContext('i18n');

	let loaded = false;
	let mode = 'signin';

	let name = '';
	let email = '';
	let password = '';

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			localStorage.token = sessionUser.token;
			await user.set(sessionUser);
			goto('/');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	onMount(async () => {
		if ($user !== undefined) {
			await goto('/');
		}
		loaded = true;
		if ($config?.trusted_header_auth ?? false) {
			await signInHandler();
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div class="fixed m-10 z-50">
		<div class="flex flex-wrap space-x-4 items-center">
			<div class="self-center">
				<img src="{WEBUI_BASE_URL}/static/favicon.ico" class=" w-8 rounded-full" alt="logo" />
			</div>
			<img
				src="/logo-ciai.png"
				class="w-[70px]"
				alt="logo-ciai"
			/>
			<span class="text-lg font-semibold text-[#444]">HR Assistant Chatbot</span>
		</div>
	</div>
	<svg class="z-0 absolute top-0 left-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice"><defs><radialGradient id="Gradient1" cx="50%" cy="50%" fx="0.441602%" fy="50%" r=".5"><animate attributeName="fx" dur="34s" values="0%;3%;0%" repeatCount="indefinite"></animate><stop offset="0%" stop-color="rgba(95, 120, 234, 1)"></stop><stop offset="100%" stop-color="rgba(95, 120, 234, 0)"></stop></radialGradient><radialGradient id="Gradient2" cx="50%" cy="50%" fx="2.68147%" fy="50%" r=".5"><animate attributeName="fx" dur="23.5s" values="0%;3%;0%" repeatCount="indefinite"></animate><stop offset="0%" stop-color="rgba(14, 139, 254, 1)"></stop><stop offset="100%" stop-color="rgba(14, 139, 254, 0)"></stop></radialGradient><radialGradient id="Gradient3" cx="50%" cy="50%" fx="0.836536%" fy="50%" r=".5"><animate attributeName="fx" dur="21.5s" values="0%;3%;0%" repeatCount="indefinite"></animate><stop offset="0%" stop-color="rgba(27, 232, 217, 1)"></stop><stop offset="100%" stop-color="rgba(27, 232, 217, 0)"></stop></radialGradient></defs><rect x="13.744%" y="1.18473%" width="100%" height="100%" fill="url(#Gradient1)" transform="rotate(334.41 50 50)"><animate attributeName="x" dur="20s" values="25%;0%;25%" repeatCount="indefinite"></animate><animate attributeName="y" dur="21s" values="0%;25%;0%" repeatCount="indefinite"></animate><animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="7s" repeatCount="indefinite"></animateTransform></rect><rect x="-2.17916%" y="35.4267%" width="100%" height="100%" fill="url(#Gradient2)" transform="rotate(255.072 50 50)"><animate attributeName="x" dur="23s" values="-25%;0%;-25%" repeatCount="indefinite"></animate><animate attributeName="y" dur="24s" values="0%;50%;0%" repeatCount="indefinite"></animate><animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="12s" repeatCount="indefinite"></animateTransform></rect><rect x="9.00483%" y="14.5733%" width="100%" height="100%" fill="url(#Gradient3)" transform="rotate(139.903 50 50)"><animate attributeName="x" dur="25s" values="0%;25%;0%" repeatCount="indefinite"></animate><animate attributeName="y" dur="12s" values="0%;25%;0%" repeatCount="indefinite"></animate><animateTransform attributeName="transform" type="rotate" from="360 50 50" to="0 50 50" dur="9s" repeatCount="indefinite"></animateTransform></rect></svg>
	<div class=" z-50 bg-[#ffffff80] dark:bg-[#ffffff80] backdrop-blur-xl min-h-screen w-full flex justify-center font-mona">
		<!-- <div class="hidden lg:flex lg:flex-1 px-10 md:px-16 w-full bg-yellow-50 justify-center">
			<div class=" my-auto pb-16 text-left">
				<div>
					<div class=" font-bold text-yellow-600 text-4xl">
						Get up and running with <br />large language models, locally.
					</div>

					<div class="mt-2 text-yellow-600 text-xl">
						Run Llama 2, Code Llama, and other models. Customize and create your own.
					</div>
				</div>
			</div>
		</div> -->

		<div class="w-full sm:max-w-lg px-4 min-h-screen flex flex-col">
			{#if $config?.trusted_header_auth ?? false}
				<div class=" my-auto pb-10 w-full">
					<div
						class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-bold dark:text-gray-200"
					>
						<div>
							{$i18n.t('Signing in')}
							{$i18n.t('to')}
							{$WEBUI_NAME}
						</div>

						<div>
							<Spinner />
						</div>
					</div>
				</div>
			{:else}
				<div class=" my-auto pb-10 w-full">
					<form
						class=" flex flex-col justify-center bg-white py-6 sm:py-16 px-6 sm:px-16 rounded-2xl"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div class=" text-xl sm:text-2xl font-bold">
							{mode === 'signin' ? $i18n.t('Sign in') : $i18n.t('Sign up')}
							{$i18n.t('to')}
						</div>
						<div class="text-xl sm:text-xl font-semibold">{$WEBUI_NAME}</div>

						{#if mode === 'signup'}
							<div class=" mt-1 text-xs font-medium text-gray-500">
								ⓘ {$WEBUI_NAME}
								{$i18n.t(
									'does not make any external connections, and your data stays securely on your locally hosted server.'
								)}
							</div>
						{/if}

						<div class="flex flex-col mt-4">
							{#if mode === 'signup'}
								<div>
									<div class=" text-sm font-semibold text-left mb-1">{$i18n.t('Name')}</div>
									<input
										bind:value={name}
										type="text"
										class=" border px-4 py-2.5 rounded-2xl w-full text-sm"
										autocomplete="name"
										placeholder={$i18n.t('Enter Your Full Name')}
										required
									/>
								</div>

								<hr class=" my-3" />
							{/if}

							<div class="mb-2">
								<div class=" text-sm font-semibold text-left mb-1">{$i18n.t('Email')}</div>
								<input
									bind:value={email}
									type="email"
									class=" border px-4 py-2.5 rounded-2xl w-full text-sm"
									autocomplete="email"
									placeholder={$i18n.t('Enter Your Email')}
									required
								/>
							</div>

							<div>
								<div class=" text-sm font-semibold text-left mb-1">{$i18n.t('Password')}</div>
								<input
									bind:value={password}
									type="password"
									class=" border px-4 py-2.5 rounded-2xl w-full text-sm"
									placeholder={$i18n.t('Enter Your Password')}
									autocomplete="current-password"
									required
								/>
							</div>
						</div>

						<div class="mt-5">
							<button
								class=" bg-gray-900 hover:bg-gray-800 w-full rounded-full text-white font-semibold text-sm py-3 transition"
								type="submit"
							>
								{mode === 'signin' ? $i18n.t('Sign in') : $i18n.t('Create Account')}
							</button>

							<div class=" mt-4 text-sm text-center">
								{mode === 'signin'
									? $i18n.t("Don't have an account?")
									: $i18n.t('Already have an account?')}

								<button
									class=" font-medium underline"
									type="button"
									on:click={() => {
										if (mode === 'signin') {
											mode = 'signup';
										} else {
											mode = 'signin';
										}
									}}
								>
									{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
								</button>
							</div>
						</div>
					</form>
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.font-mona {
		font-family: 'Mona Sans', -apple-system, 'Arimo', ui-sans-serif, system-ui, 'Segoe UI', Roboto,
			Ubuntu, Cantarell, 'Noto Sans', sans-serif, 'Helvetica Neue', Arial, 'Apple Color Emoji',
			'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
	}
</style>
