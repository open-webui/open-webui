<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		models,
		prompts,
		knowledge,
		tools
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import MenuLines from '$lib/components/icons/MenuLines.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			if ($page.url.pathname.includes('/models') && !$user?.permissions?.workspace?.models) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/knowledge') &&
				!$user?.permissions?.workspace?.knowledge
			) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/prompts') &&
				!$user?.permissions?.workspace?.prompts
			) {
				goto('/');
			} else if ($page.url.pathname.includes('/tools') && !$user?.permissions?.workspace?.tools) {
				goto('/');
			}
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="sticky top-0 z-10 px-3 py-2 backdrop-blur-xl bg-white/80 dark:bg-gray-900/80 border-b border-gray-100 dark:border-gray-800 drag-region">
			<div class="flex items-center gap-3">
				<div class="md:hidden flex-none">
					<button
						id="sidebar-toggle-button"
						class="p-2 flex items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<MenuLines />
					</button>
				</div>

				<div class="flex-1 overflow-hidden">
					<div
						class="flex gap-1.5 scrollbar-none overflow-x-auto text-sm font-medium bg-gray-50 dark:bg-gray-850 rounded-lg p-1"
					>
						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models}
							<a
								class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes(
									'/workspace/models'
								)
									? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
									: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
								href="/workspace/models"
							>
								{$i18n.t('Models')}
							</a>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
							<a
								class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes(
									'/workspace/knowledge'
								)
									? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
									: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
								href="/workspace/knowledge"
							>
								{$i18n.t('Knowledge')}
							</a>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.prompts}
							<a
								class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes(
									'/workspace/prompts'
								)
									? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
									: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
								href="/workspace/prompts"
							>
								{$i18n.t('Prompts')}
							</a>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools}
							<a
								class="min-w-fit px-4 py-2 rounded-md transition-all {$page.url.pathname.includes('/workspace/tools')
									? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
									: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'}"
								href="/workspace/tools"
							>
								{$i18n.t('Tools')}
							</a>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class="flex-1 px-5 py-4 overflow-y-auto" id="workspace-container">
			<slot />
		</div>
	</div>
{/if}