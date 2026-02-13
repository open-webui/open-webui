<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { forceResetPassword, getSessionUser } from '$lib/apis/auths';
	import { getBackendConfig } from '$lib/apis';
	import { WEBUI_NAME, config, user } from '$lib/stores';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let newPassword = '';
	let confirmPassword = '';
	let loading = false;

	onMount(async () => {
		if (!localStorage.token) {
			await goto('/auth');
			return;
		}

		// Verify user actually needs to change password
		const sessionUser = await getSessionUser(localStorage.token).catch(() => null);
		if (!sessionUser) {
			localStorage.removeItem('token');
			await goto('/auth');
			return;
		}

		if (!sessionUser.must_change_password) {
			// User doesn't need to change password, redirect to home
			await goto('/');
			return;
		}

		loaded = true;
	});

	const handleSubmit = async () => {
		if (newPassword.length < 8) {
			toast.error($i18n.t('Password must be at least 8 characters.'));
			return;
		}

		if (newPassword !== confirmPassword) {
			toast.error($i18n.t('Passwords do not match.'));
			return;
		}

		loading = true;
		try {
			await forceResetPassword(localStorage.token, newPassword);
			toast.success($i18n.t('Password updated successfully.'));

			// Refresh session and redirect
			const sessionUser = await getSessionUser(localStorage.token).catch(() => null);
			if (sessionUser) {
				await user.set(sessionUser);
				await config.set(await getBackendConfig());
			}
			await goto('/');
		} catch (error) {
			toast.error(`${error}`);
		}
		loading = false;
	};
</script>

<svelte:head>
	<title>Set New Password | {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="fixed m-10 z-50">
		<div class="flex space-x-2">
			<div class=" self-center">
				<img
					crossorigin="anonymous"
					src={$config?.ui?.favicon_url ?? '/static/favicon.png'}
					class=" size-6 rounded-full"
					alt="logo"
				/>
			</div>
		</div>
	</div>

	<div class="min-h-screen w-full flex items-center justify-center bg-white dark:bg-gray-950">
		<div class="w-full max-w-md px-6">
			<div class="text-center mb-8">
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Set New Password')}
				</h1>
				<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('Your administrator requires you to set a new password before continuing.')}
				</p>
			</div>

			<form class="flex flex-col gap-4" on:submit|preventDefault={handleSubmit}>
				<div>
					<label
						for="new-password"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
					>
						{$i18n.t('New Password')}
					</label>
					<SensitiveInput
						id="new-password"
						bind:value={newPassword}
						placeholder={$i18n.t('Enter new password')}
						required
					/>
				</div>

				<div>
					<label
						for="confirm-password"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
					>
						{$i18n.t('Confirm Password')}
					</label>
					<SensitiveInput
						id="confirm-password"
						bind:value={confirmPassword}
						placeholder={$i18n.t('Confirm new password')}
						required
					/>
				</div>

				<button
					type="submit"
					disabled={loading}
					class="w-full mt-2 py-2.5 px-4 rounded-xl bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-medium text-sm hover:bg-gray-800 dark:hover:bg-gray-100 transition disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if loading}
						{$i18n.t('Updating...')}
					{:else}
						{$i18n.t('Set Password')}
					{/if}
				</button>
			</form>

			<div class="mt-6 text-center">
				<button
					type="button"
					class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition"
					on:click={async () => {
						localStorage.removeItem('token');
						await goto('/auth');
					}}
				>
					{$i18n.t('Sign out and use a different account')}
				</button>
			</div>
		</div>
	</div>
{/if}
