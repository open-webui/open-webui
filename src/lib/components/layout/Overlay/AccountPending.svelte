<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { getAdminDetails, getLogoutRedirectUrl, userSignOut } from '$lib/apis/auths';
	import { onMount, getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { config, WEBUI_NAME } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext<Readable<I18n>>('i18n');

	let adminDetails: { name: string; email: string } | null = null;

	$: title = ($config?.ui?.pending_user_overlay_title ?? '').trim();
	$: content = ($config?.ui?.pending_user_overlay_content ?? '').trim();

	const signOut = async () => {
		const res = await userSignOut().catch((err) => {
			console.error(err);
			return null;
		});
		localStorage.removeItem('token');
		location.href = getLogoutRedirectUrl(res?.redirect_url);
	};

	onMount(async () => {
		adminDetails = await getAdminDetails(localStorage.token).catch((err) => {
			console.error(err);
			return null;
		});
	});
</script>

<div
	class="fixed inset-0 z-999 overflow-y-auto bg-base-0 text-base-1000 dark:bg-base-1000 dark:text-base-0"
>
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>
	<main
		id="main-content"
		tabindex="-1"
		class="min-h-dvh w-full p-6 flex flex-col items-center justify-center text-center"
	>
		<div class="my-auto w-full sm:max-w-xl py-20 sm:pb-10 sm:pt-0 dark:text-base-100">
			<h1 class="text-xl font-normal whitespace-pre-wrap">
				{title || $i18n.t('Account Activation Pending')}
			</h1>

			<div
				class="mt-3 text-xs leading-5 text-balance text-base-500 dark:text-base-400 [&_a]:underline"
			>
				{#if content}
					{@html DOMPurify.sanitize(marked.parse(content.replace(/\n/g, '<br>')) as string)}
				{:else}
					{$i18n.t('Your account status is currently pending activation.')}
					{$i18n.t(
						'To access the WebUI, please reach out to the administrator. Admins can manage user statuses from the Admin Panel.'
					)}
				{/if}
			</div>

			{#if adminDetails}
				<p class="mt-1 text-xs leading-5 text-base-500 dark:text-base-400">
					{$i18n.t('Admin')}: {adminDetails.name} ·
					<a
						class="underline hover:text-base-1000 dark:hover:text-base-0 transition"
						href="mailto:{adminDetails.email}">{adminDetails.email}</a
					>
				</p>
			{/if}

			<div class="mt-6 flex justify-center gap-1">
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
					on:click={() => (location.href = '/')}
				>
					{$i18n.t('Check Again')}
				</button>
				<button
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal text-base-600 transition hover:bg-base-100 hover:text-base-900 dark:text-base-400 dark:hover:bg-base-850 dark:hover:text-base-0"
					on:click={signOut}
				>
					{$i18n.t('Sign Out')}
				</button>
			</div>
		</div>
	</main>

	<div class="fixed top-0 left-0 m-10 z-50">
		<img
			crossorigin="anonymous"
			src="{WEBUI_BASE_URL}/static/favicon.png"
			class="w-6 rounded-full"
			alt="{$WEBUI_NAME} logo"
		/>
	</div>
</div>
