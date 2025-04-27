<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { completeInvite } from '$lib/apis/auths';

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
	let showConfirmPassword = '';

	let resetToken = '';

	let loading = false;

	onMount(() => {
		if ($page.url.searchParams.get('inviteToken')) {
			resetToken = $page.url.searchParams.get('inviteToken')
		}
	})

	const changePassword = async () => {
		if (password !== confirmPassword) {
			showToast('error', `The passwords you entered don't quite match. Please double-check and try again.`);
			return;
		}
		const strongPasswordRegex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/;

		if (!strongPasswordRegex.test(password)) {
			showToast('error', "Password must be 8+ characters, with a number, capital letter, and symbol.");
			return;
		}
		loading = true;
        //Login to implement
		loading = false;

        goto('/login')

	}

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
<div
	class="flex flex-col justify-between w-full h-screen max-h-[100dvh] text-white relative dark:bg-customGray-900"
>
    <div></div>
	
	<form
		class="flex flex-col self-center dark:bg-customGray-800 rounded-2xl w-[31rem] pt-8 px-24 pb-16"
		on:submit={(e) => {
			e.preventDefault();
			changePassword();
		}}
	>
        <div class="self-center flex flex-col items-center mb-5">
            <div>
                <img crossorigin="anonymous" src="/logo_dark_transparent.png" class=" w-10 mb-5" alt="logo" />
            </div>
            <div class="mb-2.5">{$i18n.t('Create new password')}</div>
            <div class="text-center text-xs dark:text-customGray-300">{$i18n.t('Please, create new password')}</div>
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
				{#if showPassword}
					<HidePassIcon/>
				{:else}
					<ShowPassIcon/>
				{/if}
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
				{#if showConfirmPassword}
					<HidePassIcon/>
				{:else}
					<ShowPassIcon/>
				{/if}
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
			{$i18n.t('Done')}
			{#if loading}
				<div class="ml-1.5 self-center">
					<LoaderIcon/>
				</div>
			{/if}
		</button>
	</form>
    <div class="self-center text-xs dark:text-customGray-100 pb-5">By using this service, you agree to our <a href="/">Terms</a> and <a href="/">Conditions</a>.</div>
</div>
