<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import { getBackendConfig } from '$lib/apis';
	import { guestLogin, updateUserTimezone } from '$lib/apis/auths';

	import { config, user, socket } from '$lib/stores';
	import { getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';

	let error = '';

	onMount(async () => {
		if ($user) {
			await goto('/');
			return;
		}

		if (!$config?.features?.enable_guest_access) {
			error = 'Guest access is not enabled.';
			return;
		}

		try {
			const sessionUser = await guestLogin();
			if (sessionUser?.token) {
				localStorage.token = sessionUser.token;
				$socket?.emit('user-join', { auth: { token: sessionUser.token } });
				await user.set(sessionUser);
				await config.set(await getBackendConfig());

				const timezone = getUserTimezone();
				if (timezone) {
					updateUserTimezone(sessionUser.token, timezone);
				}

				await goto('/');
			}
		} catch (e) {
			error = e?.toString() || 'Failed to create guest session.';
		}
	});
</script>

<div class="flex items-center justify-center min-h-screen bg-white dark:bg-gray-900">
	{#if error}
		<p class="text-red-500 text-sm">{error}</p>
	{:else}
		<Spinner className="size-5" />
	{/if}
</div>
