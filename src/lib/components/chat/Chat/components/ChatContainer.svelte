<script lang="ts">
	import { getContext } from 'svelte';
	import { fade } from 'svelte/transition';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import { showSidebar, settings, config, showArtifacts } from '$lib/stores';
	
	export let loading = false;
	
	const i18n: Writable<i18nType> = getContext('i18n');
</script>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} w-full max-w-full flex flex-col font-size-{$settings?.fontSize ?? 'normal'}"
	id="chat-container"
>
	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			{#if $settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url ?? null}
				<div
					class="absolute {$showSidebar
						? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
						: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$settings?.backgroundImageUrl ??
						$config?.license_metadata?.background_image_url})"
				/>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
				/>
			{/if}

			<PaneGroup direction="horizontal" class="w-full h-full">
				<Pane defaultSize={50} class="h-full flex relative max-w-full flex-col">
					<slot name="main" />
				</Pane>
				
				{#if $showArtifacts}
					<PaneResizer class="relative w-1 bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600 transition-colors" />
					<Pane defaultSize={50} minSize={25} class="h-full">
						<slot name="artifacts" />
					</Pane>
				{/if}
			</PaneGroup>
		</div>
	{:else}
		<div class="flex items-center justify-center h-full">
			<div class="flex flex-col items-center gap-3">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
				<div class="text-gray-600 dark:text-gray-400">{$i18n.t('Loading chat...')}</div>
			</div>
		</div>
	{/if}
</div>