<script>
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let firstName = '';
	let lastName = '';
	let password = '';
	let confirmPassword = '';

	let loading = false;

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
			goto('/');
		}
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	onMount(async () => {});
	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_dark.png';
	});

	$: console.log($WEBUI_NAME);
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh] text-white relative dark:bg-customGray-900"
>
	<div class="self-center flex flex-col items-center mt-5">
		<div>
			<img crossorigin="anonymous" src="/logo_dark_transparent.png" class=" w-10 mb-5" alt="logo" />
		</div>
		<div>{$i18n.t('Welcome to')} {$WEBUI_NAME}</div>
	</div>
	<form
		class="flex flex-col self-center dark:bg-customGray-800 rounded-2xl w-[31rem] pt-8 px-24 pb-16"
	>
		<div class="flex-1 mb-1.5">
			<div class="relative w-full dark:bg-customGray-900 rounded-md">
				{#if firstName}
					<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
						{$i18n.t('First Name')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${firstName ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('First Name')}
					bind:value={firstName}
					required
				/>
			</div>
		</div>
		<div class="flex-1 mb-1.5">
			<div class="relative w-full dark:bg-customGray-900 rounded-md">
				{#if lastName}
					<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
						{$i18n.t('Last Name')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${lastName ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('Last Name')}
					bind:value={lastName}
					required
				/>
			</div>
		</div>
		<div class="flex flex-col w-full mb-2.5">
			<div class="relative w-full dark:bg-customGray-900 rounded-md">
				{#if password}
					<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
						{$i18n.t('Create Password')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${password ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					type="password"
					bind:value={password}
					placeholder={$i18n.t('Create Password')}
					autocomplete="new-password"
					required
				/>
			</div>
		</div>
		<div class="flex flex-col w-full mb-2.5">
			<div class="relative w-full dark:bg-customGray-900 rounded-md">
				{#if confirmPassword}
					<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
						{$i18n.t('Confirm password')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${confirmPassword ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					type="password"
					bind:value={confirmPassword}
					placeholder={$i18n.t('Confirm password')}
					autocomplete="new-password"
					required
				/>
			</div>
		</div>
		<button
			class=" text-xs w-full h-10 px-3 py-2 transition rounded-lg {loading
				? ' cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
				: 'bg-black hover:bg-gray-900 text-white dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center items-center"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Register')}
		</button>
	</form>
    <div class="self-center text-xs dark:text-customGray-100 pb-5">By using this service, you agree to our <a href="/">Terms</a> and <a href="/">Conditions</a>.</div>
</div>
