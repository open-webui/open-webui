<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import {
		WEBUI_NAME,
		config,
		user,
		socket,
		toastVisible,
		toastMessage,
		toastType,
		showToast
	} from '$lib/stores';
	import { getSessionUser, userSignIn, requestPasswordReset } from '$lib/apis/auths';

	import Plus from '$lib/components/icons/Plus.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';
	import ShowPassIcon from '$lib/components/icons/ShowPassIcon.svelte';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';

	const i18n = getContext('i18n');

	let email = '';
	let loading = false;

	const resetPassword = async () => {
		loading = true;
		try {
			await requestPasswordReset(email);
			showToast('success', 'If the email exists, a reset link has been sent.');
		} catch (error) {
			console.error('Error requesting password reset:', error);
			showToast('error', 'An error occurred. Please try again later.');
		} finally {
			loading = false;
		}
	};

	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = localStorage.getItem('theme') === 'dark';
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_light_transparent.png';
	});

	$: console.log($config?.oauth?.providers?.google);
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />
<a
	href="/login"
	class="bg-transparent flex items-center text-xs font-medium text-lightGray-100 dark:text-customGray-200 w-fit fixed z-30 top-4 left-4"
>
	<ArrowLeft className="size-3 mr-1" />
	Back to Login</a
>
<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh] px-4 text-white relative bg-lightGray-300 dark:bg-customGray-900"
>
	<div></div>
	<form
		class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-full md:w-[31rem] px-5 py-5 md:pt-7 md:px-24 md:pb-4"
		on:submit={(e) => {
			e.preventDefault();
			resetPassword();
		}}
	>
		<div class="self-center flex flex-col items-center mb-5">
			<div>
				<img
					crossorigin="anonymous"
					src={logoSrc}
					class=" w-10 mb-5"
					alt="logo"
				/>
			</div>
			<div class="mb-2.5 font-medium text-lightGray-100 dark:text-customGray-100">{$i18n.t('Reset password')}</div>
			<div class="font-medium text-center text-xs text-[#8A8B8D] dark:text-customGray-300">
				{$i18n.t('Enter your email to get a reset link')}
			</div>
		</div>
		<div class="flex-1 mb-2.5">
			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if email}
					<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
						{$i18n.t('Email address')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${email ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('Email address')}
					bind:value={email}
					type="email"
					autocomplete="email"
					name="email"
					required
				/>
			</div>
		</div>
		<button
			class="font-medium text-xs w-full h-10 px-3 py-2 transition rounded-lg {loading
				? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-700 hover:bg-gray-900 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border border-lightGray-400 dark:border-customGray-700'
				: 'bg-lightGray-300 hover:bg-lightGray-700 hover:bg-gray-900 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border border-lightGray-400 dark:border-customGray-700'} flex justify-center items-center"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Send')}
			{#if loading}
				<div class="ml-1.5 self-center">
					<LoaderIcon />
				</div>
			{/if}
		</button>
	</form>

	<div class="self-center text-xs text-customGray-300 dark:text-customGray-100 pb-5 text-center">
		By using this service, you agree to our <a href="/">Terms</a> and <a href="/">Conditions</a>.
	</div>
</div>
