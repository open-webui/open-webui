<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { userResetPassword } from '$lib/apis/auths';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config } from '$lib/stores';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let password = '';

	$: token = $page.url.searchParams.get('token');

	const submitHandler = async (/** @type {string} */ token) => {
		const res = await userResetPassword(password, token).catch((error) => {
			toast.error(error);
			return null;
		});

		if (!res) return;

		toast.success($i18n.t('Password changed successfully.'));

		goto('/auth');
	};
</script>

<div class="fixed m-10 z-50">
	<div class="flex space-x-2">
		<div class=" self-center">
			<img src="{WEBUI_BASE_URL}/static/favicon.png" class=" w-8 rounded-full" alt="logo" />
		</div>
	</div>
</div>

<div class=" bg-white dark:bg-gray-950 min-h-screen w-full flex justify-center font-mona">
	<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
		<div class="my-auto pb-10 w-full dark:text-gray-100">
			{#if !($config?.email_enabled ?? false)}
				<div>
					<h1 class=" text-xl sm:text-2xl font-bold">{$i18n.t('Error')}</h1>
					<p>{$i18n.t('Email service is not properly configured. Please contact support.')}</p>
				</div>
			{:else if !token}
				<p>{$i18n.t('Error: Password reset link is invalid or has expired.')}</p>
			{:else}
				<form
					class=" flex flex-col justify-center"
					on:submit|preventDefault={() => {
						submitHandler(token);
					}}
				>
					<div class=" text-xl sm:text-2xl font-bold">
						{$i18n.t('Reset Password')}
					</div>
					<div class="flex flex-col mt-4">
						<div>
							<label for="password" class="text-sm font-semibold text-left mb-1 block">
								{$i18n.t('New Password')}
							</label>
							<input
								id="password"
								bind:value={password}
								type="password"
								class=" px-5 py-3 rounded-2xl w-full text-sm outline-none border dark:border-none dark:bg-gray-900"
								placeholder={$i18n.t('Enter Your Password')}
								autocomplete="new-password"
								required
							/>
						</div>

						<div class="mt-5">
							<button
								class=" bg-gray-900 hover:bg-gray-800 w-full rounded-full text-white font-semibold text-sm py-3 transition"
								type="submit"
							>
								{$i18n.t('Reset Password')}
							</button>
						</div>
					</div>
				</form>
			{/if}
		</div>
	</div>
</div>
