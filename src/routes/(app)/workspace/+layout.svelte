<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		settings,
		config,
		models,
		knowledge,
		tools
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext<any>('i18n');

	let loaded = false;
	$: workspaceBackgroundUrl =
		$settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url;

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
			} else if ($page.url.pathname.includes('/skills') && !$user?.permissions?.workspace?.skills) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/targets') &&
				!$user?.permissions?.workspace?.targets
			) {
				goto('/');
			}
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full overflow-hidden text-gray-700 dark:text-gray-100 vx-page-bg"
	>
		<div class="absolute inset-0 z-0 pointer-events-none">
			{#if workspaceBackgroundUrl}
				<div
					class="absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({workspaceBackgroundUrl})"
				></div>
				<div
					class="absolute top-0 left-0 w-full h-full bg-gradient-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90"
				></div>
			{/if}
		</div>

		<nav class="px-2.5 pt-2 sticky top-0 z-20 drag-region select-none">
			<div
				class="rounded-2xl bg-white/70 dark:bg-gray-900/70 backdrop-blur-md border border-gray-100/70 dark:border-gray-850/50 px-2 py-1.5"
			>
				<div class="flex items-center gap-1">
					{#if $mobile}
						<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
							<Tooltip
								content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
								interactive={true}
							>
								<button
									id="sidebar-toggle-button"
									class="cursor-pointer flex rounded-xl hover:bg-gray-100/80 dark:hover:bg-gray-850/80 transition"
									aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
									on:click={() => {
										showSidebar.set(!$showSidebar);
									}}
								>
									<div class=" self-center p-1.5">
										<Sidebar />
									</div>
								</button>
							</Tooltip>
						</div>
					{/if}

					<div class="min-w-0">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-gray-100/60 dark:bg-gray-850/50 p-1 touch-auto pointer-events-auto"
						>
							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models}
								<a
									draggable="false"
									aria-current={$page.url.pathname.includes('/workspace/models') ? 'page' : null}
									class="min-w-fit px-3 py-1.5 rounded-full {$page.url.pathname.includes(
										'/workspace/models'
									)
										? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-xs'
										: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-800/70'} transition select-none"
									href="/workspace/models">{$i18n.t('Models')}</a
								>
							{/if}

							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
								<a
									draggable="false"
									aria-current={$page.url.pathname.includes('/workspace/knowledge') ? 'page' : null}
									class="min-w-fit px-3 py-1.5 rounded-full {$page.url.pathname.includes(
										'/workspace/knowledge'
									)
										? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-xs'
										: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-800/70'} transition select-none"
									href="/workspace/knowledge"
								>
									{$i18n.t('Knowledge')}
								</a>
							{/if}

							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.prompts}
								<a
									draggable="false"
									aria-current={$page.url.pathname.includes('/workspace/prompts') ? 'page' : null}
									class="min-w-fit px-3 py-1.5 rounded-full {$page.url.pathname.includes(
										'/workspace/prompts'
									)
										? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-xs'
										: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-800/70'} transition select-none"
									href="/workspace/prompts">{$i18n.t('Prompts')}</a
								>
							{/if}

							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.skills}
								<a
									draggable="false"
									aria-current={$page.url.pathname.includes('/workspace/skills') ? 'page' : null}
									class="min-w-fit px-3 py-1.5 rounded-full {$page.url.pathname.includes(
										'/workspace/skills'
									)
										? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-xs'
										: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-800/70'} transition select-none"
									href="/workspace/skills"
								>
									{$i18n.t('Skills')}
								</a>
							{/if}

							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools}
								<a
									draggable="false"
									aria-current={$page.url.pathname.includes('/workspace/tools') ? 'page' : null}
									class="min-w-fit px-3 py-1.5 rounded-full {$page.url.pathname.includes(
										'/workspace/tools'
									)
										? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-xs'
										: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-800/70'} transition select-none"
									href="/workspace/tools"
								>
									{$i18n.t('Tools')}
								</a>
							{/if}

							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.targets}
								<a
									draggable="false"
									aria-current={$page.url.pathname.includes('/workspace/targets') ? 'page' : null}
									class="min-w-fit px-3 py-1.5 rounded-full {$page.url.pathname.includes(
										'/workspace/targets'
									)
										? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-xs'
										: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white/70 dark:hover:bg-gray-800/70'} transition select-none"
									href="/workspace/targets"
								>
									{$i18n.t('Targets')}
								</a>
							{/if}
						</div>
					</div>

					<!-- <div class="flex items-center text-xl font-medium">{$i18n.t('Workspace')}</div> -->
				</div>
			</div>
		</nav>

		<div
			class="relative z-10 pb-2 px-3 md:px-[18px] flex-1 max-h-full overflow-y-auto"
			id="workspace-container"
		>
			<div class="mx-auto w-full max-w-[120rem]">
				<slot />
			</div>
		</div>
	</div>
{/if}
