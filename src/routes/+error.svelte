<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { page } from '$app/stores';
	import { WEBUI_NAME } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext<Readable<I18n>>('i18n');
</script>

<svelte:head>
	<title>{$page.status} · {$WEBUI_NAME}</title>
</svelte:head>

<div class="min-h-dvh bg-base-0 text-base-1000 dark:bg-base-1000 dark:text-base-0 relative">
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region"></div>
	<main
		id="main-content"
		tabindex="-1"
		class="min-h-dvh w-full p-6 flex flex-col items-center justify-center text-center"
	>
		<div class="my-auto w-full sm:max-w-xl py-20 sm:pb-10 sm:pt-0 dark:text-base-100">
			<h1 class="text-xl font-normal tabular-nums">{$page.status}</h1>
			{#if $page.error?.message}
				<p class="mt-3 text-xs leading-5 text-balance text-base-500 dark:text-base-400">
					{$page.error.message}
				</p>
			{/if}

			<a
				href="/"
				class="mt-6 mx-auto flex w-fit h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
			>
				{$i18n?.t('Home') ?? 'Home'}
			</a>
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
