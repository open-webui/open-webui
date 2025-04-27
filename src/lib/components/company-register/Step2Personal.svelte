<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite } from '$lib/apis/auths';

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

	import Plus from '$lib/components/icons/Plus.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';
	import ShowPassIcon from '$lib/components/icons/ShowPassIcon.svelte';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let email = '';
	let code = '';
	let password = '';
	let showPassword = false;
	let confirmPassword = '';
	let showConfirmPassword = '';

	let inviteToken = '';

	let loading = false;

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			showToast('success', `You're now logged in.`);
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());
			goto('/');
		}
	};

	const confirmHandler = async () => {
		if (password !== confirmPassword) {
			showToast(
				'error',
				`The passwords you entered don't quite match. Please double-check and try again.`
			);
			return;
		}
		const strongPasswordRegex =
			/^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/;

		if (!strongPasswordRegex.test(password)) {
			showToast(
				'error',
				'Password must be 8+ characters, with a number, capital letter, and symbol.'
			);
			return;
		}
		dispatch('next');
	};

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

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />

<form
	class="flex flex-col self-center dark:bg-customGray-800 rounded-2xl w-[31rem] pt-8 px-24 pb-16"
	on:submit={(e) => {
		e.preventDefault();
		confirmHandler();
	}}
>
	<div class="self-center flex flex-col items-center mb-5">
		<div>
			<img crossorigin="anonymous" src="/logo_dark_transparent.png" class=" w-10 mb-5" alt="logo" />
		</div>
		<div class="mb-2.5">{$i18n.t('Verify Your identity')}</div>
		<div class="text-center text-xs dark:text-customGray-300">
			{$i18n.t('We’ve sent an email with your code to {{email}}', { email: 'test@test.test' })}
		</div>
	</div>
	<div class="flex-1 mb-2.5">
		<div class="relative w-full dark:bg-customGray-900 rounded-md">
			{#if email}
				<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
					{$i18n.t('Email address')}
				</div>
			{/if}
			<input
				class={`px-2.5 text-sm ${email ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
				placeholder={$i18n.t('Email address')}
				bind:value={email}
				type="email"
				autocomplete="email"
				name="email"
				required
			/>
			<button
				type="button"
				class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-customBlue-500"
				on:click={() => {}}
				tabindex="-1"
			>
				Edit
			</button>
		</div>
	</div>

	<div class="flex-1 mb-2.5">
		<div class="relative w-full dark:bg-customGray-900 rounded-md">
			{#if code}
				<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
					{$i18n.t('Enter the code')}
				</div>
			{/if}
			<input
				class={`px-2.5 text-sm ${code ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
				placeholder={$i18n.t('Enter the code')}
				bind:value={code}
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
			{#if showPassword}
				<input
					class={`px-2.5 text-sm ${password ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="text"
					bind:value={password}
					placeholder={$i18n.t('Create Password')}
					autocomplete="new-password"
					required
				/>
			{:else}
				<input
					class={`px-2.5 text-sm ${password ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="password"
					bind:value={password}
					placeholder={$i18n.t('Create Password')}
					autocomplete="new-password"
					required
				/>
			{/if}

			<button
				type="button"
				class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-500 dark:text-white"
				on:click={() => (showPassword = !showPassword)}
				tabindex="-1"
			>
				<ShowPassIcon />
			</button>
		</div>
	</div>
	<div class="flex flex-col w-full mb-2.5">
		<div class="relative w-full dark:bg-customGray-900 rounded-md">
			{#if confirmPassword}
				<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
					{$i18n.t('Confirm password')}
				</div>
			{/if}
			{#if showConfirmPassword}
				<input
					class={`px-2.5 text-sm ${confirmPassword ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="text"
					bind:value={confirmPassword}
					placeholder={$i18n.t('Confirm Password')}
					autocomplete="new-password"
					required
				/>
			{:else}
				<input
					class={`px-2.5 text-sm ${confirmPassword ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
					type="password"
					bind:value={confirmPassword}
					placeholder={$i18n.t('Confirm Password')}
					autocomplete="new-password"
					required
				/>
			{/if}

			<button
				type="button"
				class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-500 dark:text-white"
				on:click={() => (showConfirmPassword = !showConfirmPassword)}
				tabindex="-1"
			>
				<ShowPassIcon />
			</button>
		</div>
	</div>
	<button
		class=" text-xs w-full h-10 px-3 py-2 transition rounded-lg {loading
			? ' cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
			: 'bg-black hover:bg-gray-900 text-white dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center items-center"
		type="submit"
		disabled={loading}
	>
		{$i18n.t('Continue')}
		{#if loading}
			<div class="ml-1.5 self-center">
				<LoaderIcon />
			</div>
		{/if}
	</button>
	<div class="mt-5 text-xs dark:text-customGray-300 flex justify-center">
		{$i18n.t(`Didn't recive an email?`)}
		<button on:click={() => {}} class="text-customBlue-500 ml-1">{$i18n.t('Resend')}</button>
	</div>
</form>
