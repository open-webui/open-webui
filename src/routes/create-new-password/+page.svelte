<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite, confirmPasswordReset } from '$lib/apis/auths';

	import { WEBUI_NAME, config, user, socket, toastVisible, toastMessage, toastType, showToast } from '$lib/stores';

	import Plus from '$lib/components/icons/Plus.svelte';
	import UserIcon from '$lib/components/icons/UserIcon.svelte';
	import ShowPassIcon from '$lib/components/icons/ShowPassIcon.svelte';
	import CustomToast from '$lib/components/common/CustomToast.svelte';
	import LoaderIcon from '$lib/components/icons/LoaderIcon.svelte';
	import HidePassIcon from '$lib/components/icons/HidePassIcon.svelte';

	const i18n = getContext('i18n');

    let password = '';
	let showPassword = false;
	let confirmPassword = '';
	let showConfirmPassword = false;

	let resetToken = '';
	let inviteToken = '';
	let isPasswordReset = false;
	let isInvite = false;
	let tokenValid = true;
	let resetComplete = false;

	let loading = false;

	onMount(() => {
		// Check for invite token
		if ($page.url.searchParams.get('inviteToken')) {
			inviteToken = $page.url.searchParams.get('inviteToken');
			isInvite = true;
		}
		
		// Check for password reset token
		if ($page.url.searchParams.get('token')) {
			resetToken = $page.url.searchParams.get('token');
			isPasswordReset = true;
		}
		
		// Validate token presence
		if (!inviteToken && !resetToken) {
			tokenValid = false;
			showToast('error', 'Invalid or missing token. Please request a new link.');
		}
	});

	const validatePassword = (password: string): boolean => {
		// Same regex as used in backend
		const strongPasswordRegex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$/;
		return strongPasswordRegex.test(password);
	};

	const changePassword = async () => {
		if (password !== confirmPassword) {
			showToast('error', `The passwords you entered don't quite match. Please double-check and try again.`);
			return;
		}
		
		if (!validatePassword(password)) {
			showToast('error', "Password must be 8+ characters, with a number, capital letter, and symbol.");
			return;
		}
		
		loading = true;
		
		try {
			if (isPasswordReset) {
				// Handle password reset
				await confirmPasswordReset(resetToken, password);
				resetComplete = true;
				showToast('success', 'Password has been reset successfully. You can now log in with your new password.');
			} else if (isInvite) {
				// Handle invite completion
				// This is the existing functionality
				// TODO: Implement invite completion
			}
		} catch (error) {
			console.error('Error processing request:', error);
			showToast('error', isPasswordReset 
				? 'Failed to reset password. The link may be invalid or expired.' 
				: 'Failed to complete invitation. Please try again.');
		} finally {
			loading = false;
		}

		if (resetComplete) {
			setTimeout(() => {
				goto('/login');
			}, 3000);
		}
	}

	let logoSrc = '/logo_light.png';

	onMount(() => {
		const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		logoSrc = isDark ? '/logo_dark_transparent.png' : '/logo_light_transparent.png';
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME} - ${isPasswordReset ? 'Reset Password' : 'Create New Password'}`}
	</title>
</svelte:head>

<CustomToast message={$toastMessage} type={$toastType} visible={$toastVisible} />
<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh] px-4 bg-lightGray-300 text-white relative dark:bg-customGray-900"
>
    <div></div>
	
	{#if !tokenValid}
		<div class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-full md:w-[31rem] px-5 py-5 md:pt-7 md:px-24 md:pb-4">
			<div class="self-center flex flex-col items-center mb-5">
				<div>
					<img crossorigin="anonymous" src={logoSrc} class="w-10 mb-5" alt="logo" />
				</div>
				<div class="mb-2.5">{$i18n.t('Invalid Link')}</div>
				<div class="text-center text-xs dark:text-customGray-300">
					{$i18n.t('The link is invalid or has expired.')}
				</div>
			</div>
			<button
				class="text-xs w-full h-10 px-3 py-2 transition rounded-lg bg-black hover:bg-gray-900 text-white dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700 flex justify-center items-center"
				on:click={() => goto(isPasswordReset ? '/reset-password' : '/login')}
			>
				{isPasswordReset ? $i18n.t('Request New Reset Link') : $i18n.t('Go to Login')}
			</button>
		</div>
	{:else if resetComplete}
		<div class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-full md:w-[31rem] px-5 py-5 md:pt-7 md:px-24 md:pb-4">
			<div class="self-center flex flex-col items-center mb-5">
				<div>
					<img crossorigin="anonymous" src={logoSrc} class="w-10 mb-5" alt="logo" />
				</div>
				<div class="mb-2.5 font-medium text-lightGray-100 dark:text-customGray-100">{$i18n.t('Password Reset Complete')}</div>
				<div class="font-medium text-center text-xs text-[#8A8B8D] dark:text-customGray-300">
					{$i18n.t('Your password has been reset successfully.')}
				</div>
			</div>
			<button
				class="text-xs w-full h-10 px-3 py-2 transition rounded-lg bg-lightGray-300 border-lightGray-400 font-medium hover:bg-lightGray-700 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700 flex justify-center items-center"
				on:click={() => goto('/login')}
			>
				{$i18n.t('Go to Login')}
			</button>
		</div>
	{:else}
		<form
			class="flex flex-col self-center bg-lightGray-800 dark:bg-customGray-800 rounded-2xl w-full md:w-[31rem] px-5 py-5 md:pt-8 md:px-24 md:pb-16"
			on:submit={(e) => {
				e.preventDefault();
				changePassword();
			}}
		>
			<div class="self-center flex flex-col items-center mb-5">
				<div>
					<img crossorigin="anonymous" src={logoSrc} class=" w-10 mb-5" alt="logo" />
				</div>
				<div class="mb-2.5 font-medium text-lightGray-100 dark:text-customGray-100">
					{isPasswordReset ? $i18n.t('Reset Your Password') : $i18n.t('Create new password')}
				</div>
				<div class="text-center text-xs font-medium text-[#8A8B8D] dark:text-customGray-300">
					{isPasswordReset ? $i18n.t('Please enter your new password') : $i18n.t('Please, create new password')}
				</div>
			</div>
			<div class="flex flex-col w-full mb-2.5">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if password}
						<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
							{isPasswordReset ? $i18n.t('New Password') : $i18n.t('Create Password')}
						</div>
					{/if}
					{#if showPassword}
						<input
							class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
							type="text"
							bind:value={password}
							placeholder={isPasswordReset ? $i18n.t('New Password') : $i18n.t('Create Password')}
							autocomplete="new-password"
							required
						/>
					{:else}
						<input
							class={`px-2.5 text-sm ${password ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
							type="password"
							bind:value={password}
							placeholder={isPasswordReset ? $i18n.t('New Password') : $i18n.t('Create Password')}
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
					{#if showPassword}
						<HidePassIcon/>
					{:else}
						<ShowPassIcon/>
					{/if}
					</button>
				</div>
			</div>
			<div class="flex flex-col w-full mb-2.5">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if confirmPassword}
						<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
							{$i18n.t('Confirm password')}
						</div>
					{/if}
					{#if showConfirmPassword}
						<input
							class={`px-2.5 text-sm ${confirmPassword ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
							type="text"
							bind:value={confirmPassword}
							placeholder={$i18n.t('Confirm Password')}
							autocomplete="new-password"
							required
						/>
					{:else}
						<input
							class={`px-2.5 text-sm ${confirmPassword ? 'pt-2' : 'pt-0'} text-lightGray-100 placeholder:text-lightGray-100 w-full h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none pr-10`}
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
					{#if showConfirmPassword}
						<HidePassIcon/>
					{:else}
						<ShowPassIcon/>
					{/if}
					</button>
				</div>
			</div>
			
			<div class="text-xs text-[#8A8B8D] dark:text-customGray-300 mb-4">
				{$i18n.t('Password must be at least 8 characters with a number, capital letter, and symbol.')}
			</div>
			
			<button
				class=" text-xs w-full h-10 font-medium px-3 py-2 transition rounded-lg {loading
					? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-700 hover:bg-gray-900 text-lightGray-100 border-lightGray-400 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
					: 'bg-lightGray-300 hover:bg-lightGray-700 hover:bg-gray-900 text-lightGray-100 border-lightGray-400 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center items-center"
				type="submit"
				disabled={loading}
			>
				{isPasswordReset ? $i18n.t('Reset Password') : $i18n.t('Done')}
				{#if loading}
					<div class="ml-1.5 self-center">
						<LoaderIcon/>
					</div>
				{/if}
			</button>
		</form>
	{/if}
    <div class="self-center text-xs text-customGray-300 dark:text-customGray-100 pb-5 text-center">By using this service, you agree to our <a href="/">Terms</a> and <a href="/">Conditions</a>.</div>
</div>
