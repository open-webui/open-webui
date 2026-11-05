<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { get, type Readable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { user, config, WEBUI_NAME } from '$lib/stores';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<Readable<I18n>>('i18n');

	let error = '';

	onMount(async () => {
		if (!/^[a-f0-9-]{36}$/i.test($page.params.id ?? '')) {
			error = $i18n.t('Invalid login request.');
			return;
		}
		const continuation = `/auth/sessions/${$page.params.id}`;
		sessionStorage.setItem('auth:continue', continuation);
		try {
			if (!get(user)) {
				const provider = $page.url.searchParams.get('provider');
				if (provider && Object.hasOwn(get(config)?.oauth?.providers ?? {}, provider)) {
					location.href = `${WEBUI_BASE_URL}/oauth/${encodeURIComponent(provider)}/login`;
				} else {
					await goto('/auth?redirect=' + encodeURIComponent(continuation));
				}
				return;
			}
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/auths/sessions/${encodeURIComponent($page.params.id ?? '')}/authorize`,
				{
					method: 'POST',
					headers: { Authorization: `Bearer ${localStorage.token}` },
					credentials: 'include'
				}
			);
			const result = await response.json();
			if (!response.ok) throw new Error(result.detail || $i18n.t('Could not complete sign-in.'));
			const callback = new URL(result.redirect_uri);
			if (callback.protocol !== 'http:' || callback.hostname !== '127.0.0.1')
				throw new Error($i18n.t('Invalid callback.'));
			sessionStorage.removeItem('auth:continue');
			location.assign(callback.href);
		} catch (cause) {
			sessionStorage.removeItem('auth:continue');
			error = cause instanceof Error ? cause.message : String(cause);
		}
	});
</script>

<svelte:head>
	<title
		>{error ? $i18n.t('Could not complete sign-in') : $i18n.t('Completing sign-in…')} · {$WEBUI_NAME}</title
	>
</svelte:head>

<div class="min-h-dvh bg-white text-black dark:bg-black dark:text-white relative">
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>
	<main
		id="main-content"
		tabindex="-1"
		class="min-h-dvh w-full p-6 flex flex-col items-center justify-center text-center"
	>
		<div class="my-auto w-full sm:max-w-md py-20 sm:pb-10 sm:pt-0 dark:text-gray-100">
			{#if $config?.metadata?.auth_logo_position === 'center'}
				<div class="flex justify-center mb-6">
					<img
						crossorigin="anonymous"
						src="{WEBUI_BASE_URL}/static/favicon.png"
						class="size-24 rounded-full"
						alt="{$WEBUI_NAME} logo"
					/>
				</div>
			{/if}

			{#if error}
				<h1 class="text-xl font-normal">{$i18n.t('Could not complete sign-in')}</h1>
				<p role="alert" class="mt-4 text-xs leading-4 text-red-600 dark:text-red-400">{error}</p>
				<p class="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400">
					{$i18n.t('Return to the app and sign in again.')}
				</p>
			{:else}
				<div role="status">
					<h1 class="text-xl font-normal">{$i18n.t('Completing sign-in…')}</h1>
					<div class="mt-5 flex justify-center text-gray-500 dark:text-gray-400">
						<Spinner className="size-5" />
					</div>
				</div>
			{/if}
		</div>
	</main>

	{#if !$config?.metadata?.auth_logo_position || $config?.metadata?.auth_logo_position === 'top-right'}
		<div
			class="fixed top-0 m-10 z-50"
			class:left-0={!$config?.metadata?.auth_logo_position}
			class:right-0={$config?.metadata?.auth_logo_position === 'top-right'}
		>
			<img
				crossorigin="anonymous"
				src="{WEBUI_BASE_URL}/static/favicon.png"
				class="w-6 rounded-full"
				alt="{$WEBUI_NAME} logo"
			/>
		</div>
	{/if}
</div>
