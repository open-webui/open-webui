<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, config } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext<Readable<I18n>>('i18n');

	let loaded = false;

	onMount(async () => {
		if ($config) return goto('/');
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('{{webUIName}} Backend Required', { webUIName: $WEBUI_NAME })}</title>
</svelte:head>

{#if loaded}
	<div class="min-h-dvh bg-base-0 text-base-1000 dark:bg-base-1000 dark:text-base-0 relative">
		<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>
		<main
			id="main-content"
			tabindex="-1"
			class="min-h-dvh w-full p-6 flex flex-col items-center justify-center text-center"
		>
			<div class="my-auto w-full sm:max-w-xl py-20 sm:pb-10 sm:pt-0 dark:text-base-100">
				<h1 class="text-xl font-normal">
					{$i18n.t('{{webUIName}} Backend Required', { webUIName: $WEBUI_NAME })}
				</h1>
				<p class="mt-3 text-xs leading-5 text-balance text-base-500 dark:text-base-400">
					{$i18n.t(
						"You're using an unsupported method (frontend only). Please serve the WebUI from the backend."
					)}
				</p>
				<p class="mt-1 text-xs leading-5 text-base-500 dark:text-base-400">
					<a
						class="underline hover:text-base-1000 dark:hover:text-base-0 transition"
						href="https://github.com/open-webui/open-webui#how-to-install-"
						target="_blank"
						rel="noopener noreferrer">{$i18n.t('See readme.md for instructions')}</a
					>
					{$i18n.t('or')}
					<a
						class="underline hover:text-base-1000 dark:hover:text-base-0 transition"
						href="https://discord.gg/5rJgQTnV4s"
						target="_blank"
						rel="noopener noreferrer">{$i18n.t('join our Discord for help.')}</a
					>
				</p>

				<button
					class="mt-6 mx-auto flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
					on:click={() => (location.href = '/')}
				>
					{$i18n.t('Check Again')}
				</button>
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
{/if}
